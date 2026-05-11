# Convert env values into custom types

When the built-in type set isn't enough — most commonly for enums or
types like `Decimal` and `pathlib.Path` — pass a callable as
`convert_using`. The callable receives the raw `str` from the environment
and must return the typed value.

```python
import enum
from decimal import Decimal
from env_proxy import EnvConfig, Field

class Level(enum.Enum):
    LOW = "low"
    HIGH = "high"

class AppConfig(EnvConfig):
    env_prefix: str = "APP"
    level: Level = Field(convert_using=Level, default=Level.LOW)
    amount: Decimal = Field(convert_using=Decimal)
```

## Behaviour

- The converter is called **only when the env value is present**. If the
  env var is missing and a `default` is provided, the default is returned
  as-is — supply a default of the **target type** (e.g.
  `default=Level.LOW`, not `default="low"`).
- If the converter raises, the exception is wrapped in `EnvValueError`.
  The original exception is preserved on `__cause__`.
- Passing both `convert_using` and `type_hint` emits a `UserWarning` and
  ignores `type_hint`.
- The annotation on the field is informational (used by static type
  checkers); `convert_using` is the source of truth for runtime
  conversion.

## Type label in exports and errors

For the type label shown in exported `.env` files and `EnvValueError`
messages, the resolution order is:

1. Explicit `type_name=` if given.
2. The field annotation, if it's a simple type (`int`, `Level`, …).
3. `convert_using.__name__`, unless it would be `"<lambda>"`.
4. Fallback: `"custom"`.

So `field: Level = Field(convert_using=Level)` renders as `(Level)` in
`.env` exports, and:

```python
field = Field(convert_using=lambda s: ..., type_name="Doubled")
```

renders as `(Doubled)`.

## Common patterns

```python
from pathlib import Path
import json

class AppConfig(EnvConfig):
    env_prefix: str = "APP"

    # Path
    data_dir: Path = Field(convert_using=Path)

    # Enum
    log_level: LogLevel = Field(convert_using=LogLevel)

    # Comma-separated list of ints
    port_ranges: list[int] = Field(
        convert_using=lambda s: [int(p) for p in s.split(",")],
        type_name="list[int]",
    )

    # Tagged JSON
    metadata: dict[str, str] = Field(convert_using=json.loads, type_name="json")
```
