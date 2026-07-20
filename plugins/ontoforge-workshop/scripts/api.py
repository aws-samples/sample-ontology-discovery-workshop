#!/usr/bin/env python3
"""Small JSON client for the repository-local OntoForge server."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call the local OntoForge API")
    parser.add_argument("method", choices=("GET", "POST"))
    parser.add_argument("path", help="API path beginning with /")
    parser.add_argument(
        "--data", default=None,
        help="JSON object, '-' for stdin, or @path to a UTF-8 JSON file")
    return parser


def read_payload(raw: str | None) -> bytes | None:
    if raw is None:
        return None
    if raw == "-":
        text = sys.stdin.read()
    elif raw.startswith("@"):
        text = Path(raw[1:]).read_text(encoding="utf-8")
    else:
        text = raw
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("request JSON must be an object")
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.path.startswith("/"):
        parser.error("path must begin with /")
    try:
        body = read_payload(args.data)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"invalid request payload: {error}", file=sys.stderr)
        return 2

    base = os.environ.get(
        "ONTOFORGE_URL", "http://127.0.0.1:8000").rstrip("/")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    token = os.environ.get("ONTOFORGE_TOKEN")
    if token:
        headers["X-OntoForge-Token"] = token
    request = urllib.request.Request(
        base + args.path, data=body, headers=headers, method=args.method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        print(detail or f"HTTP {error.code}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        print(f"cannot reach OntoForge at {base}: {error}", file=sys.stderr)
        return 1

    try:
        value = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        print(raw)
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
