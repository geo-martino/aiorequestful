"""
Tests scripts found in the documentation
"""


def test_guides():
    # all guides execute immediately so just need to import them and check they shouldn't fail
    from docs.guides.scripts.request import simple, auth, cache, payload, status, timer
    from docs.guides.scripts.response import payload
    from docs.guides.scripts.timer import timer

    # from docs.guides.scripts.auth import basic, oauth2
    # from docs.guides.scripts.cache.backend import base, sqlite
