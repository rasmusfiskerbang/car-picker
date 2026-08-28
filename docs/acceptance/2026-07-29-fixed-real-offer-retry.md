# Fixed real-offer acceptance retry — 29 July 2026

## Release decision

**Blocked — no owner approval.** The complete all-provider refresh succeeded,
but the resulting current catalogue dataset contains no admitted offers. The
required fixed set and four owner tasks are therefore unavailable. No release is
authorized by this record.

## Historical disposition

This record is retained as historical evidence of an unsigned, zero-admission
intermediate candidate, not as a current acceptance or product requirement.
Its prior source-audit wording, provider-aggregate terminology, and 1280 × 720
task boundary are superseded by #67 and the later #86 live gate. No retained
candidate, source document, or intermediate access control became a current
authority.

## Application and dataset

- Application commit: `c85a41f9c3ab9bb98f533a911814e01b2252238c`
- Acceptance run: `2026-07-29T09:32:55+02:00` to
  `2026-07-29T09:38:46+02:00`
- Catalogue generation: `2026-07-29T07:32:55.089180Z`
- Source audits: ADR-0001; the dated Fleasing and Terminalen source audits
  both recorded `allowed` for this historical run.
- Provider Registry: Fleasing and Terminalen were active; no inactive records were present.
- Dataset result: zero admitted catalogue offers and 161 quarantined
  candidates—159 Fleasing and two Terminalen.

## Refresh and source checks

`uv run --locked car-picker catalogue refresh` completed both bounded first-party providers and
reported:

> Provider aggregate reconciliation: no mismatches.

Terminalen's current navigation designated eight exact Hyundai model-price
pages. Seven contained no private-leasing rows and were correctly ignored.
IONIQ 5 contained two explicit private-leasing configurations, which were
retained as quarantined candidates. The complete dataset was written atomically;
no source-wide structural or access failure occurred.

## Admission blockers

Both Terminalen IONIQ 5 configurations have explicit private eligibility,
operational end terms, provider residual-risk allocation, term, mileage, monthly
payment, upfront amount, and provider aggregate. They remain quarantined because
the designated current page API does not state:

- `passengerCarScope`: `vehicleType` is absent;
- `currentAvailability`: `isCurrent` is absent; and
- base-cash-flow VAT basis: the leasing wording does not state that the amounts
  include VAT.

Every Fleasing candidate remains quarantined because its bounded detail source
does not establish private-consumer eligibility, passenger-car scope, or a
classifiable supported leasing form. Residual-value wording alone is not used to
invent those admission facts.

The collector must not promote these candidates or borrow generic and
ambiguously applicable facts merely to satisfy acceptance. Passing requires an
explicitly applicable first-party source within a revised designated-source
audit, or a separately agreed change to the admission model.

## Required fixed set and owner tasks

| Requirement or task | Expected | Actual | Disposition |
| --- | --- | --- | --- |
| Terminalen operational offer | Current admitted, calculable offer | Two operational candidates are calculable but quarantined by three admission blockers | Blocked |
| Fleasing financial or flex offer with residual-value or third-party-buyer exposure | Current admitted offer | 159 candidates expose relevant wording but none satisfies admission | Blocked |
| Important unknown or non-admission example | Material unknown or quarantine is visible | 161 non-admission examples exist in the internal dataset, but no admitted offer can anchor the owner tasks | Partial, release blocked |
| Find two constrained offers | Owner completes task | No admitted offers to filter | Blocked |
| Compare all four headline amounts | Owner compares operational and financial/flex offers | No admitted offers to compare | Blocked |
| Explain risk, end mechanism, exposures, and unknowns | Owner uses detail and comparison views | No admitted detail or comparison routes | Blocked |
| Audit facts, arithmetic, evidence, and provider sources | Owner audits displayed real offers | No real offers are displayed | Blocked |
| Desktop and mobile equivalence | Four tasks pass at 1280 × 720 and 390 × 844 | Tasks cannot start | Blocked |

## Application checks

| Check | Actual | Result |
| --- | --- | --- |
| Direct history-check, legal-check, and contract checks | Pass |
| Live static build | Completed zero-offer artifact built successfully from the current dataset | Pass |
| Python suite | 72 tests passed | Pass |
| Fixture browser suite | 11 Playwright tests passed sequentially at desktop and mobile viewports | Pass |
| Lint, format, and Python types | All repository hooks passed | Pass |
| Frontend types | TypeScript project check passed | Pass |

An earlier concurrent browser/build attempt was invalid because two commands
wrote the ignored `var/site` artifact simultaneously. Its result was discarded;
the recorded browser result is the subsequent isolated 11-test pass.

## Defects and dispositions

- `Terminalen pages without private offers aborted collection`: fixed in
  `c85a41f`; non-offer model pages are skipped, while a source-wide absence still
  fails closed.
- `Terminalen current price-card layout was misclassified`: fixed in `c85a41f`;
  unrelated model-price cards are ignored and both explicit leasing layouts are
  parsed.
- `No admitted current offers`: release blocker. Do not weaken or infer admission
  facts inside acceptance work. Investigate explicitly applicable first-party
  admission evidence as separate source-scope/domain work, then refresh and
  repeat acceptance.

## Legal gate

The pre-transition legal validation passed and records the consumer-credit
change horizon of 20 November 2026. Post-transition revalidation remains pending.

## Owner-only sign-off

- Owner name: _not signed_
- Date: _not signed_
- Release decision: **not approved**
