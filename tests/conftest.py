import asyncio
import logging.config
import os
import shutil
from asyncio import StreamReader
from http import HTTPMethod
from pathlib import Path
from unittest import mock

import pytest
import yaml
from _pytest.fixtures import SubRequest
from aiohttp import ClientRequest, ClientResponse
# noinspection PyProtectedMember
from aiohttp.helpers import TimerNoop
from aioresponses import aioresponses
from multidict import CIMultiDictProxy
from yarl import URL

from aiorequestful import MODULE_ROOT
from tests.utils import path_resources


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# noinspection PyUnusedLocal
@pytest.hookimpl
def pytest_configure(config: pytest.Config):
    """Loads logging config"""
    config_file = path_resources.joinpath("test_logging").with_suffix(".yml")
    if not config_file.is_file():
        return

    with open(config_file, "r", encoding="utf-8") as file:
        log_config = yaml.full_load(file)

    for formatter in log_config["formatters"].values():  # ensure ANSI colour codes in format are recognised
        formatter["format"] = formatter["format"].replace(r"\33", "\33")

    log_config["loggers"][MODULE_ROOT] = log_config["loggers"]["test"]
    logging.config.dictConfig(log_config)


@pytest.fixture
def path(request: pytest.FixtureRequest | SubRequest, tmp_path: Path) -> Path:
    """
    Copy the path of the source file to the test cache for this test and return the cache path.
    Deletes the test folder when test is done.
    """
    if hasattr(request, "param"):
        src_path = request.param
    else:  # assume path is given at the top-level fixture, get param from this request
        # noinspection PyProtectedMember
        src_path = request._pyfuncitem.callspec.params[request._parent_request.fixturename]

    src_path = Path(src_path)
    trg_path = tmp_path.joinpath(src_path.name)

    os.makedirs(trg_path.parent, exist_ok=True)
    shutil.copyfile(src_path, trg_path)

    yield trg_path

    shutil.rmtree(trg_path.parent)


@pytest.fixture
def requests_mock():
    """Yields an initialised :py:class:`aioresponses` object for mocking aiohttp requests as a pytest.fixture."""
    with aioresponses() as m:
        yield m


@pytest.fixture
def dummy_request() -> ClientRequest:
    return ClientRequest(
        method=HTTPMethod.GET.name,
        url=URL.build(scheme="https", host="localhost", path="/test"),
    )


@pytest.fixture
def dummy_response(dummy_request: ClientRequest) -> ClientResponse:
    # noinspection PyTypeChecker,PyProtectedMember
    resp = ClientResponse(
        method=dummy_request.method,
        url=dummy_request.url,
        writer=None,
        continue100=None,
        timer=TimerNoop(),
        request_info=dummy_request.request_info,
        traces=[],
        loop=dummy_request.loop,
        session=dummy_request._session,
    )

    # response status
    resp.version = dummy_request.version
    resp.status = 200
    resp.reason = "test"

    # headers
    resp._headers = CIMultiDictProxy(dummy_request.headers)
    resp._raw_headers = ()

    # noinspection PyProtectedMember
    resp.content = StreamReader(loop=resp._loop)
    resp.content.feed_data("response text".encode())
    resp.content.feed_eof()

    return resp
