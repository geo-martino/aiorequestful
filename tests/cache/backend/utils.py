from typing import Any

from yarl import URL

from aiorequestful.cache.backend.base import ResponseRepositorySettings


class MockResponseRepositorySettings[V: Any](ResponseRepositorySettings[V]):

    @property
    def fields(self) -> tuple[str, ...]:
        return "id",

    def get_key(self, url: str | URL, **__) -> tuple[str | None, ...]:
        if str(url).endswith(".com"):
            return (None,)
        return URL(url).path.split("/")[-1] or None,

    @staticmethod
    def get_name(payload: V) -> str | None:
        if not isinstance(payload, dict):
            payload = eval(payload)
        return payload.get("name")


class MockPaginatedRequestSettings[V: Any](MockResponseRepositorySettings[V]):

    @property
    def fields(self) -> tuple[str, ...]:
        return *super().fields, "offset", "size"

    def get_key(self, url: str | URL, **__) -> tuple[str | int | None, ...]:
        base = super().get_key(url=url)
        return *base, self.get_offset(url), self.get_limit(url)

    @staticmethod
    def get_offset(url: str | URL) -> int:
        """Extracts the offset for a paginated request from the given ``url``."""
        params = URL(url).query
        return int(params.get("offset", 0))

    @staticmethod
    def get_limit(url: str | URL) -> int:
        """Extracts the limit for a paginated request from the given ``url``."""
        params = URL(url).query
        return int(params.get("limit", 0))
