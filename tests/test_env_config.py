"""Test EnvConfig configurations."""

import json
import logging
import os
import sys
from functools import partial
from io import StringIO
from pathlib import Path
from typing import Any, cast

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
        with pytest.raises(ValueError, match="No value found for key 'no_default' in the environment."):
            _ = config.no_default
        assert config.has_default is None
        assert config.has_implicit_default is None
        assert config.has_typehint == {"field": "value"}
        with pytest.raises(ValueError, match="No value found for key 'supports_set' in the environment."):
            _ = config.supports_set
        config.supports_set = "now it exists"
        assert config.supports_set == "now it exists"
        with pytest.raises(TypeError, match="Field 'integer' of 'BasicConfig' is read-only."):
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

        with pytest.raises(ValueError, match="No value found for key 'missing' in the environment."):
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
            match="Failed to determine value getter for field 'complex_stuff'. "
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
            match="No type annotation nor type hint found for field 'no_annotation'. "
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
    with pytest.raises(RuntimeError, match="Field was not properly initialized and has no name."):
        _ = wrong_field.field_name

    with pytest.raises(RuntimeError, match="Field was not properly initialized and has no owner."):
        _ = wrong_field.owner


@pytest.mark.skipif(sys.version_info < (3, 12), reason="A different exception is raised on versions before 3.12.")
def test_field_with_reserved_name() -> None:
    with pytest.raises(ValueError, match="Field name '_field' is reserved for internal use."):

        class _WrongField:
            _field = Field()

    with pytest.raises(ValueError, match="Field name 'env_proxy' is reserved for internal use."):

        class _WrongFieldProxy:
            env_proxy = Field()


@pytest.mark.skipif(sys.version_info >= (3, 12), reason="A different exception is raised on versions from 3.12 on.")
def test_field_with_reserved_name_runtime() -> None:
    with pytest.raises(
        RuntimeError, match="Error calling __set_name__ on 'EnvField' instance '_field' in '_WrongField'"
    ):

        class _WrongField:
            _field = Field()

    with pytest.raises(
        RuntimeError, match="Error calling __set_name__ on 'EnvField' instance 'env_proxy' in '_WrongFieldProxy'"
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
        ValueError, match="Failed to export default for field 'failure'. Its default value cannot be encoded as a JSON."
    ):
        UndocumentedConfig.export_env(file, include_defaults=True)
