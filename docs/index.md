# env-proxy

`env-proxy` reads environment variables with type hints, type conversion, and a
declarative config layer. Define your environment-driven configuration once
as a typed class, then access fields like any other attribute — with eager
validation, optional freezing, and sample `.env` generation included.

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

print(config.debug)            # True
print(config.database_url)     # "sqlite:///data.db"
print(config.cache_backends)   # ["redis", "memcached"]
```

## Where to go next

The documentation is organised by the [Diátaxis](https://diataxis.fr/) framework:

- **[Tutorial](tutorial/getting-started.md)** — start here if you're new. A
  guided walkthrough from install to your first `EnvConfig`.
- **How-to guides** — task-oriented recipes:
  [reading env vars](how-to/using-envproxy.md) ·
  [defining configs](how-to/define-envconfig.md) ·
  [overriding values](how-to/override-values.md) ·
  [validating & freezing](how-to/validate-and-freeze.md) ·
  [custom converters](how-to/custom-converters.md) ·
  [sample `.env`](how-to/generate-sample-env.md) ·
  [tuning the key cache](how-to/tune-key-cache.md) ·
  [handling errors](how-to/handle-errors.md).
- **Reference** — look-up material:
  [Field options](reference/field-options.md) ·
  [type hints](reference/type-hints.md) ·
  [exceptions](reference/exceptions.md) ·
  [library env vars](reference/env-vars.md) ·
  [key transformations](reference/key-transformations.md) ·
  [auto-generated API](reference/api/index.md).
- **Explanation** — the "why":
  [why EnvConfig?](explanation/why-envconfig.md) ·
  [override semantics](explanation/override-semantics.md) ·
  [lazy vs frozen](explanation/lazy-vs-frozen.md).

## Install

```bash
pip install env-proxy
# or
poetry add env-proxy
```
