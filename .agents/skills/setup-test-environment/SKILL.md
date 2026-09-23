---
name: setup-test-environment
description: Build, resume, or verify this repository's approved DynamoDB Local test environment. Use only when explicitly invoked for the test-environment setup or Environment Gate; do not use for feature TDD or ordinary test execution.
---

# Set Up the Test Environment

Build or verify the repository's DynamoDB Local test environment without starting feature TDD.

## Source of truth

Read these files before changing anything:

- `CLAUDE.md`
- `docs/todo/test-environment-rollout.md`

Treat the rollout document as authoritative for Java and Maven versions, Maven coordinates, wrapper checksum, safety checks, lifecycle, file scope, and Environment Gate criteria. Do not duplicate or reinterpret its contract. If it is missing, still marked unapproved, or conflicts with the repository state, stop and report the blocker.

## Scope

- Inspect the current branch, working tree, existing scripts, tests, and workflows before editing.
- Resume partial work instead of recreating working pieces.
- Implement only Steps 1 through 3 of the rollout plan: the shared DynamoDB Local runner, fail-closed checks, pytest integration fixture and marker, environment smoke tests, and Work Environment Gate verification.
- Keep unit tests independent from DynamoDB Local.
- Do not change product behavior, purchase feature tests, or application code unless the approved rollout contract explicitly requires a minimal testability change. Stop for human approval before such a change.
- Do not start purchase feature TDD, E2E expansion, AWS staging, or production work.
- Preserve unrelated user changes. Do not commit, push, merge, or open a pull request unless the user explicitly requests that action.

## Workflow

1. Determine whether the environment work is absent, partial, or already implemented.
2. From the repository root, run `bash scripts/bootstrap_uv.sh`, prepend `.cache/bin` to `PATH`, and verify the pinned uv and Python versions. Do not use `uv self update` or the GitHub-hosted standalone installer.
3. Run `uv sync --python 3.14.7 --frozen` in `backend/` so an older prerelease virtual environment cannot be reused.
4. Confirm that all SDK access is guarded before the first possible real-AWS call.
5. Implement the missing rollout steps as one coherent environment change, reusing the root Maven Wrapper, `tools/java-runtime/pom.xml`, `MAIN_TABLE_SCHEMA`, and the application DynamoDB access path.
6. Run existing backend unit tests without the DynamoDB Local runner.
7. Run integration and environment smoke tests through the approved runner.
8. Execute the complete Environment Gate twice consecutively, including negative fail-closed cases and child-process cleanup.
9. Record exact commands, uv and Python versions, commit SHA when available, pass/fail counts, and any deviations from the plan.

## Stop conditions

Stop without treating the result as a feature-test failure when any prerequisite, uv bootstrap, exact Python selection, Maven Wrapper bootstrap, Maven Central dependency resolution, checksum, Java, startup, readiness, safety, cleanup, or environment-smoke check fails. Classify it as `ENVIRONMENT_FAILURE`, preserve useful logs, and do not proceed to feature TDD.

Finish by reporting exactly one state:

- `ENVIRONMENT_READY`: every gate passes twice and existing unit tests do not regress.
- `ENVIRONMENT_PARTIAL`: implementation is incomplete but no unsafe action occurred.
- `ENVIRONMENT_FAILURE`: an environment or safety check failed.

Even after `ENVIRONMENT_READY`, wait for explicit human approval before starting feature TDD.
