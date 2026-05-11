"""Exceptions raised by env-proxy.

Every exception in this module inherits from both :class:`EnvProxyError`
and :class:`ValueError`. Catch :class:`EnvProxyError` to handle errors
specific to this library; catch :class:`ValueError` if you want one
handler for env-proxy errors alongside other validation errors.
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
