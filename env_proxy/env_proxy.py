"""EnvProxy creates a proxy to environmental variables with typehinting and type conversion."""

import json
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, TypeVar, overload

from ._sentinel import UNSET, Sentinel
from .exceptions import EnvKeyMissingError, EnvValueError

T = TypeVar("T")

logger = logging.getLogger(__name__)

bool_truthy = ("yes", "true", "1", "on", "enable", "enabled", "allow")
bool_falsy = ("no", "false", "0", "off", "disable", "disabled", "deny", "disallow")


@contextmanager
def apply_env(**env: str) -> Iterator[None]:
    """A context manager that temporarily sets the specified environment
    variables to the given values. When the context is exited, the original environment
    variables are restored.

    Args:
        **env: Arbitrary keyword arguments where the key is the environment variable name
               and the value is the environment variable value to set.

    Example:
        with apply_env(MY_VAR='value'):
            # MY_VAR is set to 'value' within this block
            ...
        # MY_VAR is restored to its original value after the block

    """
    original_env: dict[str, str] = {}
    for key, value in env.items():
        if (original_value := os.getenv(key)) is not None:
            original_env[key] = original_value
        os.environ[key] = value
    yield
    for key in env:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            if key in os.environ:
                del os.environ[key]


_DEFAULT_KEY_CACHE_SIZE = 1024


def _resolve_key_cache_size() -> int:
    raw = os.getenv("ENV_PROXY_KEY_CACHE_SIZE")
    if raw is None:
        return _DEFAULT_KEY_CACHE_SIZE
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid ENV_PROXY_KEY_CACHE_SIZE=%r; falling back to default %d.", raw, _DEFAULT_KEY_CACHE_SIZE)
        return _DEFAULT_KEY_CACHE_SIZE


@lru_cache(maxsize=_resolve_key_cache_size())
def _get_prefixed_key(key: str, prefix: str | None, uppercase: bool, underscored: bool) -> str:
    prefix = f"{prefix}_" if prefix else ""
    key = f"{prefix}{key}"
    if uppercase:
        key = key.upper()
    if underscored:
        key = key.replace("-", "_")
    return key


class EnvProxy:
    """A proxy to environmental variables with typehinting and type conversion."""

    def __init__(self, prefix: str | None = None, uppercase: bool = True, underscored: bool = True) -> None:
        self.prefix = prefix
        self.uppercase = uppercase
        self.underscored = underscored

    def _get_key(self, key: str) -> str:
        """Get key with prefix."""
        return _get_prefixed_key(key=key, prefix=self.prefix, uppercase=self.uppercase, underscored=self.underscored)

    def _get_raw(self, key: str) -> str | None:
        """Get raw value from the environment."""
        key = self._get_key(key)
        logger.debug("Attempting to read %r from env.", key)
        value = os.getenv(key, None)
        if not value:
            value = None
        if value is None:
            logger.debug("No value for key %r in env.", key)
        return value

    def _resolve_default(self, key: str, default: T | Sentinel = UNSET) -> T:
        if isinstance(default, Sentinel):
            raise EnvKeyMissingError(key)
        logger.debug("Using default value for key %r.", key)
        return default

    @overload
    def get_any(self, key: str, default: T) -> Any | T: ...

    @overload
    def get_any(self, key: str) -> Any: ...

    def get_any(self, key: str, default: T | Sentinel = UNSET) -> Any | T:
        """Get value from env typed as Any.

        If default is not given and the key does not exist, ValueError is raised.
        """
        value = self._get_raw(key)
        if value is None:
            return self._resolve_default(key, default)
        return value

    @overload
    def get_bool(self, key: str, default: T) -> bool | T: ...

    @overload
    def get_bool(self, key: str) -> bool: ...

    def get_bool(self, key: str, default: T | Sentinel = UNSET) -> bool | T:
        """Get bool value from the environment.

        Case-insensitive check for truthy and falsy strings is performed to determine the boolean value.

        Truthy values: yes, true, 1, on, enable, enabled, allow
        Falsy values: no, false, 0, off, disable, disabled, deny

        If default is not given and the key does not exist, ValueError is raised.
        """
        value = self._get_raw(key)
        if value is None:
            return self._resolve_default(key, default)
        if value.lower() in bool_truthy:
            return True
        if value.lower() in bool_falsy:
            return False
        raise EnvValueError(key, value, "bool")

    @overload
    def get_str(self, key: str, default: T) -> str | T: ...
    @overload
    def get_str(self, key: str) -> str: ...

    def get_str(self, key: str, default: T | Sentinel = UNSET) -> str | T:
        """Get str value from environment.

        If default is not given and the key does not exist, ValueError is raised.
        """
        value = self._get_raw(key)
        if value is None:
            return self._resolve_default(key, default)
        if isinstance(value, str):
            return value
        return str(value)  # pragma: no cover, unreachable

    @overload
    def get_int(self, key: str, default: T) -> int | T: ...
    @overload
    def get_int(self, key: str) -> int: ...

    def get_int(self, key: str, default: T | Sentinel = UNSET) -> int | T:
        """Get value from the environment as int type.
        If default is not given and the key does not exist, ValueError is raised.
        """
        value = self._get_raw(key)
        if value is None:
            return self._resolve_default(key, default)
        try:
            return int(value)
        except ValueError as error:
            raise EnvValueError(key, value, "int") from error

    @overload
    def get_float(self, key: str, default: T) -> float | T: ...
    @overload
    def get_float(self, key: str) -> float: ...

    def get_float(self, key: str, default: T | Sentinel = UNSET) -> float | T:
        """Get value from the environment as float type.

        If default is not given and the key does not exist, ValueError is raised.
        """
        value = self._get_raw(key)
        if value is None:
            return self._resolve_default(key, default)
        try:
            return float(value)
        except ValueError as error:
            raise EnvValueError(key, value, "float") from error

    @overload
    def get_list(self, key: str, default: T, *, separator: str = ",", strip: bool = True) -> list[str] | T: ...

    @overload
    def get_list(self, key: str, *, separator: str = ",", strip: bool = True) -> list[str]: ...

    def get_list(
        self, key: str, default: T | Sentinel = UNSET, *, separator: str = ",", strip: bool = True
    ) -> list[str] | T:
        """Get a list of string values from the environment.

        The list is expected to be separated by `separator` (defaults to comma `,`).
        List items are stripped of leading and trailing whitespace by default.

        If default is not given and the key does not exist, ValueError is raised.
        """
        value = self._get_raw(key)
        if value is None:
            return self._resolve_default(key, default)

        values = value.split(separator)
        if strip:
            values = list(map(str.strip, values))
        return values

    @overload
    def get_json(self, key: str, default: T) -> Any | T: ...

    @overload
    def get_json(self, key: str) -> Any: ...

    def get_json(self, key: str, default: T | Sentinel = UNSET) -> Any | T:
        """Get a JSON and parse it using `json.loads` from the environment.

        If default is not given and the key does not exist, ValueError is raised.
        Exception raised by `json.loads` are propagated.
        """
        value = self._get_raw(key)
        if value is None:
            return self._resolve_default(key, default)

        return json.loads(value)
