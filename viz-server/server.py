#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
import socket
import sys
import threading
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from cypher_export import export_cypher
from query_engine import QueryEngine, validate_query
from store import GraphStore, atomic_json, now, read_json


SCRIPT_DIR = Path(__file__).resolve().parent
LIBRARIES = ["cytoscape.min.js", "layout-base.min.js", "cose-base.min.js", "cytoscape-fcose.min.js", "cytoscape-cose-bilkent.min.js"]
STATIC_FILES = {"index.html", "app.js", "styles.css", *[f"lib/{name}" for name in LIBRARIES]}
DATA_FILES = {"current.json", "persona-index.json", "trace-links.json", "render-status.json"}


def find_open_port(start, end):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No open port in range {start}-{end}")


def safe_join(root, *parts):
    candidate = (root / Path(*parts)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


class VizServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, data_root, static_root):
        super().__init__(address, VizHandler)
        self.store = GraphStore(data_root)
        self.static_root = static_root
        self.engine = QueryEngine()
        self.token = secrets.token_urlsafe(32)
        self.file_lock = threading.RLock()

    def server_close(self):
        if hasattr(self, "engine"):
            with self.engine.lock:
                self.engine.close()
        super().server_close()


class VizHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, message, *args):
        sys.stderr.write(f"[viz-server] {message % args}\n")

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()

    def _json(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message, status=400):
        self._json({"ok": False, "error": str(message)}, status)

    def _trusted_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in {f"localhost:{port}", f"127.0.0.1:{port}"}

    def _state(self):
        state = dict(self.server.store.snapshot())
        state["query"] = self.server.engine.capability(state)
        state["session_token"] = self.server.token
        return state

    def do_GET(self):
        if not self._trusted_host():
            self._error("Localhost Host header required", 403)
            return
        path = unquote(urlparse(self.path).path)
        try:
            if path == "/api/state":
                self._json(self._state())
            elif path == "/api/quality":
                self._json(self.server.store.snapshot()["quality"])
            elif path == "/api/history":
                self._json({"entries": self.server.store.history()})
            elif path == "/api/queries":
                self._json({"entries": self._query_history()})
            elif path == "/api/export/cypher":
                parameters = parse_qs(urlparse(self.path).query, keep_blank_values=True)
                state = self.server.store.snapshot()
                revision = parameters.get("revision", [state["revision"]])[0]
                if revision != state["revision"]:
                    self._error("모델 버전이 변경됐습니다. 새로 고침 후 다시 내보내세요.", 409)
                else:
                    self._json(export_cypher(state, parameters.get("scope", ["model"])[0]))
            elif path == "/health":
                self._health()
            elif path.startswith("/source/"):
                relative = path[len("/source/"):]
                target = safe_join(self.server.store.data_root.parent, relative)
                if target is None or target.suffix != ".md" or any(part.startswith(".") for part in Path(relative).parts):
                    self._error("Only workshop Markdown documents are available", 403)
                else:
                    self._serve_file(target, "text/plain; charset=utf-8")
            elif path.startswith("/data/"):
                relative = path[len("/data/"):]
                target = safe_join(self.server.store.data_root, relative)
                if target is None:
                    self._error("Path traversal denied", 403)
                elif relative not in DATA_FILES:
                    self._error("Data file is not exposed", 404)
                elif not target.exists() and relative == "current.json":
                    self._json({"metadata": {"phase": "(no data)"}, "elements": {"nodes": [], "edges": []}})
                else:
                    self._serve_file(target, "application/json; charset=utf-8")
            else:
                relative = "index.html" if path == "/" else path.lstrip("/")
                target = safe_join(self.server.static_root, relative)
                if target is None or relative not in STATIC_FILES:
                    self._error("Not found", 404)
                else:
                    self._serve_file(target)
        except (ValueError, OSError) as error:
            self._error(error, 422)

    def _serve_file(self, path, content_type=None):
        if not path.is_file():
            self._error("Not found", 404)
            return
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _payload(self):
        if not self._trusted_host():
            raise PermissionError("Localhost Host header required")
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{self.headers.get('Host')}":
            raise PermissionError("Cross-origin requests are not allowed")
        if not secrets.compare_digest(self.headers.get("X-Ontology-Token", ""), self.server.token):
            raise PermissionError("Refresh the page to obtain a session token")
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Content-Type must be application/json")
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 65536:
            raise ValueError("JSON request must be between 1 and 65,536 bytes")
        def invalid_constant(value):
            raise ValueError(f"Non-finite JSON number: {value}")
        payload = json.loads(self.rfile.read(length), parse_constant=invalid_constant)
        if not isinstance(payload, dict):
            raise ValueError("JSON request must be an object")
        return payload

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/query", "/feedback", "/render-status"):
            self._error("No model mutation endpoints are exposed", 404)
            return
        try:
            payload = self._payload()
            if path == "/api/query":
                self._query(payload)
            elif path == "/feedback":
                self._feedback(payload)
            else:
                self._render_status(payload)
        except PermissionError as error:
            self._error(error, 403)
        except (ValueError, TypeError, UnicodeError, OSError) as error:
            self._error(error)

    def _query(self, payload):
        state = self.server.store.snapshot()
        if payload.get("revision") != state["revision"]:
            self._error("모델 버전이 변경됐습니다. 새로 고침 후 다시 실행하세요.", 409)
            return
        query = payload.get("cypher", "")
        entry = {"at": now(), "cypher": query if isinstance(query, str) else "", "revision": state["revision"], "parameters": payload.get("parameters", {}), "actor": "browser-query"}
        try:
            validate_query(query)
            capability = self.server.engine.capability(state)
            if not capability["available"]:
                self._error(capability["reason"], 503)
                return
            result = self.server.engine.execute(state, query, payload.get("parameters"))
            entry.update({key: result[key] for key in ("ok", "count", "truncated", "elapsed_ms")})
            self._append_query(entry)
            self._json(result)
        except Exception as error:
            entry.update({"ok": False, "error": str(error)[:2000]})
            self._append_query(entry)
            self._error(str(error)[:2000], 422)

    def _append_query(self, entry):
        self.server.store.append_query(entry)

    def _query_history(self):
        path = self.server.store.data_root / "query-history.jsonl"
        if not path.exists():
            return []
        with self.server.file_lock, path.open("rb") as stream:
            stream.seek(0, 2)
            if stream.tell() > 1024 * 1024:
                stream.seek(-1024 * 1024, 2)
                stream.readline()
            else:
                stream.seek(0)
            lines = deque(stream, maxlen=30)
        records = []
        for line in reversed(lines):
            try:
                records.append(json.loads(line))
            except (ValueError, UnicodeError):
                continue
        return records

    def _feedback(self, payload):
        element_id = payload.get("nodeId")
        note = payload.get("note")
        if not isinstance(element_id, str) or not element_id.strip() or not isinstance(note, str) or not note.strip():
            raise ValueError("nodeId와 note가 필요합니다.")
        if len(element_id) > 300 or len(note) > 4000:
            raise ValueError("Feedback is too long")
        state = self.server.store.snapshot()
        if payload.get("revision") != state["revision"]:
            self._error("모델 버전이 변경됐습니다. 대상을 다시 확인하세요.", 409)
            return
        known_ids = {item["data"]["id"] for graph in state["graphs"].values() for elements in graph.values() for item in elements}
        if element_id not in known_ids:
            raise ValueError("현재 모델에 없는 대상입니다.")
        feedback = self.server.store.data_root.parent / "feedback-pending.md"
        escaped_id = json.dumps(element_id, ensure_ascii=False)
        quoted_note = "\n".join("> " + line for line in note.strip().splitlines())
        entry = f"\n## Feedback: {now()}\n**Node:** {escaped_id}\n**Revision:** {state['revision']}\n**Type:** review-request\n\n{quoted_note}\n\n---\n"
        with self.server.file_lock, feedback.open("a", encoding="utf-8") as stream:
            if stream.tell() == 0:
                stream.write("# Feedback Pending\n")
            stream.write(entry)
        self._json({"ok": True, "appended_to": "feedback-pending.md"})

    def _render_status(self, payload):
        if not isinstance(payload.get("ok"), bool):
            raise ValueError("ok must be boolean")
        for key in ("nodes_rendered", "edges_rendered"):
            if not isinstance(payload.get(key), int) or isinstance(payload[key], bool) or payload[key] < 0:
                raise ValueError(f"{key} must be a nonnegative integer")
        errors = payload.get("errors", [])
        if not isinstance(errors, list) or not isinstance(payload.get("extensions", {}), dict):
            raise ValueError("Invalid render report")
        report = {"reported_at": now(), "server_pid": os.getpid(), "ok": payload["ok"], "revision": str(payload.get("revision", "")), "view": str(payload.get("view", "")), "nodes_rendered": payload["nodes_rendered"], "edges_rendered": payload["edges_rendered"], "extensions": payload.get("extensions", {}), "errors": [str(error)[:500] for error in errors[:10]]}
        with self.server.file_lock:
            atomic_json(self.server.store.data_root / "render-status.json", report)
        self._json({"ok": True})

    def _health(self):
        libraries = {name: (self.server.static_root / "lib" / name).is_file() for name in LIBRARIES}
        try:
            state = self.server.store.snapshot()
            errors = []
        except (ValueError, OSError) as error:
            state = None
            errors = [str(error)]
        report_path = self.server.store.data_root / "render-status.json"
        try:
            report = read_json(report_path) if report_path.exists() else None
            if report is not None and not isinstance(report, dict):
                raise ValueError("render-status.json must be an object")
        except (ValueError, OSError):
            report = None
            errors.append("render-status.json is invalid")
        current_render = bool(state and report and report.get("revision") == state["revision"] and report.get("server_pid") == os.getpid())
        extensions = report.get("extensions", {}) if isinstance(report, dict) else {}
        if not isinstance(extensions, dict):
            extensions = {}
            errors.append("render-status.json extensions must be an object")
        graph = state["graphs"].get(report.get("view"), {}) if state and isinstance(report, dict) else {}
        count_matches = bool(graph and report.get("nodes_rendered") == len(graph["nodes"]) and report.get("edges_rendered") == len(graph["edges"]))
        render_ok = bool(current_render and report.get("ok") and count_matches and all(extensions.get(name) is True for name in ("fcose", "cose-bilkent")))
        ready = bool(state and not state["empty"] and all(libraries.values()) and render_ok and not errors)
        self._json({"status": "ok" if ready else "degraded", "checked_at": now(), "pid": os.getpid(), "libs": libraries, "errors": errors, "data": {"current_json_valid": state is not None, "revision": state["revision"] if state else None}, "last_client_render": report, "client_render_current": current_render, "client_render_ok": render_ok, "query": self.server.engine.capability(state) if state else None, "quality": state["quality"]["counts"] if state else None})


def main():
    parser = argparse.ArgumentParser(description="Read-only ontology workshop browser")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--port-start", type=int, default=5173)
    parser.add_argument("--port-end", type=int)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--static-dir", default=str(SCRIPT_DIR))
    args = parser.parse_args()
    end_port = args.port_end if args.port_end is not None else args.port_start + 10
    if not 1 <= args.port_start <= end_port <= 65535:
        parser.error("port range must be within 1..65535")
    static_root = Path(args.static_dir).resolve()
    if not (static_root / "index.html").is_file():
        parser.error("static-dir must contain index.html")
    data_root = Path(args.data_dir).resolve()
    data_root.mkdir(parents=True, exist_ok=True)
    server = None
    for port in range(args.port_start, end_port + 1):
        try:
            server = VizServer(("127.0.0.1", port), data_root, static_root)
            break
        except OSError:
            continue
    if server is None:
        parser.error("No open port in requested range")
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"ONTOLOGY_VIZ_PID={os.getpid()}", flush=True)
    print(f"ONTOLOGY_VIZ_URL={url}", flush=True)
    print(f"ONTOLOGY_VIZ_DATA={data_root}", flush=True)
    if not args.no_browser:
        threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
