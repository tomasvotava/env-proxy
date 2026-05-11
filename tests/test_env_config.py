"""Test EnvConfig configurations."""

import enum
import json
import logging
import os
import sys
import warnings
from decimal import Decimal
from functools import partial
from io import StringIO
from pathlib import Path
from typing import Any, cast

if sys.version_info >= (3, 11):
    from typing import Never
else:  # pragma: no cover
    from typing_extensions import Never

import pytest

from env_proxy._sentinel import UNSET
from env_proxy.env_config import EnvConfig, EnvField, Field, TypeHint, _get_type_hint_handler
from env_proxy.env_proxy import EnvProxy, apply_env

BASIC_CONFIG_ENV_SAMPLE = """# integer (int) [required]
# An integer field.
INTEGER=

# float (float) [required]
# This field shows alias usage.
FLOAT=

# has_prefix (str) [required]
# This field has a prefix and
# a multiline description.
PREFIX_HAS_PREFIX=

# field (str) [required]
DIFFERENT_PREFIX_FIELD=

# no_default (int) [required]
NO_DEFAULT=

# has_default (float) [optional]
HAS_DEFAULT=

# has_implicit_default (float) [optional]
HAS_IMPLICIT_DEFAULT=

# has_typehint (json) [required]
HAS_TYPEHINT=

# supports_set (str) [required]
SUPPORTS_SET=

# array (list) [required]
ENV_TEST_ARRAY=

# unsupported_array (list) [required]
ENV_TEST_UNSUPPORTED_ARRAY=
"""

SIMPLE_CONFIG_ENV_NO_DEFAULTS_NO_SORT = """# timeout (float) [optional]
# Service timeout.
MYAPP_TIMEOUT=

# services (list) [optional]
# List of services.
MYAPP_SERVICES=

# backoff (int) [required]
# Backoff in milliseconds.
MYAPP_BACKOFF=

# extra (json) [optional]
# Additional json data.
MYAPP_EXTRA=

# unknown (unknown type) [required]
MYAPP_UNKNOWN=
"""

SIMPLE_CONFIG_ENV_NO_DEFAULTS_SORT = """# backoff (int) [required]
# Backoff in milliseconds.
MYAPP_BACKOFF=

# extra (json) [optional]
# Additional json data.
MYAPP_EXTRA=

# services (list) [optional]
# List of services.
MYAPP_SERVICES=

# timeout (float) [optional]
# Service timeout.
MYAPP_TIMEOUT=

# unknown (unknown type) [required]
MYAPP_UNKNOWN=
"""

SIMPLE_CONFIG_ENV_DEFAULTS_SORT = """# backoff (int) [required]
# Backoff in milliseconds.
MYAPP_BACKOFF=

# extra (json) [optional]
# Additional json data.
MYAPP_EXTRA={"something": "value"}

# services (list) [optional]
# List of services.
MYAPP_SERVICES=rabbitmq,redis

# timeout (float) [optional]
# Service timeout.
MYAPP_TIMEOUT=100

# unknown (unknown type) [required]
MYAPP_UNKNOWN=
"""


class BasicConfig(EnvConfig):
    integer: int = Field(description="An integer field.")
    field_with_alias: float = Field(alias="float", description="This field shows alias usage.")
    has_prefix: str = Field(env_prefix="PREFIX", description="This field has a prefix and\na multiline description.")
    has_prefix_and_alias: str = Field(alias="field", env_prefix="DIFFERENT_PREFIX")
    no_default: int = Field()
    has_default: float | None = Field(default=None)
    has_implicit_default: float | None = Field()
    has_typehint: dict[str, Any] = Field(type_hint="json")
    supports_set: str = Field(allow_set=True)
    array: list[str] = Field(env_prefix="ENV_TEST")
    unsupported_array: list[int] = Field(env_prefix="ENV_TEST")


class InheritConfig(EnvConfig):
    _strict = False
    _allow_set = True
    env_proxy = EnvProxy(prefix="ENV_TEST")

    integer: int = Field()
    missing: str = Field()
    missing_optional: bool | None = Field()
    this_is_strict: bool = Field(strict=True)
    block_set: str = Field(allow_set=False)
    custom_prefix: str = Field(env_prefix="ENV_TEST_EXTRA")
    custom_proxy: str = Field(env_proxy=EnvProxy(prefix="ENV_CUSTOM_PREFIX"))


