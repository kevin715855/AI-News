---
name: release-qa
description: Use before calling repository work complete, preparing a release, or verifying daily-use readiness for the digest workflow.
---

# Release QA

## Required verification
- Run the full automated test suite.
- Smoke-test one GitHub Trending run and one manual GitHub URL run.
- Exercise LM Studio failure paths: unavailable endpoint, timeout, malformed response.
- Inspect the final Markdown artifact, not only intermediate files.

## Acceptance bar
- CLI commands are understandable and recover cleanly from common failures.
- Reader-facing Markdown is immediately usable.
- No regression in validator behavior.
- A change is not "done" until it could plausibly survive seven days of daily use without a blocking defect.
