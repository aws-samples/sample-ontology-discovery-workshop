from __future__ import annotations

import argparse
import json
import sys

from store import GraphStore, read_json
from pathlib import Path
from query_engine import QueryEngine
from store import now
from cypher_export import export_cypher


def main():
    parser = argparse.ArgumentParser(description="Local AI publisher. The browser never modifies the model.")
    parser.add_argument("--data-dir", required=True)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("inspect")
    subcommands.add_parser("quality")
    export = subcommands.add_parser("export-cypher")
    export.add_argument("--scope", choices=("schema", "data", "model"), default="model")
    export.add_argument("--output")
    query = subcommands.add_parser("query")
    query.add_argument("--cypher", required=True)
    query.add_argument("--parameters", default="{}")
    query.add_argument("--actor", required=True)
    publish = subcommands.add_parser("publish")
    publish.add_argument("--file", required=True)
    publish.add_argument("--actor", required=True)
    publish.add_argument("--summary", required=True)
    publish.add_argument("--expected-revision")
    publish.add_argument("--approval-note", default="")
    args = parser.parse_args()
    store = GraphStore(args.data_dir)
    try:
        if args.command == "export-cypher":
            result = export_cypher(store.snapshot(), args.scope)
            if args.output:
                destination = Path(args.output).expanduser()
                if destination.suffix.lower() != ".cypher":
                    raise ValueError("출력 파일의 확장자는 .cypher여야 합니다.")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("x", encoding="utf-8") as stream:
                    stream.write(result["content"])
                print(json.dumps({"file": str(destination.resolve()), "scope": result["scope"], "revision": result["revision"], "statements": result["statement_count"]}, ensure_ascii=False))
            else:
                print(result["content"], end="")
            return 0
        if args.command == "query":
            engine = QueryEngine()
            state = store.snapshot()
            entry = {"at": now(), "actor": args.actor, "cypher": args.cypher, "revision": state["revision"]}
            try:
                parameters = json.loads(args.parameters)
                entry["parameters"] = parameters
                result = engine.execute(state, args.cypher, parameters)
                entry.update({key: result[key] for key in ("ok", "count", "truncated", "elapsed_ms")})
                store.append_query(entry)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0
            except Exception as error:
                entry.update({"ok": False, "error": str(error)[:2000]})
                store.append_query(entry)
                raise ValueError(str(error)) from error
            finally:
                engine.close()
        if args.command == "publish":
            state = store.publish(read_json(Path(args.file)), args.actor, args.summary, args.expected_revision, args.approval_note)
        else:
            state = store.snapshot()
        if args.command == "quality":
            result = state["quality"]
        else:
            result = {key: state[key] for key in ("revision", "document_revision", "metadata", "counts", "empty", "publication")}
            if result["publication"]:
                result["publication"] = {key: value for key, value in result["publication"].items() if key != "changes"}
            result["quality"] = {"open_count": state["quality"]["open_count"], "counts": state["quality"]["counts"]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
