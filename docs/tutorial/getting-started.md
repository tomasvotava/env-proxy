# Getting started

This tutorial walks you through installing `env-proxy`, reading a single
environment variable, and then defining a full typed configuration class.
By the end you'll have a working `EnvConfig` and a sample `.env` file.

## Install

```bash
# Using pip
pip install env-proxy

# Using Poetry
poetry add env-proxy
```

`env-proxy` supports Python 3.10+. The package has no required runtime
dependencies on Python 3.11 and above.

## Step 1 — read a single env var

Create an `EnvProxy` instance. The optional `prefix` adds a common
namespace to every lookup, so you don't have to repeat it.

```python
import os
from env_proxy import EnvProxy

os.environ["MYAPP_NAME"] = "demo"
os.environ["MYAPP_PORT"] = "8080"

proxy = EnvProxy(prefix="MYAPP")

name = proxy.get_str("name")    # reads MYAPP_NAME → "demo"
port = proxy.get_int("port")    # reads MYAPP_PORT → 8080
```

`get_str` and `get_int` are two of seven typed getters. See
[Reading environment variables](../how-to/using-envproxy.md) for the full
list (`get_bool`, `get_float`, `get_list`, `get_json`, `get_any`).

## Step 2 — declare a config class

For more than a handful of variables, prefer `EnvConfig`. You describe
each field once — type, default, description — and `env-proxy` wires it to
the environment for you.

```python
from env_proxy import EnvConfig, EnvProxy, Field

class MyConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="MYAPP")

    debug: bool = Field(description="Enable debug mode", default=False)
    database_url: str = Field(description="Database connection URL")
    max_connections: int = Field(description="Maximum DB connections", default=10)
    cache_backends: list[str] = Field(description="Cache backends", type_hint="list")
```

A few things to notice:

- `env_proxy` (the class attribute) holds an `EnvProxy` instance — its
  `prefix` is applied to every field. You can also use `env_prefix: str =
  "MYAPP"` as a shorthand.
- The annotation (`bool`, `str`, `int`, `list[str]`) drives type
  conversion automatically; you only need `type_hint` when the annotation
  is ambiguous (see [Type hints reference](../reference/type-hints.md)).
- A field without a `default` is **required** — missing it raises
  `EnvKeyMissingError` at access time.

## Step 3 — use the config

```python
import os
os.environ["MYAPP_DATABASE_URL"] = "sqlite:///data.db"
os.environ["MYAPP_CACHE_BACKENDS"] = "redis,memcached"

config = MyConfig()

print(config.debug)              # False (default; MYAPP_DEBUG not set)
print(config.database_url)       # "sqlite:///data.db"
print(config.max_connections)    # 10 (default)
print(config.cache_backends)     # ["redis", "memcached"]
```

Fields are resolved **lazily** — the environment is read the first time
each attribute is accessed. To pay that cost upfront and fail fast on
missing/malformed values, call `.validate()` at startup:

```python
config = MyConfig()
config.validate()   # raises EnvValidationError if anything is wrong
```

See [Validating and freezing](../how-to/validate-and-freeze.md) for the
full pattern (including `.freeze()` to lock the config for the rest of
the process and speed up reads).

## Step 4 — generate a sample `.env`

`env-proxy` can export a documented sample `.env` from the class:

```python
MyConfig.export_env("sample.env", include_defaults=True)
```

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

That's the full happy path. From here, the
[how-to guides](../how-to/using-envproxy.md) cover individual tasks, and
the [explanation pages](../explanation/why-envconfig.md) cover the design.