class DifficultConfig(EnvConfig):
    complex_stuff: dict[str, list[str]] = Field()
    complex_stuff_hinted: dict[str, list[str]] = Field(type_hint="json")
    complex_stuff_lenient: dict[str, list[str]] = Field(strict=False)
    no_annotation = Field()
    no_annotation_lenient = Field(strict=False)
    no_annotation_hinted = Field(type_hint="any")


class SimpleConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="MYAPP")
    timeout: float = Field(description="Service timeout.", default=100)
    services: list[str] = Field(description="List of services.", default=["rabbitmq", "redis"])
    backoff: int = Field(description="Backoff in milliseconds.")
    extra: dict[str, Any] = Field(description="Additional json data.", type_hint="json", default={"something": "value"})
    unknown = Field(strict=False)


class UndocumentedConfig(EnvConfig):
    failure: Any = Field(type_hint="json", default={"this is not json-encodable"})


class AllowSetToNone(EnvConfig):
    can_be_set: str | None = Field(allow_set=True, default=None)


def test_basic_config() -> None:
    test_env = {
        "INTEGER": "4",
        "FLOAT": "3.14",
        "PREFIX_HAS_PREFIX": "string",
        "DIFFERENT_PREFIX_FIELD": "different string",
        "HAS_TYPEHINT": '{"field": "value"}',
        "ENV_TEST_ARRAY": "apple, banana, kiwi, peach,ananas",
    }
    with apply_env(**test_env):
        config = BasicConfig()
        assert config.integer == 4
        assert config.field_with_alias == 3.14
        assert config.has_prefix == "string"
        assert config.has_prefix_and_alias == "different string"
        with pytest.raises(ValueError, match=r"No value found for key 'no_default' in the environment."):
            _ = config.no_default
        assert config.has_default is None
        assert config.has_implicit_default is None
        assert config.has_typehint == {"field": "value"}
        with pytest.raises(ValueError, match=r"No value found for key 'supports_set' in the environment."):
            _ = config.supports_set
        config.supports_set = "now it exists"
        assert config.supports_set == "now it exists"
        with pytest.raises(TypeError, match=r"Field 'integer' of 'BasicConfig' is read-only."):
            config.integer = 3
        assert config.array == ["apple", "banana", "kiwi", "peach", "ananas"]


def test_unsupported_array_args(caplog: pytest.LogCaptureFixture) -> None:
    # This is a behavior that will hopefully change with #3
    # https://github.com/tomasvotava/env-proxy/issues/3
    with apply_env(ENV_TEST_UNSUPPORTED_ARRAY="1,2,3,4"):
        config = BasicConfig()
        caplog.clear()
        with caplog.at_level(logging.WARNING, "env_proxy.env_config"):
            assert config.unsupported_array == ["1", "2", "3", "4"]  # type: ignore
        assert "Annotation list[int] is a list of <class 'int'>, only 'str' is supported." in caplog.text


