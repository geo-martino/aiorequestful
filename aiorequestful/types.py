"""
All core type hints to use throughout the entire package.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence, MutableSequence, Collection, Mapping, MutableMapping, Callable, \
    Awaitable
from http import HTTPMethod
from types import SimpleNamespace
from typing import TypedDict, Any, Union, NotRequired

from aiohttp import BasicAuth, ClientResponse, ClientTimeout, Fingerprint
# noinspection PyProtectedMember
from aiohttp.client import SSLContext
# noinspection PyProtectedMember
from aiohttp.helpers import _SENTINEL
from aiohttp.typedefs import LooseCookies, LooseHeaders, StrOrURL
from yarl import URL

type UnitIterable[T] = T | Iterable[T]
type UnitCollection[T] = T | Collection[T]
type UnitSequence[T] = T | Sequence[T]
type UnitMutableSequence[T] = T | MutableSequence[T]
type UnitList[T] = T | list[T]

Number = int | float

ImmutableHeaders = Mapping[str, str]
MutableHeaders = MutableMapping[str, str]
Headers = dict[str, str]

JSON_VALUE = str | int | float | list | dict | bool | None
ImmutableJSON = Mapping[str, JSON_VALUE]
MutableJSON = MutableMapping[str, JSON_VALUE]
JSON = dict[str, JSON_VALUE]

URLInput = str | URL
MethodInput = str | HTTPMethod


class RequestKwargs(TypedDict):
    """
    TypedDict for kwargs relating to an HTTP request.

    Arguments passed through to `.aiohttp.ClientSession.request`.
    See aiohttp reference for more info on available kwargs:
    https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
    """
    method: MethodInput
    url: URLInput
    params: NotRequired[Mapping[str, str]]
    data: NotRequired[Any]
    json: NotRequired[Any]
    cookies: NotRequired[LooseCookies]
    headers: NotRequired[LooseHeaders]
    skip_auto_headers: NotRequired[Iterable[str]]
    auth: NotRequired[BasicAuth]
    allow_redirects: NotRequired[bool]
    max_redirects: NotRequired[int]
    compress: NotRequired[str]
    chunked: NotRequired[bool]
    expect100: NotRequired[bool]
    raise_for_status: NotRequired[
        Union[bool, Callable[[ClientResponse], Awaitable[None]]]
    ]
    read_until_eof: NotRequired[bool]
    proxy: NotRequired[StrOrURL]
    proxy_auth: NotRequired[BasicAuth]
    timeout: NotRequired[Union[ClientTimeout, _SENTINEL]]
    verify_ssl: NotRequired[bool]
    fingerprint: NotRequired[bytes]
    ssl_context: NotRequired[SSLContext]
    ssl: NotRequired[Union[SSLContext, bool, Fingerprint]]
    server_hostname: NotRequired[str]
    proxy_headers: NotRequired[LooseHeaders]
    trace_request_ctx: NotRequired[SimpleNamespace]
    read_bufsize: NotRequired[int]
    auto_decompress: NotRequired[bool]
    max_line_size: NotRequired[int]
    max_field_size: NotRequired[int]
