# Fixed real-offer acceptance after VAT decision — 29 July 2026

## Release decision

**Ready for owner task execution and sign-off, but not approved.** The owner's
private-consumer VAT and aggregate-difference decisions unlock a current fixed
set: the catalogue publishes 13 Fleasing offers and two Terminalen offers, and
all four headline amounts remain available. Terminalen's exact source
arithmetic conflict is displayed as an unexplained-difference warning instead
of silently correcting either total. This record does not authorize release
without the owner's dated task results and approval.

## Application and dataset

- Application commit: `e85f1e9fd13eb8f7e2a42dee12134c17859378eb`
- Acceptance implementation rerun completed: `2026-07-29T11:42:19+02:00`
- Catalogue generation: `2026-07-29T08:57:15.069074Z`
- Provider access policy: ADR-0001; the dated Fleasing and Terminalen source
  audits both record `allowed`, matching `config/provider-access.json`.
- Provider control: Fleasing and Terminalen retrieval enabled; no withdrawals
  recorded.
- Dataset result: 15 admitted catalogue offers—13 Fleasing and two Terminalen—
  and 146 quarantined Fleasing candidates.

## Owner VAT decision

[ADR-0002](../adr/0002-unqualified-private-prices-include-vat.md) records the
owner's decision that an unqualified price explicitly meant for a private
consumer is VAT-inclusive. Explicit excluding or contradictory VAT wording
takes precedence. Applying that rule, together with exact current source
evidence, resolves the previous VAT blocker without inventing provider wording.

The owner subsequently decided that a provider aggregate mismatch is acceptable
when the reconstructed amounts remain visible with a frontend warning and an
unknown residual amount. The domain model names that amount the **unexplained
aggregate difference** to distinguish it from vehicle residual value.

## Fixed offer set

| Role | Exact identity | Important facts | Disposition |
| --- | --- | --- | --- |
| Terminalen operational | `terminalen:HY_IONIQ5_NE_DK_IONIQ5_MY27:private-e779a612333a` | Hyundai IONIQ 5; provider bears residual risk; return to provider; 36 months; 10,000 km/year | Admitted and comparison-ready with an unexplained aggregate-difference warning |
| Fleasing financial/flex | `fleasing:442795427:private-8f745634e8cf` | Aston Martin DB9 Volante aut.; financial; customer must sell or designate a buyer at normal end; proportional registration tax | Admitted and comparison-ready |
| Important unknown | `fleasing:771869804:private-e4d3ad141ff6` | Aston Martin DB11 V8 Volante aut.; residual value is stated, but residual-risk allocation remains `unclear` | Admitted; important unknown remains visible |

The identities were copied from the fresh canonical dataset before the live
static build.

## Headline amounts and arithmetic

| Headline amount | Fleasing DB9 | Terminalen IONIQ 5 |
| --- | ---: | ---: |
| Advertised monthly payment | 15,865 DKK | 2,795 DKK |
| Upfront cash requirement | 142,813 DKK | 49,995 DKK |
| Nominal base outlay | 333,193 DKK | 151,615 DKK |
| Nominal monthly equivalent | 27,766 DKK | 4,212 DKK |

The Fleasing calculation reproduces:

`142,813 + (15,865 × 12) = 333,193 DKK`

and `333,193 ÷ 12 = 27,766.08 DKK`, displayed as 27,766 DKK.

For Terminalen, the exact offer source states a 1,000 DKK inspection fee,
collected with the last payment and included in the advertised aggregate:

`49,995 + (2,795 × 36) + 1,000 = 151,615 DKK`

The provider advertises 151,395 DKK, a difference of 220 DKK. The second
Terminalen configuration has the same 220 DKK conflict:

`14,995 + (3,995 × 36) + 1,000 = 159,815 DKK`

versus an advertised 159,595 DKK. The application preserves the provider total,
the reconstructed amounts, and the signed `-220 DKK` unexplained difference.
Catalogue, detail, and comparison views warn that the cause is unknown and do
not select one side of the conflict as a correction for the other.

## Required owner tasks

| Requirement or task | Expected | Actual | Disposition |
| --- | --- | --- | --- |
| Terminalen operational offer | Current admitted, comparison-ready offer | Two admitted operational offers; derived amounts remain visible beside the provider-total warning | Pass |
| Fleasing financial/flex offer | Current admitted offer with residual-value or buyer exposure | 13 admitted offers; selected DB9 exposes both residual value and buyer obligation | Pass |
| Important unknown | Material unknown is visible | Selected DB11 shows residual-risk allocation as `unclear` | Pass |
| Find two constrained offers | Owner completes task at desktop and mobile | Technically available; not yet owner-tested | Not signed |
| Compare all four headline amounts | Owner compares the selected operational and financial/flex offers | All four amounts are available; Terminalen warning remains visible | Ready, not signed |
| Explain risk, end mechanism, exposures, and unknowns | Owner uses detail and comparison views | Fixed set exists, but owner task is not signed | Not signed |
| Audit facts, arithmetic, evidence, and provider sources | Owner audits the selected offers | Arithmetic and unexplained difference are inspectable; owner task is not signed | Ready, not signed |
| Desktop and mobile equivalence | Four owner tasks pass at 1280 × 720 and 390 × 844 | Automated regression passes both viewports; real-offer owner tasks remain unsigned | Ready, not signed |

## Application checks

| Check | Actual | Result |
| --- | --- | --- |
| Checkout validation | Dataset, Git history, provider controls, access records, and pre-transition legal gate passed | Pass |
| Live static build | Completed artifact built from generation `2026-07-29T08:57:15.069074Z` | Pass |
| Projection safety | Both Terminalen derived amounts remain available with provider total and signed unexplained difference kept separate | Pass |
| Python suite | 76 tests passed | Pass |
| Fixture browser suite | 12 Playwright tests passed sequentially, including catalogue/detail/comparison mismatch warnings | Pass |
| Frontend types | TypeScript project check passed | Pass |
| Lint, format, and Python types | All repository hooks passed after formatting | Pass |

The fixture browser suite temporarily replaces the ignored `var/site` artifact.
The fresh real-offer artifact was rebuilt afterward.

## Defects and dispositions

- `Private prices without VAT wording were quarantined`: resolved by the
  owner's ADR-0002 decision and deterministic provider mappings.
- `Fleasing generic flex terms lacked exact applicability`: resolved narrowly
  for current catalogue configurations with explicit residual-value and
  private-leasing evidence; other candidates remain quarantined.
- `Terminalen aggregate differs from its stated cash flows by 220 DKK`:
  accepted by the owner as an unexplained aggregate difference. Preserve both
  totals, show the warning and difference, and do not substitute an unstated fee
  or silently reconcile the values.
## Legal gate

The pre-transition legal validation passed and records the consumer-credit
change horizon of 20 November 2026. Post-transition revalidation remains
pending.

## Owner-only sign-off

- Owner name: _not signed_
- Date: _not signed_
- Release decision: **not approved**
