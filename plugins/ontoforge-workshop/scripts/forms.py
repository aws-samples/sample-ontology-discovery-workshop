#!/usr/bin/env python3
"""Manage stage Markdown forms for a repository-local OntoForge workshop."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


FORM_FILES = {
    "inception": "01-inception.md",
    "discovery": "02-discovery.md",
    "event_discovery": "03-event-discovery.md",
    "story_to_question": "04-story-to-question.md",
    "model_synthesis": "05-model-synthesis.md",
    "data_grounding": "06-data-grounding.md",
    "adversarial_review": "07-adversarial-review.md",
    "validation_handoff": "08-validation-handoff.md",
}
STATE_START = "<!-- ONTOFORGE:SERVER-STATE:START -->"
STATE_END = "<!-- ONTOFORGE:SERVER-STATE:END -->"
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "skills" / "run-workshop" / "assets" / "forms"


class FormError(RuntimeError):
    """An expected stage-form error."""


def project_root() -> Path:
    override = os.environ.get("ONTOFORGE_PROJECT_ROOT")
    if override:
        root = Path(override).expanduser().resolve()
    else:
        current = Path.cwd().resolve()
        root = next(
            (path for path in (current, *current.parents)
             if (path / "src/ontology_workshop/server.py").is_file()),
            current,
        )
    if not (root / "src/ontology_workshop/server.py").is_file():
        raise FormError(
            "run this command inside a sample-ontology-discovery-workshop checkout "
            "or set ONTOFORGE_PROJECT_ROOT")
    return root


def answers_dir() -> Path:
    return project_root() / "answers"


def registry_path() -> Path:
    return answers_dir() / ".form-submissions.json"


def api_request(method: str, path: str,
                payload: dict[str, Any] | None = None) -> dict[str, Any]:
    base = os.environ.get("ONTOFORGE_URL", "http://127.0.0.1:8000").rstrip("/")
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    token = os.environ.get("ONTOFORGE_TOKEN")
    if token:
        headers["X-OntoForge-Token"] = token
    request = urllib.request.Request(
        base + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw).get("error")
        except (json.JSONDecodeError, AttributeError):
            detail = raw.strip()
        raise FormError(detail or f"OntoForge returned HTTP {error.code}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise FormError(f"cannot reach OntoForge at {base}: {error}") from error
    try:
        result = json.loads(raw) if raw else {}
    except json.JSONDecodeError as error:
        raise FormError("OntoForge returned invalid JSON") from error
    if not isinstance(result, dict):
        raise FormError("OntoForge returned a non-object response")
    return result


def workflow_state() -> dict[str, Any]:
    workflow = api_request("GET", "/workflow/state").get("workflow")
    if not isinstance(workflow, dict):
        raise FormError("workflow state is missing")
    return workflow


def resolve_stage(workflow: dict[str, Any]) -> str:
    stage = str(workflow.get("current_stage") or "")
    if stage not in FORM_FILES:
        raise FormError(f"unsupported workflow stage: {stage or '(empty)'}")
    return stage


def form_path(stage: str) -> Path:
    return answers_dir() / FORM_FILES[stage]


def ensure_form(stage: str) -> Path:
    path = form_path(stage)
    if path.exists():
        return path
    template = TEMPLATE_DIR / FORM_FILES[stage]
    if not template.is_file():
        raise FormError(f"form template is missing: {template}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def validate_form(stage: str, text: str) -> None:
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not frontmatter:
        raise FormError("form YAML frontmatter is missing")
    header = frontmatter.group(1)
    if not re.search(r"(?m)^ontoforge_form:\s*1\s*$", header):
        raise FormError("form identity is missing or unsupported")
    match = re.search(r"(?m)^stage:\s*([a-z_]+)\s*$", header)
    actual = match.group(1) if match else ""
    if actual != stage:
        raise FormError(f"form stage is {actual or '(missing)'}, expected {stage}")
    if text.count(STATE_START) != 1 or text.count(STATE_END) != 1:
        raise FormError("form server-state markers are missing or damaged")

    template = TEMPLATE_DIR / FORM_FILES[stage]
    expected = re.findall(
        r"<!--\s*REQUIRED:([a-z0-9_]+)\s*-->",
        template.read_text(encoding="utf-8"),
    )
    actual = re.findall(r"<!--\s*REQUIRED:([a-z0-9_]+)\s*-->", text)
    if len(actual) != len(set(actual)) or sorted(actual) != sorted(expected):
        raise FormError(
            "required-section markers are missing, duplicated, or damaged")


def one_line(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value or "-").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def state_block(workflow: dict[str, Any], stage: str) -> str:
    gate = (workflow.get("gates") or {}).get(stage) or {}
    lines = [
        STATE_START,
        f"> 동기화: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"> 현재 서버 단계: {workflow.get('current_stage') or '-'} · 이 양식: {stage}",
        f"> Gate: {str(gate.get('status') or 'unknown').upper()}",
        f"> 다음 안내: {one_line(workflow.get('active_question'))}",
    ]
    missing = gate.get("missing") or []
    if missing:
        lines.extend([">", "> 미충족 증거:"])
        lines.extend(f"> - {one_line(item)}" for item in missing)
    checks = gate.get("checks") or []
    if checks:
        lines.extend([">", "> 조건별 상태:"])
        for check in checks:
            if isinstance(check, dict):
                lines.append(
                    f"> - {str(check.get('status') or 'fail').upper()} "
                    f"{one_line(check.get('id'), 90)} — "
                    f"{one_line(check.get('requirement'))}")
    if stage == "adversarial_review":
        rows: list[tuple[str, dict[str, Any]]] = []
        for collection in (
                "review_findings", "contradictions", "assumptions", "risks",
                "action_items"):
            rows.extend(
                (collection, item)
                for item in workflow.get(collection) or []
                if isinstance(item, dict))
        if rows:
            lines.extend([">", "> 검토 대상:"])
            for collection, item in rows[:40]:
                title = one_line(
                    item.get("text") or item.get("name")
                    or item.get("id"), 150)
                lines.append(
                    f"> - {collection}/{one_line(item.get('id'), 60)} "
                    f"[{one_line(item.get('severity') or item.get('status'), 30)}] "
                    f"{title}")
    if stage == "validation_handoff":
        validation = workflow.get("last_validation") or {}
        manifest = workflow.get("handoff_manifest") or {}
        lines.extend([
            ">",
            f"> 정적 RDF 검증: "
            f"{one_line(validation.get('status') or 'not_run', 40)}"
            f" · freshness "
            f"{one_line(validation.get('freshness') or 'not_run', 40)}",
            f"> 인계 manifest: "
            f"{one_line(manifest.get('status') or 'not_generated', 40)}",
        ])
    lines.append(STATE_END)
    return "\n".join(lines)


def replace_state(text: str, block: str) -> str:
    pattern = re.compile(
        re.escape(STATE_START) + r".*?" + re.escape(STATE_END), re.S)
    if not pattern.search(text):
        raise FormError("form server-state markers are missing or damaged")
    return pattern.sub(lambda _match: block, text, count=1)


def set_status(text: str, status: str) -> str:
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not frontmatter:
        raise FormError("form YAML frontmatter is missing")
    header = frontmatter.group(1)
    header = re.sub(
        r"(?m)^status:\s*.*$", f"status: {status}", header)
    return f"---\n{header}\n---\n" + text[frontmatter.end():]


def answer_text(text: str) -> str:
    text = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)
    text = re.sub(
        re.escape(STATE_START) + r".*?" + re.escape(STATE_END),
        "", text, count=1, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    return re.sub(r"\n{3,}", "\n\n", normalized) + "\n"


def fingerprint(text: str) -> str:
    return hashlib.sha256(answer_text(text).encode("utf-8")).hexdigest()


def required_sections(text: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    required: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    for section in re.finditer(
            r"(?ms)^##\s+(.+?)\n(.*?)(?=^##\s+|\Z)", text):
        heading, body = section.group(1).strip(), section.group(2)
        marker = re.search(r"<!--\s*REQUIRED:([a-z0-9_]+)\s*-->", body)
        if not marker:
            continue
        item = {"key": marker.group(1), "heading": heading}
        required.append(item)
        if not re.sub(r"<!--.*?-->", "", body, flags=re.S).strip():
            missing.append(item)
    return required, missing


def load_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.exists():
        return {"version": 1, "submissions": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FormError(f"cannot read form submission registry: {error}") from error
    if not isinstance(value, dict) or not isinstance(value.get("submissions"), dict):
        raise FormError("form submission registry has an invalid shape")
    return value


def save_registry(value: dict[str, Any]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def status(stage: str, path: Path, text: str,
           workflow: dict[str, Any]) -> dict[str, Any]:
    validate_form(stage, text)
    required, missing = required_sections(text)
    digest = fingerprint(text)
    submission = (load_registry().get("submissions") or {}).get(stage)
    state = (
        "draft" if missing else "ready" if not submission else
        "submitted" if submission.get("fingerprint") == digest else "revised")
    return {
        "ok": True,
        "stage": stage,
        "server_stage": workflow.get("current_stage"),
        "path": str(path),
        "status": state,
        "required_count": len(required),
        "completed_count": len(required) - len(missing),
        "missing": missing,
        "fingerprint": digest,
        "previous_submission": submission or None,
    }


def sync(stage: str, workflow: dict[str, Any]) -> dict[str, Any]:
    path = ensure_form(stage)
    text = path.read_text(encoding="utf-8")
    validate_form(stage, text)
    text = replace_state(text, state_block(workflow, stage))
    current = status(stage, path, text, workflow)
    path.write_text(set_status(text, current["status"]), encoding="utf-8")
    os.chmod(path, 0o600)
    return status(stage, path, path.read_text(encoding="utf-8"), workflow)


def extracted_path(raw: str) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = project_root() / candidate
    candidate = Path(os.path.abspath(candidate))
    allowed = Path(os.path.abspath(answers_dir() / ".extracted.json"))
    if candidate != allowed or candidate.is_symlink():
        raise FormError("--extracted-file must be answers/.extracted.json")
    if not candidate.is_file():
        raise FormError(f"extracted evidence file is missing: {candidate}")
    return candidate


def submit(stage: str, workflow: dict[str, Any], raw_path: str) -> dict[str, Any]:
    current_stage = str(workflow.get("current_stage") or "")
    if stage != current_stage:
        raise FormError(
            f"cannot submit {stage}: the server is currently at {current_stage}")
    path = extracted_path(raw_path)
    try:
        extracted = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise FormError(f"extracted JSON is invalid: {error.msg}") from error
    if not isinstance(extracted, dict):
        raise FormError("extracted JSON must be an object")

    current = sync(stage, workflow)
    if current["missing"]:
        headings = ", ".join(item["heading"] for item in current["missing"])
        raise FormError(f"required form sections are empty: {headings}")
    previous = current.get("previous_submission")
    if previous and previous.get("fingerprint") == current["fingerprint"]:
        path.unlink()
        return {
            "ok": True, "duplicate": True, "stage": stage,
            "claim_id": previous.get("claim_id"),
            "message": "unchanged form was already submitted",
        }

    form = Path(current["path"])
    endpoint = "/workflow/clarify" if previous else "/workflow/answer"
    response = api_request("POST", endpoint, {
        "stage": stage,
        "role": "customer",
        "status": "candidate",
        "source": "stage_markdown_form",
        "text": answer_text(form.read_text(encoding="utf-8")),
        "extracted": extracted,
    })
    claim = response.get("claim") or {}
    claim_id = claim.get("id") if isinstance(claim, dict) else None
    registry = load_registry()
    registry["submissions"][stage] = {
        "fingerprint": current["fingerprint"],
        "claim_id": claim_id,
        "endpoint": endpoint,
        "submitted_at": dt.datetime.now().isoformat(timespec="seconds"),
        "path": str(form),
    }
    save_registry(registry)
    path.unlink()
    updated = response.get("workflow") or {}
    if isinstance(updated, dict) and updated:
        refreshed = replace_state(
            form.read_text(encoding="utf-8"), state_block(updated, stage))
        form.write_text(set_status(refreshed, "submitted"), encoding="utf-8")
        os.chmod(form, 0o600)
    gate = (updated.get("gates") or {}).get(stage) or {}
    return {
        "ok": bool(response.get("ok", True)),
        "duplicate": False,
        "stage": stage,
        "endpoint": endpoint,
        "claim_id": claim_id,
        "gate_status": gate.get("status"),
        "missing": gate.get("missing") or [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage OntoForge stage forms")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync")
    commands.add_parser("status")
    commands.add_parser("path")
    submit_parser = commands.add_parser("submit")
    submit_parser.add_argument(
        "--extracted-file", required=True,
        help="must be answers/.extracted.json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        workflow = workflow_state()
        stage = resolve_stage(workflow)
        if args.command == "sync":
            result = sync(stage, workflow)
        elif args.command == "status":
            path = ensure_form(stage)
            result = status(
                stage, path, path.read_text(encoding="utf-8"), workflow)
        elif args.command == "path":
            result = {"ok": True, "stage": stage, "path": str(ensure_form(stage))}
        else:
            result = submit(stage, workflow, args.extracted_file)
    except FormError as error:
        print(json.dumps(
            {"ok": False, "error": str(error)}, ensure_ascii=False, indent=2),
            file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
