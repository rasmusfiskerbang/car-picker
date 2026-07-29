# Fleasing designated offer-source audit

Originally checked 22 July 2026; access decision revalidated 29 July 2026 under
[ADR-0001](../adr/0001-public-provider-access.md).

## Designated source

- Catalogue: <https://fleasing.dk/biler/>
- Detail pages: the catalogue's same-site `/bil/?...&vid=<id>` links only.
- The adapter uses the `vid` value as the provider source identity and an explicit
  private, VAT-inclusive configuration key as the source-local part of the offer
  identity.

The adapter does not call Bilinfo, FindLeasing, WordPress administration, an
undocumented API, or any third-party embedded source. It retains normalized facts,
short source wording, source URLs, content hashes, retrieval time, and parser
version; fetched documents are not written to the active catalogue dataset.

The checked detail shape provides a private, VAT-inclusive monthly payment and
term, but does not itself establish passenger-car scope or a supported leasing form.
The adapter therefore quarantines such candidates instead of inferring an active
catalogue offer from residual-value wording. Obtain an explicitly applicable
first-party source before changing that admission decision.

## Access decision

- Decision: **allowed**
- `robots.txt`: checked 29 July 2026; public paths remain permitted,
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
