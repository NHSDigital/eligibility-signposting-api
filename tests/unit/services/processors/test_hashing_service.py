import hashlib
import hmac

from eligibility_signposting_api.processors.hashing_service import _hash

HASH_DIGEST_LENGTH_SHA512 = 128  # sha512 produces 512 bits = 64 bytes = 128 hex characters


def test_hash_with_valid_secret_matches_hmac_sha512():
    nhs_number = "1234567890"
    secret_value = "super-secret-value"  # noqa: S105

    expected = hmac.new(
        secret_value.encode("utf-8"),
        nhs_number.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()

    actual = _hash(nhs_number, secret_value)

    assert actual == expected
    # sanity check: sha512 hex digest length
    assert len(actual) == HASH_DIGEST_LENGTH_SHA512


def test_hash_returns_none_when_secret_is_none():
    nhs_number = "1234567890"

    result = _hash(nhs_number, None)

    assert result is None


def test_hash_returns_none_when_secret_is_empty_string():
    nhs_number = "1234567890"

    result = _hash(nhs_number, "")

    assert result is None


def test_hash_is_deterministic_for_same_inputs():
    nhs_number = "9876543210"
    secret_value = "another-secret"  # noqa: S105

    first = _hash(nhs_number, secret_value)
    second = _hash(nhs_number, secret_value)

    assert first == second
    assert first is not None  # type: ignore[unreachable]


def test_hash_changes_when_secret_changes():
    nhs_number = "9876543210"

    result_1 = _hash(nhs_number, "secret-one")
    result_2 = _hash(nhs_number, "secret-two")

    assert result_1 is not None  # type: ignore[unreachable]
    assert result_2 is not None  # type: ignore[unreachable]
    assert result_1 != result_2


def test_hash_uses_string_representation_of_nhs_number():
    # Even though the function type hints str, it calls str(nhs_number) internally.
    # This test documents that behaviour.
    nhs_number_int = 1234567890
    nhs_number_str = "1234567890"
    secret_value = "secret"  # noqa: S105

    result_from_int = _hash(nhs_number_int, secret_value)  # type: ignore[arg-type]
    result_from_str = _hash(nhs_number_str, secret_value)

    assert result_from_int == result_from_str
