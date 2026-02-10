"""Lightweight HTTP helpers built on the Python standard library."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


def http_post_json(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Send a JSON POST request and return the parsed JSON body."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST")
    resp_body = _read_response(req, timeout=timeout)
    return _parse_json_body(url, resp_body)


def http_get_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Send a GET request and return the parsed JSON body."""
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    resp_body = _read_response(req, timeout=timeout)
    return _parse_json_body(url, resp_body)


def _read_response(req: urllib.request.Request, timeout: int) -> bytes:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        # Attempt to decode the error body for a human readable message.
        try:
            error_body = exc.read().decode("utf-8")
        except Exception:
            error_body = ""
        safe_body = _truncate_error_body(error_body)
        raise RuntimeError(
            f"HTTP {exc.code} error when calling {req.full_url}: {safe_body}".strip()
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Network error when calling {req.full_url}: {exc}") from exc


def _parse_json_body(url: str, body: bytes) -> Dict[str, Any]:
    try:
        return json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Invalid JSON response from {url}") from exc


def _truncate_error_body(body: str, limit: int = 200) -> str:
    """Limit error bodies to reduce accidental leakage of sensitive data."""
    if not body:
        return ""
    body = body.strip()
    if len(body) <= limit:
        return body
    return f"{body[:limit]}... [truncated]"
