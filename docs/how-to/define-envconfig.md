# Define a configuration class with `EnvConfig`

`EnvConfig` lets you describe environment-based configuration declaratively
— each field carries its type, default, description, and any conversion
hints in one place.

```python
from env_proxy import EnvConfig, EnvProxy, Field

class MyConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="MYAPP")

    debug: bool = Field(description="Enable debug mode", default=False)
    database_url: str = Field(description="Database connection URL")
    max_connections: int = Field(description="Maximum DB connections", default=10)
    cache_backends: list[str] = Field(description="Cache backends", type_hint="list")
```

## Configure the proxy

Two equivalent ways to attach an `EnvProxy` to a config class:

```python
# Option A — class attribute (most flexible; full EnvProxy control)
class MyConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="MYAPP", uppercase=True, underscored=True)
    ...

# Option B — shorthand prefix
class MyConfig(EnvConfig):
    env_prefix: str = "MYAPP"
    ...
```

Per-field overrides are also available: pass `env_prefix=` to a specific
`Field()` to escape the class-level prefix.

## Access values

Instantiate the class and read attributes:

```python
config = MyConfig()
print(config.debug)            # looks up MYAPP_DEBUG
print(config.database_url)     # raises EnvKeyMissingError if unset
```

Fields are resolved **on first access**, not at construction. That keeps
construction cheap and avoids touching env vars you don't end up reading
— but it also means malformed env values surface lazily. To force eager
resolution at startup, see [Validate and freeze](validate-and-freeze.md).

## Required vs optional fields

```python
class MyConfig(EnvConfig):
    env_prefix: str = "MYAPP"

    # Required — no `default`. Missing env raises EnvKeyMissingError.
    api_token: str = Field()

    # Optional — `default` provided.
    timeout: int = Field(default=30)

    # Optional — `default=None` for an explicit "missing means None".
    callback_url: str | None = Field(default=None)
```

### Per-instance defaults with `default_factory`

When you want a fresh value for each instance — a mutable container, a
generated identifier, a timestamp captured at startup — pass a zero-arg
callable as `default_factory`:

```python
import uuid
from datetime import datetime

from env_proxy import EnvConfig, Field

class MyConfig(EnvConfig):
    env_prefix: str = "MYAPP"

    tags: list[str] = Field(default_factory=list)
    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    started_at: datetime = Field(
        convert_using=datetime.fromisoformat,
        default_factory=datetime.now,
    )
```

**Always use `default_factory` for mutable defaults.** `Field(default=[])`
shares one list across every instance of the class; mutating
`cfg.tags` mutates the next `MyConfig()`'s `tags` too. This is the same
trap `dataclasses` warns about, and the fix is the same:
`Field(default_factory=list)`.

The factory runs **once at `MyConfig()` construction time**, mirroring
`dataclasses.field(default_factory=...)`. The result is stored on the
instance and used whenever the env var is missing, so `started_at`
captures the moment the config was built — not the moment you first read
the attribute. Two separate `MyConfig()` instances each get their own
factory call.

`default_factory` is mutually exclusive with `default`; passing both
raises `EnvConfigError` at class-definition time. A constructor override
(`MyConfig(tags=[...])`) skips the factory entirely.

#### Choosing between `default` and `default_factory`

| Field shape                              | Use                |
|------------------------------------------|--------------------|
| Immutable scalar (`int`, `str`, `bool`)  | `default=`         |
| Explicit `None` fallback                 | `default=None`     |
| Mutable container (`list`, `dict`, `set`) | `default_factory=` |
| Per-instance identity (`uuid`, `now`)    | `default_factory=` |
| Computed from runtime state              | `default_factory=` |

## Customizing field names

By default the env-var name is derived from the field name (uppercased,
prefixed). Use `alias` to override on a per-field basis:

```python
class MyConfig(EnvConfig):
    env_prefix: str = "MYAPP"
    # Reads MYAPP_LEGACY_NAME instead of MYAPP_DATABASE_URL:
    database_url: str = Field(alias="legacy_name")
```

See [Field options reference](../reference/field-options.md) for the full
list of `Field()` parameters.
