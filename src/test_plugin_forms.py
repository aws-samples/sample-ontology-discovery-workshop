"""Contract checks for the marketplace plugin's stage Markdown forms."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins/ontoforge-workshop/scripts/forms.py"
)
SPEC = importlib.util.spec_from_file_location("ontoforge_plugin_forms", MODULE_PATH)
assert SPEC and SPEC.loader
forms = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(forms)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def workflow(stage="inception", status="fail"):
    return {
        "current_stage": stage,
        "active_question": "Complete the current evidence.",
        "gates": {
            stage: {
                "status": status,
                "missing": [] if status == "pass" else ["required evidence"],
                "checks": [{
                    "id": f"{stage}.quality",
                    "status": status,
                    "requirement": "required evidence",
                }],
            }
        },
        "review_findings": [{
            "id": "finding-001",
            "text": "Resolve an ambiguous term",
            "severity": "medium",
            "status": "open",
        }],
        "last_validation": {
            "status": "pass",
            "freshness": "current",
        },
        "handoff_manifest": {"status": "complete"},
    }


def fill_required(text):
    output = []
    for line in text.splitlines():
        output.append(line)
        if line.startswith("<!-- REQUIRED:"):
            key = line.removeprefix("<!-- REQUIRED:").removesuffix(" -->")
            output.append(f"사용자가 작성한 {key} 증거")
    return "\n".join(output) + "\n"


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        answers = root / "answers"
        old_project_root = os.environ.get("ONTOFORGE_PROJECT_ROOT")
        os.environ["ONTOFORGE_PROJECT_ROOT"] = str(root)
        (root / "src/ontology_workshop").mkdir(parents=True)
        (root / "src/ontology_workshop/server.py").write_text(
            "# test marker\n", encoding="utf-8")
        try:
            initial = workflow()
            created = forms.sync("inception", initial)
            path = Path(created["path"])
            require(path.is_file(), "sync did not create the current-stage form")
            require(created["status"] == "draft" and len(created["missing"]) == 6,
                    "blank form did not report required sections")
            require(len(list(answers.glob("*.md"))) == 1,
                    "sync created future-stage forms")

            path.write_text(
                fill_required(path.read_text(encoding="utf-8")),
                encoding="utf-8")
            ready = forms.status(
                "inception", path, path.read_text(encoding="utf-8"), initial)
            require(ready["status"] == "ready" and not ready["missing"],
                    "completed form was not ready")
            digest = ready["fingerprint"]
            require(forms.sync("inception", initial)["fingerprint"] == digest,
                    "server-state sync changed the answer fingerprint")

            damaged = path.read_text(encoding="utf-8").replace(
                "<!-- REQUIRED:actor -->", "")
            try:
                forms.status("inception", path, damaged, initial)
            except forms.FormError as error:
                require("required-section markers" in str(error),
                        "damaged marker produced the wrong error")
            else:
                raise AssertionError("deleted required marker bypassed validation")

            calls = []

            def fake_api(method, endpoint, payload=None):
                calls.append((method, endpoint, payload))
                return {
                    "ok": True,
                    "claim": {"id": f"claim-{len(calls):03d}"},
                    "workflow": workflow(status="pass"),
                }

            forms.api_request = fake_api
            extracted = answers / ".extracted.json"
            extracted.write_text(
                json.dumps({"user_stories": [{"priority": "high"}]}),
                encoding="utf-8")
            submitted = forms.submit(
                "inception", initial, str(extracted))
            require(submitted["endpoint"] == "/workflow/answer",
                    "first form did not use workflow answer")
            require(not extracted.exists(),
                    "successful submit retained temporary extracted JSON")
            require(calls[0][2]["source"] == "stage_markdown_form",
                    "form provenance was not preserved")
            require("ONTOFORGE:SERVER-STATE" not in calls[0][2]["text"],
                    "generated state leaked into customer evidence")

            duplicate_file = answers / ".extracted.json"
            duplicate_file.write_text("{}", encoding="utf-8")
            duplicate = forms.submit(
                "inception", workflow(status="pass"), str(duplicate_file))
            require(duplicate["duplicate"] and len(calls) == 1,
                    "unchanged form was submitted twice")
            require(not duplicate_file.exists(),
                    "duplicate submit retained temporary extracted JSON")

            revised_text = path.read_text(encoding="utf-8").replace(
                "사용자가 작성한 actor 증거", "사용자가 수정한 actor 증거")
            path.write_text(revised_text, encoding="utf-8")
            revised_file = answers / ".extracted.json"
            revised_file.write_text(
                '{"user_stories":[{"priority":"high"}]}', encoding="utf-8")
            revised = forms.submit(
                "inception", workflow(status="pass"), str(revised_file))
            require(revised["endpoint"] == "/workflow/clarify" and len(calls) == 2,
                    "revised submitted form did not become a clarification")

            wrong_stage_file = answers / ".extracted.json"
            wrong_stage_file.write_text("{}", encoding="utf-8")
            try:
                forms.submit(
                    "discovery", workflow("inception"), str(wrong_stage_file))
            except forms.FormError as error:
                require("currently at inception" in str(error),
                        "wrong-stage error lost server-stage detail")
            else:
                raise AssertionError("wrong-stage form submission was accepted")
            require(wrong_stage_file.exists(),
                    "failed submit deleted temporary extracted JSON")

            review_block = forms.state_block(
                workflow("adversarial_review"), "adversarial_review")
            require("review_findings/finding-001" in review_block,
                    "review form state omitted decision targets")
            handoff_block = forms.state_block(
                workflow("validation_handoff"), "validation_handoff")
            require("정적 RDF 검증: pass" in handoff_block
                    and "인계 manifest: complete" in handoff_block,
                    "handoff form state omitted validation evidence")
        finally:
            if old_project_root is None:
                os.environ.pop("ONTOFORGE_PROJECT_ROOT", None)
            else:
                os.environ["ONTOFORGE_PROJECT_ROOT"] = old_project_root

    print("Marketplace plugin form lifecycle checks passed")


if __name__ == "__main__":
    main()
