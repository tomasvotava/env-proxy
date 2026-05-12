# Exceptions

`env-proxy` raises `EnvProxyError` and its subclasses. Catch `EnvProxyError`
to handle every error from this library in one block.

## `EnvProxyError` hierarchy

| Exception              | Inherits from                            | When raised                                                                                                                                                  | Attributes                                                                 |
|------------------------|------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| `EnvProxyError`        | `Exception`                              | Base class — never raised directly. Catch this to handle every library error.                                                                                | —                                                                          |
| `EnvKeyMissingError`   | `EnvProxyError`, `ValueError`            | A required env var is absent and no default was given.                                                                                                       | `.key`                                                                     |
| `EnvValueError`        | `EnvProxyError`, `ValueError`            | An env value couldn't be converted to the target type. The underlying exception (e.g. from a `convert_using` callable) is preserved on `__cause__`.          | `.key`, `.value`, `.target`                                                |
| `EnvValidationError`   | `EnvProxyError`, `ValueError`            | Raised by `EnvConfig.validate()`. Aggregates every failing field into one exception.                                                                          | `.errors` — `dict[str, EnvProxyError]` (field name → underlying exception) |
| `EnvConfigError`       | `EnvProxyError`, `RuntimeError`, `ValueError` | An `EnvConfig` is declared or resolved incorrectly: unsupported `type_hint=`, strict-mode annotation failure, reserved field name, unknown override key, or a non-JSON-encodable default. | —                                                                          |

Because every concrete exception is also a `ValueError`, a single
`except ValueError:` block still catches them all. `EnvConfigError`
additionally inherits from `RuntimeError`, so legacy `except RuntimeError`
handlers around former bare-`RuntimeError` call sites continue to work.

## Documented deviations

Three exceptions intentionally escape env-proxy without being wrapped in
`EnvProxyError`:

1. **`json.JSONDecodeError`** from `EnvProxy.get_json()` (and from any
   `EnvConfig` field with `type_hint="json"`) when the env-var value
   isn't valid JSON. `JSONDecodeError` is itself a `ValueError`
   subclass, so `except ValueError:` still catches it.

2. **`RuntimeError`** from `EnvField.field_name` / `EnvField.owner`
   when accessed on a free-floating `Field()` instance that was never
   bound to a class. Treated as a bug indicator (you're using the
   descriptor outside a class body).

3. **`TypeError`** from assignment to a frozen `EnvConfig` instance or
   to a field with `allow_set=False`. Matches the standard library's
   `@dataclass(frozen=True)` idiom for "this operation isn't allowed
   on this object".

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
