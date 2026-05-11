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

- Construction is cheap — fields you never touch don't cost anything.
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
