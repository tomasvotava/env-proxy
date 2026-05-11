"""Shared fixtures for the benchmark suite."""

import warnings
from collections.abc import Iterator

import pytest

from env_proxy import EnvConfig, EnvProxy, Field
from env_proxy.env_proxy import apply_env

BENCH_ENV = {
    "BENCH_STR": "hello",
    "BENCH_INT": "42",
    "BENCH_BOOL": "true",
    "BENCH_LIST": "a,b,c,d,e",
}


@pytest.fixture(scope="module")
def bench_env() -> Iterator[None]:
    with apply_env(**BENCH_ENV):
        yield


@pytest.fixture(scope="module")
def proxy(bench_env: None) -> EnvProxy:
    p = EnvProxy(prefix="BENCH")
    # Warm the _get_prefixed_key lru_cache so steady-state reads
    # don't include the first-call cost.
    for key in ("str", "int", "bool", "list"):
        p._get_key(key)
    return p


@pytest.fixture(scope="module")
def bench_config_cls(bench_env: None) -> type[EnvConfig]:
    class BenchConfig(EnvConfig):
        env_proxy = EnvProxy(prefix="BENCH")
        str_field: str = Field(alias="str")
        int_field: int = Field(alias="int")
        bool_field: bool = Field(alias="bool")
        list_field: list[str] = Field(alias="list")
        any_field: str = Field(alias="str")

    return BenchConfig


@pytest.fixture(scope="module")
def full_overrides() -> dict[str, object]:
    return {
        "str_field": "x",
        "int_field": 1,
        "bool_field": True,
        "list_field": ["a", "b"],
        "any_field": "y",
    }


@pytest.fixture(scope="module")
def bench_config_no_overrides(bench_config_cls: type[EnvConfig]) -> EnvConfig:
    cfg = bench_config_cls()
    # Warm cached_property attrs on EnvField (value_getter, default, env_proxy, …).
    _ = cfg.str_field  # type: ignore[attr-defined]
    return cfg


@pytest.fixture(scope="module")
def bench_config_with_overrides(bench_config_cls: type[EnvConfig], full_overrides: dict[str, object]) -> EnvConfig:
    cfg = bench_config_cls(**full_overrides)
    _ = cfg.str_field  # type: ignore[attr-defined]
    return cfg


@pytest.fixture(scope="module")
def bench_config_frozen(bench_config_cls: type[EnvConfig]) -> EnvConfig:
    cfg = bench_config_cls()
    # Warm cached_property attrs so freeze() pays them once outside the bench.
    _ = cfg.str_field  # type: ignore[attr-defined]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cfg.freeze()
    return cfg
