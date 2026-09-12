# Fixed real-offer acceptance — 29 July 2026

## Release decision

**Blocked — no owner approval.** The fixed real-offer acceptance could not
start because the complete all-provider refresh was rejected. No release is
authorized by this record.

## Historical disposition

This record is retained as historical evidence of a blocked pre-replacement
candidate, not as a current acceptance or product requirement. Its failed
withdrawal-isolation regression, provider-aggregate diagnostic, coverage
wording, and 1280 × 720 fixture observation are superseded by #67 and #86.
The current tree has no withdrawal workflow or coverage authority, and the
historical failed test does not define the current test contract.

## Application and dataset

- Application commit: `7f7a076f10856cf2ab396654135151b6e50484ad`
- Acceptance run: `2026-07-29T08:08:00+02:00` to
  `2026-07-29T08:13:00+02:00`
- Provider Registry: Fleasing and Terminalen were active; no inactive records were present.
- Requested dataset generation: not created. There was no prior active dataset
  at `var/catalogue-dataset.json`, and the fixture dataset is not a substitute
  for a current real-offer dataset.

## Provider-source check and blocker

The run used the bounded first-party sources defined by the owner guide:

- Fleasing catalogue: <https://fleasing.dk/biler/>
- Terminalen catalogue: <https://www.terminalen.dk/nye-biler/hyundai>

`uv run --locked car-picker catalogue refresh` completed Fleasing collection far enough to begin
Terminalen collection, then retried Terminalen and rejected the complete
replacement. The reported blocker was:

> Terminalen collection failed after two retries

with the underlying structural reason:

> Terminalen catalogue contains no model price pages

A direct source check immediately after the failed refresh returned HTTP 200,
270,379 bytes, and current first-party model links including Hyundai Inster,
Kona Electric, IONIQ 5, IONIQ 6, and IONIQ 9. That check was performed before
the required post-failure terms, robots-policy, and access-boundary review. It
was a procedural error and does not establish permitted access, source
authorization, or that the linked pages meet the designated-source and
exact-offer requirements. No further provider retrieval was attempted.

The complete replacement was correctly rejected. No partial or mixed-age
catalogue dataset was written. The live fixed set therefore lacks the required
current Terminalen operational offer and cannot satisfy the four owner tasks.

## Fixture and static-artifact checks

These checks establish the current application behaviour only; they do not pass
the real-offer acceptance:

| Check | Expected | Actual | Result |
| --- | --- | --- | --- |
| Direct history-check, legal-check, and contract checks | Passed; legal gate reports the 20 November 2026 horizon and pending post-transition revalidation | Pass |
| Fixture static build | Completed verified artifact is produced | Passed into ignored `var/site` | Pass |
| Browser suite | Completed artifact passes catalogue, detail, comparison, evidence, unknown-value, and route checks | 11 of 11 Playwright tests passed | Pass |
| Full Python suite | All repository tests pass | 62 passed; `test_terminalen_withdrawal_leaves_only_the_ended_coverage_fact` failed because the generated browser schema still names Terminalen | Fail |
| Desktop viewport | Catalogue, detail, and aligned comparison remain usable at 1280 × 720 with no page-level horizontal overflow | Passed | Pass |
| Mobile viewport | Catalogue rows stack at 390 × 844; comparison remains horizontally scrollable with pinned labels and equivalent material facts | Passed | Pass |
| Fixture arithmetic | `15,990 + (3,795 × 36)` reproduces nominal base outlay `152,610` DKK and monthly equivalent `4,239.17` DKK before display rounding | Passed | Pass |
| Provider aggregate diagnostic | Missing provider aggregate is not invented and its blocker is named | `not_available`; asks for a provider aggregate covering the same normal-completion base cash-flow scope | Pass |

The fixture evidence URLs use the reserved `example.test` domain and were not
treated as current provider evidence.

## Required fixed set and owner tasks

| Requirement or task | Expected | Actual | Disposition |
| --- | --- | --- | --- |
| Terminalen operational offer | Current comparison-ready offer | Missing because Terminalen's current catalogue structure is not discovered by the bounded collector | Blocked |
| Fleasing financial or flex offer with residual-value or third-party-buyer exposure | Current admitted offer | Not evaluated without a complete current dataset | Blocked |
| Important unknown or non-admission example | Current offer whose material fact state is visible | Not evaluated without a complete current dataset | Blocked |
| Find two constrained offers | Owner completes task | Not run | Blocked |
| Compare all four headline amounts | Owner completes task | Not run | Blocked |
| Explain risk, end mechanism, exposures, and unknowns | Owner completes task | Not run | Blocked |
| Audit facts, arithmetic, evidence, and provider sources | Owner completes task | Not run | Blocked |
| Desktop and mobile equivalence | Owner completes all four tasks at both representative viewports | Fixture behavior passed, but the real-offer tasks were not run | Blocked |

## Defects and dispositions

- `Required source-access preflight was missed`: release blocker and procedural
  defect. The Fleasing source audit was not reviewed before the live command,
  and Terminalen was fetched once more after failure before its current terms,
  robots policy, and access boundaries were rechecked. This remains a procedural
  defect in that run. The repository has since adopted
  [ADR-0001](../adr/0001-public-provider-access.md), under which absence of
  affirmative written permission is not a blocker; both providers still require
  current source-audit decisions before another live refresh.
- `Terminalen designated catalogue structure changed`: release blocker. Reassess
  the designated model pages and their exact-offer evidence only after checking
  the provider's current terms, robots policy, and access boundaries. Update
  the collector in separate implementation work, then run a fresh complete
  refresh and repeat this acceptance.
- `Withdrawn Terminalen name remains in the generated browser schema`: failed
  regression check. The fixture-backed browser tasks passed, but the full
  automated suite is not green. Resolve and verify the withdrawal-isolation
  behavior before release.

## Legal gate

The pre-transition validation passed and recorded the consumer-credit change
horizon of 20 November 2026. Post-transition revalidation remains pending. This
acceptance has no release approval, so it does not assert a post-transition
legal decision.

## Owner-only sign-off

- Owner name: _not signed_
- Date: _not signed_
- Release decision: **not approved**
