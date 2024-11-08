"""EnvConfig allows you to create configuration objects based on env variables declaratively with
auto-documenting approach.
"""

import json
import logging
import os
from collections.abc import Callable
from functools import cached_property, partial
from inspect import get_annotations
from pathlib import Path
from types import NoneType, UnionType
from typing import Any, Literal, TextIO, TypeVar, get_args, get_origin

from env_proxy.env_proxy import EnvProxy

from ._sentinel import UNSET

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


class FieldDocsBuilder:
    __env_field_doc_template = "# {key_name} ({field_type}) [{required}]\n{description}{env_key}={default}\n"

    def __init__(self, fields: list["EnvField"]) -> None:
        self.fields = list(fields)

    @staticmethod
    def _get_field_type(field: "EnvField") -> str:
        if field.type_hint is not None:
            return field.type_hint
        if field.simplified_annotation is not None:
            if isinstance(field.simplified_annotation, type):
                return field.simplified_annotation.__name__
            return str(field.simplified_annotation).lower()  # pragma: no cover, unreachable
        return "unknown type"

    @staticmethod
    def _get_field_default(field: "EnvField") -> str:
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


class EnvConfig:
    """A base class for your configurations based on environment variables.

    Use fields along with Field factory to easily describe your configuration in an self-documenting way.
    """

    @classmethod
    def __generate_env_file_content(
        cls: "type[EnvConfig]", include_defaults: bool = True, sort_by_name: bool = False
    ) -> str:
        fields: list[EnvField] = []
        for field_name, field in vars(cls).items():
            if not isinstance(field, EnvField):
                logger.debug(f"Skipping class variable {field_name!r}, not a Field.")
                continue
            fields.append(field)
        builder = FieldDocsBuilder(fields)
        return builder.generate_env_file_content(include_defaults=include_defaults, sort_by_name=sort_by_name)

    @classmethod
    def export_env(
        cls: "type[EnvConfig]",
        file_or_path: Path | str | TextIO,
        include_defaults: bool = True,
        sort_by_name: bool = False,
    ) -> None:
        content = cls.__generate_env_file_content(include_defaults=include_defaults, sort_by_name=sort_by_name)
        if isinstance(file_or_path, str | Path):
            Path(file_or_path).write_text(content, encoding="utf-8")
            return
        file_or_path.write(content)


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
    def value_getter(self) -> Callable[[str, Any], Any]:
        """
        Determines and returns the appropriate value getter method based on type hints or annotations.
        Returns:
            Callable[[str, Any], Any]: A function that retrieves the value from the environment proxy.
        Raises:
            ValueError: If no type annotation or type hint is found and strict mode is enabled.
            RuntimeError: If the annotation is too complicated and strict mode is enabled.
        """

        if self.type_hint is not None:
            return _get_type_hint_handler(self.type_hint, self.env_proxy)
        if self._annotation is None:
            msg = f"No type annotation nor type hint found for field {self.field_name!r}."
            if self.strict:
                raise ValueError(f"{msg} {STRING_ERROR_TO_WARNING}")
            logger.warning(f"{msg} Falling back to 'Any'. {STRING_WARNING_TO_ERROR}")
            return self.env_proxy.get_any
        type_to_method_map: dict[Any, Callable[[str, Any], Any]] = {
            Any: self.env_proxy.get_any,
            bool: self.env_proxy.get_bool,
            float: self.env_proxy.get_float,
            int: self.env_proxy.get_int,
            list: self.env_proxy.get_list,
            str: self.env_proxy.get_str,
        }
        if self.simplified_annotation is not None:
            return type_to_method_map[self.simplified_annotation]
        msg = (
            f"Failed to determine value getter for field {self.field_name!r}. "
            "No type hint was provided and the annotation is too complicated."
        )
        if self.strict:
            raise RuntimeError(f"{msg} {STRING_ERROR_TO_WARNING}")
        logger.warning(f"{msg} {STRING_WARNING_TO_ERROR}")
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
            logger.debug(f"Creating EnvProxy instance using provided env_prefix {self._env_prefix!r}.")
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
        if not self.allow_set:
            raise TypeError(f"Field {self.field_name!r} of {instance.__class__.__name__!r} is read-only.")
        key = self.env_proxy._get_key(self.key_name)
        logger.debug(f"Setting {key!r} in os.environ.")
        os.environ[key] = str(value)

    def __get__(self, instance: EnvConfig, instance_type: type[EnvConfig]) -> Any:
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
) -> Any:
    # A factory function that will help us deal with our descriptor's typehinting issues.
    return EnvField(alias, description, default, env_proxy, env_prefix, strict, allow_set, type_hint)
