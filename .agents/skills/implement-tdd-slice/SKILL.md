---
name: implement-tdd-slice
description: "Act as the implementation agent for a repository vertical slice: use approved specifications, frozen TDD tests, and Red evidence to make the smallest product implementation Green while preserving test expectations. Use only after the Automated Red Gate passes; never edit TDD tests or specification artifacts."
---

# Implement a TDD Slice

Make frozen TDD tests Green with the smallest complete vertical-slice implementation.

## Read first

- `CLAUDE.md`
- `docs/FOUR-AGENT-DEVELOPMENT-WORKFLOW.md`
- `docs/TDD-WORKFLOW.md`
- `docs/VERTICAL-SLICE-DEVELOPMENT-WORKFLOW.md`
- The approved feature artifacts, cycle-state file, frozen tests, and Red evidence

## Preconditions

- The cycle state is `RED_VALIDATED`.
- The base/head SHA and frozen test diff are recorded.
- The environment smoke is Green.

Stop if these are absent or inconsistent.

## Change boundary

- May change product code and product configuration required by the approved slice, plus append Green evidence to the TDD execution record.
- Do not change tests, fixtures that encode expectations, specifications, logical test cases, or approved expected results.
- Do not add unrelated behavior or broad refactoring.

## Workflow

1. Re-read repository artifacts without inheriting the test agent's conversational claims.
2. Verify frozen tests have not changed since Red validation.
3. Trace the smallest implementation path from user-visible input to final output or persisted state.
4. Implement in small steps. If a test or specification appears wrong, stop without editing it and classify the return.
5. Run the targeted TDD tests, affected regression tests, lint/format/type/build checks required by the plan, and the environment smoke when integration is involved.
6. Re-check that frozen tests are unchanged and that no unrelated files entered the diff.
7. Record commands, exit codes, counts, SHA, known exceptions, and implementation scope.

Return Green evidence to `orchestrate-development-cycle`. Do not declare `TDD_GREEN`, start post-implementation testing, or merge.