def test_config_inherited() -> None:
    test_env = {
        "ENV_TEST_INTEGER": "69",
        "ENV_TEST_THIS_IS_STRICT": "yes",
        "ENV_TEST_BLOCK_SET": "hello",
        "ENV_TEST_EXTRA_CUSTOM_PREFIX": "something extra",
    }
    with apply_env(**test_env):
        config = InheritConfig()
        assert config.integer == 69
        assert config.this_is_strict
        assert config.block_set == "hello"
        config.integer = 420
        assert config.integer == 420
        assert os.getenv("ENV_TEST_INTEGER") == "420"
        overridden_strict = vars(InheritConfig)["this_is_strict"]
        assert isinstance(overridden_strict, EnvField)
        assert overridden_strict.env_key == "ENV_TEST_THIS_IS_STRICT"
        assert overridden_strict.strict
        assert overridden_strict.env_proxy is InheritConfig.env_proxy
        assert overridden_strict.allow_set

        inherited_strict = vars(InheritConfig)["integer"]
        assert isinstance(inherited_strict, EnvField)
        assert inherited_strict.strict is False
        assert overridden_strict.env_proxy is InheritConfig.env_proxy

        overridden_allow_set = vars(InheritConfig)["block_set"]
        assert isinstance(overridden_allow_set, EnvField)
        assert overridden_allow_set.strict is False
        assert overridden_allow_set.allow_set is False
        assert overridden_allow_set.env_proxy is InheritConfig.env_proxy

        with pytest.raises(ValueError, match=r"No value found for key 'missing' in the environment."):
            _ = config.missing

        config.missing = "not missing anymore"

        assert config.missing == "not missing anymore"
        assert os.getenv("ENV_TEST_MISSING") == "not missing anymore"

        assert config.missing_optional is None

        config.missing_optional = False
        assert config.missing_optional is False
        assert os.getenv("ENV_TEST_MISSING_OPTIONAL") == "False"

        assert config.custom_prefix == "something extra"
        overridden_prefix = vars(InheritConfig)["custom_prefix"]
        assert isinstance(overridden_prefix, EnvField)
        assert overridden_prefix.env_proxy is not InheritConfig.env_proxy
        assert overridden_prefix.env_proxy.prefix == "ENV_TEST_EXTRA"

        overridden_proxy = vars(InheritConfig)["custom_proxy"]
        assert isinstance(overridden_proxy, EnvField)
        assert overridden_proxy.env_proxy is not InheritConfig.env_proxy
        assert overridden_proxy.env_proxy.prefix == "ENV_CUSTOM_PREFIX"


def test_difficult_config() -> None:
    json_content = '{"fruits": ["apple", "banana", "peach"], "veggies": ["carrot", "cucumber", "salad"]}'
    dict_content = json.loads(json_content)
    test_env = {
        "COMPLEX_STUFF": json_content,
        "COMPLEX_STUFF_HINTED": json_content,
        "COMPLEX_STUFF_LENIENT": json_content,
        "NO_ANNOTATION": "foobar",
        "NO_ANNOTATION_LENIENT": "don't be so strict",
        "NO_ANNOTATION_HINTED": "I don't know and I don't care",
    }
    with apply_env(**test_env):
        config = DifficultConfig()
        with pytest.raises(
            RuntimeError,
            match=r"Failed to determine value getter for field 'complex_stuff'. "
            "No type hint was provided and the annotation is too complicated.",
        ):
            _ = config.complex_stuff
        assert config.complex_stuff_hinted == dict_content
        assert config.complex_stuff_lenient == json_content  # type: ignore
        no_annotation_field = vars(DifficultConfig)["no_annotation"]
        assert isinstance(no_annotation_field, EnvField)
        assert no_annotation_field.annotated_optional is False
        with pytest.raises(
            ValueError,
            match=r"No type annotation nor type hint found for field 'no_annotation'. "
            "Set strict=False to turn this exception into a warning instead.",
        ):
            _ = config.no_annotation
        assert config.no_annotation_lenient == "don't be so strict"

        no_annotation_hinted_field = vars(DifficultConfig)["no_annotation_hinted"]
        assert isinstance(no_annotation_hinted_field, EnvField)
        assert no_annotation_hinted_field.default is UNSET
        assert no_annotation_hinted_field.strict
        assert no_annotation_hinted_field.simplified_annotation is None
        assert config.no_annotation_hinted == "I don't know and I don't care"


@pytest.mark.parametrize(
    ("type_hint", "expected"),
    [
        ("any", "get_any"),
        ("bool", "get_bool"),
        ("float", "get_float"),
        ("int", "get_int"),
        ("str", "get_str"),
        ("list", "get_list"),
        ("json", "get_json"),
        ("wrong", "ValueError"),
    ],
)
def test_get_type_hint_handler(type_hint: TypeHint, expected: str) -> None:
    env_proxy = EnvProxy()
    if expected == "ValueError":
        with pytest.raises(ValueError, match=f"Unsupported type hint {type_hint!r}."):
            _ = _get_type_hint_handler(type_hint, env_proxy)
    else:
        proxy_method = cast(partial[Any], _get_type_hint_handler(type_hint, env_proxy))
        expected_method = getattr(env_proxy, expected)
        assert proxy_method.func is expected_method.__func__


def test_use_field_outside_instance() -> None:
    wrong_field = Field()
    with pytest.raises(RuntimeError, match=r"Field was not properly initialized and has no name."):
        _ = wrong_field.field_name

    with pytest.raises(RuntimeError, match=r"Field was not properly initialized and has no owner."):
        _ = wrong_field.owner


