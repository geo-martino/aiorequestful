"""
Generic utility functions and classes which can be used throughout the entire package.
"""
from collections.abc import Iterator, Iterable
from typing import Any

from aiohttp import RequestInfo
from yarl import URL

from aiorequestful.exception import AIORequestfulImportError
from aiorequestful.types import UnitIterable


def get_iterator(value: Any) -> Iterator | None:
    """
    Safely get an iterator.

    When a string is given, the iterator will be size 1 where the first element is the given string.
    """
    if value is None:
        return iter(())
    elif isinstance(value, Iterator):
        return value
    elif isinstance(value, str) or isinstance(value, RequestInfo) or not isinstance(value, Iterable):
        value = (value,)
    return iter(value)


def format_url_log(method: str, url: URL, messages: UnitIterable[Any]) -> str:
    """Format a request for a given ``url`` of a given ``method`` appending the given ``messages``"""
    url = str(url.with_query(None))
    url_pad_map = [30, 40, 70, 100]
    url_pad = next((pad for pad in url_pad_map if len(url) < pad), url_pad_map[-1])

    return f"{method.upper():<7}: {url:<{url_pad}} | {" | ".join(map(str, get_iterator(messages)))}"


def required_modules_installed(modules: list, this: object = None) -> bool:
    """Check the required modules are installed, raise :py:class:`AIORequestfulImportError` if not."""
    modules_installed = all(module is not None for module in modules)
    if not modules_installed and this is not None:
        names = [name for name, obj in globals().items() if obj in modules and not name.startswith("_")]
        if isinstance(this, str):
            message = f"Cannot run {this}. Required modules: {", ".join(names)}"
        else:
            message = f"Cannot create {this.__class__.__name__} object. Required modules: {", ".join(names)}"

        raise AIORequestfulImportError(message)

    return modules_installed
