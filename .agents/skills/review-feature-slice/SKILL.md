---
name: review-feature-slice
description: "Act as the independent final review agent for a vertical slice: directly inspect approved specifications, logical tests, implementation, all test evidence, CI, and residual risk; classify findings and recommend the correct return stage. Use in a fresh context after the Completion Gate; never fix findings or approve on behalf of the human."
---

# Review a Feature Slice

Perform the final integrated review and hand the decision to the human.

## Independence

Run in a new context that does not inherit specification, test, or implementation conversations. Verify repository artifacts and command evidence directly.

## Read first

- `CLAUDE.md`
- `docs/FOUR-AGENT-DEVELOPMENT-WORKFLOW.md`
- `docs/VERTICAL-SLICE-DEVELOPMENT-WORKFLOW.md`
- `docs/templates/final-review-report.md`
- The feature specification, logical test cases, TDD plan, cycle state, relevant diffs, post-test report, and CI results

## Preconditions and boundary

- Require cycle state `REVIEW_READY`; otherwise stop and report the missing Completion Gate evidence.
- May create or update only `docs/specs/<feature-slug>-final-review.md` from the template.
- Do not change specifications, tests, product code, expected results, or cycle state. Do not fix your own findings.

## Workflow

1. Resolve the approved artifact revisions and independently inspect the complete diff.
2. Verify specification-to-Test Case-to-test traceability, Valid Red or exception evidence, frozen-test integrity, and Green evidence.
3. Review post-implementation coverage across branches, boundaries, errors, state, authorization, concurrency, connections, regression, security, and operations.
4. Verify required lint/type/build/unit/component/integration/E2E and CI results with exact SHAs.
5. Identify scope creep, missing evidence, Deferred items, known constraints, and residual risks.
6. Classify every finding as specification, test, implementation, testability, environment, or multi-stage and name the earliest return stage.
7. Complete the final-review report. If no blocking finding exists, request the human's `Slice Complete` decision.

Return findings and the report path to `orchestrate-development-cycle`. Keep the state at `REVIEWING` until the human decides; never merge or self-approve.
