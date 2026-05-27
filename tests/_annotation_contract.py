"""Shared assertions for runtime annotation inference.

Both the eager-annotation module (``test_annotation_inference.py``) and the
``from __future__ import annotations`` module call these helpers, so the two
import styles are held to a single contract.

A *contract config* is any :class:`EnvConfig` subclass that declares exactly
these fields with these annotations (env keys are derived from the class's own
proxy prefix, so each module uses its own prefix and the two never collide)::

    count: int
    ratio: float
    flag: bool
    name: str
    items: list[str]
    maybe: str | None
    anything: Any
    with_default: int = Field(default=7)

A *warn config* declares a single ``nums: list[int]`` field. It is kept
separate because the unsupported-element warning is emitted once per descriptor
(``simplified_annotation`` is cached), so it needs a descriptor no other test
has already resolved.
"""

import logging
from io import StringIO
from typing import Any, Protocol, cast

import pytest

from env_proxy import EnvConfig, EnvProxy
from env_proxy.env_config import EnvField
from env_proxy.env_proxy import apply_env


class ContractConfig(Protocol):
    """Instance-level view of a contract config, so field reads in the helpers
    are typed against the field set rather than the bare :class:`EnvConfig`
    base (which declares none of them)."""

    count: int
    ratio: float
    flag: bool
    name: str
    items: list[str]
    maybe: str | None
    anything: Any
    with_default: int


class WarnConfig(Protocol):
    """Instance-level view of the warn config: a single ``list[int]`` field."""

    nums: list[int]


# field name -> the EnvProxy method its annotation must resolve to
EXPECTED_BINDINGS: dict[str, object] = {
    "count": EnvProxy.get_int,
    "ratio": EnvProxy.get_float,
    "flag": EnvProxy.get_bool,
    "name": EnvProxy.get_str,
    "items": EnvProxy.get_list,
    "maybe": EnvProxy.get_str,
    "anything": EnvProxy.get_any,
}

# field name -> the type label that export_env must render for it
EXPECTED_LABELS: dict[str, str] = {
    "count": "int",
    "ratio": "float",
    "flag": "bool",
    "name": "str",
    "items": "list",
    "maybe": "str",
    "anything": "any",
    "with_default": "int",
}


def _prefix(config_cls: type[EnvConfig], anchor: str) -> str | None:
    """The proxy prefix the config resolves env keys under, read off one of its
    own fields (``env_proxy`` is set by convention on subclasses, not declared
    on the base)."""
    # getattr resolves through the MRO; EnvField.__get__ returns self on the class.
    field = cast(EnvField, getattr(config_cls, anchor))
    return field.env_proxy.prefix


def _env_for(prefix: str | None) -> dict[str, str]:
    pre = f"{prefix}_" if prefix else ""
    return {
        f"{pre}COUNT": "42",
        f"{pre}RATIO": "3.14",
        f"{pre}FLAG": "yes",
        f"{pre}NAME": "hello",
        f"{pre}ITEMS": "a, b ,c",
        f"{pre}ANYTHING": "raw",
    }


def assert_inference(config_cls: type[EnvConfig]) -> None:
    """Every supported annotation converts the env value to the right type."""
    with apply_env(**_env_for(_prefix(config_cls, "count"))):
        cfg = cast(ContractConfig, config_cls())
        assert cfg.count == 42
        assert isinstance(cfg.count, int)
        assert cfg.ratio == 3.14
        assert cfg.flag is True
        assert cfg.name == "hello"
        assert cfg.items == ["a", "b", "c"]
        assert cfg.anything == "raw"
        assert cfg.maybe is None  # optional, unset -> None
        assert cfg.with_default == 7  # unset -> declared default


def assert_optional_when_set(config_cls: type[EnvConfig]) -> None:
    """An ``X | None`` field returns the converted value when the env is set."""
    pre = f"{_prefix(config_cls, 'count')}_"
    with apply_env(**{f"{pre}MAYBE": "present"}):
        assert cast(ContractConfig, config_cls()).maybe == "present"


def assert_value_getter_bindings(config_cls: type[EnvConfig]) -> None:
    """Each field's annotation resolves to the expected EnvProxy getter."""
    for name, expected in EXPECTED_BINDINGS.items():
        field = getattr(config_cls, name)
        assert isinstance(field, EnvField)
        getter = field.value_getter
        assert getattr(getter, "__func__", None) is expected, f"{name!r} resolved to {getter!r}, expected {expected!r}"


def assert_export_labels(config_cls: type[EnvConfig]) -> None:
    """export_env renders the annotation-derived type label for each field."""
    buf = StringIO()
    config_cls.export_env(buf, include_defaults=False)
    content = buf.getvalue()
    for name, label in EXPECTED_LABELS.items():
        assert f"# {name} ({label})" in content, f"missing/wrong label for {name!r} in:\n{content}"


def assert_list_int_warns(config_cls: type[EnvConfig], caplog: pytest.LogCaptureFixture) -> None:
    """A ``list[int]`` field warns about the unsupported element type and falls
    back to a list of strings. ``config_cls`` must declare ``nums``."""
    pre = f"{_prefix(config_cls, 'nums')}_"
    with apply_env(**{f"{pre}NUMS": "1,2,3"}):
        cfg = cast(WarnConfig, config_cls())
        caplog.clear()
        with caplog.at_level(logging.WARNING, "env_proxy.env_config"):
            # Runtime value is list[str]: list[int] degrades to a string list (the limitation under test).
            assert cast(list[str], cfg.nums) == ["1", "2", "3"]
        assert "is a list of <class 'int'>, only 'str' is supported" in caplog.text
