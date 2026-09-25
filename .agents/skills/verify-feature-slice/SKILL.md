---
name: verify-feature-slice
description: "Act as an independent post-implementation test agent for a completed TDD slice: analyze the implemented flow, add missing unit/component/integration/E2E coverage, map every logical Test Case ID, and produce the post-test report. Use in a fresh context after TDD Green; never change product code or infer expectations from implementation."
---

# Verify a Feature Slice

Independently test the implemented slice beyond the minimum TDD set.

## Independence

Run in a new context that does not inherit implementation-agent conversation. Derive expected behavior only from approved specifications and logical test cases.

## Read first

- `CLAUDE.md`
- `docs/FOUR-AGENT-DEVELOPMENT-WORKFLOW.md`
- `docs/VERTICAL-SLICE-DEVELOPMENT-WORKFLOW.md`
- `docs/templates/post-implementation-test-report.md`
- The approved feature artifacts, cycle-state file, implementation diff, and Green evidence

## Preconditions and boundary

- Require cycle state `TDD_GREEN`; otherwise stop.
- May add or revise tests, fixtures/helpers, minimum test configuration, and `docs/specs/<feature-slug>-post-test-report.md`.
- Do not change product code, specifications, expected results, or frozen TDD tests merely to fit the implementation.

## Workflow

1. Inspect the code and diff directly. Map branches, boundaries, exceptions, state transitions, authorization, concurrency, and cross-layer connections.
2. Map every logical Test Case ID to existing coverage, a new test, or an explicit Deferred reason.
3. Select the smallest useful mix of unit, component, integration, and representative E2E tests without duplicating lower-level coverage.
4. Run environment smoke before integration/E2E and classify environment failures separately.
5. Add tests only when expected behavior is uniquely defined. Return `BLOCKED_SPEC` when it is not.
6. Run required regression, static, build, integration, and E2E checks and record commands, counts, exit codes, SHA, and residual risks.
7. Complete the post-implementation test report and confirm no product code changed.

Return the report to `orchestrate-development-cycle` for the Completion Gate. Do not perform the final review or declare the slice complete.
