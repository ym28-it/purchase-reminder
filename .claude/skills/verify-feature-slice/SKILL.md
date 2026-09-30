---
name: verify-feature-slice
description: "Execute the verification task at the end of a superpowers implementation plan in this repository: analyze the implemented flow, add missing unit/component/integration/E2E coverage, map every logical Test Case ID, run full verification, and produce the post-implementation test report. Use in a fresh context after all Green tasks; never change product code or infer expectations from implementation."
---

# Verify a Feature Slice (verification task)

Independently test the implemented slice beyond the minimum TDD set.

## Independence

Run in a fresh context (a new subagent under superpowers:subagent-driven-development). Derive expected behavior only from the approved spec and logical test cases.

## Read first

- `CLAUDE.md`
- `docs/TDD-WORKFLOW.md` (section 5.7)
- `docs/templates/post-implementation-test-report.md`
- The approved spec, logical test cases, TDD plan with Red/Green evidence, the implementation diff, and the task brief

## Preconditions and boundary

- Require Green evidence for every TDD contract in the TDD plan; otherwise stop.
- May add or revise tests, fixtures/helpers, minimum test configuration, and `<prefix>-post-test-report.md`.
- Do not change product code, spec artifacts, expected results, or frozen TDD tests to fit the implementation.

## Workflow

1. Inspect the code and diff directly, and collect line/branch coverage. Map branches, boundaries, exceptions, state transitions, authorization, concurrency, and cross-layer connections.
2. Map every logical Test Case ID to TDD, existing coverage, a new test, or an explicit justified exclusion.
3. Classify uncovered code as Critical / Important / Low risk / Unreachable / Specification gap, and pick the cheapest deterministic test level without duplicating lower-level coverage.
4. Run the environment smoke before integration/E2E and classify environment failures separately.
5. Add tests only when expected behavior is uniquely defined by the spec. Otherwise stop as `BLOCKED_SPEC`.
6. Run required regression, static, build, integration, and E2E checks; record commands, counts, exit codes, SHA, unexecuted checks, and residual risks.
7. Complete the report, confirm no product code changed, and commit.

Report whether the Completion Gate conditions in `docs/TDD-WORKFLOW.md` are met. Do not perform the final code review or merge.
