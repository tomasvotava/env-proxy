"""Exceptions raised by env-proxy.

:class:`EnvProxyError` is the catch-all base for every typed exception
raised by this library. The three value-shaped subclasses
(:class:`EnvKeyMissingError`, :class:`EnvValueError`,
:class:`EnvValidationError`) also inherit from :class:`ValueError` so
``except ValueError:`` keeps working. :class:`EnvConfigError` — raised
for declaration/resolution mistakes — additionally inherits from
:class:`RuntimeError` because its call sites previously raised raw
``RuntimeError`` and the dual inheritance preserves that back-compat.

Three documented deviations exist on purpose and are *not*
:class:`EnvProxyError` instances:

* :class:`json.JSONDecodeError` from :meth:`EnvProxy.get_json` — propagated
  as-is by design; it is itself a :class:`ValueError` subclass.
* :class:`RuntimeError` from :attr:`EnvField.field_name` /
  :attr:`EnvField.owner` — only reachable if a free-floating ``Field()``
  instance is used outside a class body; treated as a bug indicator.
* :class:`TypeError` from assignment to a frozen instance or a
  non-``allow_set`` field — matches the standard library's
  ``@dataclass(frozen=True)`` idiom.
"""

from __future__ import annotations


class EnvProxyError(Exception):
    """Base class for every exception raised by env-proxy."""


class EnvKeyMissingError(EnvProxyError, ValueError):
    """Raised when a required env var is absent and no default was given.

    The env var name is available on :attr:`key`.
    """

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"No value found for key {key!r} in the environment.")


class EnvValueError(EnvProxyError, ValueError):
    """Raised when an env value cannot be converted to the target type.

    Inspect :attr:`key`, :attr:`value`, and :attr:`target` for the
    failing env var name, its raw string value, and the type label.
    The underlying exception (e.g. from a custom ``convert_using``
    callable) is preserved on ``__cause__``.
    """

    def __init__(self, key: str, value: str, target: str) -> None:
        self.key = key
        self.value = value
        self.target = target
        super().__init__(f"Value {value!r} for key {key!r} is not a valid {target}.")


class EnvValidationError(EnvProxyError, ValueError):
    """Raised by :meth:`EnvConfig.validate` with every field failure aggregated.

    :attr:`errors` is a mapping from Python field name to the underlying
    :class:`EnvProxyError` for that field (typically an
    :class:`EnvKeyMissingError` or :class:`EnvValueError`).
    """

    def __init__(self, config_name: str, errors: dict[str, EnvProxyError]) -> None:
        self.config_name = config_name
        self.errors = errors
        lines = [f"{name}: {exc}" for name, exc in errors.items()]
        super().__init__(f"{config_name} failed validation:\n  - " + "\n  - ".join(lines))


class EnvConfigError(EnvProxyError, RuntimeError, ValueError):
    """Raised when an :class:`EnvConfig` is declared or resolved incorrectly.

    Covers: unsupported ``type_hint=`` strings, strict-mode failures to
    determine a value getter from an annotation (missing or too-complex
    annotation), reserved field names, unknown override keys passed to
    :class:`EnvConfig`, and ``type_hint='json'`` fields whose default is
    not JSON-encodable.

    Inherits from both :class:`RuntimeError` and :class:`ValueError` so
    that legacy ``except RuntimeError`` / ``except ValueError`` handlers
    keep working after the migration from raw built-in exceptions. New
    code should prefer ``except EnvProxyError`` (or this class directly)
    for clarity.
    """
