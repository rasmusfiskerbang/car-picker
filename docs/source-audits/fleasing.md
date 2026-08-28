# Fleasing designated offer-source audit

Originally checked 22 July 2026; access decision revalidated 24 August 2026 under
[ADR-0001](../adr/0001-public-provider-access.md).

## Designated source

- Catalogue: <https://fleasing.dk/biler/>
- Detail pages: the catalogue's same-site `/bil/?...&vid=<id>` links only.
- Supporting explanation: <https://fleasing.dk/flexleasing/>.
- The adapter uses the `vid` value as the provider source identity and an explicit
  private, VAT-inclusive configuration key as the source-local part of the offer
  identity.

The adapter does not call Bilinfo, FindLeasing, WordPress administration, an
undocumented API, or any third-party embedded source. It retains normalized facts,
short source wording, source URLs, content hashes, retrieval time, and parser
version; fetched documents are not written to the active catalogue dataset.

## Applicability and normalization

- The catalogue's own `Personbiler` navigation label applies passenger-car scope
  to the detail links enumerated from that exact catalogue page. A detail-level
  contradictory vehicle type takes precedence.
- The detail page's private-pricing tab and configuration-specific
  `privatleasing` wording establish private-consumer eligibility. The adapter
  does not treat an unlabelled gross amount alone as private eligibility.
- The supporting explanation explicitly calls the site's current inventory
  flexleasing cars, identifies flexleasing as financial leasing, states that the
  lessee is responsible for selling the car at the end unless buying it, and
  describes monthly proportional registration tax. Those facts apply only when
  a linked passenger-car detail contains the matching private configuration and
  an explicit residual value excluding VAT and registration tax. An explicit
  conflicting detail-level form or vehicle type is not overridden.
- Private-configuration payments explicitly state their VAT basis. If that
  wording later becomes unqualified, [ADR-0002](../adr/0002-unqualified-private-prices-include-vat.md)
  applies only after the same configuration has established private-consumer
  eligibility.

## Access decision

- Decision: **allowed**
- `robots.txt`: checked 24 August 2026; public paths remain permitted,
  `/wp-admin/` is disallowed, and `/wp-admin/admin-ajax.php` is allowed. The
  designated catalogue and detail paths are outside the disallowed boundary.
- Published terms surfaces: the public catalogue, footer, sitemap, privacy, and
  cookie material disclosed no explicit prohibition on bounded automated
  collection or minimized factual reuse.
- Authentication or access control: `robots.txt` and the designated source used
  by the owner refresh were publicly accessible without authentication during
  the check.
- Applicable restrictions: do not access WordPress administration.

ADR-0001 allows the bounded first-party source without affirmative written
permission because no applicable opt-out was found. Do not call Bilinfo,
FindLeasing, WordPress administration, or another third-party or unrelated
endpoint. Stop on an applicable prohibition, authentication requirement, bot
challenge, persistent authorization denial, rate limit, or provider instruction.
Recheck this decision after a material source or terms change, access failure, or
provider contact.