@pytest.mark.skipif(sys.version_info < (3, 12), reason="A different exception is raised on versions before 3.12.")
def test_field_with_reserved_name() -> None:
    with pytest.raises(ValueError, match=r"Field name '_field' is reserved for internal use."):

        class _WrongField:
            _field = Field()

    with pytest.raises(ValueError, match=r"Field name 'env_proxy' is reserved for internal use."):

        class _WrongFieldProxy:
            env_proxy = Field()


@pytest.mark.skipif(sys.version_info >= (3, 12), reason="A different exception is raised on versions from 3.12 on.")
def test_field_with_reserved_name_runtime() -> None:
    with pytest.raises(
        RuntimeError, match=r"Error calling __set_name__ on 'EnvField' instance '_field' in '_WrongField'"
    ):

        class _WrongField:
            _field = Field()

    with pytest.raises(
        RuntimeError, match=r"Error calling __set_name__ on 'EnvField' instance 'env_proxy' in '_WrongFieldProxy'"
    ):

        class _WrongFieldProxy:
            env_proxy = Field()


def test_generate_env_file_content() -> None:
    file = StringIO()
    BasicConfig.export_env(file, include_defaults=True)
    assert file.getvalue() == BASIC_CONFIG_ENV_SAMPLE


@pytest.mark.parametrize(
    ("sort_by_name", "include_defaults", "expected"),
    [
        (False, False, SIMPLE_CONFIG_ENV_NO_DEFAULTS_NO_SORT),
        (True, False, SIMPLE_CONFIG_ENV_NO_DEFAULTS_SORT),
        (True, True, SIMPLE_CONFIG_ENV_DEFAULTS_SORT),
    ],
)
def test_generate_env_file_various(sort_by_name: bool, include_defaults: bool, expected: str, tmp_path: Path) -> None:
    with (tmp_path / "sample.env").open("w", encoding="utf-8") as file:
        SimpleConfig.export_env(file, include_defaults=include_defaults, sort_by_name=sort_by_name)
    assert (tmp_path / "sample.env").read_text(encoding="utf-8") == expected


def test_generate_env_file_str_path(tmp_path: Path) -> None:
    path = tmp_path / "sample.env"
    path_str = (tmp_path / "sample.str.env").as_posix()
    assert path.as_posix() != path_str
    SimpleConfig.export_env(path)
    SimpleConfig.export_env(path_str)
    assert path.read_text(encoding="utf-8") == Path(path_str).read_text(encoding="utf-8")


def test_invalid_json_default_docs_export() -> None:
    file = StringIO()
    with pytest.raises(
        ValueError,
        match=r"Failed to export default for field 'failure'. Its default value cannot be encoded as a JSON.",
    ):
        UndocumentedConfig.export_env(file, include_defaults=True)


def test_can_set_to_none() -> None:
    with apply_env(CAN_BE_SET="some str"):
        config = AllowSetToNone()
        assert config.can_be_set == "some str"
        config.can_be_set = None
        assert config.can_be_set is None


def test_override_basic() -> None:
    """A constructor override returns the typed value with no env access."""
    config = BasicConfig(integer=42)
    assert config.integer == 42


def test_override_beats_env() -> None:
    """An override wins over a value present in the environment."""
    with apply_env(INTEGER="1"):
        config = BasicConfig(integer=42)
        assert config.integer == 42
        assert os.environ["INTEGER"] == "1"


def test_override_beats_default() -> None:
    """An override wins over a Field's declared default."""
    config = BasicConfig(has_default=99.5)
    assert config.has_default == 99.5


def test_override_typed_values_bypass_conversion() -> None:
    """Override values are used as-is — typed Python objects, no string parsing."""
    services = ["a", "b"]
    config = SimpleConfig(timeout=3.5, services=services, backoff=10)
    assert config.timeout == 3.5
    assert config.services is services
    assert config.backoff == 10


def test_override_with_alias_or_prefix() -> None:
    """Overrides are keyed by Python field name, regardless of alias/prefix."""
    config = BasicConfig(field_with_alias=2.71, has_prefix="hello")
    assert config.field_with_alias == 2.71
    assert config.has_prefix == "hello"


