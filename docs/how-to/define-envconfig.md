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
