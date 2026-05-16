---
name: project-orientation
description: Use when working on this repository and you need the current architecture, canonical entrypoints, legacy placeholders, artifact layout, or invariants that must not be broken.
---

# Project Orientation

## Canonical shape
- Treat `digest/cli.py` + `digest/workflow.py` as the production workflow.
- Treat older scaffold-style modules under `github_trending_vi_digest/` and placeholder groups in `cli/main.py` as legacy unless the task explicitly targets them.
- Generated artifacts belong under the workflow output directory; never mutate cloned upstream repositories.

## Core flow
1. discover repos
2. clone
3. analyze README/docs
4. summarize/localize
5. validate
6. emit final reader-facing Markdown

## Invariants
- Preserve code blocks, URLs, filenames, API names, and package names when localizing.
- Keep workflow state recoverable through JSON state files.
- Prefer behavior-level changes in the canonical workflow instead of duplicating logic in legacy surfaces.
