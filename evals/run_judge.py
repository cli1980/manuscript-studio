"""Export judge training data, evaluate a judge blindly, or score new translations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIMENSIONS = ("fidelity", "english_naturalness", "literary_voice")
METRICS = ("overall_score", *DIMENSIONS)
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
LIMIT = 4 * 1024 * 1024
SCORE_SCHEMA = {"type": "integer", "minimum": 1, "maximum": 5}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": SCORE_SCHEMA,
        "dimension_scores": {
            "type": "object",
            "properties": {name: SCORE_SCHEMA for name in DIMENSIONS},
            "required": list(DIMENSIONS),
            "additionalProperties": False,
        },
        "rationale": {"type": ["string", "null"]},
    },
    "required": ["overall_score", "dimension_scores", "rationale"],
    "additionalProperties": False,
}


class EvaluationError(ValueError):
    pass


def identifier(value):
    if not isinstance(value, str) or len(value) > 100 or not ID.fullmatch(value):
        raise EvaluationError("Invalid case, passage, or rubric identifier.")
    return value


def guarded(path, area):
    path, area = Path(os.path.abspath(path)), Path(os.path.abspath(area))
    if not path.is_relative_to(area):
        raise EvaluationError("A file reference escapes its permitted data directory.")
    for entry in (path, *path.parents):
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ) or (stat.S_ISREG(info.st_mode) and info.st_nlink > 1):
            raise EvaluationError("Linked or redirected files are not permitted.")
    return path


def reference(parent, name, area):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or Path(name).is_absolute():
        raise EvaluationError("Stored file references must be relative paths using forward slashes.")
    return guarded(parent / name, area)


def read_bytes(path, area):
    path = guarded(path, area)
    with path.open("rb") as handle:
        raw = handle.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise EvaluationError("An input file exceeds the 4 MiB limit.")
    return raw


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise EvaluationError("Duplicate JSON keys are not permitted.")
            result[key] = value
        return result

    def invalid_constant(value):
        raise EvaluationError("Non-finite JSON numbers are not permitted.")

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as exc:
        raise EvaluationError("Invalid JSON data.") from exc


def object_json(raw):
    result = parse_json(raw)
    if not isinstance(result, dict):
        raise EvaluationError("Expected a JSON object.")
    return result


def text_value(value):
    if value is not None and (not isinstance(value, str) or len(value) > 10000):
        raise EvaluationError("Rubric guidance must be text of at most 10,000 characters or null.")
    return value


def rubric_contract(rubric):
    if rubric.get("scale", {}).get("min") != 1 or rubric.get("scale", {}).get("max") != 5:
        raise EvaluationError("The translation judge requires a 1–5 rubric.")
    anchors = rubric["scale"].get("anchors", {})
    dimensions = rubric.get("dimensions", {})
    if any(not isinstance(anchors.get(str(n)), str) for n in range(1, 6)):
        raise EvaluationError("The rubric must define all five score anchors.")
    if any(not isinstance(dimensions.get(name), str) for name in DIMENSIONS):
        raise EvaluationError("The rubric must define all three translation dimensions.")
    return {
        "rubric_id": identifier(rubric.get("rubric_id")),
        "source_language": rubric.get("source_language"),
        "target_language": rubric.get("target_language"),
        "scale": {"min": 1, "max": 5, "anchors": {str(n): anchors[str(n)] for n in range(1, 6)}},
        "dimensions": {name: dimensions[name] for name in DIMENSIONS},
        "guidance": text_value(rubric.get("guidance")),
    }


def prepare_case(root, case_id, *, model=None, smoke_test=False, temperature=None,
                 purpose="evaluate", translation_file=None):
    case_root = root / "cases/literary-translation" / identifier(case_id)
    paths, hashes, areas = {}, {}, {}

    def read(name, path, area):
        path = guarded(path, area)
        raw = read_bytes(path, area)
        paths[name], hashes[name], areas[name] = path, sha(raw), area
        return raw

    case = object_json(read("case", case_root / "case.json", root / "cases/literary-translation"))
    if case.get("case_id") != case_id or case.get("task") != "literary-translation-quality":
        raise EvaluationError("Case identity or task does not match the requested judge.")
    source_meta_path = reference(case_root, case.get("source_metadata_file"), root / "fixtures/manuscripts")
    if source_meta_path.name != "passage.json":
        raise EvaluationError("Expected shared passage metadata.")
    source = object_json(read("source_metadata", source_meta_path, root / "fixtures/manuscripts"))
    if any(case.get(key) != source.get(key) for key in ("passage_id", "group_id", "source_language")):
        raise EvaluationError("Case and source identifiers do not match.")
    identifier(case.get("passage_id"))
    identifier(case.get("group_id"))
    if (
        type(case.get("revision")) is not int or case["revision"] < 1
        or type(source.get("revision")) is not int or source["revision"] < 1
        or type(case.get("source_revision")) is not int or case["source_revision"] != source["revision"]
    ):
        raise EvaluationError("Case and source revision bindings are invalid.")
    if case.get("source_language") != "zh" or case.get("target_language") != "en":
        raise EvaluationError("This judge currently supports Chinese-to-English translation only.")
    eligible = (
        case.get("status") == "ready"
        and case.get("provenance", {}).get("usage_rights") == "permitted"
        and source.get("provenance", {}).get("usage_rights") == "permitted"
    )
    if not eligible and not smoke_test and purpose != "judge":
        raise EvaluationError("Case is not benchmark-ready. Use --smoke-test for an explicitly exploratory run.")
    source_path = reference(case_root, case.get("source_file"), root / "fixtures/manuscripts")
    if source_path != reference(source_meta_path.parent, source.get("source_file"), source_meta_path.parent):
        raise EvaluationError("Case and passage reference different source texts.")
    if translation_file is None:
        translation_area = case_root
        translation_path = reference(case_root, case.get("translation_file"), case_root)
    else:
        if purpose != "judge":
            raise EvaluationError("A translation override is allowed only in judge mode.")
        translation_path = Path(os.path.abspath(translation_file))
        translation_area = translation_path.parent
        if translation_path.name.lower() == "skill.md" or any(
            translation_path.is_relative_to(area)
            for area in (ROOT.parent / "plugins", root / "judges", root / "rubrics")
        ):
            raise EvaluationError("Provide translated text, not skill instructions or rubric files.")
    if source_path.suffix != ".txt" or translation_path.suffix.lower() not in {".txt", ".md"}:
        raise EvaluationError("Source and translation must be text files.")
    source_text = read("source", source_path, root / "fixtures/manuscripts").decode("utf-8")
    translation_text = read("translation", translation_path, translation_area).decode("utf-8")
    if not source_text.strip() or not translation_text.strip():
        raise EvaluationError("Both source and translation must be populated.")
    rubric_id = identifier(case.get("rubric_id") or "literary-translation-quality-v1")
    rubric = object_json(read("rubric", root / "rubrics" / f"{rubric_id}.json", root / "rubrics"))
    clean_rubric = rubric_contract(rubric)
    if clean_rubric["rubric_id"] != rubric_id or any(
        clean_rubric[key] != case[key] for key in ("source_language", "target_language")
    ):
        raise EvaluationError("Rubric identity or language pair does not match the case.")
    skill = read("judge_skill", root / "judges/literary-translation-judge/SKILL.md", root / "judges").decode("utf-8")
    if not skill.strip():
        raise EvaluationError("Judge skill is empty.")
    embedded = re.findall(r"```json\s*\n(.*?)\n```", skill.replace("\r\n", "\n"), flags=re.DOTALL)
    if len(embedded) != 1 or object_json(embedded[0]) != clean_rubric:
        raise EvaluationError("The judge skill's embedded rubric must match the human scoring rubric.")
    model_input = {
        "source_text": source_text, "translation_text": translation_text,
    }
    request = {
        "messages": [
            {"role": "system", "content": skill},
            {"role": "user", "content": json.dumps(model_input, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "translation_judgment", "strict": True, "schema": OUTPUT_SCHEMA},
        },
    }
    if model:
        request["model"] = model
    if temperature is not None:
        request["temperature"] = temperature
    return {
        "case": case, "rubric_id": rubric_id, "request": request, "paths": paths,
        "areas": areas, "input_hashes": hashes,
        "candidate_source": "external_translation" if translation_file is not None else "case_translation",
        "benchmark_eligible": eligible and not smoke_test and purpose != "judge",
    }


def validate_score(value):
    if type(value) is not int or not 1 <= value <= 5:
        raise EvaluationError("Scores must be integers from 1 to 5.")
    return value


def validate_prediction(value):
    if not isinstance(value, dict) or set(value) != {"overall_score", "dimension_scores", "rationale"}:
        raise EvaluationError("Prediction must contain exactly overall_score, dimension_scores, and rationale.")
    validate_score(value["overall_score"])
    if not isinstance(value["dimension_scores"], dict) or set(value["dimension_scores"]) != set(DIMENSIONS):
        raise EvaluationError("Prediction must score all three translation dimensions.")
    for score in value["dimension_scores"].values():
        validate_score(score)
    if value["rationale"] is not None and (
        not isinstance(value["rationale"], str) or not value["rationale"].strip()
    ):
        raise EvaluationError("Rationale must be nonblank text or null when unavailable.")
    return value


def human_reference(prepared, reviewer):
    case = prepared["case"]
    directory = prepared["paths"]["case"].parent
    raw = read_bytes(directory / "judgments.jsonl", directory)
    records = [object_json(line) for line in raw.splitlines() if line.strip()]
    seen, superseded = {}, set()
    for record in records:
        jid = identifier(record.get("judgment_id"))
        if jid in seen or record.get("case_id") != case["case_id"]:
            raise EvaluationError("Invalid or duplicate human judgment identity.")
        parent = record.get("supersedes_judgment_id")
        if parent is not None:
            identifier(parent)
            if parent not in seen:
                raise EvaluationError("Human judgment history has a missing or forward reference.")
            superseded.add(parent)
        seen[jid] = record
    current = next((r for r in reversed(records) if
        r["judgment_id"] not in superseded and r.get("rater_id") == reviewer
        and r.get("case_revision") == case["revision"]
        and r.get("passage_id") == case["passage_id"]
        and r.get("source_revision") == case["source_revision"]
        and r.get("rubric_version") == prepared["rubric_id"]), None)
    if current is None:
        raise EvaluationError("No current human judgment matches the requested reviewer and versions.")
    if current.get("status") != "complete":
        raise EvaluationError("The current human assessment is a draft; an older completed score will not be substituted.")
    validate_score(current.get("overall_score"))
    dimensions = current.get("dimension_scores") or {}
    if not isinstance(dimensions, dict):
        raise EvaluationError("Invalid human dimension scores.")
    for dimension in DIMENSIONS:
        if dimensions.get(dimension) is not None:
            validate_score(dimensions[dimension])
    return current, sha(raw)


def compare(prediction, human):
    result = {}
    for name in METRICS:
        predicted = prediction["overall_score"] if name == "overall_score" else prediction["dimension_scores"][name]
        expected = human["overall_score"] if name == "overall_score" else (human.get("dimension_scores") or {}).get(name)
        result[name] = {
            "human": expected, "predicted": predicted,
            "signed_error": None if expected is None else predicted - expected,
            "absolute_error": None if expected is None else abs(predicted - expected),
            "exact_match": None if expected is None else predicted == expected,
        }
    return result


def training_target(human):
    dimensions = human.get("dimension_scores") or {}
    if any(dimensions.get(name) is None for name in DIMENSIONS):
        raise EvaluationError("Training export requires all dimension scores; missing human labels are never invented.")
    target = {
        "overall_score": human["overall_score"],
        "dimension_scores": {name: dimensions[name] for name in DIMENSIONS},
        "rationale": human.get("rationale") or None,
    }
    return validate_prediction(target)


def aggregate(comparisons):
    result = {}
    for name in METRICS:
        values = [comparison[name] for comparison in comparisons if comparison[name]["human"] is not None]
        count = len(values)
        result[name] = {
            "count": count,
            "mean_signed_error": sum(v["signed_error"] for v in values) / count if count else None,
            "mean_absolute_error": sum(v["absolute_error"] for v in values) / count if count else None,
            "exact_agreement_rate": sum(v["exact_match"] for v in values) / count if count else None,
        }
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def endpoint(base_url):
    try:
        parsed = urllib.parse.urlsplit(base_url)
        parsed.port
    except ValueError as exc:
        raise EvaluationError("Invalid API base URL.") from exc
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise EvaluationError("API base URL must not contain credentials, a query, or a fragment.")
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        raise EvaluationError("Use HTTPS for model APIs; HTTP is allowed only for local test endpoints.")
    return base_url.rstrip("/") + "/chat/completions"


def call_model(request, url, key, timeout):
    data = json.dumps(request, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json",
    }, method="POST")
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=timeout) as response:
            raw = response.read(LIMIT + 1)
    except urllib.error.HTTPError as exc:
        raise EvaluationError(f"Model API returned HTTP {exc.code}; response body omitted to protect credentials.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise EvaluationError("Could not contact the model API within the configured timeout.") from None
    if len(raw) > LIMIT:
        raise EvaluationError("Model response exceeds the 4 MiB limit.")
    return object_json(raw)


def extract_prediction(response):
    try:
        choice = response["choices"][0]
        message = choice["message"]
        if choice.get("finish_reason") != "stop" or message.get("refusal") or message.get("tool_calls"):
            raise EvaluationError("The model did not finish a plain JSON scoring response.")
        if not isinstance(message.get("content"), str):
            raise EvaluationError("The model returned no text prediction.")
        return validate_prediction(parse_json(message["content"]))
    except (KeyError, IndexError, TypeError, AttributeError):
        raise EvaluationError("Unexpected Chat Completions response format.") from None


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def ensure_inputs_unchanged(prepared, root):
    if any(sha(read_bytes(path, prepared["areas"][name])) != prepared["input_hashes"][name]
           for name, path in prepared["paths"].items()):
        raise EvaluationError("Inputs changed during the run; the result cannot be finalized.")


def run(args):
    purpose = getattr(args, "mode", "evaluate")
    translation_file = getattr(args, "translation_file", None)
    if purpose not in {"evaluate", "judge", "export-training"}:
        raise EvaluationError("Unknown runner mode.")
    if purpose == "export-training" and args.prepare_only:
        raise EvaluationError("Training export reads human labels; it cannot be combined with --prepare-only.")
    if purpose == "judge" and args.reviewer:
        raise EvaluationError("Judge mode does not use human references; omit --reviewer.")
    if translation_file is not None and (purpose != "judge" or not args.case or len(args.case) != 1):
        raise EvaluationError("--translation-file requires judge mode and exactly one --case.")
    if purpose == "export-training" and (not args.reviewer or not args.reviewer.strip()):
        raise EvaluationError("Training export requires --reviewer to select the human targets.")
    root = guarded(args.data_dir, args.data_dir)
    cases_root = guarded(root / "cases/literary-translation", root)
    case_ids = list(dict.fromkeys(args.case or [
        path.name for path in sorted(cases_root.iterdir())
        if not path.name.startswith(".") and (path / "case.json").is_file()
    ]))
    if not case_ids:
        raise EvaluationError("No literary-translation cases found.")
    key = None
    url = endpoint(args.base_url) if purpose != "export-training" else None
    if not args.prepare_only and purpose != "export-training":
        if not args.model:
            raise EvaluationError("Scoring requires --model.")
        if purpose == "evaluate" and (not args.reviewer or not args.reviewer.strip()):
            raise EvaluationError("Live evaluation requires --model and --reviewer.")
        key = os.environ.get(args.api_key_env)
        if not key:
            raise EvaluationError(f"{args.api_key_env} is not set. Configure a model API key or use --prepare-only.")
    prepared = [prepare_case(root, case_id, model=args.model, smoke_test=args.smoke_test,
                             temperature=args.temperature, purpose=purpose,
                             translation_file=translation_file) for case_id in case_ids]
    results = guarded(root / "results", root)
    results.mkdir(exist_ok=True)
    run_id = "judge-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    destination = results / run_id
    destination.mkdir()
    manifest = {
        "schema_version": 1, "run_id": run_id, "started_at": datetime.now(timezone.utc).isoformat(),
        "purpose": purpose,
        "mode": "prepare_only" if args.prepare_only else {
            "evaluate": "model_evaluation", "judge": "judgment", "export-training": "training_export",
        }[purpose],
        "scope": "smoke_test" if args.smoke_test else {
            "evaluate": "benchmark", "judge": "judgment", "export-training": "training",
        }[purpose],
        "benchmark_eligible": purpose == "evaluate" and not args.smoke_test and all(p["benchmark_eligible"] for p in prepared),
        "training_eligible": False,
        "model": args.model, "api_base_url": args.base_url if purpose != "export-training" else None,
        "temperature": args.temperature, "reviewer": args.reviewer,
        "human_labels_sent_to_model": False, "cases": [], "status": "running",
    }
    write_json(destination / "run.json", manifest)
    comparisons = []
    training_rows = []
    training_index = []
    failures = 0
    for item in prepared:
        case = item["case"]
        case_dir = destination / case["case_id"]
        case_dir.mkdir()
        write_json(case_dir / "request.json", item["request"])
        record = {
            "case_id": case["case_id"], "case_revision": case["revision"],
            "group_id": case["group_id"], "passage_id": case["passage_id"],
            "source_revision": case["source_revision"], "rubric_id": item["rubric_id"],
            "input_hashes": item["input_hashes"],
            "candidate_source": item["candidate_source"],
            "request_sha256": sha((case_dir / "request.json").read_bytes()),
            "status": "prepared",
        }
        manifest["cases"].append(record)
        if purpose == "export-training":
            try:
                ensure_inputs_unchanged(item, root)
                human, human_hash = human_reference(item, args.reviewer.strip())
                target = training_target(human)
                row = {
                    "messages": [
                        *item["request"]["messages"],
                        {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)},
                    ],
                }
                write_json(case_dir / "training-target.json", target)
                training_rows.append(row)
                training_index.append({
                    "line": len(training_rows), "case_id": case["case_id"],
                    "group_id": case["group_id"], "case_revision": case["revision"],
                    "source_revision": case["source_revision"], "rubric_id": item["rubric_id"],
                    "human_judgment_id": human["judgment_id"], "human_judgments_sha256": human_hash,
                    "input_hashes": item["input_hashes"],
                })
                record["human_judgment_id"] = human["judgment_id"]
                record["status"] = "exported"
            except (EvaluationError, OSError, UnicodeError) as exc:
                failures += 1
                record["status"] = "failed"
                record["error"] = str(exc)
        elif not args.prepare_only:
            started = time.monotonic()
            try:
                response = call_model(item["request"], url, key, args.timeout)
                record["duration_seconds"] = round(time.monotonic() - started, 3)
                write_json(case_dir / "response.json", response)
                record["response_model"] = response.get("model")
                record["response_id"] = response.get("id")
                prediction = extract_prediction(response)
                write_json(case_dir / "prediction.json", prediction)
                record["status"] = "predicted"
                ensure_inputs_unchanged(item, root)
                if purpose == "evaluate":
                    human, human_hash = human_reference(item, args.reviewer.strip())
                    difference = compare(prediction, human)
                    write_json(case_dir / "comparison.json", {
                        "case_id": case["case_id"], "human_judgment_id": human["judgment_id"],
                        "human_judgments_sha256": human_hash, "scores": difference,
                    })
                    comparisons.append(difference)
                    record["human_judgment_id"] = human["judgment_id"]
                    record["status"] = "compared"
            except (EvaluationError, OSError, UnicodeError) as exc:
                failures += 1
                record["status"] = "failed"
                record["error"] = str(exc)
        write_json(destination / "run.json", manifest)
    manifest["status"] = "prepared" if args.prepare_only else "failed" if failures else "completed"
    manifest["training_eligible"] = (
        purpose == "export-training" and not args.smoke_test and bool(training_rows) and not failures
    )
    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_json(destination / "run.json", manifest)
    if purpose == "export-training":
        for filename, rows in (("training.jsonl", training_rows), ("training-index.jsonl", training_index)):
            (destination / filename).write_text(
                "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows),
                encoding="utf-8",
            )
    if not args.prepare_only:
        summary = {
            "scope": manifest["scope"], "benchmark_eligible": manifest["benchmark_eligible"],
            "cases_requested": len(prepared), "cases_failed": failures,
        }
        if purpose == "evaluate":
            summary.update(cases_compared=len(comparisons), metrics=aggregate(comparisons))
        elif purpose == "judge":
            summary["cases_judged"] = sum(case["status"] == "predicted" for case in manifest["cases"])
        else:
            summary["cases_exported"] = len(training_rows)
        write_json(destination / "summary.json", summary)
    return destination, manifest


def print_report(destination, manifest):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    print(f"{manifest['status']}: {len(manifest['cases'])} case(s)")
    print(f"Artifacts: {destination}")
    if manifest["scope"] == "smoke_test":
        print("Exploratory smoke test; excluded from benchmark results.")
    if manifest["mode"] == "prepare_only":
        print("No model was called. No prediction or evaluation result is available.")
        return
    if manifest["mode"] == "training_export":
        summary = object_json(read_bytes(destination / "summary.json", destination))
        print("No model was called. Human scores are assistant targets; model inputs remain blind.")
        print(f"Human reference reviewer: {manifest['reviewer']}")
        print(f"Exported: {summary['cases_exported']}/{summary['cases_requested']}; failed: {summary['cases_failed']}")
        print(f"Training examples: {destination / 'training.jsonl'}")
        print(f"Case and work-group index: {destination / 'training-index.jsonl'}")
        for case in manifest["cases"]:
            if case["status"] == "failed":
                print(f"{case['case_id']}: {case['error']}")
        return
    print(f"Model: {manifest['model']}")
    judgment_only = manifest["mode"] == "judgment"
    if not judgment_only:
        print(f"Human reference reviewer: {manifest['reviewer']}")
    labels = {
        "overall_score": "Overall", "fidelity": "Fidelity",
        "english_naturalness": "English naturalness", "literary_voice": "Literary voice",
    }
    for case in manifest["cases"]:
        print(f"\nCase: {case['case_id']}")
        if case["status"] != ("predicted" if judgment_only else "compared"):
            print(f"Evaluation failed: {case.get('error', 'No result available.')}")
            continue
        directory = destination / case["case_id"]
        prediction = object_json(read_bytes(directory / "prediction.json", destination))
        if judgment_only:
            print(f"{'Dimension':<21} {'LLM score':>10}")
            for name in METRICS:
                score = prediction["overall_score"] if name == "overall_score" else prediction["dimension_scores"][name]
                print(f"{labels[name]:<21} {score:>10}")
            print(f"Judge rationale: {prediction['rationale'] or 'Not provided.'}")
            continue
        comparison = object_json(read_bytes(directory / "comparison.json", destination))
        print(f"Human judgment: {comparison['human_judgment_id']}")
        print(f"{'Dimension':<21} {'Human':>6} {'LLM':>6} {'LLM-human':>10} {'Abs error':>10}")
        for name in METRICS:
            score = comparison["scores"][name]
            human = "n/a" if score["human"] is None else str(score["human"])
            delta = "n/a" if score["signed_error"] is None else f"{score['signed_error']:+d}"
            error = "n/a" if score["absolute_error"] is None else str(score["absolute_error"])
            print(f"{labels[name]:<21} {human:>6} {score['predicted']:>6} {delta:>10} {error:>10}")
        print(f"Judge rationale: {prediction['rationale'] or 'Not provided.'}")
    summary = object_json(read_bytes(destination / "summary.json", destination))
    if judgment_only:
        print(f"\nJudged: {summary['cases_judged']}/{summary['cases_requested']}; failed: {summary['cases_failed']}")
        print("Human reference comparison is disabled in judge mode.")
        return
    print(f"\nCompared: {summary['cases_compared']}/{summary['cases_requested']}; failed: {summary['cases_failed']}")
    if not summary["cases_compared"]:
        print("No valid comparisons are available; judge quality cannot be assessed.")
        return
    print(f"{'Dimension':<21} {'Count':>6} {'Mean error':>11} {'MAE':>7} {'Exact agreement':>16}")
    for name in METRICS:
        metric = summary["metrics"][name]
        bias = "n/a" if metric["mean_signed_error"] is None else f"{metric['mean_signed_error']:+.2f}"
        mae = "n/a" if metric["mean_absolute_error"] is None else f"{metric['mean_absolute_error']:.2f}"
        agreement = "n/a" if metric["exact_agreement_rate"] is None else f"{metric['exact_agreement_rate']:.1%}"
        print(f"{labels[name]:<21} {metric['count']:>6} {bias:>11} {mae:>7} {agreement:>16}")
    print("Missing human dimension scores are excluded, not treated as zero.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export human-labeled judge training data, evaluate a judge blindly, or judge translations.")
    parser.add_argument("--mode", choices=["evaluate", "judge", "export-training"], default="evaluate")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--case", action="append", help="Case ID; repeat to select multiple cases.")
    selection.add_argument("--all", action="store_true", help="Select all literary-translation cases.")
    parser.add_argument("--data-dir", type=Path, default=ROOT)
    parser.add_argument("--reviewer", help="Human reference label; never sent to the model.")
    parser.add_argument("--translation-file", type=Path, help="Judge mode only: the actual translated output (.txt or .md), using --case for its source.")
    parser.add_argument("--model", help="Model identifier supported by your Chat Completions endpoint.")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY", help="Name of the environment variable containing the API key.")
    parser.add_argument("--prepare-only", action="store_true", help="Write blind requests without reading human judgments or calling a model.")
    parser.add_argument("--smoke-test", action="store_true", help="Allow incomplete case metadata; mark results as exploratory, not benchmark data.")
    parser.add_argument("--temperature", type=float, help="Optional sampling temperature; omitted by default for model compatibility.")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 300:
        parser.error("--timeout must be greater than zero and at most 300 seconds.")
    if args.temperature is not None and not 0 <= args.temperature <= 2:
        parser.error("--temperature must be between 0 and 2.")
    try:
        destination, manifest = run(args)
        print_report(destination, manifest)
        return 1 if manifest["status"] == "failed" else 0
    except (EvaluationError, OSError, UnicodeError) as exc:
        print(f"run-judge: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
