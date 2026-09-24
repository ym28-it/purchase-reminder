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

Treat the rollout document, `bin/mise`, root `mise.toml`, and root `.python-version` as authoritative for bootstrap and tool versions, checksums, Maven coordinates, safety checks, lifecycle, file scope, and Environment Gate criteria. Do not duplicate or reinterpret their contract. If any is missing, the rollout is still marked unapproved, or they conflict with the repository state, stop and report the blocker.

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
2. Confirm the host is Linux (including WSL2) or macOS and that the committed `bin/mise` wrapper is executable. Confirm `curl` or `wget`, `tar`, and `sha256sum` or `shasum` are available for its verified bootstrap. Native Windows or a missing bootstrap prerequisite is an environment blocker; do not fall back to system package managers, system Python, or a global mise installation.
3. From the repository root, run `bash scripts/setup_host_prerequisites.sh --install`. This is the approved setup action: `bin/mise` bootstraps the pinned mise release, verifies its checksum, and installs uv 0.12.18 and Temurin Java 17 sequentially with `mise install --jobs=1`; uv then installs the Python version pinned by `.python-version` into the ignored `.mise/uv-python/` directory. Do not replace either step or enable parallel installation.
4. Run `bash scripts/setup_host_prerequisites.sh --check` and record the mise, uv-managed Python, uv, and Java versions. The check must not download anything. Run subsequent tool commands through the committed wrapper so `UV_MANAGED_PYTHON=1`, the repository-local Python installation directory, `JAVA_HOME`, and `PATH` are inherited without shell activation.
5. In `backend/`, run `../bin/mise exec -- uv sync --python 3.14.7 --frozen` so an older prerelease or system Python environment cannot be reused.
6. Confirm that all SDK access is guarded before the first possible real-AWS call.
7. Implement the missing rollout steps as one coherent environment change, reusing the root Maven Wrapper, `tools/java-runtime/pom.xml`, `MAIN_TABLE_SCHEMA`, and the application DynamoDB access path.
8. Run existing backend unit tests without the DynamoDB Local runner.
9. Run integration and environment smoke tests through the approved runner. From `backend/`, invoke the runner and every child `uv` command through `../bin/mise exec --`.
10. Execute the complete Environment Gate twice consecutively, including negative fail-closed cases and child-process cleanup.
11. Record exact commands, mise, uv, Python, and Java versions, commit SHA when available, pass/fail counts, and any deviations from the plan.

## Stop conditions

Stop without treating the result as a feature-test failure when any host support, mise wrapper prerequisite, mise bootstrap or checksum, mise tool installation, uv-managed Python installation or exact tool selection, Maven Wrapper bootstrap, Maven Central dependency resolution, checksum, Java, startup, readiness, safety, cleanup, or environment-smoke check fails. Classify it as `ENVIRONMENT_FAILURE`, preserve useful logs, and do not proceed to feature TDD.

Finish by reporting exactly one state:

- `ENVIRONMENT_READY`: every gate passes twice and existing unit tests do not regress.
- `ENVIRONMENT_PARTIAL`: implementation is incomplete but no unsafe action occurred.
- `ENVIRONMENT_FAILURE`: an environment or safety check failed.

Even after `ENVIRONMENT_READY`, wait for explicit human approval before starting feature TDD.
