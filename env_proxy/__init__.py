"""EnvProxy creates a proxy to environmental variables with typehinting and type conversion."""

import os
from typing import Any, Optional

bool_truthy = ("yes", "true", "1", "on", "enable", "enabled", "allow")
bool_falsy = ("no", "false", "0", "off", "disable", "disabled", "deny")


class EnvProxy:
    """A proxy to environmental variables with typehinting and type conversion."""

    env_prefix: Optional[str] = None

    @classmethod
    def _get_key(cls, key: str) -> str:
        """Get key with prefix"""
        prefix = f"{cls.env_prefix}_" if cls.env_prefix else ""
        return f"{prefix}{key.upper().replace('-', '_')}"

    @classmethod
    def get_any(cls, key: str) -> Any:
        """Get any value"""
        key_cleaned = cls._get_key(key)
        val = os.getenv(key_cleaned, None)
        return val

    @classmethod
    def get_bool(cls, key: str) -> bool | None:
        key_cleaned = cls._get_key(key)
        val = os.getenv(key_cleaned, None)
        if val is None:
            return None
        if val.lower() in bool_truthy:
            return True
        if val.lower() in bool_falsy:
            return False
        raise ValueError(
            f"Key {key} is present in the environment, but its value {val!r} is neither truthy, nor falsy."
        )

    @classmethod
    def get_bool_strict(cls, key: str) -> bool:
        val = cls.get_bool(key)
        if val is None:
            raise ValueError(f"No valid boolean value for key {key} in environment.")
        return val

    @classmethod
    def get_str(cls, key: str) -> Optional[str]:
        """Get str value from environment"""
        val = cls.get_any(key)
        if val is None:
            return None
        if isinstance(val, str):
            return val
        return str(val)

    @classmethod
    def get_str_strict(cls, key: str) -> str:
        """Get str value from environment, raise ValueError if no such key exists"""
        val = cls.get_str(key)
        if val is None:
            raise ValueError(f"No value for key {key} in environment")
        return val

    @classmethod
    def get_int(cls, key: str) -> Optional[int]:
        """Get int value from environment"""
        val = cls.get_any(key)
        if val is None:
            return None
        if isinstance(val, int):
            return val
        try:
            return int(val)
        except ValueError as error:
            raise ValueError(f"Value for key {key} is not a valid integer") from error

    @classmethod
    def get_int_strict(cls, key: str) -> int:
        """Get int value from environment, raise ValueError if no such key exists"""
        val = cls.get_int(key)
        if val is None:
            raise ValueError(f"No value for key {key} in environment")
        return val

    @classmethod
    def get_float(cls, key: str) -> Optional[float]:
        """Get float value from environment"""
        val = cls.get_any(key)
        if val is None:
            return None
        if isinstance(val, float):
            return val
        try:
            return float(val)
        except ValueError as error:
            raise ValueError(f"Value for key {key} is not a valid integer") from error

    @classmethod
    def get_float_strict(cls, key: str) -> float:
        """Get float value from environment, raise ValueError if no such key exists"""
        val = cls.get_float(key)
        if val is None:
            raise ValueError(f"No value for key {key} in environment")
        return val
