"""Generate unscored candidates with a non-reasoning model and one minimal instruction."""

import argparse
import concurrent.futures
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from .prepare_translation import prepare_tasks
    from .run_judge import ROOT, EvaluationError, call_model, endpoint, guarded, identifier, object_json, read_bytes, reference, sha
    from .translation_cases import candidates, discover_cases, new_candidate_id, OPAQUE_CANDIDATE
else:
    from prepare_translation import prepare_tasks
    from run_judge import ROOT, EvaluationError, call_model, endpoint, guarded, identifier, object_json, read_bytes, reference, sha
    from translation_cases import candidates, discover_cases, new_candidate_id, OPAQUE_CANDIDATE

PROMPT = "translate the Chinese to English"
LIGHT_MODELS = {"gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o-mini"}


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def request_for(task, model):
    if model.split("/")[-1] not in LIGHT_MODELS:
        raise EvaluationError("Select an explicitly supported lightweight non-reasoning model.")
    if task["input"]["source_language"] != "zh" or task["input"]["target_language"] != "en":
        raise EvaluationError("This minimal-prompt generator expects Chinese-to-English cases.")
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": task["input"]["source_text"]},
        ],
        "temperature": 0,
        "max_tokens": 24000 if len(task["input"]["source_text"]) > 8000 else 6000,
    }


def output_text(response):
    try:
        choice = response["choices"][0]
        message = choice["message"]
        if choice.get("finish_reason") != "stop" or message.get("refusal") or message.get("tool_calls"):
            raise EvaluationError("Incomplete or refused generation; candidate was not published.")
        text = message["content"]
        if not isinstance(text, str) or not text.strip():
            raise EvaluationError("Empty generated translation.")
        details = (response.get("usage") or {}).get("completion_tokens_details") or {}
        if details.get("reasoning_tokens", 0):
            raise EvaluationError("The response reports reasoning tokens; expected a non-reasoning model.")
        return text
    except (KeyError, IndexError, TypeError) as exc:
        raise EvaluationError("Malformed translation response.") from exc


