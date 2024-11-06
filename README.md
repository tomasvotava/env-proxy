# EnvProxy

EnvProxy is a Python package that provides a convenient proxy for accessing environment variables with type
hints, type conversion, and customizable options for key formatting. It simplifies retrieving environment
variables with support for type-specific conversions, including `bool`, `int`, `float`, `list`, and JSON objects.

## Installation

To install `EnvProxy`, use standard package management tools for Python:

```bash
# Using pip
pip install env-proxy

# Using poetry
poetry add env-proxy
```

## Usage

### Basic Usage

Start by creating an `EnvProxy` instance with optional configuration for environment variable key transformations:

```python
from env_proxy import EnvProxy

proxy = EnvProxy(prefix="MYAPP")
```

The `prefix` option adds a prefix to all keys, allowing you to group related variables under a common namespace.
For example, with `prefix="MYAPP"`, `proxy.get_any("var")` will look for the environment variable `MYAPP_VAR`.
See the [Configuration Options](#configuration-options) section for more options.

### Retrieving Environment Variables

Each method returns the value of an environment variable, converting it to the specified type.
If the variable is missing, it either raises an error or returns the provided default.

#### Methods

`get_any`

Retrieve the raw value of a variable as `Any`. If the key does not exist,
`ValueError` is raised unless a default is provided.

```python
# export MYAPP_VAR="value"
value = proxy.get_any("var")  # returns "value"

# With a default
value = proxy.get_any("missing_var", "default_value")  # returns "default_value"
```

`get_bool`

Retrieve a boolean variable. The following values are considered truthy:

> `yes`, `true`, `1`, `on`, `enable`, `enabled`, `allow`

 Similarly, common falsy values are handled:

> `no`, `false`, `0`, `off`, `disable`, `disabled`, `disallow`, `deny`

```python
# export MYAPP_ENABLED="true"
value = proxy.get_bool("enabled")  # returns True
```

Values are case-insensitive, so `True`, `TRUE`, and `true` are all valid.

`get_str`

Retrieve a string variable, returning the value directly as a string.

```python
# export MYAPP_NAME="example"
name = proxy.get_str("name")  # returns "example"
```

`get_int`

Retrieve an integer variable, converting the value to an `int`.

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

Retrieve a list of strings by splitting the variable’s value based on a separator
(default is `,`). Leading and trailing whitespace is stripped by default.

```python
# export MYAPP_ITEMS="a,b,c ,d"
items = proxy.get_list("items")  # returns ["a", "b", "c", "d"]
```

You can specify a custom separator or choose to keep whitespace:

```python
# export MYAPP_ITEMS="a;b;c ;d"
items = proxy.get_list("items", separator=";", strip=False) # returns ["a", "b", "c ", "d"]
```

`get_json`

Parse a JSON string from the environment and return it as a Python object.
This method supports complex JSON structures.

```python
# export MYAPP_CONFIG='{"key": "value"}'
config = proxy.get_json("config")  # returns {"key": "value"}
```

### Configuration Options

You can control how keys are transformed when retrieving variables:

- `prefix`: Adds a prefix to all keys. For example, with `prefix="MYAPP"`,
  `proxy.get_any("var")` will look for `MYAPP_VAR`.
- `uppercase`: Converts keys to uppercase before lookup.
- `underscored`: Replaces hyphens with underscores.

```python
proxy = EnvProxy(prefix="myapp", uppercase=True, underscored=False)
proxy.get_any("var")  # Looks for "MYAPP_VAR"
proxy.get_any("my-var")  # Looks for "MYAPP_MY-VAR"
```

### Error Handling

If a variable is not found, and no default value is provided, a `ValueError` will be raised. Each method
also raises a `ValueError` for invalid conversions (e.g., non-numeric values for `get_int` or invalid JSON).

```python
try:
    missing_value = proxy.get_int("missing_key")
except ValueError as e:
    print(e)  # Output: No value found for key 'missing_key' in the environment.
```

## Examples

```python
import os
from env_proxy import EnvProxy

# Set some environment variables for testing
os.environ["MYAPP_DEBUG"] = "true"
os.environ["MYAPP_MAX_CONNECTIONS"] = "5"
os.environ["MYAPP_TIMEOUT"] = "30.5"
os.environ["MYAPP_SERVICES"] = "api,web,worker"
os.environ["MYAPP_CONFIG"] = '{"api_key": "12345", "debug": true}'

proxy = EnvProxy(prefix="MYAPP")

# Get a boolean
debug = proxy.get_bool("debug")  # True

# Get an integer
max_connections = proxy.get_int("max_connections")  # 5

# Get a float
timeout = proxy.get_float("timeout")  # 30.5

# Get a list
services = proxy.get_list("services")  # ["api", "web", "worker"]

# Get JSON
config = proxy.get_json("config")  # {"api_key": "12345", "debug": True}
```

## License

`EnvProxy` is open-source and distributed under the MIT License.
See [LICENSE.md](LICENSE.md) for more information.
