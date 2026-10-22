import hashlib
import json
import tempfile
from pathlib import Path

from .repository import DataError, Repository, SKILLS
from ..translation_cases import candidates

MAX_WORKSPACE = 16 * 1024 * 1024


def snapshot(repository):
    files = {}
    total = 0

    def include(path, area):
        nonlocal total
        content = repository.read(path, area)
        relative = path.relative_to(repository.root).as_posix()
        if relative not in files:
            total += len(content)
        if total > MAX_WORKSPACE or len(files) >= 5000:
            raise DataError("The review workspace exceeds its size limit.")
        files[relative] = content

    for path in repository.metadata_files(repository.passages, "passage.json"):
        _, source = repository.passage_at(path)
        include(path, repository.passages)
        include(source, repository.passages)
    repository.list_passages()
    for skill in SKILLS:
        for case in repository.list_cases(skill):
            path = repository.cases / skill / case["case_id"] / "case.json"
            include(path, repository.cases)
            if skill == "literary-translation":
                repository.get_case(case["case_id"])
                for candidate in candidates(case):
                    translation = repository.reference(path.parent, candidate["translation_file"], path.parent)
                    include(translation, repository.cases)
                judgments = repository.guarded(path.parent / "judgments.jsonl", repository.cases)
                if judgments.exists():
                    include(judgments, repository.cases)
    repository.rubric_list()
    for path in repository.rubrics.iterdir():
        if path.suffix == ".json" and not path.name.startswith("."):
            include(path, repository.rubrics)
    return files


def version_of(files):
    digest = hashlib.sha256()
    for name, content in sorted(files.items()):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


class Workspace:
    def __init__(self, root):
        self.source = Repository(root)
        self.baseline = snapshot(self.source)
        self.writable = {
            (Path(name).parent / "judgments.jsonl").as_posix()
            for name in self.baseline
            if name.startswith("cases/literary-translation/")
            and len(Path(name).parts) == 4 and Path(name).name == "case.json"
        }
        self.temporary = tempfile.TemporaryDirectory(prefix="manuscript-evals-")
        try:
            temporary_root = Path(self.temporary.name).resolve()
            for directory in ("fixtures/manuscripts", "rubrics", *(f"cases/{skill}" for skill in SKILLS)):
                (temporary_root / directory).mkdir(parents=True, exist_ok=True)
            for name, content in self.baseline.items():
                path = temporary_root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            self.repository = Repository(temporary_root)
            self.lock = self.repository.lock
        except BaseException:
            self.temporary.cleanup()
            raise

    def close(self):
        self.temporary.cleanup()

    def changes(self, current):
        if set(self.baseline) - set(current):
            raise DataError("Deleting source records through the workspace is not supported.")
        changed = {name: content for name, content in current.items() if self.baseline.get(name) != content}
        for name in changed:
            if name not in self.writable:
                raise DataError("Only human judgments for existing cases may be submitted; all other data is read-only.")
            previous = [json.loads(line) for line in self.baseline.get(name, b"").splitlines() if line.strip()]
            updated = [json.loads(line) for line in current[name].splitlines() if line.strip()]
            if updated[:len(previous)] != previous:
                raise DataError("Earlier judgments must be preserved. Save an amendment instead.")
        return changed

    def status(self):
        with self.lock:
            current = snapshot(self.repository)
            changed = self.changes(current)
            return self.describe(current, changed)

    def describe(self, current, changed):
        cases = set()
        for name in changed:
            path = Path(name)
            if name.startswith("cases/"):
                cases.add(json.loads(current[(path.parent / "case.json").as_posix()])["case_id"])
        return {
            "version": version_of(current),
            "pending_files": len(changed),
            "cases": sorted(cases),
        }

    def assert_originals_unchanged(self):
        try:
            matches = snapshot(self.source) == self.baseline
        except (DataError, OSError) as exc:
            raise DataError("Original data is no longer safely readable. Draft changes were kept.", 409) from exc
        if not matches:
            raise DataError("Original data changed outside this workspace. Draft changes were kept; reconcile the source before submitting.", 409)

    def submit(self, expected_version):
        with self.lock:
            current = snapshot(self.repository)
            if version_of(current) != expected_version:
                raise DataError("The temporary workspace changed. Review the latest pending changes before submitting.", 409)
            changed = self.changes(current)
            if not changed:
                return self.describe(current, changed)
            self.assert_originals_unchanged()
            published = []
            try:
                for name, content in sorted(changed.items()):
                    path = self.source.guarded(self.source.root / name, self.source.cases)
                    old = self.source.read(path, self.source.cases) if path.exists() else None
                    if old != self.baseline.get(name):
                        raise DataError("An original record changed during submission. Draft changes were kept.", 409)
                    self.source.atomic(path, content, self.source.cases)
                    published.append((name, content))
                if snapshot(self.source) != current:
                    raise DataError("Original data changed during submission. Draft changes were kept.", 409)
            except BaseException:
                self.rollback(published)
                raise
            self.baseline = current
            return self.describe(current, {})

    def rollback(self, published):
        try:
            for name, content in reversed(published):
                path = self.source.guarded(self.source.root / name, self.source.cases)
                if self.source.read(path, self.source.cases) != content:
                    raise DataError("An original record changed during rollback.")
                if name in self.baseline:
                    self.source.atomic(path, self.baseline[name], self.source.cases)
                else:
                    path.unlink()
        except (OSError, DataError) as exc:
            raise DataError("Submission failed and rollback could not finish. Stop further submissions and inspect the originals; draft changes remain available.", 500) from exc
