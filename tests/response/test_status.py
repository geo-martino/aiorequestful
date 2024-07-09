from abc import ABC, abstractmethod
from copy import copy
from http import HTTPStatus
from random import choice

import pytest
from aiohttp import ClientResponse, ClientSession, ClientRequest
from aiohttp.helpers import TimerNoop
from multidict import CIMultiDictProxy, CIMultiDict

from aiorequestful.request.timer import StepCountTimer
from aiorequestful.response.exception import ResponseError, StatusHandlerError
from aiorequestful.response.status import StatusHandler, ClientErrorStatusHandler, UnauthorisedStatusHandler, \
    RateLimitStatusHandler
from tests.auth.utils import MockAuthoriser


class StatusHandlerTester(ABC):

    @abstractmethod
    def handler(self) -> StatusHandler:
        raise NotImplementedError

    @pytest.fixture
    def response_valid(self, handler: ClientErrorStatusHandler, dummy_response: ClientResponse) -> ClientResponse:
        response = copy(dummy_response)
        response.status = choice(handler.status_codes)
        return response

    @pytest.fixture
    def response_invalid(self, handler: ClientErrorStatusHandler, dummy_response: ClientResponse) -> ClientResponse:
        response = copy(dummy_response)
        response.status = choice([enum for enum in HTTPStatus if enum.value not in handler.status_codes]).value
        return response

    @staticmethod
    async def test_match(
            handler: ClientErrorStatusHandler, response_valid: ClientResponse, response_invalid: ClientResponse
    ):
        assert handler.match(response_valid)
        assert not handler.match(response_invalid)

        with pytest.raises(StatusHandlerError):
            assert not handler.match(response_invalid, fail_on_error=True)

        with pytest.raises(StatusHandlerError):
            await handler(response_invalid)

    @staticmethod
    async def test_handle_invalid_response(handler: ClientErrorStatusHandler, response_invalid: ClientResponse):
        with pytest.raises(StatusHandlerError):
            await handler(response_invalid)


class TestClientErrorStatusHandler(StatusHandlerTester):

    @pytest.fixture
    def handler(self) -> ClientErrorStatusHandler:
        return ClientErrorStatusHandler()

    async def test_handle(self, handler: ClientErrorStatusHandler, response_valid: ClientResponse):
        with pytest.raises(ResponseError):  # always raises an error
            await handler(response_valid)


class TestUnauthorisedStatusHandler(StatusHandlerTester):

    @pytest.fixture
    def handler(self) -> UnauthorisedStatusHandler:
        return UnauthorisedStatusHandler()

    async def test_handle(self, handler: UnauthorisedStatusHandler, response_valid: ClientResponse):
        authoriser = MockAuthoriser()
        session = ClientSession()

        # authoriser and session not supplied
        assert not await handler(response_valid)
        assert not await handler(response_valid, authoriser=authoriser)
        assert not await handler(response_valid, session=session)

        assert await handler(response_valid, authoriser=authoriser, session=session)
        assert session.headers == await authoriser()


class TestRateLimitStatusHandler(StatusHandlerTester):

    @pytest.fixture
    def handler(self) -> RateLimitStatusHandler:
        return RateLimitStatusHandler()

    async def test_handle(
            self, handler: RateLimitStatusHandler, dummy_request: ClientRequest
    ):
        # noinspection PyTypeChecker,PyProtectedMember
        response = ClientResponse(
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
        response.status = choice(handler.status_codes)

        response._headers = CIMultiDictProxy(CIMultiDict({"retry-after": 1}))
        assert await handler(response)

        retry_timer = StepCountTimer(initial=0.1, count=0, step=0.01)
        with pytest.raises(ResponseError):  # retry after time > total retry timer
            await handler(response, retry_timer=retry_timer)

    async def test_handle_timers(self, handler: RateLimitStatusHandler, response_valid: ClientResponse):
        wait_timer = StepCountTimer(initial=0.1, count=2, step=0.1)
        retry_timer = StepCountTimer(initial=0.1, count=3, step=0.1)

        # no retry-after header, increases wait time
        assert not await handler(response_valid, wait_timer=wait_timer, retry_timer=retry_timer)
        assert wait_timer.value > wait_timer.initial
        assert wait_timer.value < wait_timer.final
        assert retry_timer.value == retry_timer.initial

        # maxes wait time
        assert not await handler(response_valid, wait_timer=wait_timer, retry_timer=retry_timer)
        assert wait_timer.value == wait_timer.final
        assert retry_timer.value == retry_timer.initial
