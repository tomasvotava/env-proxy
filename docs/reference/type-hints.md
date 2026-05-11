# Type hints

`Field()` infers its conversion from the field's annotation. When the
annotation is ambiguous, pass `type_hint=` explicitly.

## Supported `type_hint` values

| `type_hint` | Converted to       | Example                                           |
|-------------|--------------------|---------------------------------------------------|
| `any`       | `str` (raw value)  | `value: Any = Field(type_hint="any")`             |
| `bool`      | `bool`             | `debug: bool = Field(type_hint="bool")`           |
| `float`     | `float`            | `ratio: float = Field(type_hint="float")`         |
| `int`       | `int`              | `count: int = Field(type_hint="int")`             |
| `str`       | `str`              | `name: str = Field(type_hint="str")`              |
| `list`      | `list[str]`        | `tags: list[str] = Field(type_hint="list")`       |
| `json`      | `Any` (`json.loads`) | `settings: dict = Field(type_hint="json")`      |

## Inference from annotations

When an annotation is one of the simple types above, `type_hint` can be
omitted:

```python
class MyConfig(EnvConfig):
    env_prefix: str = "MYAPP"

    # annotation → type_hint inferred automatically
    debug: bool = Field()
    port: int = Field(default=8080)
    timeout: float = Field(default=5.0)
```

Pass `type_hint="list"` for `list[str]` fields whose annotation is
parametrised; pass `type_hint="json"` for `dict[...]` annotations that
should be parsed via `json.loads`.

## Custom types

For anything outside the built-in set — enums, `Decimal`, `pathlib.Path`,
nested dataclasses — use [`convert_using`](../how-to/custom-converters.md).
