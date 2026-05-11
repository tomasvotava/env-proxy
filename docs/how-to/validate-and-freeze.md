# Validate and freeze configuration

`EnvConfig` resolves each field lazily, on first access. Two methods change
that for production use.

## `.validate()` — eager checks, mutability preserved

`.validate()` resolves every field once and raises `EnvValidationError`
if any field is missing or malformed. **All** field failures are
aggregated into one exception; inspect its `.errors` mapping
(field name → underlying exception) to see them all at once.

```python
from env_proxy import EnvValidationError

config = MyConfig()
try:
    config.validate()
except EnvValidationError as exc:
    for name, error in exc.errors.items():
        log.error("config field %s failed: %s", name, error)
        if error.__cause__ is not None:
            log.debug("caused by: %r", error.__cause__)
    raise
```

After `.validate()` succeeds, reads still go through the environment —
nothing is cached. Use this when you need eager checks but still want
runtime mutability (e.g. tests that mutate `os.environ`).

## `.freeze()` — resolve once, cache forever

`.freeze()` resolves every field once and caches the result on the
instance. Subsequent reads become a single dict lookup (~200 ns versus
~1.3 µs for a fresh env lookup).

```python
config = MyConfig()
config.freeze()

assert config.is_frozen
```

After freezing:

- **Reads** return the cached value; the environment is not touched.
- **Assignment is disallowed**, even for fields with `allow_set=True`.
  Any such fields are listed in a `UserWarning` at the moment of
  freezing, so you can spot any unintentionally-locked fields.

The two methods are independent. Combine them at startup to fail fast
and then lock the config for the rest of the process:

```python
config = MyConfig()
config.validate()
config.freeze()
```

See [Lazy vs frozen](../explanation/lazy-vs-frozen.md) for the rationale
and the performance numbers behind these choices.
