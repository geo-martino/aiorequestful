"""
All core type hints to use throughout the entire package.
"""
from __future__ import annotations
from collections.abc import Iterable, Sequence, MutableSequence, Collection, Mapping, MutableMapping
from enum import Enum
from typing import Self

from yarl import URL

from aiorequestful.exception import MethodError

type UnitIterable[T] = T | Iterable[T]
type UnitCollection[T] = T | Collection[T]
type UnitSequence[T] = T | Sequence[T]
type UnitMutableSequence[T] = T | MutableSequence[T]
type UnitList[T] = T | list[T]

type ImmutableHeaders = Mapping[str, str]
type MutableHeaders = MutableMapping[str, str]
type Headers = dict[str, str]

type JSON_VALUE = str | int | float | list | dict | bool | None
type ImmutableJSON = Mapping[str, JSON_VALUE]
type MutableJSON = MutableMapping[str, JSON_VALUE]
type JSON = dict[str, JSON_VALUE]

type URLInput = str | URL
type MethodInput = str | Method


class Method(Enum):
    """HTTP request method types."""
    GET = 1
    POST = 2
    PUT = 3
    DELETE = 4
    OPTIONS = 5
    HEAD = 6
    PATCH = 7

    @classmethod
    def from_name(cls, name: str) -> Self:
        try:
            return next(enum for enum in cls if enum.name == name.upper())
        except StopIteration:
            raise MethodError(name)

    @classmethod
    def get(cls, method: MethodInput) -> Self:
        if isinstance(method, cls):
            return method
        return cls.from_name(method)
