# Terminalen designated offer-source audit

Checked 29 July 2026 under
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

## Access decision

- Decision: **allowed**
- `robots.txt`: checked 29 July 2026; `User-agent: *` explicitly allows `/`.
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