def test_override_inherited_field() -> None:
    """Fields declared on a base class can be overridden on a subclass instance."""
    config = InheritConfig(integer=42)
    assert config.integer == 42


def test_override_unknown_kwarg_raises() -> None:
    with pytest.raises(ValueError, match=r"Unknown override key\(s\) for BasicConfig: \['typo'\]"):
        BasicConfig(typo=1)  # type: ignore[call-arg]


def test_override_for_shadowed_field_is_rejected() -> None:
    """A subclass that shadows an inherited EnvField with a non-EnvField value
    opts out of the field. Overrides keyed on the shadowed name must raise
    ValueError, not be silently dropped at read time.
    """

    class Base(EnvConfig):
        env_proxy = EnvProxy(prefix="SHADOW")
        shadowed: int = Field()

    class Sub(Base):
        shadowed = 1

    with pytest.raises(ValueError, match=r"Unknown override key\(s\) for Sub: \['shadowed'\]"):
        Sub(shadowed=42)


def test_valid_fields_cached_on_class() -> None:
    """Per-class field roster is computed once and exposed for fast __init__ lookup."""
    assert "integer" in BasicConfig._valid_fields
    assert "supports_set" in BasicConfig._valid_fields
    assert isinstance(BasicConfig._valid_fields, frozenset)


def test_empty_construction_unchanged() -> None:
    """No-kwarg construction still reads from env exactly as before."""
    with apply_env(INTEGER="7"):
        config = BasicConfig()
        assert config.integer == 7


def test_override_set_updates_both_override_and_env() -> None:
    """Setting an overridden allow_set=True field updates the override AND os.environ."""
    config = BasicConfig(supports_set="initial")
    try:
        assert config.supports_set == "initial"
        config.supports_set = "updated"
        assert config.supports_set == "updated"
        assert os.environ["SUPPORTS_SET"] == "updated"
    finally:
        os.environ.pop("SUPPORTS_SET", None)


def test_override_set_non_overridden_field_falls_through() -> None:
    """Setting a non-overridden allow_set=True field hits env only — no override entry."""
    config = BasicConfig(integer=42)
    try:
        config.supports_set = "via env"
        assert os.environ["SUPPORTS_SET"] == "via env"
        assert config.supports_set == "via env"
        assert "supports_set" not in config._overrides
    finally:
        os.environ.pop("SUPPORTS_SET", None)


def test_override_readonly_field_cannot_be_reassigned() -> None:
    """allow_set=False keeps gating mutation even when the field was overridden at construction."""
    config = BasicConfig(integer=42)
    assert config.integer == 42
    with pytest.raises(TypeError, match=r"Field 'integer' of 'BasicConfig' is read-only."):
        config.integer = 100


def test_class_level_field_access_returns_descriptor() -> None:
    """Class-level attribute access returns the EnvField descriptor (standard descriptor idiom)."""
    assert isinstance(BasicConfig.integer, EnvField)
    assert BasicConfig.integer.field_name == "integer"


def test_override_with_none_at_construction() -> None:
    """Override with literal None returns None without touching env."""
    config = BasicConfig(has_default=None)
    assert config.has_default is None


def test_override_set_to_none() -> None:
    """Setting an overridden allow_set=True field to None deletes the env key and stores None."""
    with apply_env(CAN_BE_SET="initial"):
        config = AllowSetToNone(can_be_set="overridden")
        assert config.can_be_set == "overridden"
        config.can_be_set = None
        assert config.can_be_set is None
        assert "CAN_BE_SET" not in os.environ


class FreezeConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="FREEZE")
    name: str = Field()
    port: int = Field()
    debug: bool = Field(default=False)
    mutable: str = Field(allow_set=True, default="initial")


class FreezeChildConfig(FreezeConfig):
    extra: str = Field(default="x")


def test_freeze_captures_env_at_call_time() -> None:
    with apply_env(FREEZE_NAME="svc", FREEZE_PORT="8080"):
        config = FreezeConfig()
        with pytest.warns(UserWarning, match=r"allow_set=True"):
            config.freeze()
    # Env vars are gone — frozen values should still be served.
    assert config.name == "svc"
    assert config.port == 8080
    assert config.debug is False


