# `Field()` options

Every `EnvConfig` attribute is declared via the `Field()` factory. The
parameters are listed below; `UNSET` means "no value supplied — the field
is required".

| Option          | Type                | Default | Description |
|-----------------|---------------------|---------|-------------|
| `alias`         | `str`               | field name | Custom env-var key. Defaults to the field name (transformed by the proxy's `prefix` / `uppercase` / `underscored` rules). |
| `description`   | `str`               | `""`    | Human-readable description; rendered into the sample `.env` and the auto API reference. |
| `default`       | `Any`               | `UNSET` | Default value used when the env var is missing. If `UNSET` (and no `default_factory`), the field is required. |
| `default_factory` | `Callable[[], Any]` | `None`  | Zero-arg callable invoked **once at `EnvConfig.__init__`**; the result is stored on the instance and used whenever the env var is missing. Mutually exclusive with `default`. Skipped when the field is supplied via constructor override. |
| `type_hint`     | str literal         | `None`  | Explicit type label. One of `any`, `bool`, `float`, `int`, `str`, `list`, `json`. See [type hints](type-hints.md). |
| `env_prefix`    | `str`               | inherited | Per-field override of the class-level prefix. |
| `allow_set`     | `bool`              | `False` | If `True`, the field can be reassigned at runtime; assignment also writes to `os.environ`. |
| `convert_using` | `Callable[[str], T]`| `None`  | Custom converter for non-standard types. See [Custom converters](../how-to/custom-converters.md). |
| `type_name`     | `str`               | derived | Overrides the type label used in `.env` exports and `EnvValueError` messages. |

## Notes

- A field is considered to have a default — and is therefore **optional**
  in the sample `.env` and in error messages — when any of these holds:
  an explicit `default=`, a `default_factory=`, `optional=True`, or an
  annotation that includes `None` (e.g. `str | None`). The last case
  trips up readers who expect `field: str | None = Field()` to be
  required; it is not — the field implicitly defaults to `None`.
- `default` is evaluated once at class-definition time. Mutable defaults
  (`[]`, `{}`) follow the same caveat as Python defaults — share carefully.
  Reach for `default_factory` when you want a fresh value per instance.
- `default_factory` runs eagerly at `EnvConfig.__init__`, once per
  instance. The exporter never invokes it — factory-defaulted fields
  appear in the generated `.env` as `[optional]` with an empty value.
- `convert_using` is the source of truth for runtime conversion. If both
  `convert_using` and `type_hint` are passed, `type_hint` is ignored and
  a `UserWarning` is emitted.
- `allow_set=True` instances mutate `os.environ` on assignment;
  `.freeze()` makes such fields read-only and warns about them.
