"""Synthetic analysis output for engine tests, not evidence of model reading accuracy."""

import json
from pathlib import Path

from workflow.src.storage import digest


def analysis_context(request):
    return json.JSONDecoder().raw_decode(request.prompt[request.prompt.index('{\n  "stage"'):])[0]


def analyze(request):
    context = analysis_context(request)
    manifest = context["manifest_template"]
    manifest["evidence_audit"] = "passed"
    root = Path(request.cwd)
    for key, artifact in manifest["artifacts"].items():
        content = (f"# Synthetic {key}\n\nFixture-only notes for all prepared units:\n\n"
                   + "\n".join(unit["chapter_id"] for unit in manifest["basis"]["units"]) + "\n").encode()
        path = root / artifact["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        artifact["sha256"] = digest(content)
    for entry, unit in zip(manifest["coverage"], manifest["basis"]["units"]):
        entry["status"] = "read"
        text = (root / unit["path"]).read_text(encoding="utf-8")
        entry["evidence"] = [{"locator": "Synthetic fixture prefix", "quote": text[:200]}]
    path = root / context["manifest_path"]
    path.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
    result = dict(outcome="completed", message="Synthetic analysis package saved.",
                  state_path=context["manifest_path"], work_record=None, output_path=None,
                  gate=None, review_path=None, binding_path=None)
    if "approval_recommendation" in request.output_schema.get("required", []):
        result["approval_recommendation"] = {
            "action": "accept", "response": "continue", "reason": "Synthetic analysis; no approval gate follows.",
        }
    return result
