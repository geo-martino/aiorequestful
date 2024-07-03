import os
import shutil
from pathlib import Path

import pytest
from _pytest.fixtures import SubRequest
from aioresponses import aioresponses


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
