"""Workflow template discovery, validation, engine resolution, and engine identity."""

from __future__ import annotations

import copy
import functools
import hashlib
import importlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = WORKFLOW_ROOT / "templates"
ENGINE_VERSION = "m1"
ID = {"type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"}
PATHS = {"type": "array", "items": {"type": "string", "minLength": 1}}
TEMPLATE_SCHEMA = {
    "type": "object",
    "required": ["id", "title", "workflow", "engine", "agents", "gates", "stages"],
    "properties": {
        "id": ID,
        "title": {"type": "string", "minLength": 1},
        "workflow": ID,
        "engine": {"type": "string", "pattern": r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$"},
        "locked_metadata": PATHS,
        "prepared_input": {"type": "boolean"},
        "work_preparation": {"type": "boolean"},
        # Default maximum passage size, by unit; a run may choose another value at creation.
        "passage_size": {"type": "object", "required": ["cjk_chars", "words"], "additionalProperties": False,
                         "properties": {"cjk_chars": {"type": "integer", "minimum": 100},
                                        "words": {"type": "integer", "minimum": 100}}},
        "produces": {"type": "string"},
        # The completed run's document becomes a new work, ready for further workflows.
        "hands_off": {"type": "boolean"},
        "consumes": {"type": "string"},
        "agents": {"type": "object", "minProperties": 1, "additionalProperties": {
            "type": "object", "required": ["skill", "skills", "model"],
            "properties": {
                "skill": {"type": "string", "minLength": 1},
                "skills": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string"}},
                "model": {"type": ["string", "null"], "minLength": 1},
            },
        }},
        "library": {"type": "object", "properties": {
            "checkout": {"type": "array", "items": {
                "type": "object", "required": ["artifact", "path"], "additionalProperties": False,
                "properties": {"artifact": {"type": "string"}, "path": {"type": "string"}},
            }},
            "areas": PATHS,
        }},
        "gates": {"type": "object", "additionalProperties": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "sheet": {"enum": ["required", "optional"]},
                "binding": {"enum": ["required", "optional"]},
                "closure": {"enum": ["required", "implied"]},
                "item_binding": {"type": "boolean"},
                "command": {"type": "string", "minLength": 1},
                "empty_command": {"type": "string", "minLength": 1},
                "empty_evidence": {"type": "string", "minLength": 1},
                # Workspace documents the reviewer reads and approves as presented (e.g. glossary and voice).
                "documents": {**PATHS, "minItems": 1},
            },
        }},
        "stages": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["id", "kind"],
            "properties": {
                "id": ID,
                "kind": {"enum": ["agent", "metadata_review", "select", "acceptance", "production",
                                   "publication", "export"]},
                "agent": {"type": "string"},
                "preparation": {"type": "boolean"},
                # A select stage: the user picks option stages one at a time (e.g. editing passes) and accepts
                # each one's output, until choosing to continue with the next stage.
                "options": {"type": "array", "minItems": 1, "items": {
                    "type": "object", "required": ["stage", "title"], "additionalProperties": False,
                    "properties": {"stage": ID, "title": {"type": "string", "minLength": 1},
                                   "description": {"type": "string", "minLength": 1}},
                }},
                # A workflow-specific review presented with the front-matter unit, after preparation.
                "front_matter": {"type": "boolean"},
                "edits_text": {"type": "boolean"},
                "iterate": {"enum": ["chapters"]},
                "gates": {"type": "array", "items": {"type": "string"}},
                "owns": PATHS,
                "iteration": {"type": "object", "properties": {
                    "owns": PATHS, "carry_forward": PATHS, "restartable": {"type": "boolean"},
                    "conclude": {"type": "boolean"},
                }},
            },
        }},
    },
}
_registered: dict[str, Path] = {}


