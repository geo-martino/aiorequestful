import json
from collections.abc import Mapping
from http import HTTPMethod
from typing import Any
from unittest.mock import AsyncMock

import aiohttp
import pytest
from aiohttp import ClientResponse
from aioresponses import aioresponses
from aioresponses.core import RequestCall
from pytest_mock import MockerFixture
from yarl import URL

from aiorequestful.auth import Authoriser
from aiorequestful.auth.basic import BasicAuthoriser
from aiorequestful.cache.backend.base import ResponseCache
from aiorequestful.cache.backend.sqlite import SQLiteCache
from aiorequestful.cache.session import CachedSession
from aiorequestful.exception import RequestError
from aiorequestful.request import RequestHandler
from aiorequestful.response.exception import ResponseError
from aiorequestful.response.payload import JSONPayloadHandler, StringPayloadHandler
from aiorequestful.response.status import ClientErrorStatusHandler, RateLimitStatusHandler, UnauthorisedStatusHandler
from aiorequestful.timer import StepCountTimer, Timer
from tests.cache.backend.utils import MockResponseRepositorySettings


class TestRequestHandler:

    @pytest.fixture
    def url(self) -> URL:
        """Yield a simple :py:class:`URL` object"""
        return URL("http://test.com")

    @pytest.fixture
    def cache(self) -> ResponseCache:
        """Yield a simple :py:class:`ResponseCache` object"""
        return SQLiteCache.connect_with_in_memory_db()

    @pytest.fixture
    def authoriser(self, token: dict[str, Any]) -> Authoriser:
        """Yield a simple :py:class:`Authoriser` object"""
        return BasicAuthoriser(login="test")

    @pytest.fixture
    def request_handler(self, authoriser: Authoriser, cache: ResponseCache) -> RequestHandler:
        """Yield a simple :py:class:`RequestHandler` object"""
        return RequestHandler.create(
            authoriser=authoriser,
            cache=cache,
            headers={"Content-Type": "application/json"},
            response_handlers=(),
            payload_handler=JSONPayloadHandler(),
        )

    @pytest.fixture
    def token(self) -> dict[str, Any]:
        """Yield a basic token example"""
        return {
            "access_token": "fake access token",
            "token_type": "Bearer",
            "scope": "test-read"
        }

    @pytest.fixture
    def mock_handle_response(self, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            RequestHandler, attribute="_handle_response", side_effect=AsyncMock(return_value=False),
        )

    @pytest.fixture
    def mock_log_response(self, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            RequestHandler, attribute="_log_response", side_effect=AsyncMock,
        )

    @pytest.fixture
    def mock_retry(self, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            RequestHandler, attribute="_retry", side_effect=AsyncMock,
        )

    async def test_init(self, token: dict[str, Any], authoriser: Authoriser, cache: ResponseCache):
        handler = RequestHandler.create(authoriser=authoriser, cache=cache)
        assert handler.authoriser == authoriser
        assert not isinstance(handler.session, CachedSession)

        handler = RequestHandler.create(authoriser=authoriser, cache=cache)
        assert handler.closed

    async def test_context_management(self, request_handler: RequestHandler, cache: ResponseCache):
        with pytest.raises(RequestError):
            await request_handler.authorise()

        request_handler.payload_handler = JSONPayloadHandler()

        async with cache:  # add some repositories to check whether payload handler is set on them
            await cache.create_repository(MockResponseRepositorySettings(name="test1"))
            await cache.create_repository(MockResponseRepositorySettings(name="test2"))

        assert cache.values()
        for repository in cache.values():
            assert isinstance(repository.settings.payload_handler, StringPayloadHandler)

        async with request_handler as handler:
            assert isinstance(handler.session, CachedSession)

            for k, v in (await handler.authoriser).items():
                assert handler.session.headers.get(k) == v

            for repository in cache.values():
                assert not isinstance(repository.settings.payload_handler, StringPayloadHandler)
                assert repository.settings.payload_handler == handler.payload_handler

            # set back via property assignment
            request_handler.payload_handler = StringPayloadHandler()
            for repository in cache.values():
                assert isinstance(repository.settings.payload_handler, StringPayloadHandler)

    async def test_kwargs_cleaned(self, request_handler: RequestHandler, url: URL, requests_mock: aioresponses):
        url = url.joinpath("test")
        expected = {"key": "value"}
        requests_mock.get(url, status=200, payload=expected, repeat=False)
        valid_kwargs = dict(
            headers={"Content-Type": "application/json"},
            json={"key": "value"},
            allow_redirects=False,
        )

        async with request_handler as handler:
            result = await handler.get(url=url, persist=False, invalid_param="value", **valid_kwargs)
            valid_kwargs["headers"] |= handler.session.headers

        assert result == expected

        # check that only valid kwargs were passed
        request: RequestCall = next(
            req for (request_method, request_url), requests in requests_mock.requests.items() for req in requests
            if request_method == HTTPMethod.GET and request_url == url
        )
        # some remapping is necessary to get the kwargs back to the original state
        actual_kwargs = {k: dict(v) if isinstance(v, Mapping) else v for k, v in request.kwargs.items()}
        actual_kwargs["json"] = json.loads(actual_kwargs.pop("data").decode())
        assert actual_kwargs == valid_kwargs

    async def test_uses_unique_retry_timer(
            self,
            request_handler: RequestHandler,
            url: URL,
            mock_retry: AsyncMock,
            requests_mock: aioresponses,
    ):
        request_handler.retry_timer = StepCountTimer(initial=0.1, count=3, step=0.1)
        request_handler._retry_timer.increase()
        request_handler._retry_timer.increase()

        timer_new = request_handler.retry_timer
        assert id(timer_new) != id(request_handler._retry_timer)
        assert float(timer_new) == timer_new.initial != float(request_handler._retry_timer)

        def _retry(*_, timer: Timer | None, **__) -> None:
            if timer is None or not timer.can_increase or timer == 0:
                raise RequestError("Max retries exceeded")
            timer.increase()

        requests_mock.get(url, status=400, payload={"key": "value"}, repeat=True)
        mock_retry.side_effect = _retry

        async with request_handler as handler:
            with pytest.raises(RequestError, match="Max retries exceeded"):
                await handler.request(method=HTTPMethod.GET, url=url)

            timer_call = mock_retry.call_args.kwargs["timer"]
            assert id(timer_call) != id(request_handler._retry_timer) != id(request_handler.retry_timer)
            assert timer_call == timer_call.final

    async def test_response_handling(self, request_handler: RequestHandler, dummy_response: ClientResponse):
        request_handler.response_handlers = [
            UnauthorisedStatusHandler(), RateLimitStatusHandler(), ClientErrorStatusHandler()
        ]
        response = dummy_response

        async with request_handler as handler:
            response.status = 400
            with pytest.raises(ResponseError):
                await handler._handle_response(response=response)

            response.status = 401
            assert await handler._handle_response(response=response)

            assert "retry-after" not in response.headers
            response.status = 429
            assert not await handler._handle_response(response=response)

    # noinspection PyTestUnpassedFixture
    async def test_cache_usage(self, request_handler: RequestHandler, requests_mock: aioresponses):
        url = "http://localhost/test"
        expected_json = {"key": "value"}
        requests_mock.get(url, payload=expected_json, repeat=True)

        async with request_handler as handler:
            repository_settings = MockResponseRepositorySettings(name="test", payload_handler=handler.payload_handler)
            repository = await handler.session.cache.create_repository(repository_settings)
            handler.session.cache.repository_getter = lambda _, __: repository

            async with handler._request(method=HTTPMethod.GET, url=url, persist=False) as response:
                assert await response.json() == expected_json
                requests_mock.assert_called_once()

            key = repository.get_key_from_request(response.request_info)
            assert await repository.get_response(key) is None

            async with handler._request(method=HTTPMethod.GET, url=url, persist=True) as response:
                assert await response.json() == expected_json
            assert sum(map(len, requests_mock.requests.values())) == 2
            assert await repository.get_response(key)

            async with handler._request(method=HTTPMethod.GET, url=url) as response:
                assert await response.json() == expected_json
            assert sum(map(len, requests_mock.requests.values())) == 2

            await repository.clear()
            async with handler._request(method=HTTPMethod.GET, url=url) as response:
                assert await response.json() == expected_json
            assert sum(map(len, requests_mock.requests.values())) == 3

    async def test_retry_on_max_retries_reached(
            self, request_handler: RequestHandler, url: URL, dummy_response: ClientResponse
    ):
        # should always raise an error based on the response
        with pytest.raises(RequestError, match="Max retries exceeded"):
            await request_handler._retry(None, method=HTTPMethod.GET, url=url, timer=None)
        with pytest.raises(IOError):
            await request_handler._retry(IOError(), method=HTTPMethod.GET, url=url, timer=None)
        with pytest.raises(ResponseError, match=f"Status code: {dummy_response.status}"):
            await request_handler._retry(dummy_response, method=HTTPMethod.GET, url=url, timer=None)

        retry_timer = StepCountTimer(initial=0.1, count=2, step=0.1)
        retry_timer.increase()
        retry_timer.increase()

        with pytest.raises(IOError):
            await request_handler._retry(IOError(), method=HTTPMethod.GET, url=url, timer=retry_timer)

    async def test_request_with_valid_response(
            self,
            request_handler: RequestHandler,
            url: URL,
            mock_handle_response: AsyncMock,
            mock_log_response: AsyncMock,
            mock_retry: AsyncMock,
            requests_mock: aioresponses,
    ):
        expected_json = {"key": "value"}
        requests_mock.get(url, status=200, payload=expected_json, repeat=True)

        async with request_handler as handler:
            # default payload handler returns as string
            handler.payload_handler = StringPayloadHandler()
            assert await handler.request(method=HTTPMethod.GET, url=url) == json.dumps(expected_json)

        mock_handle_response.assert_called_once()
        mock_log_response.assert_not_called()
        mock_retry.assert_not_called()

        async with request_handler as handler:
            handler.payload_handler = JSONPayloadHandler()
            assert await handler.request(method=HTTPMethod.GET, url=url) == expected_json

    async def test_request_handles_error(
            self,
            request_handler: RequestHandler,
            url: URL,
            mock_handle_response: AsyncMock,
            mock_log_response: AsyncMock,
            requests_mock: aioresponses,
    ):
        def raise_error(*_, **__):
            """Just raise a ConnectionError"""
            raise aiohttp.ClientConnectionError()

        requests_mock.get(url, callback=raise_error, repeat=True)
        assert request_handler.retry_timer is None

        async with request_handler as handler:
            async with handler._request(method=HTTPMethod.GET, url=url) as response:
                assert isinstance(response, aiohttp.ClientConnectionError)

            with pytest.raises(aiohttp.ClientConnectionError):
                # response is Exception raises error on main request method
                await handler.request(method=HTTPMethod.GET, url=url)

        mock_handle_response.assert_not_called()
        mock_log_response.assert_not_called()
        # mock_handle_retry_timer.assert_not_called()

    async def test_request_repeats_on_handled_response(
            self,
            request_handler: RequestHandler,
            url: URL,
            mock_handle_response: AsyncMock,
            mock_log_response: AsyncMock,
            requests_mock: aioresponses,
    ):
        requests_mock.get(url, status=400)
        mock_handle_response.side_effect = AsyncMock(return_value=True)
        assert request_handler.retry_timer is None

        async with request_handler as handler:
            with pytest.raises(aiohttp.ClientError):  # fails on 2nd request as requests mock only mocks 1st request
                await handler.request(method=HTTPMethod.GET, url=url)

        mock_handle_response.assert_called_once()
        mock_log_response.assert_not_called()

    async def test_request_logs_and_retries(
            self,
            request_handler: RequestHandler,
            url: URL,
            mock_handle_response: AsyncMock,
            mock_log_response: AsyncMock,
            mock_retry: AsyncMock,
            requests_mock: aioresponses,
    ):
        def _retry(*_, **__) -> None:
            raise RequestError("Max retries exceeded")

        requests_mock.get(url, status=400, repeat=True)
        mock_retry.new_callable = AsyncMock
        mock_retry.side_effect = _retry

        async with request_handler as handler:
            with pytest.raises(RequestError, match="Max retries exceeded"):
                await handler.request(method=HTTPMethod.GET, url=url)

        mock_handle_response.assert_called_once()
        mock_log_response.assert_called_once()
        mock_retry.assert_called_once()

    async def test_request_fails(
            self,
            request_handler: RequestHandler,
            url: URL,
    ):
        assert request_handler.closed
        with pytest.raises(RequestError):
            await request_handler.get(url)
