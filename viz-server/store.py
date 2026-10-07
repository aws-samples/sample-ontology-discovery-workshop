from __future__ import annotations

import datetime
import json
import os
import re
import tempfile
import threading
import uuid
from pathlib import Path

from model import diff_states, normalize, structural_errors
from quality import analyze


MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
REVISION_ID = re.compile(r"^[0-9a-f]{32}$")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path):
    with path.open("rb") as stream:
        content = stream.read(MAX_DOCUMENT_BYTES + 1)
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("Graph file exceeds the 8 MiB local workshop limit")
    def invalid_constant(value):
        raise ValueError(f"Non-finite JSON number is not supported: {value}")
    return json.loads(content, parse_constant=invalid_constant)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".ontology-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class GraphStore:
    def __init__(self, data_root):
        self.data_root = Path(data_root).resolve()
        self.lock = threading.RLock()
        self.cache_key = None
        self.cached = None

    def snapshot(self):
        with self.lock:
            path = self.data_root / "current.json"
            if not path.exists():
                state = normalize({"metadata": {"title": "아직 게시된 모델이 없습니다"}, "elements": {"nodes": [], "edges": []}})
                state.update({"empty": True, "publication": None})
                state["quality"] = analyze(state)
                return state
            stat = path.stat()
            key = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
            if key != self.cache_key:
                document = read_json(path)
                state = normalize(document)
                publication = document.get("_publication")
                if publication is not None and (not isinstance(publication, dict) or not REVISION_ID.fullmatch(str(publication.get("id", ""))) or not isinstance(publication.get("changes"), list)):
                    raise ValueError("게시 메타데이터가 손상되었습니다. 원본 파일을 보존하고 마지막 게시 버전을 확인하세요.")
                state.update({"empty": False, "publication": publication})
                state["quality"] = analyze(state)
                self.cached = state
                self.cache_key = key
            return self.cached

    def history(self, limit=30):
        state = self.snapshot()
        entry = state.get("publication")
        records = []
        seen = set()
        while isinstance(entry, dict) and len(records) < limit:
            entry_id = entry.get("id", "")
            if not REVISION_ID.fullmatch(entry_id) or entry_id in seen:
                break
            seen.add(entry_id)
            records.append(entry)
            parent_id = entry.get("parent_id")
            if not isinstance(parent_id, str) or not REVISION_ID.fullmatch(parent_id):
                break
            target = self.data_root / "revisions" / f"{parent_id}.json"
            if not target.is_file() or target.resolve().parent != (self.data_root / "revisions").resolve():
                break
            entry = read_json(target).get("_publication")
        return records

    def append_query(self, entry):
        import fcntl

        self.data_root.mkdir(parents=True, exist_ok=True)
        with (self.data_root / "query-history.jsonl").open("a", encoding="utf-8") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            stream.flush()

    def publish(self, document, actor, summary, expected_revision=None, approval_note=""):
        import fcntl

        if not actor.strip() or not summary.strip():
            raise ValueError("actor와 summary를 명시해야 합니다.")
        state = normalize(document)
        errors = structural_errors(state)
        if errors:
            raise ValueError("; ".join(errors[:10]))
        self.data_root.mkdir(parents=True, exist_ok=True)
        with (self.data_root / ".publish.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            current = self.snapshot()
            if not current["empty"] and expected_revision != current["document_revision"]:
                raise ValueError(f"Revision conflict: 먼저 현재 상태를 읽고 --expected-revision {current['document_revision']}을 지정하세요.")
            if current["empty"] and expected_revision not in (None, ""):
                raise ValueError("Revision conflict: 현재 게시된 모델이 없습니다.")
            entry = {"id": uuid.uuid4().hex, "parent_id": (current.get("publication") or {}).get("id"), "published_at": now(), "actor": actor.strip(), "summary": summary.strip(), "approval_note": approval_note.strip(), "graph_revision": state["revision"], "changes": diff_states(None if current["empty"] else current, state)}
            output = dict(document)
            output["_publication"] = entry
            if len(json.dumps(output, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")) + 1 > MAX_DOCUMENT_BYTES:
                raise ValueError("게시 문서와 변경 내역이 8 MiB 제한을 초과합니다.")
            archive = self.data_root / "revisions" / f"{entry['id']}.json"
            atomic_json(archive, output)
            atomic_json(self.data_root / "current.json", output)
            return self.snapshot()
