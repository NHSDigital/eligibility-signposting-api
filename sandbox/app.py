"""
Proxy server for Stoplight Prism with response example selection logic.

Adapted from https://stackoverflow.com/a/36601467
"""

import logging
import os
import sys

import requests  # pyright: ignore [reportMissingModuleSource]
from flask import Flask, Request, Response, request  # pyright: ignore [reportMissingImports]

# Configure logging to output to stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# HTTP proxy to Prism
UPSTREAM_HOST = os.environ.get("UPSTREAM_HOST")
if not UPSTREAM_HOST:
    NO_UPSTREAM_HOST = "UPSTREAM_HOST environment variable not set"
    raise ValueError(NO_UPSTREAM_HOST)

app = Flask(__name__)
app.logger.setLevel("INFO")
session = requests.Session()

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

PATIENT_EXAMPLES = {
    "patient=0000000001": "example1",
    "patient=0000000002": "example2",
    "patient=0000000003": "code404",
}


def exclude_hop_by_hop(headers: dict) -> list[tuple[str, str]]:
    """
    Exclude hop-by-hop headers, which are meaningful only for a single
    transport-level connection, and are not stored by caches or forwarded by
    proxies. See https://www.rfc-editor.org/rfc/rfc2616#section-13.5.1.
    """
    return [(k, v) for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS]


def get_prism_prompt_for_example(patient_examples: dict, request: Request) -> str | None:
    """
    Given the whole request, return the `Prefer:` header value if a specific
    example is desired. Otherwise, return `None`.
    """
    for patient_id, example in patient_examples.items():
        if patient_id in request.full_path:
            return example
    return None


def parse_prefer_header_value(prefer_header_value: str) -> str:
    """
    Parse the Prefer header value to extract the example name.
    """
    if prefer_header_value.startswith("example"):
        return f"example={prefer_header_value}"
    if prefer_header_value.startswith("code"):
        return f"code={prefer_header_value[4:]}"
    return ""


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy_to_upstream(path: str) -> Response:  # noqa: ARG001
    headers_to_upstream = {k: v for k, v in request.headers if k.lower() != "host"}

    prefer_header_value = get_prism_prompt_for_example(PATIENT_EXAMPLES, request)
    if prefer_header_value:
        headers_to_upstream["prefer"] = parse_prefer_header_value(prefer_header_value)

    request_to_upstream = requests.Request(
        method=request.method,
        url=request.url.replace(request.host_url, UPSTREAM_HOST + "/"),  # pyright: ignore [reportOptionalOperand]
        headers=headers_to_upstream,
        data=request.get_data(),
        cookies=request.cookies,
    ).prepare()
    response_from_upstream = session.send(request_to_upstream)

    return Response(
        response_from_upstream.content,
        response_from_upstream.status_code,
        exclude_hop_by_hop(response_from_upstream.raw.headers),
    )
