---
name: create-tdd-tests
description: "Execute a Red task of a superpowers implementation plan in this repository: translate the approved minimum TDD set into tests, run the environment smoke and baseline, capture Valid Red or an approved Red exception, and freeze the tests. Use when a plan task says to write the TDD tests for approved contracts; never change product code or expected behavior."
---

# Create TDD Tests (Red task)

Implement only the approved minimum TDD tests assigned to this task and return Red evidence.

## Read first

- `CLAUDE.md`
- `docs/TDD-WORKFLOW.md`
- `docs/MINIMUM-TDD-TEST-PRINCIPLES.md`
- The approved spec, logical test cases, TDD plan, and the task brief from the implementation plan

## Preconditions

- Logical Test Case, Core Contract, and Test Plan gates are approved in the TDD plan.
- The human approved the implementation plan and chose an execution method.
- The task names the Contract IDs and Test Case IDs to cover.

Stop as `BLOCKED_SPEC` if any precondition is absent. Do not fill the gap yourself.

## Change boundary

- May change test code, test fixtures/helpers, minimum test configuration, and the Red section of the TDD plan.
- Do not change product code, spec artifacts, expected results, or the approved meaning of the TDD set.
- Do not weaken assertions to manufacture Red or Green. Do not add pre-implementation tests outside the approved TDD set.
- Do not use `superpowers:test-driven-development`; this skill replaces it.

## Workflow

1. Record the head SHA and confirm no unrelated working-tree changes overlap the task.
2. Run the environment smoke and baseline. On an environment failure, stop as `ENVIRONMENT_FAILURE` and point to `setup-test-environment`.
3. Implement tests traceable to the approved Contract IDs and Test Case IDs (test name or metadata).
4. Run the relevant tests, then the required baseline checks.
5. Confirm Valid Red: the target tests fail, the reason is the unimplemented approved contract, and the failure happens after collection and environment setup. If the plan records an approved Red exception, prove its conditions instead of forcing a failure.
6. Confirm the diff contains no product code, commit, and append command, exit code, failing assertion, reason, count, SHA, and the frozen test paths to the TDD plan.

Report `RED_VALIDATED`, `INVALID_RED`, `BLOCKED_TEST`, `BLOCKED_SPEC`, or `ENVIRONMENT_FAILURE` with the evidence location. Do not start the Green task.
