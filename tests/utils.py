from enum import Enum
from pathlib import Path
from typing import Any

from aiorequestful.response.payload import PayloadHandler
from aiorequestful.response.status import StatusHandler

path_tests = Path(__file__).parent
path_root = path_tests.parent
path_resources = path_tests.joinpath("__resources")

path_token = path_resources.joinpath("token").with_suffix(".json")


# noinspection SpellCheckingInspection
def idfn(value: Any) -> str | None:
    """Generate test ID for Spotify API tests"""
    if isinstance(value, Enum):
        return value.name
    elif isinstance(value, ParamTester):
        return value.name
    elif isinstance(value, PayloadHandler | StatusHandler):
        return value.__class__.__name__
    return value


class ParamTester:
    """Identifies this class as one that has a special name for logging the ID when used as a pytest param"""
    @property
    def name(self) -> str:
        """The name to use when logging the ID of this param"""
        return self.__class__.__name__
