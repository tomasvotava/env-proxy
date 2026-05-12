# env-proxy

[![PyPI version](https://img.shields.io/pypi/v/env-proxy.svg?logo=pypi&logoColor=white)](https://pypi.org/project/env-proxy/)
[![Python versions](https://img.shields.io/pypi/pyversions/env-proxy.svg?logo=python&logoColor=white)](https://pypi.org/project/env-proxy/)
[![License](https://img.shields.io/pypi/l/env-proxy.svg)](https://opensource.org/licenses/MIT)
[![CI](https://img.shields.io/github/actions/workflow/status/tomasvotava/env-proxy/lint.yml?branch=master&label=CI&logo=github)](https://github.com/tomasvotava/env-proxy/actions)
[![Coverage](https://img.shields.io/codecov/c/github/tomasvotava/env-proxy?logo=codecov&logoColor=white)](https://codecov.io/gh/tomasvotava/env-proxy)

`env-proxy` reads environment variables with type hints, type conversion,
and a declarative configuration layer. Define your env-driven config once
as a typed class, then access fields like any other attribute — with
eager validation, optional freezing for performance, and sample `.env`
generation included.

## Install

```bash
# Using pip
pip install env-proxy

# Using Poetry
poetry add env-proxy
```

Supports Python 3.10+.

## Quickstart

```python
import os
from env_proxy import EnvConfig, Field

os.environ["MYAPP_DEBUG"] = "true"
os.environ["MYAPP_DATABASE_URL"] = "sqlite:///data.db"
os.environ["MYAPP_CACHE_BACKENDS"] = "redis,memcached"

class MyConfig(EnvConfig):
    env_prefix: str = "MYAPP"
    debug: bool = Field(description="Enable debug mode", default=False)
    database_url: str = Field(description="Database connection URL")
    cache_backends: list[str] = Field(description="Cache backends", type_hint="list")

config = MyConfig()
config.validate()   # fail fast on missing/bad env values
config.freeze()     # optional: turn reads into a dict lookup

print(config.debug)              # True
print(config.database_url)       # "sqlite:///data.db"
print(config.cache_backends)     # ["redis", "memcached"]
```

For one-off lookups without a full config class, the lower-level
`EnvProxy` exposes typed getters (`get_str`, `get_int`, `get_bool`,
`get_list`, `get_json`, …):

```python
from env_proxy import EnvProxy

proxy = EnvProxy(prefix="MYAPP")
proxy.get_int("port", default=8080)
```

## Documentation

Full documentation — tutorial, how-to guides, reference, and the
auto-generated API — lives at
**<https://tomasvotava.github.io/env-proxy/>**.

Quick links:

- [Getting started](https://tomasvotava.github.io/env-proxy/tutorial/getting-started/)
- [How-to guides](https://tomasvotava.github.io/env-proxy/how-to/using-envproxy/) — recipes for the common tasks
- [Reference](https://tomasvotava.github.io/env-proxy/reference/field-options/) — Field options, type hints, exceptions
- [API reference](https://tomasvotava.github.io/env-proxy/reference/api/) — auto-generated from docstrings

## Contributing

`make ci` runs every check that CI runs (`ruff format --check`, `ruff
check`, `mypy`, `pytest`). `make docs-serve` previews the docs at
http://127.0.0.1:8000.

## License

`env-proxy` is open-source under the MIT License. See
[LICENSE.md](./LICENSE.md).
