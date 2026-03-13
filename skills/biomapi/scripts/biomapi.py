#!/usr/bin/env python3
"""
BiomAPI Client - Zero-dependency client for BiomAPI biometry extraction.

Processes biometry PDFs/images through the BiomAPI service and retrieves
results via BiomPIN secure sharing codes.

Usage:
    biomapi.py process <file_path> [--pin]
    biomapi.py retrieve <biompin_code>
    biomapi.py status

Environment:
    BIOMAPI_URL  - API base URL (default: https://biomapi.com)
    BIOMAPI_KEY  - Optional API key for higher rate limits
"""

import json
import os
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("BIOMAPI_URL", "https://biomapi.com").rstrip("/")
API_KEY = os.environ.get("BIOMAPI_KEY", "")

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def _build_multipart(file_path: str, generate_pin: bool) -> tuple[bytes, str]:
    """Build a multipart/form-data body using only stdlib."""
    boundary = f"----BiomAPI{uuid.uuid4().hex}"
    filename = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        file_data = f.read()

    # Determine content type from extension
    ext = os.path.splitext(filename)[1].lower()
    content_types = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    content_type = content_types.get(ext, "application/octet-stream")

    parts = []

    # File part
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    )
    parts.append(file_data)
    parts.append(b"\r\n")

    # BiomPIN part
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="biompin"\r\n\r\n'
        f"{'true' if generate_pin else 'false'}\r\n"
    )

    # Closing boundary
    parts.append(f"--{boundary}--\r\n")

    # Combine parts (mix of str and bytes)
    body = b""
    for part in parts:
        body += part.encode("utf-8") if isinstance(part, str) else part

    return body, f"multipart/form-data; boundary={boundary}"


def _request(method: str, url: str, body: bytes | None = None, content_type: str | None = None) -> dict:
    """Make an HTTP request and return parsed JSON."""
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if content_type:
        headers["Content-Type"] = content_type

    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            error_json = json.loads(error_body)
            detail = error_json.get("detail", error_body)
        except json.JSONDecodeError:
            detail = error_body
        print(json.dumps({"error": True, "status": e.code, "detail": detail}))
        sys.exit(1)
    except URLError as e:
        print(json.dumps({"error": True, "detail": f"Connection failed: {e.reason}"}))
        sys.exit(1)


def cmd_process(file_path: str, generate_pin: bool = False) -> None:
    """Upload a biometry file for AI extraction."""
    file_path = os.path.abspath(file_path)

    if not os.path.isfile(file_path):
        print(json.dumps({"error": True, "detail": f"File not found: {file_path}"}))
        sys.exit(1)

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(json.dumps({
            "error": True,
            "detail": f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        }))
        sys.exit(1)

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 20:
        print(json.dumps({"error": True, "detail": f"File too large ({file_size_mb:.1f}MB). Maximum: 20MB"}))
        sys.exit(1)

    body, content_type = _build_multipart(file_path, generate_pin)
    result = _request("POST", f"{BASE_URL}/api/v1/biom/process", body=body, content_type=content_type)
    print(json.dumps(result, indent=2))


def cmd_retrieve(biompin_code: str) -> None:
    """Retrieve biometry data using a BiomPIN code."""
    from urllib.parse import quote

    url = f"{BASE_URL}/api/v1/biom/retrieve?biom_pin={quote(biompin_code)}"
    result = _request("GET", url)
    print(json.dumps(result, indent=2))


def cmd_status() -> None:
    """Check API health status."""
    result = _request("GET", f"{BASE_URL}/api/v1/status")
    print(json.dumps(result, indent=2))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: biomapi.py <process|retrieve|status> [args]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "process":
        if len(sys.argv) < 3:
            print("Usage: biomapi.py process <file_path> [--pin]", file=sys.stderr)
            sys.exit(1)
        file_path = sys.argv[2]
        generate_pin = "--pin" in sys.argv[3:]
        cmd_process(file_path, generate_pin)

    elif command == "retrieve":
        if len(sys.argv) < 3:
            print("Usage: biomapi.py retrieve <biompin_code>", file=sys.stderr)
            sys.exit(1)
        cmd_retrieve(sys.argv[2])

    elif command == "status":
        cmd_status()

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Commands: process, retrieve, status", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
