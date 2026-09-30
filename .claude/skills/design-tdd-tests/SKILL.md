---
name: design-tdd-tests
description: "Design this repository's TDD inputs after superpowers:brainstorming has produced an approved spec and before superpowers:writing-plans: create logical test cases, screen central contracts, record the baseline, and propose the minimum TDD test set for human approval. Use when a feature spec was just approved, or when a spec or test-case return must be applied; never write tests or product code."
---

# Design TDD Tests

Produce approval-ready logical test cases and a minimum TDD plan, then stop before planning or implementation.

## Read first

- `CLAUDE.md`
- `docs/TDD-WORKFLOW.md`
- `docs/MINIMUM-TDD-TEST-PRINCIPLES.md`
- `docs/CORE-CONTRACT-SELECTION.md`
- `docs/templates/minimum-tdd-test-plan.md`
- The approved spec (`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, or legacy `docs/specs/<feature-slug>.md`) and relevant code, read-only

## Preconditions

- The human approved the written spec in superpowers:brainstorming.
- Every requirement has a spec ID and Blocking open items are zero.

If either is missing, stop and return to the human and brainstorming. Do not fill gaps yourself.

## Change boundary

- May create or update `<prefix>-test-cases.md` and `<prefix>-tdd-plan.md` next to the spec.
- Do not change the spec, test code, fixtures, product code, CI, or environment code.
- Do not record a human approval that was not explicitly given.

## Workflow

1. Create logical test cases traceable to every spec ID: success, boundary, validation, failure, authorization, state, and critical concurrency as applicable. No implementation details.
2. Present mechanically derivable cases together; decide ambiguous boundaries, exclusivity, and failure states with the human one by one. Stop for approval (Logical Test Case Gate).
3. Copy the template to the TDD plan, screen every Test Case ID, and propose central contracts with selection reasons, existing protection, TDD eligibility, and post-implementation destinations for excluded cases. Stop for approval (Core Contract Gate).
4. Run the baseline (related tests, lint, type check, build) and record the commit SHA, commands, results, pre-existing failures, and skipped checks.
5. Select the smallest discriminating TDD set from approved contracts (change purpose, critical counterexamples, representative regressions); reuse existing tests where they already protect a contract. Stop for approval (Test Plan Gate).
6. For a return, update the earliest affected artifact and list which approvals and downstream artifacts (implementation plan, Red/Green evidence) are invalidated.

Finish by reporting the artifact paths, the referenced test-case commit, and open items. After all three gates are approved, hand off to `superpowers:writing-plans` following `docs/TDD-WORKFLOW.md` section 5.4. Do not write tests.
