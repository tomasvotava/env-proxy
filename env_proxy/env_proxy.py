"""EnvProxy creates a proxy to environmental variables with typehinting and type conversion."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any, TypeVar, overload

T = TypeVar("T")

logger = logging.getLogger(__name__)

bool_truthy = ("yes", "true", "1", "on", "enable", "enabled", "allow")
bool_falsy = ("no", "false", "0", "off", "disable", "disabled", "deny", "disallow")


class Sentinel: ...


UNSET = Sentinel()


@lru_cache(maxsize=100)
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
        logger.debug(f"Attempting to read {key!r} from env.")
        value = os.getenv(key, None)
        if value is None:
            logger.debug(f"No value for key {key!r} in env.")
        return value

    def _resolve_default(self, key: str, default: T | Sentinel = UNSET) -> T:
        if isinstance(default, Sentinel):
            raise ValueError(f"No value found for key {key!r} in the environment.")
        logger.debug(f"Using default value for key {key!r}.")
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
        raise ValueError(
            f"Key {key!r} is present in the environment, but its value {value!r} is neither truthy, nor falsy."
        )

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
        return str(value)

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
            raise ValueError(f"Value for key {key!r} is not a valid integer.") from error

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
            raise ValueError(f"Value for key {key!r} is not a valid float.") from error

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
