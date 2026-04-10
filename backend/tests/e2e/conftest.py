"""
E2E conftest — re-exports the AsyncClient fixture from integration conftest
and adds the SAMPLE_ARTIFACTS constant needed by mock patches.
"""

from tests.integration.conftest import test_client, auth_headers, other_auth_headers  # noqa: F401
