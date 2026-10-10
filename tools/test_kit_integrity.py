"""Host-side regressions for kit installation and integrity checks."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from check_kits import check

ROOT = Path(__file__).resolve().parent.parent


class KitIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.game = self.home / "game"
        self.game.mkdir()
        (self.game / "default.project.json").write_text("{}")

    def install(self):
        return subprocess.run(
            [str(ROOT / "tools/add_kit.sh"), str(self.game), "leaderboard"],
            capture_output=True, text=True,
        )

    def test_symlink_and_forged_lock_cannot_escape(self):
        outside = self.home / "outside"
        outside.write_text("untouched")
        (self.game / "src").symlink_to(self.home)
        (self.game / "kits.lock.json").write_text(json.dumps({"leaderboard": {"files": {
            "src/shared/Kits/Leaderboard.luau": "forged"}}}))
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual(outside.read_text(), "untouched")

    def test_late_conflict_does_not_install_first_file(self):
        target = self.game / "tests/unit/Kit_Leaderboard.spec.luau"
        target.parent.mkdir(parents=True)
        target.write_text("mine")
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse((self.game / "src/shared/Kits/Leaderboard.luau").exists())
        self.assertFalse((self.game / "kits.lock.json").exists())

    def test_changed_deleted_and_forged_files_fail_integrity(self):
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(check(self.game), [])
        module = self.game / "src/shared/Kits/Leaderboard.luau"
        module.write_text("tampered")
        self.assertTrue(check(self.game))
        module.write_bytes((ROOT / "kits/leaderboard/src/Leaderboard.luau").read_bytes())
        spec = self.game / "tests/unit/Kit_Leaderboard.spec.luau"
        spec.unlink()
        self.assertTrue(check(self.game))
        (self.game / "kits.lock.json").write_text("{}")
        self.assertTrue(check(self.game, require_all=True))


if __name__ == "__main__":
    unittest.main()
