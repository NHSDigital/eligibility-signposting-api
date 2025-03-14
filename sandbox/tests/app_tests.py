from unittest.mock import Mock

import pytest  # pyright: ignore [reportMissingImports]
from hamcrest import assert_that, equal_to  # pyright: ignore [reportMissingImports]

from sandbox.app import exclude_hop_by_hop, get_prism_prompt_for_example, parse_prefer_header_value

HOP_BY_HOP_HEADERS = [
    "connection",
    "content-encoding",
    "content-length",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
]


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        (
            {
                "Connection": "keep-alive",
                "Content-Encoding": "gzip",
                "Content-Length": "1234",
                "Keep-Alive": "timeout=5, max=1000",
                "Proxy-Authenticate": "Basic",
                "Proxy-Authorization": "Basic",
                "TE": "trailers",
                "Trailers": "value",
                "Transfer-Encoding": "chunked",
                "Upgrade": "h2c",
                "Custom-Header": "custom-value",
            },
            [("Custom-Header", "custom-value")],
        ),
    ],
)
def test_exclude_hop_by_hop(headers: dict, expected: dict) -> None:
    assert_that(exclude_hop_by_hop(headers), equal_to(expected))


@pytest.mark.parametrize(
    ("full_path", "expected"),
    [
        ("/api/resource?patient=0000000001", "example1"),
        ("/api/resource?patient=0000000002", "example2"),
        ("/api/resource?patient=0000000003", "code404"),
        ("/api/resource?patient=0000000004", None),
    ],
)
def test_get_prism_prompt_for_example(full_path: str, expected: str) -> None:
    patient_examples = {
        "patient=0000000001": "example1",
        "patient=0000000002": "example2",
        "patient=0000000003": "code404",
    }
    request = Mock()
    request.full_path = full_path
    assert_that(get_prism_prompt_for_example(patient_examples, request), equal_to(expected))


@pytest.mark.parametrize(
    ("prefer_header_value", "expected"),
    [
        ("example1", "example=example1"),
        ("code404", "code=404"),
        ("unknown", ""),
    ],
)
def test_parse_prefer_header_value(prefer_header_value: str, expected: str) -> None:
    assert_that(parse_prefer_header_value(prefer_header_value), equal_to(expected))
