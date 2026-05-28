"""Runtime annotation inference under PEP 563 (``from __future__ import annotations``).

This module mirrors :mod:`tests.test_annotation_inference` against stringized
annotations by sharing :mod:`tests._annotation_contract` — so both import
styles are held to a single contract. It additionally covers PEP-563-specific
paths that don't exist in the eager-annotation case:

- a ``TYPE_CHECKING``-only annotation on a field that uses ``convert_using=``
  must not crash the whole config class at import (the regression an eager
  whole-dict ``get_annotations(eval_str=True)`` would cause);
- a strict field whose string annotation can't be resolved at runtime and has
  no ``type_hint=``/``convert_using=`` still surfaces an ``EnvConfigError``;
- ``export_env`` labels reflect the resolved annotation, fixing the silent
  ``unknown type`` corruption PEP 563 used to introduce.
"""

from __future__ import annotations

import json
from io import StringIO
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

import pytest

from env_proxy import EnvConfig, EnvConfigError, EnvProxy, Field
from env_proxy.env_config import EnvField
from env_proxy.env_proxy import apply_env

from . import _annotation_contract as contract

if TYPE_CHECKING:
    # Names visible only to the type checker; at runtime resolving these
    # annotation strings raises NameError, exercising the degraded path.
    class FancyType: ...

    class Unresolvable: ...


class FutureConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="CONTRACT_FUTURE")
    count: int = Field()
    ratio: float = Field()
    flag: bool = Field()
    name: str = Field()
    items: list[str] = Field()
    maybe: str | None = Field()
    anything: Any = Field()
    with_default: int = Field(default=7)


class FutureWarnConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="CONTRACT_FUTURE_WARN")
    nums: list[int] = Field()


def test_inference_resolves_supported_types_under_pep_563() -> None:
    contract.assert_inference(FutureConfig)


def test_optional_returns_value_when_set_under_pep_563() -> None:
    contract.assert_optional_when_set(FutureConfig)


def test_value_getter_bindings_under_pep_563() -> None:
    contract.assert_value_getter_bindings(FutureConfig)


def test_export_labels_reflect_annotations_under_pep_563() -> None:
    contract.assert_export_labels(FutureConfig)


def test_unsupported_list_element_warns_under_pep_563(caplog: pytest.LogCaptureFixture) -> None:
    contract.assert_list_int_warns(FutureWarnConfig, caplog)


# PEP-563-specific cases -----------------------------------------------------


def _upper(value: str) -> str:
    return value.upper()


_T = TypeVar("_T")


class _BoomGeneric(Generic[_T]):
    """A generic whose subscription raises ``ValueError`` — used to verify
    that ``resolved_annotation`` degrades on *any* eval failure, not just the
    obvious ``NameError``/``AttributeError``/``SyntaxError``/``TypeError`` set."""

    def __class_getitem__(cls, item: Any) -> Any:
        raise ValueError("__class_getitem__ refuses subscription")


class TypeCheckingOnlyAnnotated(EnvConfig):
    """``fancy``'s annotation is only importable under ``TYPE_CHECKING``;
    class creation must succeed and the field must resolve via ``convert_using``."""

    env_proxy = EnvProxy(prefix="TCO")
    fancy: FancyType = Field(convert_using=_upper)


def test_type_checking_only_annotation_does_not_break_class() -> None:
    """The class imports cleanly; the field resolves through its converter,
    not its (unresolvable) annotation."""
    with apply_env(TCO_FANCY="hello"):
        cfg = TypeCheckingOnlyAnnotated()
        # Runtime value comes from convert_using (a plain str); the FancyType
        # annotation exists only for the type checker.
        assert cast(str, cfg.fancy) == "HELLO"


def test_type_checking_only_annotation_leaves_sibling_fields_working() -> None:
    """A second field on the same class with a normal annotation still resolves
    — i.e. one unresolvable annotation does not poison the rest of the class."""

    class Mixed(EnvConfig):
        env_proxy = EnvProxy(prefix="MIX")
        fancy: FancyType = Field(convert_using=_upper)
        count: int = Field()

    with apply_env(MIX_FANCY="hi", MIX_COUNT="3"):
        cfg = Mixed()
        assert cast(str, cfg.fancy) == "HI"
        assert cfg.count == 3


def test_unresolvable_annotation_strict_field_raises_envconfigerror() -> None:
    """A strict field whose annotation can't be resolved and has neither
    ``type_hint`` nor ``convert_using`` still surfaces an :class:`EnvConfigError`
    — the existing "too complicated" path, just triggered by an eval failure."""

    class BadAnno(EnvConfig):
        env_proxy = EnvProxy(prefix="BAD")
        whoops: Unresolvable = Field()

    with apply_env(BAD_WHOOPS="present"), pytest.raises(EnvConfigError):
        _ = BadAnno().whoops


