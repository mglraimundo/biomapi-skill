#!/usr/bin/env python3
"""
BiomAPI Client - Zero-dependency client for BiomAPI biometry extraction.

Processes biometry PDFs/images through the BiomAPI service and retrieves
results via BiomPIN secure sharing codes.

Usage:
    biomapi.py process <file_path> [<file_path2> ...] [--pin]
    biomapi.py retrieve <biompin_code>
    biomapi.py status

Stdout (process/retrieve):
    One JSON object per file, in input order:
      {"patient_id": ..., "patient_name": ..., "device": ..., "biompin": ..., "saved_json": "/abs/path.json"}
    The full raw API response is always saved to disk at saved_json.
    On error: {"error": true, "detail": "...", ...}

Environment:
    BIOMAPI_URL  - API base URL (default: https://biomapi.com)
    BIOMAPI_KEY  - Optional API key for higher rate limits
"""

import json
import os
import re
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
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


def _generate_filename(result: dict) -> str:
    """Mirror generateSmartFilename from downloadManager.js.

    Format: biomapi-{patient_id}-{device}.json
    - patient_id: lowercase, [^a-z0-9-] → '-', collapse runs, max 50 chars
    - device: lowercase, only [a-z0-9], max 30 chars
    - Fallbacks: YYYY-MM-DD for missing patient_id, 'unknown' for missing device
    """
    patient_id = (result.get("data") or {}).get("patient", {}).get("patient_id")
    device_name = (result.get("data") or {}).get("biometer", {}).get("device_name")

    if patient_id:
        id_part = re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "-", str(patient_id).lower()))[:50]
    else:
        id_part = date.today().isoformat()

    if device_name:
        device_part = re.sub(r"[^a-z0-9]", "", str(device_name).lower())[:30]
    else:
        device_part = "unknown"

    return f"biomapi-{id_part}-{device_part}.json"


def _save_result(result: dict, source_path: str) -> str:
    """Save full API response JSON next to source_path. Returns absolute save path."""
    filename = _generate_filename(result)
    save_dir = os.path.dirname(source_path) or os.getcwd()
    try:
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return os.path.abspath(save_path)
    except OSError:
        # Fallback to cwd if source dir is not writable
        save_path = os.path.join(os.getcwd(), filename)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return os.path.abspath(save_path)


def _process_one(file_path: str, generate_pin: bool) -> dict:
    """Validate and upload a single biometry file.

    Returns a compact summary dict (not the full API response) so the LLM
    context stays small. The full raw response is always saved to disk first.
    """
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
    result = _request("POST", f"{BASE_URL}/api/v1/biom/process", body=body, content_type=content_type)

    if result.get("error"):
        return result

    # Save full response to disk before returning — metadata is preserved here
    saved_path = _save_result(result, file_path)

    patient = (result.get("data") or {}).get("patient", {})
    return {
        "patient_id": patient.get("patient_id"),
        "patient_name": patient.get("patient_name"),
        "device": (result.get("data") or {}).get("biometer", {}).get("device_name"),
        "biompin": result.get("biompin"),
        "saved_json": saved_path,
    }


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

    if result.get("error"):
        print(json.dumps(result))
        sys.exit(1)

    saved_path = _save_result(result, os.path.join(os.getcwd(), "_retrieve"))
    patient = (result.get("data") or {}).get("patient", {})
    print(json.dumps({
        "patient_id": patient.get("patient_id"),
        "patient_name": patient.get("patient_name"),
        "device": (result.get("data") or {}).get("biometer", {}).get("device_name"),
        "biompin": result.get("biompin") or biompin_code,
        "saved_json": saved_path,
    }))


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
