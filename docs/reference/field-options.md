# `Field()` options

Every `EnvConfig` attribute is declared via the `Field()` factory. The
parameters are listed below; `UNSET` means "no value supplied — the field
is required".

| Option          | Type                | Default | Description |
|-----------------|---------------------|---------|-------------|
| `alias`         | `str`               | field name | Custom env-var key. Defaults to the field name (transformed by the proxy's `prefix` / `uppercase` / `underscored` rules). |
| `description`   | `str`               | `""`    | Human-readable description; rendered into the sample `.env` and the auto API reference. |
| `default`       | `Any`               | `UNSET` | Default value used when the env var is missing. If `UNSET`, the field is required. |
| `type_hint`     | str literal         | `None`  | Explicit type label. One of `any`, `bool`, `float`, `int`, `str`, `list`, `json`. See [type hints](type-hints.md). |
| `env_prefix`    | `str`               | inherited | Per-field override of the class-level prefix. |
| `allow_set`     | `bool`              | `False` | If `True`, the field can be reassigned at runtime; assignment also writes to `os.environ`. |
| `convert_using` | `Callable[[str], T]`| `None`  | Custom converter for non-standard types. See [Custom converters](../how-to/custom-converters.md). |
| `type_name`     | `str`               | derived | Overrides the type label used in `.env` exports and `EnvValueError` messages. |

## Notes

- `default` is evaluated once at class-definition time. Mutable defaults
  (`[]`, `{}`) follow the same caveat as Python defaults — share carefully.
- `convert_using` is the source of truth for runtime conversion. If both
  `convert_using` and `type_hint` are passed, `type_hint` is ignored and
  a `UserWarning` is emitted.
- `allow_set=True` instances mutate `os.environ` on assignment;
  `.freeze()` makes such fields read-only and warns about them.