def validate(template, *, origin="template"):
    error = next(Draft202012Validator(TEMPLATE_SCHEMA).iter_errors(template), None)
    if error:
        location = ".".join(map(str, error.absolute_path)) or "<root>"
        raise ValueError(f"Invalid {origin} at {location}: {error.message}")
    ids = [stage["id"] for stage in template["stages"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{origin}: stage IDs must be unique.")
    for stage in template["stages"]:
        if stage["kind"] == "agent" and stage.get("agent") not in template["agents"]:
            raise ValueError(f"{origin}: stage {stage['id']} names an unknown agent.")
        if stage["kind"] != "agent" and ("agent" in stage or "gates" in stage or "iterate" in stage):
            raise ValueError(f"{origin}: only agent stages run agents, raise gates, or iterate.")
        for gate in stage.get("gates", []):
            if gate not in template["gates"]:
                raise ValueError(f"{origin}: stage {stage['id']} names an undeclared gate {gate}.")
        if (stage["kind"] == "select") != ("options" in stage):
            raise ValueError(f"{origin}: select stages, and only they, declare options.")
        if stage.get("front_matter"):
            before = template["stages"][:template["stages"].index(stage)]
            if stage["kind"] != "agent" or stage.get("iterate") or stage.get("preparation") \
                    or not (template.get("prepared_input") or any(s.get("preparation") for s in before)):
                raise ValueError(f"{origin}: a front-matter stage is a non-iterating agent stage after preparation.")
            if not any("documents" in template["gates"][gate] for gate in stage.get("gates", [])):
                raise ValueError(f"{origin}: a front-matter stage needs a gate that presents documents.")
    for name, rules in template["gates"].items():
        if "documents" in rules and not rules.get("command"):
            raise ValueError(f"{origin}: document gate {name} needs an approval command.")
    stages = {stage["id"]: stage for stage in template["stages"]}
    chosen = [option["stage"] for stage in template["stages"] for option in stage.get("options", [])]
    if len(chosen) != len(set(chosen)):
        raise ValueError(f"{origin}: a stage can be an option of only one select stage, once.")
    for stage_id in chosen:
        option = stages.get(stage_id)
        if option is None or option["kind"] != "agent" or option.get("preparation") or option.get("front_matter"):
            raise ValueError(f"{origin}: select option {stage_id} must be an agent stage other than preparation or front matter.")
    kinds = [stage["kind"] for stage in template["stages"]]
    if "export" in kinds and kinds.index("export") != len(kinds) - 1:
        raise ValueError(f"{origin}: export must be the final stage.")
    if "export" in kinds and "acceptance" not in kinds[:kinds.index("export")]:
        raise ValueError(f"{origin}: export requires a preceding acceptance stage.")
    if "consumes" in template and any(stage.get("preparation") for stage in template["stages"]):
        raise ValueError(f"{origin}: a derived template has no preparation stage.")
    return template


def load(path):
    path = Path(path).resolve()
    template = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(template, dict):
        raise ValueError(f"{path}: a template must be a JSON object.")
    return validate(template, origin=str(path))


def _paths():
    paths = {}
    for path in sorted(TEMPLATES.glob("*/template.json")):
        paths[load(path)["id"]] = path
    paths.update(_registered)
    return paths


def register(path):
    """Add a template at runtime, e.g. a test-only template outside workflow/templates."""
    path = Path(path).resolve()
    template = load(path)
    engine_class(template["engine"])
    _registered[template["id"]] = path
    return template["id"]


def unregister(template_id):
    _registered.pop(template_id, None)


def templates():
    return {template_id: load(path) for template_id, path in _paths().items()}


def get(template_id):
    path = _paths().get(template_id)
    if path is None:
        raise ValueError(f"Unknown workflow template: {template_id}")
    return copy.deepcopy(load(path))


def template_dir(template_id):
    return _paths()[template_id].parent


def engine_class(reference):
    module_name, _, name = reference.partition(":")
    if not module_name.startswith("workflow."):
        raise ValueError("Template engines must live in the workflow package.")
    cls = getattr(importlib.import_module(module_name), name, None)
    from .engine import Engine
    if not (isinstance(cls, type) and issubclass(cls, Engine)):
        raise ValueError(f"Template engine is not an Engine subclass: {reference}")
    return cls


def _tree_hash(root, pattern):
    result = hashlib.sha256()
    for path in sorted(root.glob(pattern)):
        if path.is_file() and "__pycache__" not in path.parts:
            result.update(path.relative_to(root).as_posix().encode() + b"\0")
            result.update(hashlib.sha256(path.read_bytes()).digest())
    return result.hexdigest()


@functools.lru_cache(maxsize=1)
def _source_hash():
    python = _tree_hash(Path(__file__).resolve().parent, "**/*.py")
    pi_extension = _tree_hash(WORKFLOW_ROOT / "adapters/pi", "*.mjs")
    return hashlib.sha256(f"{python}:{pi_extension}".encode()).hexdigest()


def engine_identity(template_id):
    """Engine code plus the template directory; skill bundles are pinned per run separately."""
    combined = hashlib.sha256(f"{_source_hash()}:{_tree_hash(template_dir(template_id), '**/*')}".encode())
    return {"version": ENGINE_VERSION, "sha256": combined.hexdigest()}
