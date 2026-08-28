# Terminalen designated offer-source audit

Checked 24 August 2026 under
[ADR-0001](../adr/0001-public-provider-access.md).

## Designated source

- Catalogue: <https://www.terminalen.dk/nye-biler/hyundai>
- Model-price pages: exact first-party Hyundai `modelSubpage` paths discovered
  from the catalogue's bounded navigation state.
- Page API: the corresponding same-origin
  `/api/page/url?url=<exact-model-price-path>&culture=da-DK` response.

The adapter verifies that each API response identifies the exact requested path
and the `modelSubpage` template. It does not treat Terminalen's used-car inventory
or unrelated model pages as private-leasing offers. It retains normalized facts,
short source wording, source URLs, content hashes, retrieval time, and parser
version; fetched documents are not written to the active catalogue dataset.

## Applicability and normalization

- A matching `modelSubpage` discovered through the current bounded Hyundai
  navigation and still containing an explicit private-leasing block establishes
  current availability when the legacy `isCurrent` flag is absent. An explicit
  false or malformed flag is not overridden.
- `vehicleType: Personbil` establishes passenger-car scope directly. For the
  current IONIQ 5 source shape, `bodyType: SUV` is the replacement passenger-car
  classification when `vehicleType` is absent; other unstated body types are not
  generalized.
- Once the same block establishes private-consumer eligibility, unqualified
  advertised amounts are VAT-inclusive under
  [ADR-0002](../adr/0002-unqualified-private-prices-include-vat.md). Explicit
  excluding or contradictory VAT wording takes precedence and quarantines the
  candidate.

## Current arithmetic conflict

The 24 August 2026 audit confirmed the unchanged conflict first recorded on 29
July. The current source still exposes two admitted IONIQ 5 configurations,
but its stated provider aggregates do not reconcile with its other exact-offer
amounts:

- `49,995 + (2,795 × 36) + 1,000 = 151,615 DKK`, while the source advertises
  `151,395 DKK`;
- `14,995 + (3,995 × 36) + 1,000 = 159,815 DKK`, while the source advertises
  `159,595 DKK`.

The `1,000 DKK` inspection fee is explicitly stated as included in the
aggregate and collected with the last payment. The adapter therefore preserves
all first-party facts and the aggregate mismatch. The presentation retains the
reconstructed nominal base outlay and nominal monthly equivalent, shows the
provider aggregate separately, and warns that the `-220 DKK` difference is
unexplained rather than selecting one side as a correction for the other.

## Access decision

- Decision: **allowed**
- `robots.txt`: checked 24 August 2026; `User-agent: *` explicitly allows `/`.
- Published terms surfaces: the publicly discoverable privacy, cookie, and
  contact material contained no explicit prohibition on bounded automated
  collection or minimized factual reuse.
- Authentication or access control: the designated catalogue and `robots.txt`
  were publicly accessible without authentication during the check.
- Applicable restrictions: none found for the designated source.

The same-origin page API is an undocumented structured representation used by
Terminalen's public site. ADR-0001 allows that bounded use without affirmative
written permission. Stop on an applicable prohibition, authentication
requirement, bot challenge, persistent authorization denial, rate limit, or
provider instruction. Recheck this decision after a material source or terms
change, access failure, or provider contact.
