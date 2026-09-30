---
name: implement-tdd-slice
description: "Execute a Green task of a superpowers implementation plan in this repository: make frozen TDD tests pass with the smallest product implementation while preserving test expectations, and record Green evidence. Use when a plan task implements contracts whose Red was validated; never edit frozen TDD tests or specification artifacts."
---

# Implement a TDD Slice (Green task)

Make the frozen TDD tests Green with the smallest complete implementation.

## Read first

- `CLAUDE.md`
- `docs/TDD-WORKFLOW.md`
- The approved spec, logical test cases, TDD plan (including Red evidence), frozen tests, and the task brief

## Preconditions

- The TDD plan records Valid Red (or an approved Red exception) and the frozen test paths and SHA for this task's contracts.
- The environment smoke is Green.

Stop if these are absent or inconsistent.

## Change boundary

- May change product code and product configuration required by the task, plus append Green evidence to the TDD plan.
- Do not change frozen TDD tests, fixtures that encode expectations, spec artifacts, logical test cases, or approved expected results. This also applies when fixing review findings.
- Do not add unrelated behavior or broad refactoring. Do not use `superpowers:test-driven-development`.

## Workflow

1. Re-read repository artifacts; do not rely on the Red task's conversational claims.
2. Verify the frozen tests are unchanged since Red validation (`git diff <red-sha> -- <frozen paths>`).
3. Implement the smallest path from user-visible input to final output or persisted state. Refactor without relaxing tests.
4. If a test or the spec appears wrong, stop without editing it and report `BLOCKED_TEST` or `BLOCKED_SPEC`. Do not settle expected behavior with a ruling.
5. Run the target TDD tests, affected regression tests, and the lint/format/type/build checks required by the plan, plus the environment smoke when integration is involved.
6. Re-check frozen tests are unchanged and no unrelated files entered the diff; commit and record commands, exit codes, counts, SHA, and known exceptions in the TDD plan.

Report `TDD_GREEN` or `IMPLEMENTATION_FAILED` with the evidence location. Do not start post-implementation testing.
