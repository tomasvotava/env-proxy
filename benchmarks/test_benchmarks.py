"""Benchmarks for EnvProxy and EnvConfig hot paths.

Run with:

    poetry run pytest benchmarks/ --no-cov

`--no-cov` overrides the project's default coverage instrumentation, which
otherwise distorts timings by ~30%. Numbers are machine-dependent and not
asserted on — this suite is observation-only.
"""

import os

from pytest_benchmark.fixture import BenchmarkFixture

from env_proxy import EnvConfig, EnvProxy


def test_baseline_os_getenv(benchmark: BenchmarkFixture, bench_env: None) -> None:
    benchmark(os.getenv, "BENCH_STR")


def test_envproxy_get_str(benchmark: BenchmarkFixture, proxy: EnvProxy) -> None:
    benchmark(proxy.get_str, "str")


def test_envproxy_get_int(benchmark: BenchmarkFixture, proxy: EnvProxy) -> None:
    benchmark(proxy.get_int, "int")


def test_envproxy_get_bool(benchmark: BenchmarkFixture, proxy: EnvProxy) -> None:
    benchmark(proxy.get_bool, "bool")


def test_envproxy_get_list(benchmark: BenchmarkFixture, proxy: EnvProxy) -> None:
    benchmark(proxy.get_list, "list")


def test_envproxy_get_key_cache_hit(benchmark: BenchmarkFixture, proxy: EnvProxy) -> None:
    benchmark(proxy._get_key, "str")


def test_envconfig_construct_no_overrides(benchmark: BenchmarkFixture, bench_config_cls: type[EnvConfig]) -> None:
    benchmark(bench_config_cls)


def test_envconfig_construct_full_overrides(
    benchmark: BenchmarkFixture, bench_config_cls: type[EnvConfig], full_overrides: dict[str, object]
) -> None:
    benchmark(lambda: bench_config_cls(**full_overrides))


def test_envconfig_read_env_fallthrough(benchmark: BenchmarkFixture, bench_config_no_overrides: EnvConfig) -> None:
    benchmark(lambda: bench_config_no_overrides.str_field)  # type: ignore[attr-defined]


def test_envconfig_read_override_hit(benchmark: BenchmarkFixture, bench_config_with_overrides: EnvConfig) -> None:
    benchmark(lambda: bench_config_with_overrides.str_field)  # type: ignore[attr-defined]
