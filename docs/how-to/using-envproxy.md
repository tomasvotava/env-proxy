# Read environment variables with `EnvProxy`

`EnvProxy` exposes seven typed getters. Each accepts a key, an optional
default, and returns a value converted to the target type. If the key is
missing and no default is given, `EnvKeyMissingError` is raised
([Exceptions reference](../reference/exceptions.md)).

```python
from env_proxy import EnvProxy

proxy = EnvProxy(prefix="MYAPP")
```

The `prefix` (plus the `uppercase` and `underscored` toggles) controls
how key names are transformed into env-var names — see
[Key transformations](../reference/key-transformations.md).

## `get_any`

Retrieve the raw `str` value, untouched.

```python
# export MYAPP_VAR="value"
value = proxy.get_any("var")  # "value"
```

## `get_bool`

Case-insensitive parsing of the strings:

| Truthy  | Falsy    |
|---------|----------|
| `yes`   | `no`     |
| `true`  | `false`  |
| `1`     | `0`      |
| `on`    | `off`    |
| `enable` / `enabled` | `disable` / `disabled` |
| `allow` | `disallow` / `deny` |

```python
# export MYAPP_ENABLED="true"
value = proxy.get_bool("enabled")  # True
```

Any other value raises `EnvValueError`.

## `get_str`

```python
# export MYAPP_NAME="example"
name = proxy.get_str("name")  # "example"
```

## `get_int`

```python
# export MYAPP_COUNT="42"
count = proxy.get_int("count")  # 42
```

## `get_float`

```python
# export MYAPP_RATIO="3.14"
ratio = proxy.get_float("ratio")  # 3.14
```

## `get_list`

Splits on a separator (default `,`) and strips whitespace by default.

```python
# export MYAPP_ITEMS="a,b,c ,d"
items = proxy.get_list("items")                    # ["a", "b", "c", "d"]
items = proxy.get_list("items", separator=";")     # custom separator
items = proxy.get_list("items", strip=False)       # preserve whitespace
```

## `get_json`

Parses the value as JSON via `json.loads`.

```python
# export MYAPP_CONFIG='{"key": "value"}'
config = proxy.get_json("config")  # {"key": "value"}
```

`json.JSONDecodeError` is propagated as-is.

## Defaults

Every getter accepts a default. If the variable is missing, the default is
returned without any type conversion:

```python
port = proxy.get_int("port", default=8080)
hosts = proxy.get_list("hosts", default=["localhost"])
```
