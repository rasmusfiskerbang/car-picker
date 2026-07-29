# Fleasing designated offer-source audit

Checked 22 July 2026 for the first bounded collection implementation.

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

## Access check

The checked <https://fleasing.dk/robots.txt> permits public paths and disallows
`/wp-admin/` except `admin-ajax.php`. The designated catalogue and detail paths are
therefore not disallowed by the current robots file.

The current catalogue footer and sitemap were checked alongside the robots file.
They link Fleasing's <https://fleasing.dk/privatlivspolitik/>, but no public
commercial or content-reuse terms page was linked. The commonly named
<https://fleasing.dk/handelsbetingelser/> path also returned 404 when checked.
No public reuse permission was found. Public access and a permissive robots file
are not permission to redistribute provider content: obtain and record written
permission or a documented feed agreement before running a production refresh.

Recheck the robots file and relevant terms on a retrieval failure, material source
change, or provider contact. Do not bypass an explicit access control; stop the
source and record the boundary instead.
