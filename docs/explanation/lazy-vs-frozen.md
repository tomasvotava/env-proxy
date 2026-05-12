# Lazy resolution vs frozen config

`EnvConfig` reads from the environment **lazily** — the first time you
access a given attribute. There are three trade-offs implied by that
choice, and two opt-in escape hatches.

## What lazy means in practice

```python
config = MyConfig()          # cheap — no env reads
config.debug                 # reads MYAPP_DEBUG now
config.debug                 # reads MYAPP_DEBUG again (no caching)
```

Pros:

- Construction is cheap — no env reads. (The one exception is any
  `default_factory` you declare; see [Where `default_factory` fits](#where-default_factory-fits)
  below.)
- Tests that mutate `os.environ` between reads see the latest value
  without forcing them to recreate the config object.

Cons:

- A malformed env value surfaces only when something reads that field —
  which may be deep in a request handler, far from startup.
- Each read pays the cost of an `os.environ` lookup plus any conversion
  (~1.3 µs in our benchmarks for a typical field).

## `.validate()` — fix the first con

`.validate()` reads every field exactly once and aggregates failures
into a single `EnvValidationError`:

```python
config = MyConfig()
config.validate()   # raises on bad/missing fields, with .errors mapping
```

After `.validate()` succeeds, reads still go through the environment —
nothing is cached. This is the right escape hatch when you need
**fail-fast** but also need to keep mutating `os.environ` (e.g. tests
that exercise different env states on the same config class).

## `.freeze()` — fix the second con

`.freeze()` reads every field once and **caches** the result on the
instance. Subsequent reads become a single dict lookup:

| Read mode         | Per-read cost (approx.) |
|-------------------|-------------------------|
| Lazy (default)    | ~1.3 µs                 |
| Frozen            | ~200 ns                 |

Freezing also disables assignment — even for fields declared with
`allow_set=True`. Any such fields are listed in a `UserWarning` at the
moment of freezing, so you can audit what got locked.

## When to use which

| Situation                                              | Recommended                            |
|--------------------------------------------------------|----------------------------------------|
| Test that mutates env vars between cases               | Lazy (do nothing) or `.validate()` only |
| Startup of a long-running service                      | `.validate()` + `.freeze()`            |
| One-off script                                         | Lazy is fine                           |
| Hot-path attribute reads on a stable config            | `.freeze()`                            |

The two escape hatches are **independent**. You can call `.validate()`
without freezing, freeze without validating (don't), or combine both —
which is the recommended startup pattern.

## Where `default_factory` fits

Env reads are lazy. `default_factory` is the deliberate exception:

```python
from datetime import datetime
from env_proxy import EnvConfig, Field

class MyConfig(EnvConfig):
    env_prefix: str = "MYAPP"
    started_at: datetime = Field(
        convert_using=datetime.fromisoformat,
        default_factory=datetime.now,
    )

cfg = MyConfig()      # datetime.now() runs HERE
cfg.started_at        # returns the value captured at construction
cfg.started_at        # same value — factory is not re-invoked
```

The factory fires eagerly at `MyConfig.__init__`, once per instance, and
its result is stored on that instance. This mirrors
`dataclasses.field(default_factory=...)` so the semantics match what
users already expect: `default_factory=datetime.now` captures the moment
you built the config, not the moment you first happen to read the
attribute. Env still wins at read time — the factory result is only
served when the env var is missing.

If the env var is set when you construct the config, the factory still
runs (its result is unused). That's the same trade-off as a static
`default=` on an env-overridden field: the cost lives in the field
declaration, not in the resolution path.

`.validate()` and `.freeze()` do not re-invoke the factory — they read
the value captured at construction. So a factory runs **exactly once per
`EnvConfig` instance**, regardless of how the instance is later used:

```python
cfg = MyConfig()      # factory ran here
cfg.validate()        # reuses the captured value — no second factory call
cfg.freeze()          # captures it into the frozen snapshot
cfg.started_at        # dict lookup; factory still has been called once
```

**Side effects always run.** Because the factory fires unconditionally
at construction, any side effect it performs — opening a file,
contacting a service, allocating a resource — happens even when the env
var is set and the factory's return value will be discarded. If that's
not what you want, pass the value as a constructor override instead.

**Thread safety is yours.** `EnvConfig` does not synchronise factory
invocations. Concurrent `MyConfig()` calls run their factories
independently and concurrently; if the factory itself isn't
thread-safe (e.g. mutates shared state), the caller must add the
locking.
