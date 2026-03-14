#!/usr/bin/env python3
"""
BiomAPI Client - Zero-dependency client for BiomAPI biometry extraction.

Processes biometry PDFs/images through the BiomAPI service and retrieves
results via BiomPIN secure sharing codes.

Usage:
    biomapi.py process <file_path> [<file_path2> ...] [--pin]
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
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    """Make an HTTP request and return parsed JSON. Returns error dict on failure."""
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
        return {"error": True, "status": e.code, "detail": detail}
    except URLError as e:
        return {"error": True, "detail": f"Connection failed: {e.reason}"}


def _process_one(file_path: str, generate_pin: bool) -> dict:
    """Validate and upload a single biometry file. Returns result dict."""
    file_path = os.path.abspath(file_path)

    if not os.path.isfile(file_path):
        return {"error": True, "file": file_path, "detail": f"File not found: {file_path}"}

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return {
            "error": True,
            "file": file_path,
            "detail": f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        }

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 20:
        return {"error": True, "file": file_path, "detail": f"File too large ({file_size_mb:.1f}MB). Maximum: 20MB"}

    body, content_type = _build_multipart(file_path, generate_pin)
    return _request("POST", f"{BASE_URL}/api/v1/biom/process", body=body, content_type=content_type)


def cmd_process(file_paths: list[str], generate_pin: bool = False) -> None:
    """Upload one or more biometry files for AI extraction, concurrently."""
    if len(file_paths) == 1:
        result = _process_one(file_paths[0], generate_pin)
        print(json.dumps(result))
        if result.get("error"):
            sys.exit(1)
        return

    results = [None] * len(file_paths)
    with ThreadPoolExecutor(max_workers=len(file_paths)) as executor:
        futures = {executor.submit(_process_one, fp, generate_pin): i for i, fp in enumerate(file_paths)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    for result in results:
        print(json.dumps(result))

    if any(r.get("error") for r in results if r):
        sys.exit(1)


def cmd_retrieve(biompin_code: str) -> None:
    """Retrieve biometry data using a BiomPIN code."""
    from urllib.parse import quote

    url = f"{BASE_URL}/api/v1/biom/retrieve?biom_pin={quote(biompin_code)}"
    result = _request("GET", url)
    print(json.dumps(result))
    if result.get("error"):
        sys.exit(1)


def cmd_status() -> None:
    """Check API health status."""
    result = _request("GET", f"{BASE_URL}/api/v1/status")
    print(json.dumps(result))
    if result.get("error"):
        sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: biomapi.py <process|retrieve|status> [args]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "process":
        if len(sys.argv) < 3:
            print("Usage: biomapi.py process <file_path> [<file_path2> ...] [--pin]", file=sys.stderr)
            sys.exit(1)
        args = sys.argv[2:]
        generate_pin = "--pin" in args
        file_paths = [a for a in args if a != "--pin"]
        cmd_process(file_paths, generate_pin)

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
