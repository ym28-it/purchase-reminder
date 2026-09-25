---
name: orchestrate-development-cycle
description: "Control this repository's four-agent vertical-slice development cycle, inspect artifacts and approvals, evaluate automated gates, record state, and route work to the correct independent agent. Use only when explicitly asked to start, resume, advance, or assess a feature-development cycle; never implement specifications, tests, or product code."
---

# Orchestrate the Development Cycle

Control one feature cycle without making specification or quality judgments.

## Read first

- `CLAUDE.md`
- `docs/FOUR-AGENT-DEVELOPMENT-WORKFLOW.md`
- `docs/VERTICAL-SLICE-DEVELOPMENT-WORKFLOW.md`
- `docs/TDD-WORKFLOW.md`
- `docs/test-environment-gate-evidence.md`
- The feature specification, logical test cases, TDD plan, post-test report, and final-review report when present

Treat those files as authoritative. Do not restate or weaken their contracts.

## Change boundary

- Create or update only `docs/specs/<feature-slug>-cycle-state.md` from `docs/templates/development-cycle-state.md`.
- Do not change specifications, logical test cases, tests, product code, expected results, or another agent's report.
- Do not approve on behalf of a human, invoke the next role in the same context, merge, or mark `SLICE_COMPLETE` without explicit human approval.

## Workflow

1. Resolve the feature slug, current branch, base SHA, head SHA, working-tree state, and requested transition.
2. Create the cycle-state file if absent. Record artifact paths and exact SHAs; never infer an approval that is not recorded.
3. Verify `ENVIRONMENT_READY`. On an environment failure, record `ENVIRONMENT_FAILURE` and route to `setup-test-environment`; do not count it as Red or an implementation defect.
4. Inspect the current state and evaluate only the mechanical conditions for the next gate:
   - Start: all conditions in workflow section 5.
   - Red Gate: workflow Stage 2.
   - Green Gate: workflow Stage 4.
   - Completion Gate: workflow Stage 6.
   - Final human gate: review artifact exists and the human explicitly decides.
5. Record commands, exit codes, counts, affected SHA, exceptions, decision, and invalidated downstream gates.
6. Select exactly one next role or stop condition. State the Skill to run in a new context, but do not start it.

## Routing

- Missing or conflicting requirements: `prepare-feature-spec` / `BLOCKED_SPEC`.
- Invalid or insufficient TDD test: `create-tdd-tests` / `BLOCKED_TEST` or `INVALID_RED`.
- Product implementation failure: `implement-tdd-slice` / `IMPLEMENTATION_FAILED`.
- Missing post-implementation coverage: `verify-feature-slice` / `POST_TESTING`.
- Completion Gate passed: `review-feature-slice` in a new context / `REVIEW_READY`.
- Review finding: route to the earliest responsible role and invalidate all dependent downstream gates.

Finish with the recorded state, gate decision, evidence location, invalidated gates, and one next action. Then stop.
