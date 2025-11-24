import pytest

from eligibility_signposting_api.repos.secrets import nhs_hmac_key_factory


def test_nhs_hmac_key_factory_returns_bytes():
    key = nhs_hmac_key_factory()

    assert isinstance(key, bytes)
    assert key == b"abc123"
