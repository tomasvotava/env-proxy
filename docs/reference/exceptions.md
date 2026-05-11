# Exceptions

`env-proxy` raises four typed exceptions, all subclasses of both
`EnvProxyError` and `ValueError`:

| Exception               | When raised                                                    | Attributes                       |
|-------------------------|----------------------------------------------------------------|----------------------------------|
| `EnvProxyError`         | Base class — never raised directly. Catch this to handle every error from the library in one block. | —                                |
| `EnvKeyMissingError`    | A required env var is absent and no default was given.         | `.key`                            |
| `EnvValueError`         | An env value couldn't be converted to the target type.         | `.key`, `.value`, `.target`. Underlying exception (e.g. from a `convert_using` callable) on `__cause__`. |
| `EnvValidationError`    | Raised by `.validate()`. Aggregates every failing field into one exception. | `.errors` — `dict[str, Exception]` (field name → underlying exception) |

Because every exception is also a `ValueError`, a single
`except ValueError:` block catches them all alongside other `ValueError`
sources in your code.

## Example

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

See [Handle errors](../how-to/handle-errors.md) for end-to-end patterns
and [the API reference](api/exceptions.md) for the full class definitions.
