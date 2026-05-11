# Generate a sample `.env` file

`EnvConfig` can export a documented `.env` template directly from a class
declaration. It lists every field with its description, declared type,
and (optionally) its default value.

```python
MyConfig.export_env("sample.env", include_defaults=True)
```

Given:

```python
class MyConfig(EnvConfig):
    env_prefix: str = "MYAPP"
    debug: bool = Field(description="Enable debug mode", default=False)
    database_url: str = Field(description="Database connection URL")
    max_connections: int = Field(description="Maximum DB connections", default=10)
    cache_backends: list[str] = Field(description="Cache backends", type_hint="list")
```

…the output is:

```dotenv
# debug (bool) [optional]
# Enable debug mode
MYAPP_DEBUG=False

# database_url (str) [required]
# Database connection URL
MYAPP_DATABASE_URL=

# max_connections (int) [optional]
# Maximum DB connections
MYAPP_MAX_CONNECTIONS=10

# cache_backends (list) [required]
# Cache backends
MYAPP_CACHE_BACKENDS=
```

## Options

- `include_defaults=True` (default) — write the default value to the
  right of `=` for optional fields. With `False`, optional fields render
  with an empty value, just like required ones.
- The file is written verbatim; existing contents are overwritten.

## Custom type labels

For fields that use [custom converters](custom-converters.md), the type
label is derived as documented there. Pass `type_name=` to `Field()` to
force a specific label:

```python
amount: Decimal = Field(
    convert_using=Decimal,
    type_name="Decimal",
    description="Total in USD",
)
```

renders as:

```dotenv
# amount (Decimal) [required]
# Total in USD
MYAPP_AMOUNT=
```