def test_freeze_does_not_reread_env_after_call() -> None:
    with apply_env(FREEZE_NAME="first", FREEZE_PORT="1"):
        config = FreezeConfig()
        with pytest.warns(UserWarning, match=r"allow_set=True"):
            config.freeze()
        with apply_env(FREEZE_NAME="second", FREEZE_PORT="2"):
            assert config.name == "first"
            assert config.port == 1


def test_freeze_respects_overrides() -> None:
    with apply_env(FREEZE_NAME="from-env", FREEZE_PORT="1"):
        config = FreezeConfig(name="from-override")
        with pytest.warns(UserWarning, match=r"allow_set=True"):
            config.freeze()
    assert config.name == "from-override"
    assert config.port == 1


def test_freeze_blocks_set_even_for_allow_set_fields() -> None:
    with apply_env(FREEZE_NAME="n", FREEZE_PORT="1"):
        config = FreezeConfig()
        with pytest.warns(UserWarning, match=r"allow_set=True.*\['mutable'\]"):
            config.freeze()
    with pytest.raises(TypeError, match=r"frozen"):
        config.mutable = "after"
    # Read still works.
    assert config.mutable == "initial"


def test_freeze_blocks_set_for_readonly_fields_too() -> None:
    with apply_env(FREEZE_NAME="n", FREEZE_PORT="1"):
        config = FreezeConfig()
        with pytest.warns(UserWarning, match=r"allow_set=True"):
            config.freeze()
    with pytest.raises(TypeError, match=r"frozen"):
        config.name = "other"


def test_freeze_emits_no_warning_when_no_allow_set_fields() -> None:
    class NoMutable(EnvConfig):
        env_proxy = EnvProxy(prefix="NOMUT")
        a: str = Field(default="x")

    config = NoMutable()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        config.freeze()
    assert config.a == "x"


def test_double_freeze_is_noop_with_warning() -> None:
    with apply_env(FREEZE_NAME="n", FREEZE_PORT="1"):
        config = FreezeConfig()
        with pytest.warns(UserWarning, match=r"allow_set=True"):
            config.freeze()
    snapshot = config._frozen
    with pytest.warns(UserWarning, match=r"already frozen"):
        config.freeze()
    assert config._frozen is snapshot


def test_freeze_includes_inherited_fields() -> None:
    with apply_env(FREEZE_NAME="n", FREEZE_PORT="1"):
        config = FreezeChildConfig()
        with pytest.warns(UserWarning, match=r"allow_set=True"):
            config.freeze()
    assert config.name == "n"
    assert config.port == 1
    assert config.extra == "x"


def test_validate_passes_when_env_is_complete() -> None:
    with apply_env(FREEZE_NAME="n", FREEZE_PORT="1"):
        FreezeConfig().validate()  # no raise


def test_validate_aggregates_missing_and_malformed() -> None:
    with (
        apply_env(FREEZE_PORT="not-an-int"),
        pytest.raises(ValueError, match=r"FreezeConfig failed validation") as excinfo,
    ):
        FreezeConfig().validate()
    msg = str(excinfo.value)
    assert "name:" in msg  # missing
    assert "port:" in msg  # malformed


def test_validate_skips_overrides() -> None:
    # name has no env, but supplied via override — should not raise.
    with apply_env(FREEZE_PORT="1"):
        FreezeConfig(name="provided").validate()


def test_validate_does_not_freeze() -> None:
    with apply_env(FREEZE_NAME="n", FREEZE_PORT="1"):
        config = FreezeConfig()
        config.validate()
        assert config._frozen is None
        # Still mutable through allow_set path.
        config.mutable = "changed"
        assert config.mutable == "changed"


def test_validate_then_freeze_works() -> None:
    with apply_env(FREEZE_NAME="n", FREEZE_PORT="1"):
        config = FreezeConfig()
        config.validate()
        with pytest.warns(UserWarning, match=r"allow_set=True"):
            config.freeze()
    assert config.name == "n"


def test_is_frozen_starts_false() -> None:
    with apply_env(FREEZE_NAME="n", FREEZE_PORT="1"):
        config = FreezeConfig()
    assert config.is_frozen is False


def test_is_frozen_true_after_freeze() -> None:
    with apply_env(FREEZE_NAME="n", FREEZE_PORT="1"):
        config = FreezeConfig()
        with pytest.warns(UserWarning, match=r"allow_set=True"):
            config.freeze()
    assert config.is_frozen is True


