"""Static type-checking regression tests for EnvConfig overrides.

The blocks below are inside ``if TYPE_CHECKING:`` so they're analyzed by mypy
but never executed at runtime. Each ``# type: ignore[<code>]`` comment asserts
that mypy *would* emit that specific error code; mypy strict's
``warn_unused_ignores`` fails this file if ``dataclass_transform`` stops
surfacing field-level types — which is exactly the regression we want to catch.
"""

from typing import TYPE_CHECKING

from env_proxy import EnvConfig, EnvProxy, Field


class TypingFixture(EnvConfig):
    env_proxy = EnvProxy(prefix="TYPING")
    int_field: int = Field()
    str_field: str = Field()
    optional_field: str | None = Field()
    list_field: list[str] = Field()


if TYPE_CHECKING:
    # Positive: every field is optional in the synthesized __init__.
    _ok_empty = TypingFixture()
    _ok_subset = TypingFixture(int_field=42)
    _ok_all = TypingFixture(
        int_field=42,
        str_field="x",
        list_field=["a", "b"],
        optional_field=None,
    )

    # Negative: unknown kwarg must be flagged by mypy.
    _bad_unknown = TypingFixture(typo=42)  # type: ignore[call-arg]

    # Negative: wrong value type must be flagged by mypy.
    _bad_type = TypingFixture(int_field="not an int")  # type: ignore[arg-type]
