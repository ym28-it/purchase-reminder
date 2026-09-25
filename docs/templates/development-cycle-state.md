# Development Cycle State

## Identity

| Field | Value |
|---|---|
| Feature slug | `<feature-slug>` |
| Base SHA | `<sha>` |
| Current head SHA | `<sha>` |
| Environment Gate SHA | `<sha>` |
| Current state | `SPECIFYING` |
| Last updated | `<date-time>` |

## Artifacts

| Artifact | Path | Revision / status |
|---|---|---|
| Specification | `docs/specs/<feature-slug>.md` | `<sha / approval>` |
| Logical test cases | `docs/specs/<feature-slug>-test-cases.md` | `<sha / approval>` |
| TDD plan | `docs/specs/<feature-slug>-tdd-plan.md` | `<sha / approval>` |
| Post-test report | `docs/specs/<feature-slug>-post-test-report.md` | `<sha / pending>` |
| Final review | `docs/specs/<feature-slug>-final-review.md` | `<sha / pending>` |

## Human approvals

Record the approving instruction or artifact reference. Never infer approval.

| Gate | Status | Evidence |
|---|---|---|
| Environment Gate | `<status>` | `<reference>` |
| Specification Gate | `<status>` | `<reference>` |
| Logical Test Case Gate | `<status>` | `<reference>` |
| Core Contract Gate | `<status>` | `<reference>` |
| Test Plan Gate | `<status>` | `<reference>` |
| Slice Complete | `Pending` | — |

## Automated gates

| Gate | Input SHA | Commands / evidence | Result | Invalidated by |
|---|---|---|---|---|
| Red Gate | — | — | `Pending` | — |
| Green Gate | — | — | `Pending` | — |
| Completion Gate | — | — | `Pending` | — |

## Handoff

- Responsible role: `<role>`
- Next Skill: `<skill or stop>`
- Allowed changes: `<paths/categories>`
- Unresolved items: `<none or list>`
- Invalidated downstream gates: `<none or list>`
