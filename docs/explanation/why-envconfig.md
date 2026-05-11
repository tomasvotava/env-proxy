# Why `EnvConfig`?

The simplest way to read configuration from the environment in Python is
also the most error-prone:

```python
import os

DEBUG = os.environ["MYAPP_DEBUG"].lower() == "true"
PORT = int(os.environ.get("MYAPP_PORT", "8080"))
HOSTS = os.environ.get("MYAPP_HOSTS", "localhost").split(",")
```

That style spreads parsing, defaulting, and naming conventions across
every callsite. There's no single inventory of "what env vars this
service reads", no central description of what each one means, no way to
fail fast at startup on bad values, and no help from a type-checker.

`EnvConfig` consolidates all of that into a single declarative class:

```python
class MyConfig(EnvConfig):
    env_prefix: str = "MYAPP"
    debug: bool = Field(description="Enable debug mode", default=False)
    port: int = Field(description="HTTP port", default=8080)
    hosts: list[str] = Field(description="Comma-separated hosts", default=["localhost"])
```

The class is the inventory, the parser, the documentation, and the
type-checker's source of truth — all at once. From it you get:

- **Typed access**: `config.port` is `int`, not `str`.
- **A self-documenting schema**: descriptions live next to fields and
  are visible to both reviewers and `.env` export tooling.
- **Eager validation**: `.validate()` raises a single aggregated error at
  startup instead of crashing in production on first access.
- **Test ergonomics**: per-instance overrides
  ([Override values](../how-to/override-values.md)) replace ad-hoc
  monkey-patching of `os.environ`.
- **Performance when it matters**: `.freeze()`
  ([Lazy vs frozen](lazy-vs-frozen.md)) turns reads into a single dict
  lookup once the config has stabilised.

`EnvProxy` is still useful for one-off reads or scripts where a full
config class would be overkill — but for anything that lives in a
long-running service, `EnvConfig` is the entry point.
