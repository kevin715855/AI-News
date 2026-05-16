# github-trending-vi-digest

Local-first Python tooling for turning GitHub Trending repositories into
Vietnamese digest artifacts. The project fetches trending repositories, crawls
local repository content, extracts README/docs, generates summaries, localizes
README content, validates Markdown and Vietnamese quality, and exports results
as Markdown or JSON.

The production workflow now also supports one-off GitHub repository URLs and
can call a local LM Studio model through its OpenAI-compatible API to generate
reader-facing Vietnamese digests.

## Current Scope

- Fetch GitHub Trending repositories and cache/list the results.
- Crawl and inspect local repository files.
- Extract README and documentation sections.
- Generate repository summary data.
- Translate/localize README-style Markdown while preserving code, links, and
  technical terms.
- Validate localized Markdown output with structural and Vietnamese-language
  rules.
- Export repository summary payloads to Markdown and JSON.
- Run an integrated digest workflow CLI over the composed pieces.

## Project Layout

```text
src/
  cli/                         CLI command groups
  digest/                      End-to-end workflow orchestration
  document_extractor/          Document extraction helpers
  exporter/                    Markdown and JSON exporters
  github_trending_vi_digest/   Core package skeleton and models
  validator/                   QA validation framework and rules
tests/
  cli/                         CLI unit tests
  exporter/                    Exporter tests
  integration/                 End-to-end workflow tests
  fixtures/                    Sample repositories and README fixtures
```

## Quick Start

```bash
python -m pip install -e .
python -m pytest
```

Run CLI help:

```bash
python -m cli.main --help
```

Examples:

```bash
github-trending-vi-digest --model qwen2.5-coder run
github-trending-vi-digest --model qwen2.5-coder repo https://github.com/owner/repo
python -m validator.cli validate-localized localized/README.vi.md
```

## Validation

The merged workspace currently passes the full local test suite:

```text
134 passed
```

## Notes

Generated files should be written under `data/`, `outputs/`, or `localized/`.
Do not modify cloned upstream repositories directly. Preserve code blocks,
commands, links, filenames, API names, and package names when localizing
README/docs content.
