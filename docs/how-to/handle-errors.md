# Handle errors

`env-proxy` raises `EnvProxyError` and its subclasses. The cleanest
catch-all is `except EnvProxyError:`. For backwards compatibility, every
concrete subclass is also a `ValueError`, and `EnvConfigError` is also a
`RuntimeError`, so legacy `except ValueError:` / `except RuntimeError:`
handlers keep working.

## Catch everything env-proxy raises

```python
from env_proxy import EnvProxy, EnvProxyError

proxy = EnvProxy()

try:
    port = proxy.get_int("PORT")
except EnvProxyError as exc:
    print(f"Configuration error: {exc}", file=sys.stderr)
    sys.exit(2)
```

## Catch a specific failure mode

```python
from env_proxy import EnvProxy, EnvKeyMissingError, EnvValueError

proxy = EnvProxy()

try:
    missing_value = proxy.get_int("MISSING_KEY")
except EnvKeyMissingError as exc:
    print(exc.key)        # 'MISSING_KEY'

try:
    bad_value = proxy.get_int("PORT")   # PORT="not-a-number"
except EnvValueError as exc:
    print(exc.target)     # 'int'
    print(exc.value)      # 'not-a-number'
```

## Aggregated validation errors

`.validate()` collects every field failure into a single
`EnvValidationError` with an `.errors` mapping (Python field name →
underlying exception):

```python
from env_proxy import EnvValidationError

try:
    config.validate()
except EnvValidationError as exc:
    for name, error in exc.errors.items():
        log.error("config field %s failed: %s", name, error)
        if error.__cause__ is not None:
            log.debug("caused by: %r", error.__cause__)
    raise
```

## Edge cases — three documented deviations

The following exceptions are *not* `EnvProxyError` subclasses. They escape
env-proxy on purpose:

- **`json.JSONDecodeError`** — propagated as-is from `get_json()` (and
  from `type_hint="json"` fields) when the value is invalid JSON. It is
  a `ValueError` subclass, so `except ValueError:` catches it.

  ```python
  import json
  try:
      cfg = MyConfig()
      cfg.validate()
  except json.JSONDecodeError as exc:
      ...  # bad JSON in env
  except EnvProxyError as exc:
      ...  # everything else
  ```

- **`RuntimeError`** from `EnvField.field_name` / `EnvField.owner` —
  only reachable if you use a `Field()` outside of an `EnvConfig` class
  body. If you see this, it's a bug in your code, not a runtime
  configuration problem.

- **`TypeError`** from assignment to a frozen `EnvConfig` or a
  `allow_set=False` field — matches Python's `@dataclass(frozen=True)`
  idiom. Catch `TypeError` if you need to handle the case
  programmatically.

See the [Exceptions reference](../reference/exceptions.md) for each
exception's attributes.
