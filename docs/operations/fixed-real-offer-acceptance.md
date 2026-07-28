# Fixed real-offer acceptance

This procedure is the release acceptance for the owner-operated comparison. It
uses a fresh complete catalogue dataset and a completed static artifact; a
fixture build is useful for regression checks but cannot substitute for this
acceptance.

Run the fixed-offer tasks only after a successful all-provider refresh. Always
create an acceptance record, including when refresh fails. Do not bypass a
designated source that has changed, a provider access boundary, or a source-wide
structural check to assemble a partial dataset. A listed detail page that lacks
the required private-offer sections is retained as a quarantined candidate, not
published as an offer. A failed refresh is an acceptance blocker: record the
provider, source URL, and the exact structural or access failure, then keep the
prior completed artifact active.

## Fixed offer set

Before opening the site, copy exact offer identities from the fresh dataset
into a new record under `docs/acceptance/`. The set must contain:

- one comparison-ready Terminalen operational offer;
- one admitted Fleasing financial or flex offer with residual-value or
  third-party-buyer exposure; and
- one offer that makes an important `not_stated`, `unclear`, `conflicting`, or
  non-admission fact visible.

Do not replace an unavailable required offer with a similar car or a fixture.
The record must say that the acceptance is blocked until a current designated
source supplies the missing set.

## Four owner tasks

At a representative desktop viewport and a 390 px-wide mobile viewport, the
owner performs and records these tasks:

1. Find two constrained offers using the catalogue filters.
2. Compare an operational offer with a financial or flex offer across all four
   headline amounts.
3. Explain each offer's residual-risk allocation, normal end mechanism,
   exposures, and unknown facts from the detail and comparison views.
4. Audit displayed facts and each derived amount against its evidence, source
   URL, and cash-flow arithmetic.

The mobile comparison must remain side by side in its horizontal comparison
region, with pinned row labels and no page-level horizontal overflow. Catalogue
rows may stack on mobile. Capture the exact viewport, routes or offer
identities, expected and actual results, and any defects for every task.

## Record and sign-off

The record is a version-controlled Markdown file. It must state the application
commit, dataset generation time, provider-control status, source checks,
viewports, selected identities, arithmetic checks, task results, defects and
their disposition, legal-gate result, and an explicit owner-only release
decision. A record without the owner's dated name and approval is not a passed
acceptance and does not authorize release.
