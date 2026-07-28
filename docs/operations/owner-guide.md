# Owner operating guide

This is the canonical operating guide for the owner-only private-leasing
comparison. Run commands from the repository root with Python 3.14 or newer.
Generated catalogue data and static sites stay local and must never be committed.

## Verify a fresh checkout with fixtures

The committed hand-minimized fixture does not contact a provider. Use it to
verify the data contracts, automated checks, static build, and LAN server:

```sh
python3 -m car_picker validate \
  --dataset tests/fixtures/one-offer-catalogue-dataset.json \
  --repository .
python3 -m compileall -q car_picker tests
python3 -m unittest -v
python3 -m car_picker build-site \
  --dataset tests/fixtures/one-offer-catalogue-dataset.json \
  --output var/site
python3 -m car_picker serve-site --site var/site --port 4173
```

Open `http://127.0.0.1:4173/` on the owner computer. For another device on the
same LAN, open `http://<owner-computer-LAN-address>:4173/`. The server binds
`0.0.0.0`; stop it with Ctrl-C. It serves only the completed static artifact and
has no runtime application backend.

`validate` checks the canonical catalogue dataset, the minimized presentation
projection, the provider control, and every reachable Git-history path. It
fails if generated provider data such as `var/catalogue-dataset.json` or files
under a generated `site/` directory have entered history. It also enforces the
[dated consumer-credit release gate](consumer-credit-revalidation.md).

## Refresh, validate, build, and serve

Run collection and publication as separate operations:

```sh
python3 -m car_picker refresh-catalogue \
  --dataset var/catalogue-dataset.json
python3 -m car_picker validate \
  --dataset var/catalogue-dataset.json \
  --repository .
python3 -m car_picker build-site \
  --dataset var/catalogue-dataset.json \
  --output site
python3 -m car_picker serve-site --site site --port 4173
```

The refresh is the only operation that contacts covered providers. It collects
Fleasing first and Terminalen second into one catalogue dataset with one
generation timestamp. The separate build reads that completed dataset and replaces
the static artifact only after projection and artifact validation succeeds.

## Diagnose provider aggregate totals

Diagnose every catalogue offer:

```sh
python3 -m car_picker diagnose-aggregates \
  --dataset var/catalogue-dataset.json
```

Diagnose one exact offer identity:

```sh
python3 -m car_picker diagnose-aggregates \
  --dataset tests/fixtures/one-offer-catalogue-dataset.json \
  --offer 'terminalen:ioniq-5:essential-84'
```

For a live dataset, replace both paths with `var/catalogue-dataset.json` and an
exact identity copied from that dataset or a refresh warning. Diagnostics report
provider assertions, reconstructed cash-flow events, difference, tolerance,
recurrence, VAT basis, evidence references, and investigation prompts. A
mismatch suppresses the affected derived values; diagnostics do not edit the
dataset.

## Failure guarantees

- A provider retrieval, enumeration, or structural parsing failure rejects the
  complete replacement after at most two retries. The prior catalogue dataset
  remains byte-for-byte active; a partial or mixed-age dataset is never written.
- A schema, projection, browser-bundle, or artifact verification failure leaves
  the prior completed static artifact active.
- Full fetched provider documents exist only for the running refresh, in process
  memory. The active dataset retains normalized facts, short evidence wording,
  provenance, and hashes where applicable—not full fetched pages or a history of
  prior datasets.
- `var/`, every generated `site/` directory, and
  `catalogue-dataset.json` are ignored boundaries. Do not force-add them.

If `validate` reports generated paths in Git history, stop before sharing or
pushing the repository. Removing the current file is insufficient because the
validation scans all reachable commits; clean the accidental history, then run
validation again.

## Designated sources and access boundaries

Collection is deliberately bounded:

- Fleasing: `https://fleasing.dk/biler/` and only the linked first-party
  passenger-car detail pages.
- Terminalen: current Hyundai model price pages under
  `https://www.terminalen.dk/nye-biler/hyundai` and each page's corresponding
  same-path first-party API response.

Do not enrich an offer from third-party indexes, unlisted related pages, or a
document whose applicability to that exact offer is uncertain. Missing source
facts retain an explicit offer fact state.

Public access and a permissive `robots.txt` are not permission to reuse content.
Recheck the relevant provider terms and `robots.txt` after a retrieval failure,
a material source change, or provider contact. Stop collection when an explicit
access control, changed terms, or provider instruction blocks the designated
route; never bypass a login, bot challenge, rate limit, or other access control.
Review the current [Fleasing source audit](../source-audits/fleasing.md) before a
live refresh and apply the same checks to Terminalen's bounded sources.

## Provider withdrawal and routine maintenance

For an authenticated provider request, follow the
[provider withdrawal procedure](provider-withdrawal.md). It disables retrieval
before the next refresh, removes the provider's offers and evidence from the
replacement dataset and static artifact, and records the 24-hour deadline.

After changes to adapters, schemas, projection code, or operating configuration:

1. Update the hand-minimized fixture only with evidence needed by its test.
2. Run `validate`, the focused affected test file, and then the full automated
   checks before release.
3. Build from the validated catalogue dataset; never edit generated JSON or site
   files by hand.
4. Inspect refresh warnings and run aggregate diagnostics before serving or
   deploying the completed artifact.

Before a release, follow the [fixed real-offer acceptance
procedure](fixed-real-offer-acceptance.md). Its dated, version-controlled record
is required even when a changed designated source prevents the acceptance from
passing; in that case it must record the blocker and an explicit non-approval.

For every release, record the legal-gate result. Releases on or after 20
November 2026 require the completed, committed consumer-credit revalidation
described above.