def test_unresolvable_annotation_lenient_field_falls_back_to_any() -> None:
    """In non-strict mode the same field warns instead and serves the raw value."""

    class LenientBadAnno(EnvConfig):
        env_proxy = EnvProxy(prefix="LBA")
        whoops: Unresolvable = Field(strict=False)

    with apply_env(LBA_WHOOPS="raw-value"):
        assert cast(str, LenientBadAnno().whoops) == "raw-value"


def test_annotation_eval_raising_valueerror_degrades_gracefully() -> None:
    """When ``eval`` of an annotation raises something outside the obvious
    set (here, ``ValueError`` from a custom ``__class_getitem__``), the field
    still resolves through its converter — degradation must be uniform."""

    class HasBoom(EnvConfig):
        env_proxy = EnvProxy(prefix="BOOM")
        thing: _BoomGeneric[int] = Field(convert_using=str)

    with apply_env(BOOM_THING="raw"):
        assert cast(str, HasBoom().thing) == "raw"


def test_resolved_annotation_on_detached_field_returns_none() -> None:
    """A bare ``EnvField`` that hasn't been attached to an owner class can't
    evaluate a string annotation — there's no namespace to source globals/locals
    from — so it degrades to ``None``."""
    field = EnvField()
    # Bypass __set_name__: simulate a stringized annotation on a detached field.
    field._annotation = "int"
    assert field.resolved_annotation is None


# -- Export labels for complex / unresolvable annotations under PEP 563 -----
# These mirror the eager-annotation export-label tests under stringized
# annotations so the resolution chain in resolved_type_name is held to the
# same contract regardless of import style.


def _payload_from_json(raw: str) -> dict[str, list[str]]:
    return cast("dict[str, list[str]]", json.loads(raw))


class _ComplexConvertPEP563(EnvConfig):
    env_proxy = EnvProxy(prefix="ECC")
    payload: dict[str, list[str]] = Field(convert_using=_payload_from_json)


def test_export_label_complex_annotation_with_convert_using_under_pep_563() -> None:
    """Complex annotation + ``convert_using`` exports as the converter name —
    parity with the eager-annotation path."""
    buf = StringIO()
    _ComplexConvertPEP563.export_env(buf, include_defaults=False)
    assert "# payload (_payload_from_json)" in buf.getvalue()


class _ComplexTypeHintPEP563(EnvConfig):
    env_proxy = EnvProxy(prefix="ECTH")
    payload: dict[str, list[str]] = Field(type_hint="json")


def test_export_label_complex_annotation_with_type_hint_under_pep_563() -> None:
    """Complex annotation + ``type_hint`` exports as the type_hint name."""
    buf = StringIO()
    _ComplexTypeHintPEP563.export_env(buf, include_defaults=False)
    assert "# payload (json)" in buf.getvalue()


class _ComplexTypeNamePEP563(EnvConfig):
    env_proxy = EnvProxy(prefix="ECTN")
    payload: dict[str, list[str]] = Field(type_name="ComplexDict")


def test_export_label_complex_annotation_with_type_name_under_pep_563() -> None:
    """Complex annotation + ``type_name`` exports as the explicit type_name."""
    buf = StringIO()
    _ComplexTypeNamePEP563.export_env(buf, include_defaults=False)
    assert "# payload (ComplexDict)" in buf.getvalue()


def test_export_label_type_checking_only_annotation_uses_converter_name() -> None:
    """A ``TYPE_CHECKING``-only annotation can't be resolved at runtime; the
    export label falls through the resolution chain to the converter's
    ``__name__``."""
    buf = StringIO()
    TypeCheckingOnlyAnnotated.export_env(buf, include_defaults=False)
    assert "# fancy (_upper)" in buf.getvalue()


class _TypeCheckingOnlyWithTypeName(EnvConfig):
    env_proxy = EnvProxy(prefix="TCN")
    fancy: FancyType = Field(convert_using=_upper, type_name="Fancy")


def test_export_label_type_checking_only_annotation_with_type_name_wins() -> None:
    """``type_name`` wins immediately, even with an unresolvable annotation."""
    buf = StringIO()
    _TypeCheckingOnlyWithTypeName.export_env(buf, include_defaults=False)
    assert "# fancy (Fancy)" in buf.getvalue()


def test_resolved_annotation_owner_without_string_module_returns_none() -> None:
    """An owner whose ``__module__`` is not a string can't supply globals for
    eval; degrade rather than crash."""

    class Quirky(EnvConfig):
        env_proxy = EnvProxy(prefix="QRK")

    Quirky.__module__ = None  # type: ignore[assignment]  # quirky owner: not a real importer state
    try:
        field = EnvField()
        field._annotation = "int"
        field._owner = Quirky
        assert field.resolved_annotation is None
    finally:
        Quirky.__module__ = __name__