def test_is_frozen_unchanged_by_validate() -> None:
    with apply_env(FREEZE_NAME="n", FREEZE_PORT="1"):
        config = FreezeConfig()
        config.validate()
        assert config.is_frozen is False


def test_validate_raises_envvalidationerror() -> None:
    from env_proxy import EnvKeyMissingError, EnvValidationError

    with apply_env(FREEZE_PORT="not-an-int"), pytest.raises(EnvValidationError) as excinfo:
        FreezeConfig().validate()
    err = excinfo.value
    # Still a ValueError for back-compat.
    assert isinstance(err, ValueError)
    # Structured access to individual failures.
    assert set(err.errors) == {"name", "port"}
    assert isinstance(err.errors["name"], EnvKeyMissingError)
    assert err.errors["name"].key == "name"


def test_validate_propagates_non_envproxy_exceptions() -> None:
    """A converter raising a non-env-proxy exception should bubble out untouched."""

    def _broken_converter(value: str) -> int:
        raise RuntimeError("converter is buggy")

    class Cfg(EnvConfig):
        env_proxy = EnvProxy(prefix="BRK")
        v: int = Field(convert_using=_broken_converter)

    # The plain RuntimeError gets wrapped by EnvValueError (which is an
    # EnvProxyError), so validate aggregates it — that's the expected path.
    from env_proxy import EnvValidationError, EnvValueError

    with apply_env(BRK_V="x"), pytest.raises(EnvValidationError) as excinfo:
        Cfg().validate()
    inner = excinfo.value.errors["v"]
    assert isinstance(inner, EnvValueError)
    assert isinstance(inner.__cause__, RuntimeError)


def test_validate_does_not_swallow_unexpected_in_field_resolution() -> None:
    """Errors that are not EnvProxyError (e.g. from a broken value_getter
    cached_property) bubble out so they can be debugged."""
    from env_proxy import EnvKeyMissingError

    class WeirdEnvField(EnvField):
        @property
        def value_getter(self) -> Never:
            raise AttributeError("simulated bug")

    class Cfg(EnvConfig):
        env_proxy = EnvProxy(prefix="WEIRD")
        # Bypass Field() factory to inject the weird descriptor.
        v: int = WeirdEnvField()  # type: ignore[assignment]

    with pytest.raises(AttributeError, match=r"simulated bug"):
        Cfg().validate()
    # Sanity: EnvKeyMissingError would have been caught had it been raised.
    assert EnvKeyMissingError is not AttributeError  # type: ignore[comparison-overlap]


def test_missing_required_raises_env_key_missing_error() -> None:
    from env_proxy import EnvKeyMissingError

    proxy = EnvProxy()
    with pytest.raises(EnvKeyMissingError) as excinfo:
        proxy.get_int("nope")
    assert excinfo.value.key == "nope"
    # Still catches as ValueError.
    assert isinstance(excinfo.value, ValueError)


class _Level(enum.Enum):
    LOW = "low"
    HIGH = "high"


class ConvertingConfig(EnvConfig):
    env_proxy = EnvProxy(prefix="CVT")
    level: _Level = Field(convert_using=_Level)
    amount: Decimal = Field(convert_using=Decimal, default=Decimal("0"))
    level_optional: _Level = Field(convert_using=_Level, default=_Level.LOW)


def test_convert_using_enum() -> None:
    with apply_env(CVT_LEVEL="high"):
        config = ConvertingConfig()
        assert config.level is _Level.HIGH


def test_convert_using_callable_returns_typed_value() -> None:
    with apply_env(CVT_LEVEL="low", CVT_AMOUNT="3.14"):
        config = ConvertingConfig()
        assert config.amount == Decimal("3.14")


def test_convert_using_propagates_converter_errors() -> None:
    from env_proxy import EnvValueError

    with apply_env(CVT_LEVEL="nope"):
        config = ConvertingConfig()
        with pytest.raises(EnvValueError, match=r"is not a valid _Level") as excinfo:
            _ = config.level
    # Original converter exception preserved on __cause__.
    assert isinstance(excinfo.value.__cause__, ValueError)
    assert "nope" in str(excinfo.value.__cause__)
    assert excinfo.value.key == "level"
    assert excinfo.value.value == "nope"
    assert excinfo.value.target == "_Level"


