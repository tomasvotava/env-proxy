# Tune the key cache

`env-proxy` caches the prefixed env-var key computation (e.g. turning
`"port"` into `"MYAPP_PORT"`) in an `lru_cache` sized at **1024** entries
by default.

For apps with hundreds of fields, or many `EnvProxy` instances with
different prefixes / case rules, increase the cache via the
`ENV_PROXY_KEY_CACHE_SIZE` environment variable:

```bash
ENV_PROXY_KEY_CACHE_SIZE=4096 python -m myapp
```

## Caveats

- The value is resolved **at import time** — setting or changing it after
  `env_proxy` is imported has no effect.
- Invalid values (non-integer) fall back to the default and emit a
  warning.

## When to change the default

The default is generous for most applications. Consider raising it only
if you observe that hot-path attribute reads on a frozen `EnvConfig` are
unexpectedly slow — and even then, prefer `.freeze()`
([Validate and freeze](validate-and-freeze.md)) over a larger key cache.
Freezing eliminates the lookup entirely.
