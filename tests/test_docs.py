"""
Tests scripts found in the documentation
"""
import pytest


@pytest.mark.manual
@pytest.mark.skipif(
    "not config.getoption('-m') and not config.getoption('-k')",
    reason="Only runs when the test or marker is specified explicitly by the user",
)
def test_guides():
    # all guides execute immediately so just need to import them and check they shouldn't fail
    pass

    # from docs.guides.scripts.auth import basic, oauth2
    # from docs.guides.scripts.cache.backend import base, sqlite
