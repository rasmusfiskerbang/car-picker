# Fixed real-offer acceptance — 28 July 2026

## Release decision

**Blocked — no owner approval.** The fixed real-offer acceptance did not start
because the complete all-provider refresh was rejected. No release is
authorized by this record.

## Application and dataset

- Application commit: `0995d983d4a37725d2efba1a38b70c054967e1b9`
- Acceptance run started: `2026-07-28T16:05:00+02:00`
- Provider control: Fleasing and Terminalen retrieval both enabled;
  no withdrawals recorded.
- Requested dataset generation: not created. The prior fixture dataset is not
  a substitute for a current real-offer dataset.

## Provider-source check and blocker

The run used the bounded first-party sources defined by the owner guide:

- Fleasing catalogue: <https://fleasing.dk/biler/>
- Terminalen catalogue: <https://www.terminalen.dk/nye-biler/hyundai>

`uv run car-picker refresh-catalogue --dataset var/catalogue-dataset.json`
retried Fleasing and rejected the complete replacement. Its designated catalogue
contained `https://fleasing.dk/bil/?bmw-m3-competition-dkg&vid=1904312905`, but
that URL resolved to Fleasing's generic `/bil/` page rather than a page with
vehicle information and a private-pricing tab. The reported blocker was:

> Fleasing collection failed after two retries

with the underlying structural reason:

> Fleasing detail … no longer contains vehicle information and a
> private-pricing tab

This is the correct safe outcome: a partial or mixed-age catalogue was not
written and no static artifact was replaced. The live fixed set therefore lacks
the required admitted Fleasing financial or flex offer and cannot satisfy the
four owner tasks.

## Fixture and static-artifact checks

These checks establish the current application behaviour only; they do not pass
the real-offer acceptance:

| Check | Expected | Actual | Result |
| --- | --- | --- | --- |
| Checkout validation | Schema, generated-content boundary, and pre-transition legal status pass | Passed; legal gate reports the 20 November 2026 horizon and pending post-transition revalidation | Pass |
| Fixture static build | Completed verified artifact is produced | Passed into ignored `var/site` | Pass |
| Desktop catalogue (1280 × 720) | Catalogue is usable without page horizontal overflow and unavailable totals name their blockers | Passed; derived totals state that the complete payment stream is missing | Pass |
| Mobile catalogue (390 × 844) | Stacked catalogue row without page horizontal overflow | Passed; one catalogue card and no page horizontal overflow | Pass |
| Provider aggregate diagnostic | Provider assertion, arithmetic, and blocker are inspectable | Fixture reports `not_available` and asks for a provider aggregate for the same normal-completion base cash-flow scope | Pass |

## Required fixed set and owner tasks

| Requirement or task | Expected | Actual | Disposition |
| --- | --- | --- | --- |
| Terminalen operational offer | Current comparison-ready offer | Not evaluated because the required complete refresh was rejected before Terminalen collection could publish | Blocked |
| Fleasing financial or flex offer with residual-value or third-party-buyer exposure | Current admitted offer | Missing: Fleasing designated source structure changed | Blocked |
| Important unknown or non-admission example | Current offer whose material fact state is visible | Not evaluated without the complete current dataset | Blocked |
| Find two constrained offers | Owner completes task | Not run | Blocked |
| Compare all four headline amounts | Owner completes task | Not run | Blocked |
| Explain risk, end mechanism, exposures, and unknowns | Owner completes task | Not run | Blocked |
| Audit facts, arithmetic, and sources | Owner completes task | Not run | Blocked |
| Mobile side-by-side comparison with pinned labels | Owner completes task | Not run; a current two-offer dataset is required | Blocked |

## Defect and next action

- `Fleasing designated detail source changed`: the collector detects the stale
  detail URL and stops rather than silently publishing a partial catalogue.
  Reassess the designated source only after confirming the provider permits the
  new route and it provides first-party evidence for the exact offer. Then run
  a fresh all-provider refresh and repeat this record with actual task results.

## Legal gate

The pre-transition validation result is recorded: the consumer-credit change
horizon is 20 November 2026 and post-transition revalidation remains pending.
This acceptance has no release approval, so no separate post-transition legal
decision is asserted.

## Owner-only sign-off

- Owner name: _not signed_
- Date: _not signed_
- Release decision: **not approved**
