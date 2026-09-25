---
name: prepare-feature-spec
description: "Act as the specification agent for a repository vertical slice: create or revise the feature specification, logical test cases, central-contract candidates, baseline, and minimum TDD plan for human approval. Use only when explicitly asked to specify a feature or resolve a specification return; never write tests or product code."
---

# Prepare a Feature Specification

Produce approval-ready specification artifacts and stop before implementation.

## Read first

- `CLAUDE.md`
- `docs/VERTICAL-SLICE-DEVELOPMENT-WORKFLOW.md`
- `docs/TDD-WORKFLOW.md`
- `docs/MINIMUM-TDD-TEST-PRINCIPLES.md`
- `docs/CORE-CONTRACT-SELECTION.md`
- `docs/FOUR-AGENT-DEVELOPMENT-WORKFLOW.md`
- Relevant existing specifications and code, read-only

## Change boundary

- May create or update `docs/specs/<feature-slug>.md`, `<feature-slug>-test-cases.md`, and `<feature-slug>-tdd-plan.md`.
- Do not change test code, fixtures, product code, CI, environment code, or cycle-state decisions.
- Do not silently resolve ambiguous requirements or record human approval that was not explicitly given.

## Workflow

1. Confirm the feature objective, observable start-to-end value, scope, exclusions, and affected actors.
2. Inspect current behavior and contracts without treating implementation as the desired behavior.
3. Record every ambiguity or conflict. Ask the human only for decisions that cannot be established from authoritative sources.
4. Create traceable logical test cases covering success, validation, failure, authorization, state, and critical concurrency behavior as applicable.
5. Screen every logical case, propose central contracts, and build the smallest discriminating TDD set.
6. Record the baseline commands and results before code changes. Separate existing failures from future Red evidence.
7. Apply any return request to the earliest affected artifact and identify which approvals and downstream gates are invalidated.
8. Present the artifacts and unresolved items for human approval. Do not start test implementation.

Finish as `SPECIFYING` when approval is pending or `BLOCKED_SPEC` when a human decision is required. If all required approvals are explicitly recorded, report the evidence to `orchestrate-development-cycle` for a mechanical `READY` decision.
