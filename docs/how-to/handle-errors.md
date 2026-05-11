# Handle errors

`env-proxy` raises a small hierarchy of typed exceptions. All inherit from
both `EnvProxyError` and `ValueError`, so a single
`except ValueError:` block catches every error the library raises.

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

## Catch-all

To handle every library error in one place — for example to wrap
configuration failures into a process-exit code — catch the base class:

```python
from env_proxy import EnvProxyError

try:
    cfg = MyConfig()
    cfg.validate()
except EnvProxyError as exc:
    print(f"Configuration error: {exc}", file=sys.stderr)
    sys.exit(2)
```

See the [Exceptions reference](../reference/exceptions.md) for each
exception's attributes.
