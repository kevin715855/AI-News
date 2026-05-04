from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import repo_summary_generator as rsg


class RepoSummaryGeneratorTests(unittest.TestCase):
    def test_iter_files_ignores_hidden_and_common_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / ".git").mkdir()
            (root / "node_modules").mkdir()
            (root / ".hidden").mkdir()
            (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / ".git" / "config").write_text("x", encoding="utf-8")
            (root / "node_modules" / "dep.js").write_text("x", encoding="utf-8")
            (root / ".hidden" / "file.txt").write_text("x", encoding="utf-8")

            files = sorted(str(p.relative_to(root).as_posix()) for p in rsg.iter_files(root))
            self.assertEqual(files, ["src/app.py"])

    def test_build_summary_contains_expected_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "README.md").write_text("# title\n", encoding="utf-8")
            (root / "src" / "main.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            (root / "src" / "data.bin").write_bytes(b"\x00\xff")

            with mock.patch.object(rsg, "get_git_commit_info", return_value=[]):
                summary = rsg.build_summary(root, top_n=2)

            self.assertIn("# Repository Summary", summary)
            self.assertIn("## Language / file type breakdown", summary)
            self.assertIn("| Python | 1 |", summary)
            self.assertIn("| Docs | 1 |", summary)
            self.assertIn("## Largest files (top 2)", summary)
            self.assertIn("## Recent commits", summary)
            self.assertIn("_No commit history available._", summary)

    def test_build_summary_renders_commit_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("print('x')\n", encoding="utf-8")
            fake_commits = ["abc1234|2026-05-01|Init summary generator"]
            with mock.patch.object(rsg, "get_git_commit_info", return_value=fake_commits):
                summary = rsg.build_summary(root, top_n=1)

            self.assertIn("| `abc1234` | 2026-05-01 | Init summary generator |", summary)


if __name__ == "__main__":
    unittest.main()
