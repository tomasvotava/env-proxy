from env_proxy._sentinel import UNSET, Sentinel


def test_sentinel_is_falsy() -> None:
    assert not UNSET


def test_sentinel_is_singleton() -> None:
    assert Sentinel() is Sentinel()
    assert Sentinel() is UNSET
