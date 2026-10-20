import hashlib
import json
import os
import re
import stat
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import JudgmentCreate

SKILLS = {
    "prepare-manuscript": "Prepare manuscript",
    "literary-editing": "Literary editing",
    "literary-translation": "Literary translation",
    "literary-agent-querying": "Literary agent querying",
    "format-manuscript": "Format manuscript",
    "review-approval-sheet": "Review approval sheet",
}
DIMENSIONS = {"fidelity", "english_naturalness", "literary_voice"}
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MAX_FILE = 4 * 1024 * 1024


class DataError(Exception):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def plain_path(path):
    for component in (*reversed(path.parents), path):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise DataError("Links and filesystem reparse points are not allowed.")
        if stat.S_ISREG(info.st_mode) and info.st_nlink > 1:
            raise DataError("Files with multiple hard links are not allowed.")


def identifier(value):
    if not isinstance(value, str) or len(value) > 100 or not ID.fullmatch(value):
        raise DataError("Invalid identifier.")
    return value


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


class Repository:
    def __init__(self, root):
        root = Path(os.path.abspath(root))
        plain_path(root)
        if not root.is_dir():
            raise DataError("The evaluation data directory must already exist.")
        self.root = root.resolve()
        self.cases = self.root / "cases"
        self.passages = self.root / "fixtures/manuscripts"
        self.rubrics = self.root / "rubrics"
        for directory in (self.cases, self.passages, self.rubrics):
            plain_path(directory)
            if not directory.is_dir():
                raise DataError("Required evaluation data directories are missing.")
        self.lock = threading.RLock()

    def guarded(self, path, area):
        path = Path(os.path.abspath(path))
        if not path.is_relative_to(area):
            raise DataError("File reference is outside its permitted data area.")
        plain_path(path)
        if not path.resolve().is_relative_to(area):
            raise DataError("File reference escapes its permitted data area.")
        return path

    def read(self, path, area):
        path = self.guarded(path, area)
        if not path.is_file():
            raise DataError("A referenced data file is missing.", 404)
        if path.stat().st_size > MAX_FILE:
            raise DataError("A data file exceeds the supported size limit.")
        with path.open("rb") as handle:
            result = handle.read(MAX_FILE + 1)
        if len(result) > MAX_FILE:
            raise DataError("A data file exceeds the supported size limit.")
        return result

    def json(self, path, area):
        try:
            value = json.loads(self.read(path, area).decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise DataError("A data file contains invalid JSON or UTF-8.") from exc
        if not isinstance(value, dict):
            raise DataError("Metadata must be a JSON object.")
        return value

    def text(self, path, area):
        try:
            return self.read(path, area).decode("utf-8")
        except UnicodeError as exc:
            raise DataError("Passages must use UTF-8 text.") from exc

    def reference(self, parent, name, area):
        if not isinstance(name, str) or not name or "\\" in name or ":" in name:
            raise DataError("Invalid stored file reference.")
        if Path(name).is_absolute():
            raise DataError("Absolute file references are not allowed.")
        return self.guarded(parent / name, area)

    def metadata_files(self, directory, filename, depth=0, budget=None):
        directory = self.guarded(directory, self.root)
        if not directory.is_dir():
            return
        if depth > 5:
            raise DataError("Data directories exceed the supported nesting depth.")
        budget = [0] if budget is None else budget
        for child in sorted(directory.iterdir()):
            budget[0] += 1
            if budget[0] > 10000:
                raise DataError("The evaluation workspace contains too many entries.")
            if child.name.startswith("."):
                continue
            self.guarded(child, directory)
            if child.name == filename and child.is_file():
                yield child
            elif child.is_dir():
                identifier(child.name)
                yield from self.metadata_files(child, filename, depth + 1, budget)

    def passage_at(self, metadata_path):
        metadata = self.json(metadata_path, self.passages)
        for key in ("passage_id", "group_id"):
            identifier(metadata.get(key))
        if type(metadata.get("revision")) is not int or metadata["revision"] < 1:
            raise DataError("Invalid source revision.")
        source_path = self.reference(metadata_path.parent, metadata.get("source_file"), metadata_path.parent)
        if source_path.suffix != ".txt":
            raise DataError("A source passage must reference a text file.")
        text = self.text(source_path, self.passages)
        return {"metadata": metadata, "text": text}, source_path

    def list_passages(self):
        found = []
        seen = set()
        for path in self.metadata_files(self.passages, "passage.json"):
            passage, _ = self.passage_at(path)
            key = (passage["metadata"]["passage_id"], passage["metadata"]["revision"])
            if key in seen:
                raise DataError("Duplicate passage identifier and revision.")
            seen.add(key)
            found.append(passage["metadata"])
        return found

    def find_passage(self, passage_id, revision):
        identifier(passage_id)
        matches = []
        for path in self.metadata_files(self.passages, "passage.json"):
            metadata = self.json(path, self.passages)
            if metadata.get("passage_id") == passage_id and metadata.get("revision") == revision:
                matches.append(path)
        if not matches:
            raise DataError("Passage not found.", 404)
        if len(matches) != 1:
            raise DataError("Duplicate passage identifier and revision.")
        return matches[0]

    def get_passage(self, passage_id, revision=1):
        return self.passage_at(self.find_passage(passage_id, revision))[0]

    def rubric_list(self):
        result = []
        for path in sorted(self.rubrics.iterdir()):
            if path.suffix != ".json" or path.name.startswith("."):
                continue
            rubric = self.json(path, self.rubrics)
            identifier(rubric.get("rubric_id"))
            if (
                rubric.get("scale", {}).get("min") != 1
                or rubric.get("scale", {}).get("max") != 5
                or set(rubric.get("dimensions", {})) != DIMENSIONS
            ):
                raise DataError("Unsupported translation rubric definition.")
            if any(r["rubric_id"] == rubric["rubric_id"] for r in result):
                raise DataError("Duplicate rubric identifier.")
            result.append(rubric)
        return result

    def case_path(self, case_id):
        identifier(case_id)
        matches = []
        for skill in SKILLS:
            path = self.guarded(self.cases / skill / case_id / "case.json", self.cases)
            if path.is_file():
                matches.append((skill, path))
        if not matches:
            raise DataError("Case not found.", 404)
        if len(matches) != 1:
            raise DataError("Duplicate case identifier.")
        return matches[0]

    def assigned_rubric(self, metadata):
        candidates = [
            rubric for rubric in self.rubric_list()
            if rubric.get("source_language") == metadata["source_language"]
            and rubric.get("target_language") == metadata["target_language"]
            and (not metadata.get("rubric_id") or rubric["rubric_id"] == metadata["rubric_id"])
        ]
        return candidates[0] if len(candidates) == 1 else None

    def get_case(self, case_id):
        skill, path = self.case_path(case_id)
        if skill != "literary-translation":
            raise DataError("This skill does not yet have a case editor.", 409)
        metadata = self.json(path, self.cases)
        if metadata.get("case_id") != case_id or type(metadata.get("revision")) is not int:
            raise DataError("Invalid case identity or revision.")
        source_meta = self.reference(path.parent, metadata.get("source_metadata_file"), self.passages)
        if source_meta.name != "passage.json":
            raise DataError("A case must reference passage metadata.")
        passage, source_path = self.passage_at(source_meta)
        source = passage["metadata"]
        if any(metadata.get(key) != source.get(key) for key in ("passage_id", "group_id", "source_language")):
            raise DataError("Case and source identities do not match.")
        if metadata.get("source_revision") != source["revision"]:
            raise DataError("Case and source revisions do not match.")
        if self.reference(path.parent, metadata.get("source_file"), self.passages) != source_path:
            raise DataError("Case and passage source references disagree.")
        translation_path = self.reference(path.parent, metadata.get("translation_file"), path.parent)
        if translation_path.name != "translation.en.txt" and translation_path.name != "translation.txt":
            raise DataError("Unsupported translation filename.")
        translation = self.text(translation_path, self.cases)
        judgments_path = self.guarded(path.parent / "judgments.jsonl", self.cases)
        raw_judgments = self.read(judgments_path, self.cases) if judgments_path.exists() else b""
        try:
            judgments = [json.loads(line) for line in raw_judgments.decode("utf-8").splitlines() if line.strip()]
        except (ValueError, UnicodeError) as exc:
            raise DataError("Invalid judgment records.") from exc
        ids = set()
        for judgment in judgments:
            if not isinstance(judgment, dict) or judgment.get("case_id") != case_id:
                raise DataError("Judgment identity does not match the case.")
            jid = identifier(judgment.get("judgment_id"))
            if jid in ids:
                raise DataError("Duplicate judgment identifier.")
            ids.add(jid)
        rubric = self.assigned_rubric(metadata)
        digest = hashlib.sha256()
        for content in (
            encoded(metadata), encoded(source),
            passage["text"].encode("utf-8"), translation.encode("utf-8"),
            raw_judgments, encoded(rubric),
        ):
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
        return {
            "skill": skill, "metadata": metadata, "source": passage,
            "translation": translation, "judgments": judgments, "rubric": rubric, "version": digest.hexdigest(),
        }

    def list_cases(self, skill):
        if skill not in SKILLS:
            raise DataError("Unknown skill.", 404)
        directory = self.guarded(self.cases / skill, self.cases)
        if not directory.exists():
            return []
        result = []
        for path in sorted(directory.iterdir()):
            if path.name.startswith("."):
                continue
            self.guarded(path, directory)
            if not path.is_dir():
                continue
            identifier(path.name)
            metadata = self.json(path / "case.json", directory)
            if metadata.get("case_id") != path.name:
                raise DataError("Case directory and identifier do not match.")
            result.append(metadata)
        return result

    def atomic(self, path, content, area):
        path = self.guarded(path, area)
        if (
            area != self.cases or path.name != "judgments.jsonl"
            or path.parent.parent != self.cases / "literary-translation"
            or not self.guarded(path.parent / "case.json", self.cases).is_file()
        ):
            raise DataError("Only judgments for existing translation cases may be written.")
        if len(content) > MAX_FILE:
            raise DataError("Saved data would exceed the supported size limit.")
        descriptor, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            self.guarded(path, area)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def current(self, case_id, version):
        case = self.get_case(case_id)
        if case["version"] != version:
            raise DataError("This case changed since you opened it. Reload before saving.", 409)
        return case

    def add_judgment(self, case_id, data: JudgmentCreate, *, rater_id: str):
        with self.lock:
            case = self.current(case_id, data.version)
            metadata = case["metadata"]
            rubric_id = case["rubric"]["rubric_id"] if case["rubric"] else None
            if data.status == "complete" and (
                not rubric_id or data.overall_score is None
            ):
                raise DataError("A completed assessment needs a configured rubric and an overall score.")
            supersedes = data.supersedes_judgment_id
            if not supersedes:
                superseded = {j.get("supersedes_judgment_id") for j in case["judgments"]}
                latest = next((j for j in reversed(case["judgments"]) if
                    j["judgment_id"] not in superseded and j.get("rater_id") == rater_id
                    and j.get("case_revision") == metadata["revision"]
                    and j.get("source_revision") == metadata["source_revision"]
                    and j.get("rubric_version") == rubric_id), None)
                supersedes = latest["judgment_id"] if latest else None
            if supersedes:
                previous = next((j for j in case["judgments"] if j["judgment_id"] == supersedes), None)
                if not previous or any(j.get("supersedes_judgment_id") == supersedes for j in case["judgments"]):
                    raise DataError("Select an assessment that has not already been amended.", 409)
                if previous.get("rater_id") != rater_id and not (
                    previous.get("rater_id") is None and previous.get("status") == "pending"
                ):
                    raise DataError("This assessment belongs to another reviewer. Start an independent assessment.", 403)
                if previous.get("case_revision") != metadata["revision"] or previous.get("source_revision") != metadata["source_revision"]:
                    raise DataError("Start a new assessment for the current text revision.", 409)
                if previous.get("rubric_version") and previous["rubric_version"] != rubric_id:
                    raise DataError("Start a new assessment for the configured rubric.", 409)
                if (
                    previous.get("rater_id") == rater_id
                    and previous.get("rubric_version") == rubric_id
                    and previous.get("status") == data.status
                    and previous.get("overall_score") == data.overall_score
                    and {key: (previous.get("dimension_scores") or {}).get(key) for key in DIMENSIONS}
                    == data.dimension_scores.model_dump()
                    and (previous.get("rationale") or None) == (data.rationale or None)
                    and (previous.get("issues") or []) == [issue.model_dump() for issue in data.issues]
                ):
                    return case
            judgment = data.model_dump(exclude={"version"})
            judgment.update({
                "supersedes_judgment_id": supersedes,
                "judgment_id": "judgment-" + uuid.uuid4().hex,
                "case_id": case_id, "case_revision": metadata["revision"],
                "passage_id": metadata["passage_id"], "source_revision": metadata["source_revision"],
                "rubric_version": rubric_id,
                "rater_id": rater_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            content = "".join(json.dumps(j, ensure_ascii=False) + "\n" for j in [*case["judgments"], judgment]).encode("utf-8")
            self.current(case_id, data.version)
            self.atomic(self.case_path(case_id)[1].parent / "judgments.jsonl", content, self.cases)
            return self.get_case(case_id)