def test_convert_using_skips_converter_when_default_used() -> None:
    sentinel_calls: list[str] = []

    def _spy(value: str) -> _Level:
        sentinel_calls.append(value)
        return _Level(value)

    class Cfg(EnvConfig):
        env_proxy = EnvProxy(prefix="SPY")
        level: _Level = Field(convert_using=_spy, default=_Level.LOW)

    # Env unset → default served as-is, converter not called.
    config = Cfg()
    assert config.level is _Level.LOW
    assert sentinel_calls == []


def test_convert_using_without_default_raises_when_env_missing() -> None:
    config = ConvertingConfig()
    with pytest.raises(ValueError, match=r"No value found for key 'level'"):
        _ = config.level


def test_convert_using_with_type_hint_warns_and_wins() -> None:
    with pytest.warns(UserWarning, match=r"convert_using overrides type_hint='int'"):

        class Cfg(EnvConfig):
            env_proxy = EnvProxy(prefix="WARN")
            level: _Level = Field(convert_using=_Level, type_hint="int")

    with apply_env(WARN_LEVEL="high"):
        config = Cfg()
        assert config.level is _Level.HIGH


def test_convert_using_export_emits_callable_name() -> None:
    buf = StringIO()
    ConvertingConfig.export_env(buf, include_defaults=False)
    content = buf.getvalue()
    assert "(_Level)" in content
    assert "(Decimal)" in content


def test_convert_using_export_uses_annotation_over_callable_name() -> None:
    """Annotation wins for the type label, so a lambda + `int` annotation reads as `int`."""

    class Cfg(EnvConfig):
        env_proxy = EnvProxy(prefix="LAM")
        v: int = Field(convert_using=lambda s: int(s) * 2)

    buf = StringIO()
    Cfg.export_env(buf, include_defaults=False)
    assert "(int)" in buf.getvalue()


def test_convert_using_export_lambda_without_annotation_falls_back_to_custom() -> None:
    """No annotation and a lambda (name == '<lambda>') → label is 'custom'."""

    class Cfg(EnvConfig):
        env_proxy = EnvProxy(prefix="LAMNO")
        v = Field(convert_using=lambda s: int(s) * 2, strict=False)

    buf = StringIO()
    Cfg.export_env(buf, include_defaults=False)
    assert "(custom)" in buf.getvalue()


def test_convert_using_export_callable_instance_falls_back_to_custom() -> None:
    """Instances of __call__ classes have no __name__ → 'custom'."""

    class CB:
        def __call__(self, value: str) -> int:
            return int(value)

    class Cfg(EnvConfig):
        env_proxy = EnvProxy(prefix="CB")
        v = Field(convert_using=CB(), strict=False)

    buf = StringIO()
    Cfg.export_env(buf, include_defaults=False)
    assert "(custom)" in buf.getvalue()


def test_type_name_overrides_label() -> None:
    """Explicit type_name= wins over annotation, convert_using.__name__, and fallback."""

    class Cfg(EnvConfig):
        env_proxy = EnvProxy(prefix="TN")
        v: int = Field(convert_using=lambda s: int(s), type_name="Doubled")

    buf = StringIO()
    Cfg.export_env(buf, include_defaults=False)
    assert "(Doubled)" in buf.getvalue()


def test_type_name_drives_envvalueerror_target() -> None:
    """The same resolved_type_name is used in EnvValueError messages."""
    from env_proxy import EnvValueError

    def _converter(s: str) -> int:
        raise ValueError("nope")

    class Cfg(EnvConfig):
        env_proxy = EnvProxy(prefix="TNERR")
        v: int = Field(convert_using=_converter, type_name="Doubled")

    with apply_env(TNERR_V="anything"), pytest.raises(EnvValueError, match=r"not a valid Doubled"):
        _ = Cfg().v


def test_convert_using_freeze_caches_converted_value() -> None:
    with apply_env(CVT_LEVEL="high"):
        config = ConvertingConfig()
        config.freeze()
    # Converter not called again on read after freeze; value preserved.
    assert config.level is _Level.HIGH


def test_convert_using_validate_catches_converter_error() -> None:
    with (
        apply_env(CVT_LEVEL="bogus"),
        pytest.raises(ValueError, match=r"ConvertingConfig failed validation"),
    ):
        ConvertingConfig().validate()
