# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Security helpers for OntoForge input and filesystem boundaries."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
KUZU_TYPES = {"STRING", "INT64", "DOUBLE", "BOOLEAN", "DATE", "TIMESTAMP"}
MAX_CYPHER_CHARS = 10_000
MAX_LLM_INPUT_CHARS = 20_000
MAX_ROWS = 1_000
ANTHROPIC_HOST = "api.anthropic.com"

_DISALLOWED_READONLY_TERMS = {
    "ALTER",
    "ATTACH",
    "COPY",
    "CREATE",
    "DELETE",
    "DETACH",
    "DROP",
    "INSTALL",
    "LOAD",
    "MERGE",
    "SET",
}

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def validate_identifier(value: str, kind: str = "identifier") -> str:
    """Return a safe Kuzu identifier or raise ValueError."""
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"Invalid {kind}: {value!r}. Use 1-64 ASCII letters, digits, or "
            "underscores, starting with a letter or underscore."
        )
    return value


def validate_type(value: str) -> str:
    t = str(value).upper()
    if t not in KUZU_TYPES:
        raise ValueError(f"Invalid Kuzu type: {value!r}")
    return t


def validate_property_schema(properties: Mapping[str, str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, kuzu_type in (properties or {}).items():
        out[validate_identifier(name, "property name")] = validate_type(kuzu_type)
    return out


def validate_readonly_cypher(cypher: str) -> str:
    """Allow only read-only Cypher submitted by users."""
    if not isinstance(cypher, str):
        raise ValueError("Cypher query must be a string")
    query = cypher.strip()
    if not query:
        raise ValueError("Cypher query is empty")
    if len(query) > MAX_CYPHER_CHARS:
        raise ValueError(f"Cypher query exceeds {MAX_CYPHER_CHARS} characters")

    normalized = query[:-1].strip() if query.endswith(";") else query
    if ";" in normalized:
        raise ValueError("Multiple Cypher statements are not permitted")

    scrubbed = _strip_quoted_literals(normalized).upper()
    found = sorted(
        term for term in _DISALLOWED_READONLY_TERMS
        if re.search(rf"\b{re.escape(term)}\b", scrubbed)
    )
    if found:
        raise ValueError(
            "Only read-only Cypher is permitted; rejected keyword(s): "
            + ", ".join(found)
        )
    if not re.match(r"^\s*(MATCH|WITH|RETURN|UNWIND)\b", scrubbed):
        raise ValueError("Read-only queries must start with MATCH, WITH, RETURN, or UNWIND")
    if not re.search(r"\bRETURN\b", scrubbed):
        raise ValueError("Read-only queries must include RETURN")
    return normalized


def safe_export_path(path: str, base_dir: str = "./exports") -> str:
    """Resolve a file path and ensure it stays under the export directory."""
    target = Path(path).expanduser().resolve()
    base = Path(base_dir).expanduser().resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"Path outside allowed export directory: {path}") from exc
    return str(target)


def safe_export_dir(path: str, base_dir: str = "./exports") -> str:
    target = Path(safe_export_path(path, base_dir))
    return str(target)


def sanitize_llm_input(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("LLM input must be a string")
    cleaned = _CONTROL_CHARS.sub("", text)
    if len(cleaned) > MAX_LLM_INPUT_CHARS:
        cleaned = cleaned[:MAX_LLM_INPUT_CHARS]
    return cleaned


def validate_https_url(url: str, expected_host: str = ANTHROPIC_HOST) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != expected_host:
        raise ValueError(f"Refusing to call unapproved URL: {url}")


def audit_log(event: str, **fields) -> None:
    """Minimal structured audit log for local workshop operations."""
    import datetime as _dt
    import json
    import logging

    logging.getLogger("ontology_workshop.audit").info(
        json.dumps(
            {"ts": _dt.datetime.utcnow().isoformat() + "Z", "event": event, **fields},
            ensure_ascii=False,
            default=str,
        )
    )


def _strip_quoted_literals(query: str) -> str:
    """Replace quoted strings with spaces so keyword checks ignore string values."""
    out: list[str] = []
    quote: str | None = None
    escaped = False
    for ch in query:
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            out.append(" ")
        else:
            if ch in ("'", '"'):
                quote = ch
                out.append(" ")
            else:
                out.append(ch)
    return "".join(out)