def publish(root, case_id, task, candidate_id, text, provenance):
    path = guarded(root / "cases/literary-translation" / identifier(case_id) / "case.json", root)
    lock = guarded(path.parent / ".candidate-generation.lock", root)
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    temporary = None
    try:
        os.close(descriptor)
        before = read_bytes(path, root)
        case = object_json(before)
        if case.get("schema_version") != 2:
            raise EvaluationError("Migrate the case before adding candidates.")
        current = prepare_tasks(root, [case_id], instructions=PROMPT)[0]
        if current["task_id"] != task["task_id"]:
            raise EvaluationError("Source/task changed during generation; output retained but not published.")
        existing = next((c for c in candidates(case) if c["candidate_id"] == candidate_id), None)
        raw = text.encode("utf-8")
        if existing:
            file = reference(path.parent, existing["translation_file"], path.parent)
            if (existing.get("provenance", {}).get("request_sha256") == provenance["request_sha256"]
                    and existing.get("provenance", {}).get("task_id") == task["task_id"]
                    and read_bytes(file, path.parent) == raw):
                return "unchanged"
            raise EvaluationError("Candidate ID already exists with different content or provenance.")
        metadata_path = reference(path.parent, case["source_metadata_file"], root / "fixtures/manuscripts")
        source = object_json(read_bytes(metadata_path, root / "fixtures/manuscripts"))
        rights = source.get("provenance", {})
        usage_rights = rights.get("usage_rights", "pending")
        attribution = (
            f"Chinese source: {source.get('work', {}).get('title') or case['passage_id']}; "
            f"author: {source.get('work', {}).get('author') or 'unspecified'}; "
            f"{rights.get('source_url') or 'user-provided source'}. "
            f"Synthetic English translation generated with {provenance['requested_model']}."
        )
        entry = {
            "candidate_id": candidate_id, "revision": 1,
            "translation_file": f"candidates/{candidate_id}.en.txt",
            "status": "ready" if usage_rights == "permitted" else "placeholder",
            "provenance": {
                **provenance, "task_id": task["task_id"], "source_revision": case["source_revision"],
                "source_sha256": task["identity"]["source_sha256"], "translation_sha256": sha(raw),
                "usage_rights": usage_rights, "attribution": attribution,
                **{key: rights[key] for key in ("license", "license_url") if key in rights},
            },
        }
        file = reference(path.parent, entry["translation_file"], path.parent)
        file.parent.mkdir(exist_ok=True)
        if file.exists():
            if read_bytes(file, path.parent) != raw:
                raise EvaluationError("Refusing to replace a different candidate file.")
        else:
            with file.open("xb") as handle:
                handle.write(raw)
        case["candidates"].append(entry)
        case["candidates"].sort(key=lambda item: item["candidate_id"])
        candidates(case)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded(case))
        if path.read_bytes() != before:
            raise EvaluationError("Case changed concurrently; output retained for retry.")
        os.replace(temporary, path)
        return "published"
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def generate(task, args, root, destination, url, key):
    directory = guarded(destination / task["case_id"], destination)
    directory.mkdir(exist_ok=True)
    request = request_for(task, args.model)
    request_bytes = encoded(request)
    request_path = directory / "request.json"
    if request_path.exists() and request_path.read_bytes() != request_bytes:
        raise EvaluationError("Resume request differs; use a new run directory.")
    request_path.write_bytes(request_bytes)
    id_path = directory / "candidate-id.json"
    candidate_id = args.candidate_id
    if candidate_id is None:
        if id_path.exists():
            candidate_id = object_json(read_bytes(id_path, destination))["candidate_id"]
        else:
            existing = []
            if getattr(args, "resume", None):
                case_path = root / "cases/literary-translation" / task["case_id"] / "case.json"
                existing = [
                    c["candidate_id"] for c in candidates(object_json(read_bytes(case_path, root)))
                    if c.get("provenance", {}).get("request_sha256") == sha(request_bytes)
                    and c.get("provenance", {}).get("task_id") == task["task_id"]
                    and OPAQUE_CANDIDATE.fullmatch(c["candidate_id"])
                ]
            if len(existing) > 1:
                raise EvaluationError("Multiple saved candidates match this request; select an explicit opaque ID.")
            candidate_id = existing[0] if existing else new_candidate_id()
    if not OPAQUE_CANDIDATE.fullmatch(candidate_id):
        raise EvaluationError("Candidate ID must be opaque: c- followed by 16 lowercase hex digits.")
    if id_path.exists() and object_json(read_bytes(id_path, destination))["candidate_id"] != candidate_id:
        raise EvaluationError("Resume candidate ID differs from the saved assignment.")
    id_path.write_bytes(encoded({"candidate_id": candidate_id}))
    response_path = directory / "response.json"
    if response_path.exists():
        response = object_json(read_bytes(response_path, destination))
    else:
        for attempt in range(3):
            try:
                response = call_model(request, url, key, 300)
                break
            except EvaluationError as exc:
                transient = any(marker in str(exc) for marker in ("HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504", "within the configured timeout"))
                if not transient or attempt == 2:
                    raise
                time.sleep(3 * (attempt + 1))
        response_path.write_bytes(encoded(response))
    text = output_text(response)
    returned_model = response.get("model")
    if returned_model and args.model.split("/")[-1] not in returned_model:
        raise EvaluationError("Returned model does not match the requested non-reasoning model.")
    (directory / "translation.en.txt").write_bytes(text.encode("utf-8"))
    provenance = {
        "translation_origin": "synthetic model translation",
        "purpose": "minimal-prompt adverse-candidate pool",
        "quality_status": "unreviewed; degradation is not assumed",
        "requested_model": args.model, "returned_model": returned_model,
        "non_reasoning_model": True, "instruction": PROMPT,
        "generation_settings": {k: request[k] for k in ("temperature", "max_tokens")},
        "request_sha256": sha(request_bytes), "response_id": response.get("id"),
        "generated_at": datetime.fromtimestamp(
            response.get("created") or response_path.stat().st_mtime, timezone.utc,
        ).isoformat(),
        "usage": response.get("usage"),
        "generation_artifacts": directory.relative_to(root).as_posix(),
    }
    published = {cid: publish(root, cid, task, candidate_id, text, provenance) for cid in task["case_ids"]}
    result = {"case_id": task["case_id"], "case_ids": task["case_ids"], "task_id": task["task_id"],
              "candidate_id": candidate_id, "status": "completed", "published": published, "usage": response.get("usage"),
              "response_model": returned_model, "english_words": len(text.split()),
              "translation_sha256": sha(text.encode("utf-8"))}
    (directory / "result.json").write_bytes(encoded(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--all", action="store_true")
    selection.add_argument("--contemporary", action="store_true", help="Only the contemporary corpus cases.")
    selection.add_argument("--case", action="append")
    parser.add_argument("--model", default="azure/openai/gpt-4.1-mini")
    parser.add_argument("--candidate-id", help="Optional opaque ID (c- plus 16 hex digits); normally assigned independently per task.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args()
    if args.candidate_id is not None and not OPAQUE_CANDIDATE.fullmatch(args.candidate_id):
        parser.error("--candidate-id must be c- followed by 16 lowercase hex digits.")
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    root = args.data_dir.resolve()
    pattern = "zh-en-contemporary-*" if args.contemporary else "*"
    ids = args.case or [p.parent.name for p in discover_cases(root / "cases/literary-translation", pattern)]
    tasks = prepare_tasks(root, ids, instructions=PROMPT)
    for task in tasks:
        request_for(task, args.model)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        parser.error("OPENAI_API_KEY is not configured.")
    url = endpoint(os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    results = guarded(root / "results", root)
    results.mkdir(exist_ok=True)
    destination = guarded(args.resume.resolve(), results) if args.resume else Path(tempfile.mkdtemp(prefix="synthetic-translations-", dir=results))
    if not destination.is_dir():
        parser.error("Resume directory must exist.")
    manifest = {"model": args.model, "instruction": PROMPT, "candidate_id": args.candidate_id,
                "started_at": now(), "tasks": len(tasks), "results": [], "status": "running"}
    (destination / "run.json").write_bytes(encoded(manifest))
    print(f"Run: {destination}", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(generate, task, args, root, destination, url, key): task for task in tasks}
        for future in concurrent.futures.as_completed(pending):
            task = pending[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {"case_id": task["case_id"], "status": "failed", "error": str(exc)}
            manifest["results"].append(record)
            (destination / "run.json").write_bytes(encoded(manifest))
            print(f"{len(manifest['results'])}/{len(tasks)} {record['case_id']}: {record['status']}", flush=True)
    manifest["status"] = "completed" if all(r["status"] == "completed" for r in manifest["results"]) else "failed"
    manifest["finished_at"] = now()
    (destination / "run.json").write_bytes(encoded(manifest))
    print(f"{manifest['status']}: {destination}", flush=True)
    return 0 if manifest["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
