# Environment variables read by the library

`env-proxy` itself reads a small number of environment variables at
import time to configure its internals.

| Env var                       | Default | Effect                                                                 |
|-------------------------------|---------|------------------------------------------------------------------------|
| `ENV_PROXY_KEY_CACHE_SIZE`    | `1024`  | `maxsize` of the `lru_cache` used to memoise prefixed env-var keys. Resolved once at import time; invalid values fall back to the default with a warning. |

See [Tune the key cache](../how-to/tune-key-cache.md) for guidance on
when to change this.

!!! warning "Resolved at import time"
    These variables are read when `env_proxy` is first imported. Setting
    them later has no effect.
