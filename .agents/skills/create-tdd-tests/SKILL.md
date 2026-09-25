---
name: create-tdd-tests
description: "Act as the pre-implementation test agent for an approved vertical slice: translate the approved minimum TDD plan into tests, run the environment smoke and baseline, and capture Valid Red or an approved Red exception. Use only after an explicit TDD-start instruction and approved inputs; never change product code or expected behavior."
---

# Create TDD Tests

Implement only the approved minimum TDD set and return Red evidence.

## Read first

- `CLAUDE.md`
- `docs/FOUR-AGENT-DEVELOPMENT-WORKFLOW.md`
- `docs/TDD-WORKFLOW.md`
- `docs/MINIMUM-TDD-TEST-PRINCIPLES.md`
- The approved feature specification, logical test cases, TDD plan, and cycle-state file

## Preconditions

- Human explicitly instructed `TDD開始`.
- The cycle state is `READY` and records the base SHA.
- Environment, Specification, Logical Test Case, Core Contract, and Test Plan gates are approved.
- Blocking specification items are zero.

Stop as `BLOCKED_SPEC` if any precondition is absent. Do not fill the gap yourself.

## Change boundary

- May change test code, test fixtures/helpers, minimum test configuration, and the TDD execution record.
- Do not change product code, specification artifacts, expected results, or the approved meaning of the TDD set.
- Do not weaken assertions to manufacture Red or Green.

## Workflow

1. Record head SHA and confirm no unrelated working-tree changes overlap the task.
2. Run the approved environment smoke and baseline before interpreting feature failures.
3. Implement tests traceable to the approved Contract IDs and Test Case IDs.
4. Run only the relevant test set, then the required baseline checks.
5. Capture command, exit code, failing assertion, reason, count, SHA, and whether failure occurs after collection and environment setup.
6. If the plan records an approved Red exception, prove its conditions instead of forcing a failure.
7. Confirm the diff contains no product code and report the frozen test paths/diff for the next gate.

Return evidence to `orchestrate-development-cycle`. Do not declare `RED_VALIDATED`, start implementation, commit, push, or open a PR unless explicitly requested.
