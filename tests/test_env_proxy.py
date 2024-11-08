"""Tests for the env_proxy module."""

import os
from types import NoneType
from typing import Any

import pytest

from env_proxy import EnvProxy
from env_proxy.env_proxy import apply_env


def test_apply_env() -> None:
    os.environ["TEST_VAR_PREEXISTING"] = "this was always here"
    assert os.getenv("TEST_VAR_DOES_NOT_EXIST") is None
    assert os.getenv("TEST_VAR_PREEXISTING") == "this was always here"
    with apply_env(TEST_VAR_DOES_NOT_EXIST="it does", TEST_VAR_PREEXISTING="now it's different"):
        assert os.getenv("TEST_VAR_DOES_NOT_EXIST") == "it does"
        assert os.getenv("TEST_VAR_PREEXISTING") == "now it's different"
    assert os.getenv("TEST_VAR_DOES_NOT_EXIST") is None
    assert os.getenv("TEST_VAR_PREEXISTING") == "this was always here"


def test_get_with_prefix() -> None:
    with apply_env(SUPERPREFIX_VARIABLE="value", VARIABLE="another-value"):
        proxy = EnvProxy(prefix="superprefix")
        assert proxy.get_any("variable") == "value"


def test_empty_is_as_good_as_none() -> None:
    with apply_env(PREFIX_EMPTY=""):
        proxy = EnvProxy(prefix="PREFIX")
        assert proxy.get_any("empty", None) is None
        assert proxy.get_any("empty", 4) == 4
        with pytest.raises(ValueError, match="No value found for key 'empty' in the environment."):
            assert proxy.get_any("empty")


def test_get_without_prefix() -> None:
    with apply_env(PREFIX_VARIABLE="value", VARIABLE="another-value"):
        proxy = EnvProxy()
        assert proxy.get_any("variable") == "another-value"


def test_original_case() -> None:
    with apply_env(variable="value"):
        proxy = EnvProxy(uppercase=False)
        assert proxy.get_any("variable") == "value"


def test_keep_dashes() -> None:
    with apply_env(**{"my-variable": "value"}):
        proxy = EnvProxy(uppercase=False, underscored=False)
        assert proxy.get_any("my-variable") == "value"


def test_get_any() -> None:
    with apply_env(MY_VARIABLE="my-value"):
        proxy = EnvProxy()
        assert proxy.get_any("my-variable") == "my-value"
        assert proxy.get_any("does-not-exist", None) is None
        with pytest.raises(ValueError, match="No value found for key 'does-not-exist' in the environment."):
            proxy.get_any("does-not-exist")


@pytest.mark.parametrize(
    ("value", "result"),
    [
        ("yes", True),
        ("true", True),
        ("1", True),
        ("on", True),
        ("enable", True),
        ("enabled", True),
        ("allow", True),
        ("no", False),
        ("false", False),
        ("0", False),
        ("off", False),
        ("disable", False),
        ("disabled", False),
        ("deny", False),
    ],
)
def test_get_bool_from_words(value: str, result: bool) -> None:
    for cased_value in (value.lower(), value.upper(), value.capitalize()):
        with apply_env(MY_VARIABLE=cased_value):
            proxy = EnvProxy()
            assert proxy.get_bool("my-variable") == result


@pytest.mark.parametrize("value", ["foo", "bar", "this is stupid", "this doesn't look truthy", "nor falsy"])
def test_get_bool_bad_words(value: str) -> None:
    with apply_env(MY_VARIABLE=value):
        proxy = EnvProxy()
        with pytest.raises(ValueError, match="Key 'my-variable' is present in the environment, but its value.*"):
            proxy.get_bool("my-variable")

        with pytest.raises(ValueError, match="Key 'my-variable' is present in the environment, but its value.*"):
            proxy.get_bool("my-variable", None)


@pytest.mark.parametrize(
    ("expected_type", "method_name", "test_value", "expected_value"),
    [
        (bool, "get_bool", "yes", True),
        (bool, "get_bool", "1", True),
        (bool, "get_bool", "no", False),
        (bool, "get_bool", "disabled", False),
        (str, "get_str", "my string value", "my string value"),
        (str, "get_str", "123", "123"),
        (int, "get_int", "123", 123),
        (int, "get_int", "-30", -30),
        (float, "get_float", "123", 123.0),
        (float, "get_float", "-23.432", -23.432),
        (list, "get_list", "a,b,c, d", ["a", "b", "c", "d"]),
        (dict, "get_json", '{"key": "value"}', {"key": "value"}),
        (list, "get_json", '["key", "key2"]', ["key", "key2"]),
        (int, "get_json", "3", 3),
        (NoneType, "get_json", "null", None),
    ],
)
def test_get_typed(expected_type: type[Any], method_name: str, test_value: str, expected_value: Any) -> None:
    with apply_env(MY_VARIABLE=test_value):
        proxy = EnvProxy()
        value = getattr(proxy, method_name)("my-variable")
        assert value == expected_value
        assert isinstance(value, expected_type)
        assert getattr(proxy, method_name)("does-not-exist", None) is None
        with pytest.raises(ValueError, match="No value found for key 'does-not-exist' in the environment."):
            getattr(proxy, method_name)("does-not-exist")


@pytest.mark.parametrize(
    ("method_name", "test_value", "match"),
    [
        ("get_int", "not an int", "Value for key .* is not a valid integer."),
        ("get_float", "not a float either", "Value for key .* is not a valid float."),
    ],
)
def test_cannot_cast(method_name: str, test_value: str, match: str) -> None:
    with apply_env(MY_VARIABLE=test_value):
        proxy = EnvProxy()
        with pytest.raises(ValueError, match=match):
            getattr(proxy, method_name)("my-variable")

        with pytest.raises(ValueError, match=match):
            getattr(proxy, method_name)("my-variable", None)


@pytest.mark.parametrize(
    ("data", "separator", "strip", "expected"),
    [
        ("a,b,c,d", ",", True, ["a", "b", "c", "d"]),
        ("a, b, c , d", ",", True, ["a", "b", "c", "d"]),
        ("a, b, c, d", ",", False, ["a", " b", " c", " d"]),
        ("a,b,c", ":", True, ["a,b,c"]),
        ("a:B:c: D", ":", True, ["a", "B", "c", "D"]),
    ],
)
def test_get_list(data: str, separator: str, strip: bool, expected: list[str]) -> None:
    with apply_env(MY_VARIABLE=data):
        proxy = EnvProxy()
        assert proxy.get_list("my-variable", separator=separator, strip=strip) == expected
