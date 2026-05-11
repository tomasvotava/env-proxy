# Override config values per instance

`EnvConfig` accepts keyword arguments at construction. Overrides take
precedence over the environment, so you can layer env-derived config with
values from any other source — a YAML file, CLI arguments, programmatic
wiring, test fixtures — without touching `os.environ`.

```python
from env_proxy import EnvConfig, EnvProxy, Field

class AppConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="APP")
    timeout: int = Field(default=30)
    services: list[str] = Field(default=[])

# Layer env with values loaded from a YAML file:
file_config = load_yaml("app.yaml")          # {"timeout": 5, "services": ["redis", "rabbitmq"]}
cfg = AppConfig(**file_config)

assert cfg.timeout == 5
assert cfg.services == ["redis", "rabbitmq"]
```

## Semantics

- Keys are **Python field names** (not env-var keys), regardless of any
  `alias` or `env_prefix`.
- Values are **used as-is** — no string parsing or type conversion. Pass
  real `int`, `list`, `dict`, etc.
- Overrides **shadow the environment** for reads on that instance only;
  other instances and direct `os.environ` access are unaffected.
- Unknown override keys raise `ValueError`, listing the valid field names
  — typo-proof.
- Fields with `allow_set=False` can be initialised via override but
  cannot be reassigned afterwards; the `allow_set` contract is unchanged.
- For fields with `allow_set=True`, assignment after construction
  updates both the override entry **and** `os.environ` (preserving the
  existing side-effect contract).

The rationale behind these choices lives in
[Override semantics](../explanation/override-semantics.md).

## Static type-checking

`EnvConfig` is decorated with PEP 681's `dataclass_transform`, so mypy and
Pyright/Pylance synthesise a typed `__init__` from each subclass's
annotated fields:

```python
AppConfig(timout=5)          # ✗ unknown field — type-check error
AppConfig(timeout="bad")     # ✗ wrong type — type-check error
AppConfig(timeout=5)         # ✓ ok
```

IDEs autocomplete field names with their declared types.

## Use in tests

Overrides are particularly handy in tests — they give you full control
without monkey-patching `os.environ`:

```python
def test_short_timeout_path():
    cfg = AppConfig(timeout=1)
    assert run_with(cfg) == "...short..."
```
