"""Regression net for runtime annotation inference (eager-annotation path).

These tests pin the contract that PEP 563 (``from __future__ import
annotations``) support must preserve: every supported annotation resolves to
the right ``EnvProxy`` getter and conversion, optionals default to ``None``,
unsupported list element types warn, and ``export_env`` labels reflect the
annotation. The identical assertions run against a stringized-annotation module
in ``test_annotation_inference_future.py`` — see :mod:`tests._annotation_contract`.
"""

from typing import Any

import pytest

from env_proxy import EnvConfig, EnvProxy, Field

from . import _annotation_contract as contract


class PlainConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="CONTRACT_PLAIN")
    count: int = Field()
    ratio: float = Field()
    flag: bool = Field()
    name: str = Field()
    items: list[str] = Field()
    maybe: str | None = Field()
    anything: Any = Field()
    with_default: int = Field(default=7)


class PlainWarnConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="CONTRACT_PLAIN_WARN")
    nums: list[int] = Field()


def test_inference_resolves_supported_types() -> None:
    contract.assert_inference(PlainConfig)


def test_optional_returns_value_when_set() -> None:
    contract.assert_optional_when_set(PlainConfig)


def test_value_getter_bindings() -> None:
    contract.assert_value_getter_bindings(PlainConfig)


def test_export_labels_reflect_annotations() -> None:
    contract.assert_export_labels(PlainConfig)


def test_unsupported_list_element_warns(caplog: pytest.LogCaptureFixture) -> None:
    contract.assert_list_int_warns(PlainWarnConfig, caplog)
