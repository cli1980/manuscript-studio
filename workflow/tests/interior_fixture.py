"""Synthetic proposal with real fixture bindings; never a literary assessment."""

import json
from pathlib import Path

from workflow.src.engine import module_at
from workflow.src.storage import digest


def proposal_for(work_path, *, vendor_profile=None, format_target=None):
    work_path = Path(work_path)
    work = json.loads(work_path.read_bytes())
    revision = work["preparation"]["current_revision"]
    manifest_path = work_path.parent / "revisions" / revision / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    example = Path(__file__).resolve().parents[2] / (
        "plugins/manuscript-studio/skills/interior-design/references/proposal.example.json")
    proposal = json.loads(example.read_bytes())
    proposal["basis"]["preparation"] = {
        "work_id": work["work_id"], "record_revision": work["record_revision"],
        "work_sha256": digest(work_path.read_bytes()), "revision": revision,
        "manifest_sha256": digest(manifest_path.read_bytes()),
        "language": work["metadata"]["manuscript_language"], "scope": manifest["scope"],
        "units": [{"chapter_id": c["chapter_id"], "sha256": c["sha256"]} for c in manifest["chapters"]],
    }
    proposal["design_system"]["furniture"]["section_overrides"][0]["chapter_id"] = manifest["chapters"][0]["chapter_id"]
    chapter = manifest["chapters"][-1]
    validator = module_at(example.parents[1] / "scripts/validate_proposal.py")
    entries = validator.paragraphs((manifest_path.parent / chapter["file"]).read_bytes())
    paragraph = next((p for p in entries if p["kind"] == "paragraph"), entries[0])
    proposal["text_roles"] = [{
        "id": "test-insert", "name": "quote", "kind": "special",
        "function": "Synthetic insert for contract tests, not a real model classification.",
        "style_id": "body", "evidence_refs": ["sample-text"],
        "occurrences": [{"chapter_id": chapter["chapter_id"], "chapter_sha256": chapter["sha256"],
                         "paragraph_index": paragraph["paragraph_index"],
                         "paragraph_sha256": paragraph["paragraph_sha256"]}],
    }]
    proposal["evidence"][0].update(
        locator=f"revisions/{revision}/{chapter['file']}", sha256=chapter["sha256"])
    target = proposal["edition_brief"]["production_targets"][0]
    target.update(vendor_id=None, binding=None, ink=None)
    apply_target(proposal, vendor_profile, format_target)
    return proposal


def apply_target(proposal, profile, selection):
    """Scripted-agent behavior for supplied profile context, not production logic."""
    if selection:
        proposal["edition_brief"]["purpose"] = selection["purpose"]
    proposal["vendor_profile"] = profile
    target = proposal["edition_brief"]["production_targets"][0]
    target.update(vendor_id=profile["profile_id"] if profile else None,
                  binding=selection["binding"] if selection else None,
                  vendor_profile_ref={"locator": "vendor_profile/data", "sha256": profile["sha256"]} if profile else None,
                  trim_mm=proposal["design_system"]["page"]["trim_mm"])
