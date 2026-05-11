# EnvProxy

`EnvProxy` is a Python package that provides a convenient proxy for accessing environment variables with type hints,
type conversion, and customizable options for key formatting. It also includes `EnvConfig`, which lets you define
configuration classes that map directly to environment variables. With `EnvConfig`, you can declaratively
describe your environment-based configuration, including defaults, type hints,
and optional sample `.env` file generation.

## Installation

To install `EnvProxy`, use standard package management tools for Python:

```bash
# Using pip
pip install env-proxy

# Using poetry
poetry add env-proxy
```

## Usage

### Basic Usage with `EnvProxy`

Start by creating an `EnvProxy` instance with optional configuration for environment variable key transformations:

```python
from env_proxy import EnvProxy

proxy = EnvProxy(prefix="MYAPP")
```

The prefix option adds a prefix to all keys, allowing you to group related variables under a common namespace.
For example, with `prefix="MYAPP"`, `proxy.get_any("var")` will look for the environment variable `MYAPP_VAR`.
See the [Configuration Options for EnvProxy](#configuration-options-for-envproxy) section for more options.

### Retrieving Environment Variables

Each method returns the value of an environment variable, converting it to the specified type.
If the variable is missing, it either raises an error or returns the provided default.

#### Methods

`get_any`

Retrieve the raw value of a variable as `Any`. If the key does not exist, `ValueError` is raised
unless a default is provided.

```python
# export MYAPP_VAR="value"

value = proxy.get_any("var")  # returns "value"
```

`get_bool`

Retrieve a boolean variable. The following values are considered truthy (case-insensitive):

> yes, true, 1, on, enable, enabled, allow

 Similarly, common falsy values are handled:

> no, false, 0, off, disable, disabled, disallow, deny

```python
# export MYAPP_ENABLED="true"

value = proxy.get_bool("enabled")  # returns True
```

`get_str`

Retrieve a string variable.

```python
# export MYAPP_NAME="example"

name = proxy.get_str("name")  # returns "example"
```

`get_int`

Retrieve an integer variable.

```python
# export MYAPP_COUNT="42"

count = proxy.get_int("count")  # returns 42
```

`get_float`

Retrieve a floating-point variable.

```python
# export MYAPP_RATIO="3.14"

ratio = proxy.get_float("ratio")  # returns 3.14
```

`get_list`

Retrieve a list of strings by splitting the variable’s value based on a separator (default is `,`).

```python
# export MYAPP_ITEMS="a,b,c ,d"

items = proxy.get_list("items")  # returns ["a", "b", "c", "d"]
```

`get_json`

Parse a JSON string from the environment.

```python
# export MYAPP_CONFIG='{"key": "value"}'

config = proxy.get_json("config")  # returns {"key": "value"}
```

### EnvConfig – Declarative Configuration with Fields

The new `EnvConfig` class allows you to define environment-based configuration with type hints, descriptions,
and defaults. It automatically connects fields to environment variables using a declarative approach, and can
even generate a sample `.env` file for easy setup.

#### Defining Configuration Classes with `EnvConfig`

Define your configuration by subclassing `EnvConfig` and using `Field` factory to describe each variable.
The `Field` function supports attributes like `description`, `default`, and `type_hint`
(see [Field Options](#field-options)).

```python
from env_proxy import EnvConfig, Field, EnvProxy

class MyConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="MYAPP")  # common prefix for all fields
    debug: bool = Field(description="Enable debug mode", default=False)
    database_url: str = Field(description="Database connection URL")
    max_connections: int = Field(description="Maximum DB connections", default=10)
    cache_backends: list[str] = Field(description="Cache backends", type_hint="list")
```

#### Accessing Config Values

Once defined, `MyConfig` provides easy access to each environment variable with the specified type conversions.

```python
config = MyConfig()

# Access configuration values

debug = config.debug  # Looks for MYAPP_DEBUG in the environment
database_url = config.database_url  # Raises ValueError if not found
```

#### Overriding Values per Instance

`EnvConfig` accepts keyword arguments to override individual fields on a per-instance basis.
Overrides take precedence over the environment, letting you layer the env-derived config with
values from any other source — a config file, CLI arguments, programmatic wiring, fixtures —
without touching `os.environ`.

```python
class AppConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="APP")
    timeout: int = Field(default=30)
    services: list[str] = Field(default=[])

# Layer env with values loaded from a config file:
file_config = load_yaml("app.yaml")  # {"timeout": 5, "services": ["redis", "rabbitmq"]}
cfg = AppConfig(**file_config)

assert cfg.timeout == 5
assert cfg.services == ["redis", "rabbitmq"]
```

Semantics:

- Keys are **Python field names** (not env-var keys), regardless of any `alias` or `env_prefix`.
- Values are **used as-is** — no string parsing or type conversion. Pass real `int`, `list`, `dict`, etc.
- Overrides **shadow the environment** for reads on that instance only; other instances and direct
  `os.environ` access are unaffected.
- Unknown override keys raise `ValueError`, listing the valid field names — typo-proof.
- Fields with `allow_set=False` can be initialized via override but cannot be reassigned afterwards;
  the `allow_set` contract is unchanged.
- For fields with `allow_set=True`, assignment after construction updates both the override entry
  *and* `os.environ` (preserving the existing side-effect contract).

Overrides are statically type-checked. `EnvConfig` is decorated with PEP 681's `dataclass_transform`,
so mypy and Pyright/Pylance synthesize a typed `__init__` from each subclass's annotated fields:
typos (`AppConfig(timout=5)`) and wrong value types (`AppConfig(timeout="bad")`) are flagged at
type-check time, and IDEs autocomplete field names with their declared types.

#### Validating and Freezing Configuration

`EnvConfig` resolves each field lazily, on first access. Two methods change
that for production use:

- **`.validate()`** — eagerly resolves every field and raises
  `EnvValidationError` if any field is missing or malformed. All field
  failures are aggregated into one exception; inspect its `.errors`
  mapping (field name → underlying exception) to see them all.
- **`.freeze()`** — resolves every field once and caches the result on
  the instance. Reads become a single dict lookup (~200ns versus ~1.3µs
  for a fresh env lookup). Assignment is disallowed after freezing —
  even for fields with `allow_set=True`, which are listed in a
  `UserWarning` at the moment of freezing. Use the `.is_frozen` property
  to check the current state.

The two methods are independent. Call `.validate()` alone if you want
eager checks but still need runtime mutability; combine both at startup
to fail fast and then lock the config for the rest of the process:

```python
config = MyConfig()
config.validate()
config.freeze()

assert config.is_frozen
```

#### Exception Types

`env_proxy` raises four typed exceptions, all subclasses of both
`EnvProxyError` and `ValueError`:

- `EnvProxyError` — base class. Catch this to handle every error raised
  by the library in one block.
- `EnvKeyMissingError` — a required env var is absent and no default
  was given. The env var name is on `.key`.
- `EnvValueError` — an env value couldn't be converted to the target
  type. Inspect `.key`, `.value`, and `.target` for the offending env
  var, its raw string, and the type label. The underlying exception
  (e.g. from a `convert_using` callable) is available on `__cause__`.
- `EnvValidationError` — raised by `.validate()`. The `.errors`
  mapping holds the underlying exception for each failing field, keyed
  by Python field name.

Because every exception is also a `ValueError`, a single `except
ValueError:` block catches them all alongside other `ValueError`
sources in your code.

```python
from env_proxy import EnvValidationError

try:
    cfg.validate()
except EnvValidationError as exc:
    for name, error in exc.errors.items():
        log.error("config field %s failed: %s", name, error)
        if error.__cause__ is not None:
            log.debug("caused by: %r", error.__cause__)
    raise
```

#### Generating a Sample `.env` File

You can export a sample `.env` file from your `EnvConfig` class, which documents all fields with their
descriptions, types, and default values.

```python
MyConfig.export_env("sample.env", include_defaults=True)
```

This would produce a file like:

```plaintext
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

#### Field Options

Each Field can be customized with the following options:

- `alias`: Custom name in the environment. Defaults to the field name.
- `description`: Description of the variable.
- `default`: Default value if the variable is missing. If UNSET, the variable is required.
- `type_hint`: Specify the type explicitly (e.g., json for JSON objects).
- `env_prefix`: Override the env_prefix set on the EnvConfig class for a specific field.
- `allow_set`: Allow modification of the environment variable value at runtime.
- `convert_using`: Callable that converts the raw `str` env value into the field's
  target type (see [Custom converters](#custom-converters)).
- `type_name`: Override the type label used in exported `.env` files and in
  `EnvValueError` messages. Useful for lambdas, `functools.partial`, or other
  callables that don't have a meaningful `__name__`.

#### Field Type Hints

The following type_hint values are supported:

- `any`
- `bool`
- `float`
- `int`
- `str`
- `list`
- `json`

Example of using `type_hint`:

```python
class AdvancedConfig(EnvConfig):
    settings: dict[str, Any] = Field(type_hint="json", description="Complex JSON settings")
```

#### Custom converters

When the built-in type set isn't enough — most commonly for enums or types like
`Decimal` / `pathlib.Path` — pass a callable as `convert_using`. The callable
receives the raw `str` from the environment and must return the typed value:

```python
import enum
from decimal import Decimal
from env_proxy import EnvConfig, Field

class Level(enum.Enum):
    LOW = "low"
    HIGH = "high"

class AppConfig(EnvConfig):
    level: Level = Field(convert_using=Level, default=Level.LOW)
    amount: Decimal = Field(convert_using=Decimal)
```

Behavior:

- The converter is called **only when the env value is present**. If the env
  var is missing and a `default` is provided, the default is returned as-is —
  supply a default of the target type (e.g. `default=Level.LOW`, not
  `default="low"`).
- If the converter raises, the exception is wrapped in `EnvValueError`. The
  original exception is preserved on `__cause__`.
- Passing both `convert_using` and `type_hint` emits a `UserWarning` and
  ignores `type_hint`.
- The annotation on the field is informational (used by static type
  checkers); `convert_using` is the source of truth for runtime conversion.

For the type label shown in exported `.env` files and `EnvValueError`
messages, the resolution order is:

1. Explicit `type_name=` if given.
2. The field annotation, if it's a simple type (`int`, `Level`, …).
3. `convert_using.__name__`, unless it would be `"<lambda>"`.
4. Fallback: `"custom"`.

So `field: Level = Field(convert_using=Level)` renders as `(Level)` in
`.env` exports, and `field = Field(convert_using=lambda s: ..., type_name="Doubled")`
renders as `(Doubled)`.

### Example Usage with `EnvConfig`

```python
import os
from env_proxy import EnvConfig, Field

# Set environment variables
os.environ["MYAPP_DEBUG"] = "true"
os.environ["MYAPP_DATABASE_URL"] = "sqlite:///data.db"
os.environ["MYAPP_CACHE_BACKENDS"] = "redis,memcached"

class MyConfig(EnvConfig):
    env_prefix: str = "MYAPP"
    debug: bool = Field(description="Enable debug mode", default=False)
    database_url: str = Field(description="Database connection URL")
    cache_backends: list[str] = Field(description="Cache backends", type_hint="list")

config = MyConfig()

# Access configuration values

print(config.debug)  # True
print(config.database_url)  # "sqlite:///data.db"
print(config.cache_backends)  # ["redis", "memcached"]

# Export a sample .env file

MyConfig.export_env("sample.env", include_defaults=True)
```

## Configuration Options for `EnvProxy`

You can control how keys are transformed when retrieving variables in `EnvProxy`:

- `prefix`: Adds a prefix to all keys.
- `uppercase`: Converts keys to uppercase.
- `underscored`: Replaces hyphens with underscores.

```python
proxy = EnvProxy(prefix="myapp", uppercase=True, underscored=False)
proxy.get_any("var")  # Looks for "MYAPP_VAR"
```

### Tuning the Key Cache

`env_proxy` caches the prefixed env-var key computation in an `lru_cache`
sized at **1024** entries by default. For apps with many fields, or many
`EnvProxy` instances with different prefixes / case rules, increase the
cache via the `ENV_PROXY_KEY_CACHE_SIZE` environment variable:

```bash
ENV_PROXY_KEY_CACHE_SIZE=4096 python -m myapp
```

The value is resolved **at import time** — setting or changing it after
`env_proxy` is imported has no effect. Invalid values (non-integer) fall
back to the default and emit a warning.

## Error Handling

A missing required env var raises `EnvKeyMissingError`. An env var whose
value can't be cast to the target type raises `EnvValueError`. Both
inherit from `ValueError`, so a single `except ValueError:` covers both.
See [Exception Types](#exception-types) for the full hierarchy and the
attributes each exception carries.

```python
from env_proxy import EnvProxy, EnvKeyMissingError, EnvValueError

proxy = EnvProxy()
try:
    missing_value = proxy.get_int("missing_key")
except EnvKeyMissingError as e:
    print(e.key)  # 'missing_key'

try:
    bad_value = proxy.get_int("PORT")  # if PORT="not-a-number"
except EnvValueError as e:
    print(e.target)  # 'int'
    print(e.value)   # 'not-a-number'
```

## License

`EnvProxy` is open-source and distributed under the MIT License. See [LICENSE.md](./LICENSE.md) for more information.
