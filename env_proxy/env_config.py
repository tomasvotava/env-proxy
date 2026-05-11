"""EnvConfig allows you to create configuration objects based on env variables declaratively with
auto-documenting approach.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import warnings
from collections.abc import Callable, Iterator
from functools import cached_property, partial
from inspect import get_annotations
from pathlib import Path
from types import NoneType, UnionType
from typing import Any, ClassVar, Literal, TextIO, TypeVar, get_args, get_origin

from env_proxy.env_proxy import EnvProxy

from ._sentinel import UNSET
from .exceptions import EnvProxyError, EnvValidationError, EnvValueError

if sys.version_info >= (3, 11):
    from typing import dataclass_transform
else:  # pragma: no cover
    from typing_extensions import dataclass_transform

logger = logging.getLogger(__name__)

T = TypeVar("T")

STRING_WARNING_TO_ERROR = "Set strict=True to turn this warning into an exception instead."
STRING_ERROR_TO_WARNING = "Set strict=False to turn this exception into a warning instead."

SIMPLE_TYPES = (Any, bool, float, int, str, list)

TypeHint = Literal["any", "bool", "float", "int", "str", "list", "json"]

type_hint_map: dict[TypeHint, Callable[[EnvProxy, str, Any], Any]] = {
    "any": EnvProxy.get_any,
    "bool": EnvProxy.get_bool,
    "float": EnvProxy.get_float,
    "int": EnvProxy.get_int,
    "str": EnvProxy.get_str,
    "list": EnvProxy.get_list,
    "json": EnvProxy.get_json,
}


def _get_type_hint_handler(type_hint: TypeHint, env_proxy: EnvProxy) -> Callable[[str, Any], Any]:
    if (handler := type_hint_map.get(type_hint)) is not None:
        return partial(handler, env_proxy)
    raise ValueError(f"Unsupported type hint {type_hint!r}.")


def _annotation_to_method(env_proxy: EnvProxy) -> dict[Any, Callable[[str, Any], Any]]:
    """Bind the simplified-annotation → EnvProxy.get_* mapping to a proxy."""
    return {
        Any: env_proxy.get_any,
        bool: env_proxy.get_bool,
        float: env_proxy.get_float,
        int: env_proxy.get_int,
        list: env_proxy.get_list,
        str: env_proxy.get_str,
    }


reserved_attributes: tuple[str, ...] = ("env_proxy", "env_prefix", "_strict", "_allow_set")


def _get_simplified_annotation(annotation: Any) -> Any:
    """Simplify the annotation so that it can be used to query the correct env_proxy method."""
    if annotation in SIMPLE_TYPES:
        return annotation
    if (origin := get_origin(annotation)) is not None:
        if origin is list:
            if (args := get_args(annotation)) and args[0] is not str:
                # TODO @tomasvotava: either raise here if strict or provide a way for the user to use custom convertor
                # https://github.com/tomasvotava/env-proxy/issues/3
                logger.warning(f"Annotation {annotation!r} is a list of {args[0]!r}, only 'str' is supported.")
            return list
        if origin is not UnionType:
            logger.warning(f"Unsupported annotation origin {origin!r}.")
            return None
        args = get_args(annotation)
        if len(args) == 2 and NoneType in args:
            effective_arg = args[args.index(NoneType) - 1]
            if effective_arg in SIMPLE_TYPES:
                return effective_arg
    logger.warning(f"Annotation {annotation!r} is too complicated to parse.")
    return None


class EnvField:
    def __init__(
        self,
        alias: str | None = None,
        description: str | None = None,
        default: Any = UNSET,
        env_proxy: EnvProxy | None = None,
        env_prefix: str | None = None,
        strict: bool | None = None,
        allow_set: bool | None = None,
        type_hint: TypeHint | None = None,
        optional: bool | None = None,
        convert_using: Callable[[str], Any] | None = None,
        type_name: str | None = None,
    ) -> None:
        self.alias = alias
        self.description = description
        self._env_proxy = env_proxy
        self._env_prefix = env_prefix
        self._default = default
        self._field_name: str | None = None
        self._owner: type[EnvConfig] | None = None
        self._value_getter: Callable[[str, Any], Any] | None = None
        self._strict = strict
        self._allow_set = allow_set
        self.optional = optional
        self.type_hint = type_hint
        self._convert_using = convert_using
        self.type_name = type_name
        if convert_using is not None and type_hint is not None:
            warnings.warn(
                f"convert_using overrides type_hint={type_hint!r}; type_hint will be ignored.",
                UserWarning,
                stacklevel=3,
            )
        self._annotation: Any = None

    @property
    def key_name(self) -> str:
        if self.alias:
            return self.alias
        return self.field_name

    @property
    def field_name(self) -> str:
        if self._field_name is not None:
            return self._field_name
        raise RuntimeError("Field was not properly initialized and has no name.")

    @property
    def owner(self) -> type[EnvConfig]:
        if self._owner is not None:
            return self._owner
        raise RuntimeError("Field was not properly initialized and has no owner.")

    @property
    def strict(self) -> bool:
        if self._strict is not None:
            return self._strict
        if (inherited_value := getattr(self.owner, "_strict", None)) is not None:
            self._strict = bool(inherited_value)
            return self._strict
        # Default to strict=True
        return True

    @property
    def allow_set(self) -> bool:
        if self._allow_set is not None:
            return self._allow_set
        if (inherited_value := getattr(self.owner, "_allow_set", None)) is not None:
            self._allow_set = bool(inherited_value)
            return self._allow_set
        # Default to allow_set=False
        return False

    @cached_property
    def default(self) -> Any:
        if self._default is not UNSET:
            return self._default
        if self.optional or self.annotated_optional:
            return None
        return UNSET

    @cached_property
    def annotated_optional(self) -> bool:
        if self._annotation is None:
            return False
        if get_origin(self._annotation) is None:
            return False
        return NoneType in get_args(self._annotation)

    @cached_property
    def simplified_annotation(self) -> Any:
        return _get_simplified_annotation(self._annotation)

    @cached_property
    def resolved_type_name(self) -> str:
        """The field's type label — the value shown in exported ``.env`` files.

        Resolution order:

        1. Explicit ``type_name=`` argument, if given.
        2. The field's annotation, when it is a simple type (``int``, ``str``,
           an enum class, …).
        3. ``convert_using.__name__``, unless it would be ``"<lambda>"``.
        4. The ``type_hint=`` value, if given.
        5. ``"unknown type"`` as a last resort.
        """
        if self.type_name is not None:
            return self.type_name
        sa = self.simplified_annotation
        if sa is Any:
            return "any"
        if isinstance(sa, type):
            return sa.__name__
        if self._convert_using is not None:
            name: str | None = getattr(self._convert_using, "__name__", None)
            if name and name != "<lambda>":
                return name
            return "custom"
        if self.type_hint is not None:
            return self.type_hint
        return "unknown type"

    @cached_property
    def value_getter(self) -> Callable[[str, Any], Any]:
        """The callable that fetches and types this field's env value.

        Called internally on every attribute access; usually you don't
        need to invoke it yourself. ``convert_using`` takes precedence
        over ``type_hint``, which takes precedence over the annotation.
        """
        if self._convert_using is not None:
            return self._build_convert_using_getter()
        if self.type_hint is not None:
            return _get_type_hint_handler(self.type_hint, self.env_proxy)
        if self._annotation is None:
            return self._handle_missing_annotation()
        return self._handle_annotation()

    def _build_convert_using_getter(self) -> Callable[[str, Any], Any]:
        proxy = self.env_proxy
        convert = self._convert_using
        assert convert is not None  # narrowed by caller  # noqa: S101
        target = self.resolved_type_name

        def _getter(key: str, default: Any) -> Any:
            raw = proxy._get_raw(key)
            if raw is None:
                return proxy._resolve_default(key, default)
            try:
                return convert(raw)
            except Exception as exc:
                raise EnvValueError(key, raw, target) from exc

        return _getter

    def _handle_missing_annotation(self) -> Callable[[str, Any], Any]:
        msg = f"No type annotation nor type hint found for field {self.field_name!r}."
        if self.strict:
            raise ValueError(f"{msg} {STRING_ERROR_TO_WARNING}")
        logger.warning("%s Falling back to 'Any'. %s", msg, STRING_WARNING_TO_ERROR)
        return self.env_proxy.get_any

    def _handle_annotation(self) -> Callable[[str, Any], Any]:
        if self.simplified_annotation is not None:
            return _annotation_to_method(self.env_proxy)[self.simplified_annotation]
        msg = (
            f"Failed to determine value getter for field {self.field_name!r}. "
            "No type hint was provided and the annotation is too complicated."
        )
        if self.strict:
            raise RuntimeError(f"{msg} {STRING_ERROR_TO_WARNING}")
        logger.warning("%s %s", msg, STRING_WARNING_TO_ERROR)
        return self.env_proxy.get_any

    @property
    def env_key(self) -> str:
        return self.env_proxy._get_key(self.key_name)

    @cached_property
    def env_proxy(self) -> EnvProxy:
        if self._env_proxy is not None:
            logger.debug("Using provided EnvProxy instance.")
            return self._env_proxy
        if self._env_prefix is not None:
            logger.debug("Creating EnvProxy instance using provided env_prefix %r.", self._env_prefix)
            self._env_proxy = EnvProxy(prefix=self._env_prefix)
            return self._env_proxy
        if (inherited_value := getattr(self.owner, "env_proxy", None)) is not None and isinstance(
            inherited_value, EnvProxy
        ):
            logger.debug("Using EnvProxy instance found on owner EnvConfig.")
            self._env_proxy = inherited_value
            return self._env_proxy
        logger.debug(
            "No EnvProxy instance found on Field nor on owner EnvConfig, creating a new one with an empty prefix."
        )
        self._env_proxy = EnvProxy()
        return self._env_proxy

    def __set_name__(self, owner: type[EnvConfig], field_name: str) -> None:
        if field_name in reserved_attributes or field_name.startswith("_"):
            raise ValueError(f"Field name {field_name!r} is reserved for internal use.")
        self._owner = owner
        self._field_name = field_name
        self._annotation = get_annotations(owner).get(field_name)

    def __set__(self, instance: EnvConfig, value: Any) -> None:
        if instance.__dict__.get("_frozen") is not None:
            raise TypeError(
                f"Cannot set field {self.field_name!r} on {instance.__class__.__name__!r}: instance is frozen."
            )
        if not self.allow_set:
            raise TypeError(f"Field {self.field_name!r} of {instance.__class__.__name__!r} is read-only.")
        overrides = instance.__dict__.get("_overrides")
        if overrides is not None and self.field_name in overrides:
            overrides[self.field_name] = value
        key = self.env_proxy._get_key(self.key_name)
        logger.debug("Setting %r in os.environ.", key)
        if value is None:
            if key in os.environ:
                del os.environ[key]
        else:
            os.environ[key] = str(value)

    def __get__(self, instance: EnvConfig | None, instance_type: type[EnvConfig]) -> Any:
        if instance is None:
            return self
        frozen = instance.__dict__.get("_frozen")
        if frozen is not None:
            return frozen[self.field_name]
        overrides = instance.__dict__.get("_overrides")
        if overrides is not None and self.field_name in overrides:
            return overrides[self.field_name]
        return self.value_getter(self.key_name, self.default)


def Field(  # noqa: N802
    alias: str | None = None,
    description: str | None = None,
    default: Any = UNSET,
    env_proxy: EnvProxy | None = None,
    env_prefix: str | None = None,
    strict: bool | None = None,
    allow_set: bool | None = None,
    type_hint: TypeHint | None = None,
    convert_using: Callable[[str], Any] | None = None,
    type_name: str | None = None,
) -> Any:
    # A factory function that will help us deal with our descriptor's typehinting issues.
    return EnvField(
        alias,
        description,
        default,
        env_proxy,
        env_prefix,
        strict,
        allow_set,
        type_hint,
        convert_using=convert_using,
        type_name=type_name,
    )


class FieldDocsBuilder:
    __env_field_doc_template = "# {key_name} ({field_type}) [{required}]\n{description}{env_key}={default}\n"

    def __init__(self, fields: list[EnvField]) -> None:
        self.fields = list(fields)

    @staticmethod
    def _get_field_type(field: EnvField) -> str:
        return field.resolved_type_name

    @staticmethod
    def _get_field_default(field: EnvField) -> str:
        if field.default in (UNSET, None):
            return ""
        if not isinstance(field.default, str) and field.type_hint == "json":
            try:
                return json.dumps(field.default)
            except (ValueError, TypeError) as error:
                raise ValueError(
                    f"Failed to export default for field {field.field_name!r}. "
                    "Its default value cannot be encoded as a JSON."
                ) from error
        if isinstance(field.default, list):
            return ",".join(field.default)
        return str(field.default)

    def generate_env_file_content(self, include_defaults: bool = True, sort_by_name: bool = False) -> str:
        lines: list[str] = []
        if sort_by_name:
            self.fields.sort(key=lambda field: field.key_name)
        for field in self.fields:
            required = "required" if field.default is UNSET else "optional"
            default = self._get_field_default(field) if include_defaults else ""
            field_type = self._get_field_type(field)
            multiline_description = ""
            if field.description:
                multiline_description = "\n# ".join(field.description.splitlines())
                multiline_description = "# " + multiline_description.rstrip("\n") + "\n"
            lines.append(
                self.__env_field_doc_template.format(
                    key_name=field.key_name,
                    field_type=field_type,
                    required=required,
                    description=multiline_description,
                    env_key=field.env_key,
                    default=default,
                )
            )
        return "\n".join(lines)


@dataclass_transform(kw_only_default=True)
class EnvConfig:
    """A base class for your configurations based on environment variables.

    Use fields along with Field factory to easily describe your configuration in an self-documenting way.

    The constructor accepts keyword arguments to override individual fields on a
    per-instance basis. Overrides take precedence over the environment, allowing
    callers to layer env-derived config with values from any other source — a
    config file, CLI arguments, programmatic wiring, fixtures — without mutating
    ``os.environ``. Override values are keyed by Python field name (not env-var
    key), are used as-is (no type conversion), and shadow the environment for
    reads on this instance only::

        cfg = MyConfig(timeout=5, services=["a", "b"])

    Unknown override keys raise :class:`ValueError`. Fields with ``allow_set=False``
    can still be initialized via override but cannot be reassigned afterwards.
    """

    _valid_fields: ClassVar[frozenset[str]] = frozenset()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        seen: set[str] = set()
        valid: set[str] = set()
        # Leaf-to-root: the first occurrence of each name wins, so a subclass
        # that shadows an inherited EnvField with a non-EnvField correctly
        # excludes that name from the valid override set.
        for klass in cls.__mro__:
            for name, attr in vars(klass).items():
                if name in seen:
                    continue
                seen.add(name)
                if isinstance(attr, EnvField):
                    valid.add(name)
        cls._valid_fields = frozenset(valid)

    def __init__(self, **overrides: Any) -> None:
        unknown = overrides.keys() - self._valid_fields
        if unknown:
            raise ValueError(
                f"Unknown override key(s) for {type(self).__name__}: {sorted(unknown)}. "
                f"Valid field names: {sorted(self._valid_fields)}"
            )
        self._overrides: dict[str, Any] = dict(overrides)
        self._frozen: dict[str, Any] | None = None

    @property
    def is_frozen(self) -> bool:
        """``True`` if :meth:`freeze` has been called on this instance, else ``False``."""
        return self._frozen is not None

    def _iter_resolved_fields(self) -> Iterator[tuple[str, EnvField, Any]]:
        """Yield ``(name, field, resolved_value)`` for every Field on this instance.

        Resolution mirrors :meth:`EnvField.__get__`: overrides win over env. Raises
        whatever ``value_getter`` raises (e.g. :class:`ValueError` for missing
        required fields). Frozen state is intentionally ignored — this helper is
        used to *build* a frozen snapshot.
        """
        for name in self._valid_fields:
            field: EnvField = getattr(type(self), name)
            if name in self._overrides:
                yield name, field, self._overrides[name]
            else:
                yield name, field, field.value_getter(field.key_name, field.default)

    def freeze(self) -> None:
        """Resolve every field once and lock the instance to the resulting values.

        After calling :meth:`freeze`:

        - Every attribute read returns the cached value (a single dict lookup).
        - Assignment via ``cfg.field = ...`` raises :class:`TypeError`, even
          for fields declared with ``allow_set=True``. Any such fields are
          listed in a :class:`UserWarning` emitted by this call.
        - :attr:`is_frozen` becomes ``True``.

        Calling :meth:`freeze` again on an already-frozen instance is a no-op
        and emits a :class:`UserWarning`.
        """
        if self._frozen is not None:
            warnings.warn(
                f"{type(self).__name__} is already frozen; freeze() is a no-op.",
                stacklevel=2,
            )
            return
        snapshot: dict[str, Any] = {}
        mutable: list[str] = []
        for name, field, value in self._iter_resolved_fields():
            snapshot[name] = value
            if field.allow_set:
                mutable.append(name)
        if mutable:
            warnings.warn(
                f"freeze() locked fields with allow_set=True on {type(self).__name__}: "
                f"{sorted(mutable)}. Further assignment will raise TypeError.",
                stacklevel=2,
            )
        self._frozen = snapshot

    def validate(self) -> None:
        """Eagerly resolve every field and raise if anything is missing or malformed.

        Failures from individual fields are collected and re-raised as a single
        :class:`EnvValidationError` whose :attr:`errors` mapping contains the
        per-field exceptions. Fields supplied as constructor overrides are
        already typed Python values, so they are not re-validated.

        Returns ``None`` on success. Does not mutate the instance — call
        :meth:`freeze` afterwards if you also want to lock in the values.
        """
        errors: dict[str, EnvProxyError] = {}
        for name in self._valid_fields:
            if name in self._overrides:
                continue
            try:
                field: EnvField = getattr(type(self), name)
                field.value_getter(field.key_name, field.default)
            except EnvProxyError as exc:
                errors[name] = exc
        if errors:
            raise EnvValidationError(type(self).__name__, errors)

    @classmethod
    def __generate_env_file_content(
        cls: type[EnvConfig], include_defaults: bool = True, sort_by_name: bool = False
    ) -> str:
        fields: list[EnvField] = []
        for field_name, field in vars(cls).items():
            if not isinstance(field, EnvField):
                logger.debug("Skipping class variable %r, not a Field.", field_name)
                continue
            fields.append(field)
        builder = FieldDocsBuilder(fields)
        return builder.generate_env_file_content(include_defaults=include_defaults, sort_by_name=sort_by_name)

    @classmethod
    def export_env(
        cls: type[EnvConfig],
        file_or_path: Path | str | TextIO,
        include_defaults: bool = True,
        sort_by_name: bool = False,
    ) -> None:
        content = cls.__generate_env_file_content(include_defaults=include_defaults, sort_by_name=sort_by_name)
        if isinstance(file_or_path, str | Path):
            Path(file_or_path).write_text(content, encoding="utf-8")
            return
        file_or_path.write(content)
