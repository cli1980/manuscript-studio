import contextlib
import io
import json
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import install_skills as installer


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.destination = self.root / "destination with spaces"
        self.make_skill("alpha")
        self.make_skill("beta")

    def make_skill(self, name):
        root = self.source / name
        root.mkdir(parents=True)
        (root / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Test workflow\n---\n", encoding="utf-8"
        )
        for relative, data in {
            "references/guide.md": b"Reference\n",
            "scripts/helper.py": b"print('helper')\n",
            "assets/template.bin": bytes(range(256)),
            "agents/openai.yaml": b"interface: {}\n",
        }.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return root

    def install(self, names=(), **kwargs):
        return installer.install_skills(
            self.destination, names, source_root=self.source, **kwargs
        )

    def test_default_installs_all_resources_and_records_hashes(self):
        self.install()
        for name in ("alpha", "beta"):
            installed = self.destination / name
            self.assertEqual(installer.inventory(self.source / name), installer.inventory(installed))
            state = json.loads((installed / installer.STATE_FILE).read_text(encoding="utf-8"))
            self.assertEqual(state["skill"], name)
            self.assertEqual(state["files"], installer.inventory(installed))

    def test_selection_deduplicates_and_does_not_install_unselected_skills(self):
        self.install(["beta", "beta"])
        self.assertTrue((self.destination / "beta/SKILL.md").is_file())
        self.assertFalse((self.destination / "alpha").exists())

    def test_review_dependency_is_installed_with_query_skill(self):
        self.make_skill("literary-agent-querying")
        self.make_skill("prepare-manuscript")
        self.make_skill("review-approval-sheet")
        self.install(["literary-agent-querying"])
        self.assertTrue((self.destination / "review-approval-sheet/SKILL.md").is_file())
        self.assertTrue((self.destination / "prepare-manuscript/SKILL.md").is_file())
        self.assertFalse((self.destination / "alpha").exists())

    def test_missing_dependency_fails_without_writing(self):
        self.make_skill("literary-editing")
        self.make_skill("prepare-manuscript")
        with self.assertRaisesRegex(ValueError, "review-approval-sheet"):
            self.install(["literary-editing"])
        self.assertFalse(self.destination.exists())

    def test_missing_preparation_dependency_fails_without_writing(self):
        self.make_skill("literary-translation")
        self.make_skill("review-approval-sheet")
        with self.assertRaisesRegex(ValueError, "prepare-manuscript"):
            self.install(["literary-translation"])
        self.assertFalse(self.destination.exists())

    def test_dry_run_does_not_create_destination(self):
        messages = self.install(dry_run=True)
        self.assertTrue(any("alpha" in message for message in messages))
        self.assertFalse(self.destination.exists())

    def test_unknown_or_traversal_names_fail_without_writing(self):
        for name in ("missing", "../alpha", str(self.source / "alpha")):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.install([name])
        self.assertFalse(self.destination.exists())

    def test_repeated_install_is_noop(self):
        self.install()
        state = self.destination / "alpha" / installer.STATE_FILE
        before = state.stat().st_mtime_ns
        messages = self.install()
        self.assertTrue(all("Unchanged" in message for message in messages))
        self.assertEqual(before, state.stat().st_mtime_ns)
        self.assertFalse((self.destination.parent / installer.BACKUP_DIR).exists())

    def test_unmanaged_collision_preflights_entire_selection(self):
        target = self.destination / "beta"
        target.mkdir(parents=True)
        (target / "personal.md").write_text("keep", encoding="utf-8")
        for update in (False, True):
            with self.assertRaisesRegex(ValueError, "unmanaged"):
                self.install(update=update)
        self.assertFalse((self.destination / "alpha").exists())
        self.assertEqual((target / "personal.md").read_text(), "keep")

    def test_update_requires_explicit_flag(self):
        self.install()
        (self.source / "alpha/SKILL.md").write_text("new instructions", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "--update"):
            self.install()
        self.assertNotEqual((self.destination / "alpha/SKILL.md").read_text(), "new instructions")

    def test_update_replaces_clean_install_and_preserves_backup(self):
        self.install()
        old = installer.inventory(self.destination / "alpha")
        (self.source / "alpha/SKILL.md").write_text("new instructions", encoding="utf-8")
        (self.source / "alpha/references/guide.md").unlink()
        self.install(update=True)
        self.assertEqual(installer.inventory(self.source / "alpha"), installer.inventory(self.destination / "alpha"))
        backups = list((self.destination.parent / installer.BACKUP_DIR).iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual(old, installer.inventory(backups[0]))
        self.assertFalse((self.destination / "alpha/references/guide.md").exists())

    def test_update_dry_run_preserves_everything(self):
        self.install()
        before = installer.inventory(self.destination / "alpha")
        (self.source / "alpha/SKILL.md").write_text("new instructions", encoding="utf-8")
        self.install(update=True, dry_run=True)
        self.assertEqual(before, installer.inventory(self.destination / "alpha"))
        self.assertFalse((self.destination.parent / installer.BACKUP_DIR).exists())

    def test_locally_edited_added_or_deleted_files_block_updates(self):
        self.install()
        target = self.destination / "alpha/SKILL.md"
        original = target.read_bytes()
        for change in ("edit", "delete", "add", "directory"):
            with self.subTest(change=change):
                if change == "edit":
                    target.write_text("personal edits", encoding="utf-8")
                elif change == "delete":
                    target.unlink()
                elif change == "add":
                    (self.destination / "alpha/personal.txt").write_text("keep", encoding="utf-8")
                else:
                    (self.destination / "alpha/empty-personal-folder").mkdir()
                with self.assertRaisesRegex(ValueError, "locally modified"):
                    self.install(update=True)
                target.write_bytes(original)
                if change == "add":
                    (self.destination / "alpha/personal.txt").unlink()
                if change == "directory":
                    (self.destination / "alpha/empty-personal-folder").rmdir()

    def test_invalid_state_is_not_adopted(self):
        self.install()
        state = self.destination / "alpha" / installer.STATE_FILE
        for content in ("not JSON", "[]", '{"project": "other"}'):
            with self.subTest(content=content):
                state.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.install(update=True)

    def test_python_caches_are_not_installed_or_treated_as_local_edits(self):
        cache = self.source / "alpha/__pycache__"
        cache.mkdir()
        (cache / "helper.pyc").write_bytes(b"cache")
        self.install()
        self.assertFalse((self.destination / "alpha/__pycache__").exists())
        cache = self.destination / "alpha/__pycache__"
        cache.mkdir()
        (cache / "helper.pyc").write_bytes(b"cache")
        self.install(update=True)

    def test_overlapping_destination_is_rejected(self):
        for destination in (self.source, self.source / "alpha/installed", self.root):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                installer.install_skills(destination, source_root=self.source)

    def test_reserved_source_state_is_rejected(self):
        (self.source / "alpha" / installer.STATE_FILE).write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse(self.destination.exists())

    def test_copy_failure_leaves_existing_install_intact(self):
        self.install()
        before = installer.inventory(self.destination / "alpha")
        (self.source / "alpha/SKILL.md").write_text("new", encoding="utf-8")
        with patch.object(installer.shutil, "copytree", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.install(update=True)
        self.assertEqual(before, installer.inventory(self.destination / "alpha"))
        self.assertFalse((self.destination / installer.LOCK_FILE).exists())

    def test_failed_replacement_restores_original(self):
        self.install()
        before = installer.inventory(self.destination / "alpha")
        (self.source / "alpha/SKILL.md").write_text("new", encoding="utf-8")
        rename = Path.rename

        def fail_publish(path, target):
            if path.name == "payload":
                raise OSError("publish failed")
            return rename(path, target)

        with patch.object(Path, "rename", fail_publish):
            with self.assertRaises(OSError):
                self.install(update=True)
        self.assertEqual(before, installer.inventory(self.destination / "alpha"))

    def test_existing_lock_blocks_install(self):
        self.destination.mkdir()
        lock = self.destination / installer.LOCK_FILE
        lock.write_text("another process", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "lock"):
            self.install()
        self.assertEqual(lock.read_text(), "another process")
        self.assertFalse((self.destination / "alpha").exists())

    def test_link_and_windows_reparse_detection_without_privileges(self):
        for mode, attributes in ((stat.S_IFLNK, 0), (stat.S_IFDIR, 0x400)):
            with self.subTest(mode=mode, attributes=attributes):
                info = SimpleNamespace(st_mode=mode, st_file_attributes=attributes)
                with patch.object(Path, "lstat", return_value=info):
                    with patch.object(installer.stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400, create=True):
                        with self.assertRaisesRegex(ValueError, "link|reparse"):
                            installer.assert_plain_path(self.destination)

    def test_source_change_during_copy_is_rejected(self):
        copytree = installer.shutil.copytree

        def changed_copy(source, target, *args, **kwargs):
            result = copytree(source, target, *args, **kwargs)
            if Path(source) == self.source / "alpha":
                (Path(target) / "SKILL.md").write_text("changed during copy", encoding="utf-8")
            return result

        with patch.object(installer.shutil, "copytree", side_effect=changed_copy):
            with self.assertRaisesRegex(ValueError, "Source changed"):
                self.install(["alpha"])
        self.assertFalse((self.destination / "alpha").exists())

    def make_link(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")

    def test_source_symlink_is_rejected(self):
        outside = self.root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        self.make_link(self.source / "alpha/linked.txt", outside)
        with self.assertRaisesRegex(ValueError, "link|reparse"):
            self.install()
        self.assertFalse(self.destination.exists())

    def test_destination_symlink_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.make_link(self.destination, outside)
        with self.assertRaisesRegex(ValueError, "link|reparse"):
            self.install()
        self.assertEqual(list(outside.iterdir()), [])

    def test_broken_skill_symlink_is_not_overwritten(self):
        self.destination.mkdir()
        self.make_link(self.destination / "alpha", self.root / "missing")
        with self.assertRaisesRegex(ValueError, "link|reparse"):
            self.install()
        self.assertTrue((self.destination / "alpha").is_symlink())

    def test_default_destination_and_list(self):
        with patch.object(installer.Path, "home", return_value=self.root):
            with patch.object(installer, "install_skills", return_value=[]) as install:
                self.assertEqual(installer.main([]), 0)
                self.assertEqual(install.call_args.args[0], self.root / ".agents/skills")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(installer.main(["--list"]), 0)
        self.assertIn("literary-editing", output.getvalue())

    def test_cli_works_outside_repository_without_writes(self):
        result = subprocess.run(
            [sys.executable, "-B", str(Path(installer.__file__).resolve()),
             "--dest", str(self.destination), "--dry-run", "literary-agent-querying"],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("review-approval-sheet", result.stdout)
        self.assertFalse(self.destination.exists())


class RepositoryTests(unittest.TestCase):
    def test_installed_suite_preserves_resources_and_relative_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "skills"
            installer.install_skills(destination)
            available = installer.available_skills(installer.SKILLS_ROOT)
            self.assertEqual(set(available), {
                "literary-editing", "literary-translation", "literary-agent-querying",
                "format-manuscript", "review-approval-sheet", "prepare-manuscript",
            })
            self.assertEqual({path.name for path in destination.iterdir()}, set(available))
            for name, source in available.items():
                self.assertEqual(installer.inventory(source), installer.inventory(destination / name))
            for document in destination.rglob("*.md"):
                for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                    if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", link) or link.startswith("#"):
                        continue
                    target = document.parent / link.split("#", 1)[0]
                    self.assertTrue(target.exists(), f"Broken link in {document}: {link}")
            self.assertTrue((destination / "literary-agent-querying/scripts/sample_boundary.py").is_file())
            self.assertTrue((destination / "literary-agent-querying/scripts/validate_on_demand.py").is_file())

    def test_plugin_uses_the_same_canonical_directory(self):
        root = installer.SKILLS_ROOT.parent
        manifest = json.loads((root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual((root / manifest["skills"]).resolve(), installer.SKILLS_ROOT)

    def test_no_duplicate_top_level_skills_remain(self):
        for name in installer.available_skills(installer.SKILLS_ROOT):
            self.assertFalse((installer.REPO_ROOT / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
