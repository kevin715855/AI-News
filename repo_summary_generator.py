#!/usr/bin/env python3
"""
Generate a markdown summary of a repository.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "dist",
    "build",
}

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rb",
    ".rs",
    ".cs",
    ".php",
    ".html",
    ".css",
    ".scss",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".sh",
    ".sql",
    ".txt",
}


@dataclass
class FileInfo:
    path: Path
    size: int


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            yield Path(dirpath) / name


def detect_language(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".py":
        return "Python"
    if ext in {".js", ".jsx"}:
        return "JavaScript"
    if ext in {".ts", ".tsx"}:
        return "TypeScript"
    if ext == ".go":
        return "Go"
    if ext == ".java":
        return "Java"
    if ext == ".rs":
        return "Rust"
    if ext == ".cs":
        return "C#"
    if ext in {".md", ".txt"}:
        return "Docs"
    if ext in {".json", ".yaml", ".yml", ".toml", ".xml"}:
        return "Config/Data"
    return ext[1:].upper() if ext else "Unknown"


def get_git_commit_info(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "--no-pager", "log", "--pretty=format:%h|%ad|%s", "--date=short", "-n", "5"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def count_lines(path: Path) -> int | None:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return None
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return None


def build_summary(root: Path, top_n: int) -> str:
    files: list[FileInfo] = []
    language_counts: Counter[str] = Counter()
    total_lines = 0
    text_files = 0

    for file_path in iter_files(root):
        try:
            size = file_path.stat().st_size
        except OSError:
            continue

        rel_path = file_path.relative_to(root)
        files.append(FileInfo(path=rel_path, size=size))
        language_counts[detect_language(rel_path)] += 1

        line_count = count_lines(file_path)
        if line_count is not None:
            text_files += 1
            total_lines += line_count

    files.sort(key=lambda f: f.size, reverse=True)
    top_files = files[:top_n]

    commits = get_git_commit_info(root)
    lines: list[str] = []
    lines.append("# Repository Summary")
    lines.append("")
    lines.append(f"- **Root:** `{root.resolve()}`")
    lines.append(f"- **Total files:** {len(files)}")
    lines.append(f"- **Text files analyzed:** {text_files}")
    lines.append(f"- **Estimated lines of code/text:** {total_lines}")
    lines.append("")
    lines.append("## Language / file type breakdown")
    lines.append("")

    if language_counts:
        lines.append("| Type | Files |")
        lines.append("|---|---:|")
        for language, count in language_counts.most_common():
            lines.append(f"| {language} | {count} |")
    else:
        lines.append("_No files found._")

    lines.append("")
    lines.append(f"## Largest files (top {top_n})")
    lines.append("")
    if top_files:
        lines.append("| File | Size (bytes) |")
        lines.append("|---|---:|")
        for info in top_files:
            lines.append(f"| `{info.path.as_posix()}` | {info.size} |")
    else:
        lines.append("_No files found._")

    lines.append("")
    lines.append("## Recent commits")
    lines.append("")
    if commits:
        lines.append("| Commit | Date | Message |")
        lines.append("|---|---|---|")
        for row in commits:
            sha, date, message = row.split("|", 2)
            lines.append(f"| `{sha}` | {date} | {message} |")
    else:
        lines.append("_No commit history available._")

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a markdown summary for a repository.")
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the repository root (default: current directory).",
    )
    parser.add_argument(
        "--output",
        default="REPO_SUMMARY.md",
        help="Output markdown file path (default: REPO_SUMMARY.md).",
    )
    parser.add_argument(
        "--top-files",
        type=int,
        default=10,
        help="Number of largest files to include (default: 10).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        raise SystemExit(f"Repository path does not exist or is not a directory: {repo}")
    if args.top_files <= 0:
        raise SystemExit("--top-files must be greater than zero.")

    summary = build_summary(repo, args.top_files)
    output_path = Path(args.output)
    output_path.write_text(summary, encoding="utf-8")
    print(f"Summary generated: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
