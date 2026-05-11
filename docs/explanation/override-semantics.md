# Override semantics

`EnvConfig(**kwargs)` exists to let you layer the env-derived config
with values from any other source — a config file, CLI arguments,
programmatic wiring, test fixtures — without mutating `os.environ`.

A few decisions in the design deserve their own discussion.

## Keys are Python field names, not env-var keys

```python
class AppConfig(EnvConfig):
    env_prefix: str = "APP"
    database_url: str = Field(alias="DB_URL")   # reads APP_DB_URL
    ...

cfg = AppConfig(database_url="sqlite:///x")     # ✓ uses the Python name
cfg = AppConfig(DB_URL="sqlite:///x")           # ✗ ValueError — unknown field
```

The Python field name is the **stable identifier** across the codebase;
the env-var key is a name-mapping concern that may change (different
`alias`, different `env_prefix`). Keying overrides by the field name
keeps callers decoupled from the env-var naming scheme.

This also makes typos catchable by a static type-checker — see
[`dataclass_transform` integration](../how-to/override-values.md#static-type-checking).

## Values are used as-is — no conversion

```python
AppConfig(timeout=5)         # ✓ — int passed through verbatim
AppConfig(timeout="5")       # ✓ — str passed through verbatim (no coercion!)
```

Overrides bypass the env-string parser by design. If you're loading
values from YAML, JSON, TOML, or CLI arguments, those formats already
return typed values; running them through `str(...) → int(...)` round
trips would be lossy and silently mask bugs. The contract is: "trust the
caller; give them what they gave you."

If you genuinely need string parsing, write to `os.environ` instead.

## Overrides shadow the environment for that instance only

```python
import os
os.environ["APP_TIMEOUT"] = "30"

cfg_default = AppConfig()           # reads APP_TIMEOUT → 30
cfg_override = AppConfig(timeout=5) # 5; does NOT modify os.environ

assert cfg_default.timeout == 30
assert cfg_override.timeout == 5
assert os.getenv("APP_TIMEOUT") == "30"  # untouched
```

No cross-instance pollution; no test bleed.

## Unknown keys raise — typo-proof

```python
AppConfig(timout=5)
# ValueError: unknown override 'timout'; valid: timeout, services
```

A silent ignore would be a footgun: a typo'd override would look like it
worked, then the env-derived value would surface in production. Raising
keeps the failure mode loud and local.

## `allow_set` interaction

Fields with `allow_set=False` (the default) can still be **initialised**
via override — overrides are part of construction, not runtime
assignment. What `allow_set=False` blocks is `cfg.field = ...` after
construction; that remains true. Fields with `allow_set=True` keep their
existing side-effect contract: assignment writes to both the override
dict and `os.environ`.
