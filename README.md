# EnvProxy

`EnvProxy` is a Python package that provides a convenient proxy for accessing environment variables with type hints,
type conversion, and customizable options for key formatting. It alos includes `EnvConfig`, which lets you define
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

## Error Handling

If a variable is not found, and no default value is provided, a `ValueError` will be raised.
Each method also raises a `ValueError` for invalid conversions.

```python
try:
    missing_value = proxy.get_int("missing_key")
except ValueError as e:
    print(e)  # Output: No value found for key 'missing_key' in the environment.
```

## License

`EnvProxy` is open-source and distributed under the MIT License. See [LICENSE.md](./LICENSE.md) for more information.
