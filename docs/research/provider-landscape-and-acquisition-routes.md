# Provider landscape and acquisition routes

Research date: 2026-07-20

## Decision-grade answer

Use FindLeasing as a **candidate-provider index, not as an offer-data source or a coverage oracle**. Its current directory is broad, but its private-customer classification contains at least one demonstrable false positive, and its public JSON endpoints are undocumented, covered by an explicit copyright notice, and accompanied by robots rules that disallow the listing-query path. A provider becomes a **covered provider** only after its own site confirms that it publishes private passenger-car leasing offers and a source audit records an `allowed` access decision, provenance, and freshness under [ADR-0001](../adr/0001-public-provider-access.md).

Start the MVP with three first-party source archetypes rather than attempting all directory members:

1. **Clevr Car** for server-rendered financial/flex-leasing offers whose detail pages disclose private cash-flow terms and fees.
2. **Fleasing** for server-rendered financial/flex-leasing offers with private and business examples on each detail page.
3. **Terminalen's model-specific new-car pages** for operational private leasing with total contractual payment and included/excluded items.

This pilot spans both financial and operational leasing and exercises three materially different page shapes. Add Kvalitetsbiler only after access is independently allowed for the FindLeasing calculator embedded in its otherwise first-party catalogue. Approach Bertelsen Leasing for a feed or another route it explicitly allows because its technical access barrier blocks automated collection. Audit the remaining candidates in descending offer volume, but never infer private eligibility solely from FindLeasing.

## What FindLeasing currently shows

The [FindLeasing provider directory](https://www.findleasing.nu/forhandler/) says it covers both private and business leasing and exposes financial, operational, and monthly-rental filters. Its page is backed by an unauthenticated [dealer JSON endpoint](https://backend.findleasing.nu/api/v2/dealers/?page=1&page_size=20) and an unauthenticated [listing JSON endpoint](https://backend.findleasing.nu/api/v2/listings/?ownership=0&page=1&page_size=100).

A snapshot of those endpoints on 2026-07-20 produced:

- 128 directory records; 99 had a non-zero active-listing count.
- 4,495 listings returned by the site's private-customer filter, from 98 provider records. The one active directory member absent from that result was Kleemann.
- 3,328 financial and 1,167 operational listings.
- 4,217 records were marked for both private and business use, while only 278 were marked private-only. The site's own JavaScript maps the private toggle to `ownership=0`; the API includes records marked `ownership=2` in that result.
- 2,702 of the 4,495 records had no bodywork value and 122 were explicitly `Varebil`, so the result cannot by itself establish private passenger-car coverage.
- Contract-field completeness was uneven: all records had monthly payment and upfront payment, but 1,167 had no residual value, 2,636 had no total-cost value, and 2,075 had no included-kilometre value. Each record did have a publication timestamp and a FindLeasing URL.

The largest candidate publishers in that snapshot were:

| FindLeasing directory name | Private-filter records | Financial | Operational |
| --- | ---: | ---: | ---: |
| Bertelsen Leasing ApS | 634 | 634 | 0 |
| Bayern Autogroup A/S | 460 | 230 | 230 |
| Tørring Auto A/S (Kvalitetsbiler) | 284 | 0 | 284 |
| Clevr Car Leasing | 259 | 259 | 0 |
| Terminalen | 255 | 0 | 255 |
| Fleasing | 153 | 153 | 0 |
| Dansk Bilimport | 140 | 139 | 1 |
| Dit Autocenter ApS | 134 | 67 | 67 |
| TS Motors ApS | 130 | 130 | 0 |
| Agilease A/S | 102 | 28 | 74 |
| AROS LEASING A/S | 97 | 94 | 3 |
| Lokal Leasing A/S (two directory records combined) | 87 | 0 | 87 |
| Allan Hansen Automobiler | 71 | 36 | 35 |
| MB Group | 65 | 65 | 0 |
| City Leasing ApS | 55 | 55 | 0 |

The top five account for 1,892 records (42.1% of the private-filter snapshot), while the top fifteen account for 2,926 (65.1%). Volume-first audits therefore buy meaningful coverage quickly, but volume is not evidence of eligibility.

### Why the directory is not authoritative

FindLeasing returned 102 Agilease records under its private filter, but Agilease's own car pages describe the offers as tailored to a company and display prices excluding VAT. For example, its [BMW iX3 offer](https://agilease.dk/biler/bmw-ix3-impressive-c9b5f686) says the operational lease is for a company, and its [financial-leasing overview](https://agilease.dk/finansiel-leasing) likewise frames the product as company-car leasing. Agilease must therefore be treated as business-only unless a first-party private offer is found. This one mismatch is enough to reject automatic eligibility based on the aggregator flag.

FindLeasing is also not a safe default acquisition source. Its [robots file](https://backend.findleasing.nu/robots.txt) disallows `/listings?` and blocks several automated agents, while its site footer says all rights are reserved and its [privacy page](https://www.findleasing.nu/privacy-policy/) refers to enforceable service terms. These observations do not decide the legal position, but they do create a permission gate: do not ingest or republish the JSON listing corpus without written authorization from FindLeasing.

## Audited first-party source archetypes

### Clevr Car: complete server-rendered offer pages

Clevr Car's [catalogue](https://clevrcar.dk/leasing-biler/) exposes private/business and passenger-car/van controls and reported 910 vehicles when inspected. The catalogue and paginated result pages are server-rendered HTML. Individual vehicle pages carry the comparison-critical terms directly in HTML: a representative [BMW i4 offer](https://clevrcar.dk/vehicle/2022-bmw-i4-m50-gran-coupe-m-sport-44656/) states a 12-month private upfront payment, monthly payment, residual value and startup fees, alongside a warning that the car may be sold and that errors or changes are possible.

**Acquisition route:** enumerate catalogue pagination, follow stable `/vehicle/.../<id>/` URLs, and parse only explicitly labelled private passenger-car terms. Store the provider's vehicle id and the source URL as identity inputs.

**Constraints and freshness:** command-line requests encountered the provider's web-application firewall even though normal rendered access worked. That technical access control blocks automated collection unless Clevr Car supplies an allowed route. There is no observed source update timestamp. On an allowed route, collect slowly, use conditional requests where available, and mark an offer stale from retrieval time rather than inventing a provider timestamp.

**Fit:** strong pilot source for financial/flex leasing because complete private cash flows and mandatory fees are visible without depending on an aggregator widget.

### Fleasing: full catalogue and terms in server HTML

Fleasing's [car catalogue](https://fleasing.dk/biler/) is server-rendered WordPress HTML. Vehicle URLs use a `vid` identity and image URLs reveal Bilinfo as the upstream inventory system. A representative [Aston Martin DB9 offer](https://fleasing.dk/bil/?aston-martin-db9-volante-aut&vid=442795427) publishes separate business and private examples, including term, upfront payment, monthly payment, and residual value; the page also warns that errors are possible.

**Acquisition route:** parse the catalogue for `vid` URLs, then parse the first-party detail HTML. Do not call or copy from Bilinfo unless Fleasing or Bilinfo grants that separately; the first-party page is sufficient for the MVP fields observed here.

**Constraints and freshness:** the [robots file](https://fleasing.dk/robots.txt) allows public paths while excluding WordPress administration. Under ADR-0001 the missing affirmative reuse licence is not an opt-out; the designated public first-party paths are allowed while the administration boundary is not. No per-offer update timestamp was observed. Use retrieval time, content hashes, removal detection, and minimized evidence.

**Fit:** strong pilot source for financial/flex leasing and useful for testing separation of private and business VAT treatments.

### Terminalen: model-page offers are usable; the generic inventory is not equivalent

Terminalen publishes complete operational private-leasing examples on first-party model pages. Its [Hyundai IONIQ 5 price page](https://www.terminalen.dk/nye-biler/hyundai/hyundai-ioniq-5/pris-og-udstyr) gives two payment profiles, a 36-month term, total payment, 10,000 km/year, included service and inspection fee, exclusions, credit requirement, and leasing partner. The matching [page JSON endpoint](https://www.terminalen.dk/api/page/url?url=/nye-biler/hyundai/hyundai-ioniq-5/pris-og-udstyr) supplies `createDate` and `updateDate` provenance; it reported an update on 2026-06-01 when inspected.

Terminalen and Bayern AutoGroup also expose the same NCG-style [product inventory endpoint](https://www.terminalen.dk/api/product/filter?from=0&take=1&culture=da-DK&productType=Cars). The endpoint reported 745 used cars but only eight with `isleasing=true`, even though FindLeasing attributed 255 operational records to Terminalen and 460 financial/operational records to Bayern AutoGroup. The first-party generic inventory therefore does not reproduce the aggregator's offer set and must not be converted into leasing offers merely because the cars could potentially be leased.

**Acquisition route:** discover model price pages from first-party navigation/sitemaps, fetch their page JSON for structure and provenance, and retain only pages with explicit private-leasing terms. Treat the used-car product endpoint as vehicle inventory, not leasing-offer inventory.

**Constraints and freshness:** the [robots file](https://www.terminalen.dk/robots.txt) allows public paths. The undocumented same-origin page API is used by the public site and is allowed under ADR-0001 only as an exact, bounded representation of its model-price page. Preserve both the page's human-facing validity text and API `updateDate`; a recent CMS edit does not prove that an older stated effective date is still commercially valid.

**Fit:** strong operational-leasing pilot source and a necessary test for fee/inclusion modelling.

### Kvalitetsbiler: good first-party vehicle API, third-party contract terms

Kvalitetsbiler says every leasable car has a dynamic calculator and describes its private product as having no lessee residual-value exposure on its [private-leasing page](https://www.kvalitetsbiler.dk/leasing/privatleasing/). Its public [car API](https://www.kvalitetsbiler.dk/umbraco/api/carsapi/getcars?take=2) returned vehicle ids, source creation dates, price history, vehicle facts, and summary leasing-price fields. However, individual vehicle pages load `https://www.findleasing.nu/static/javascript/embed-sliders.js` and identify the calculator with a FindLeasing offer id; the detailed adjustable contract terms are rendered from a FindLeasing iframe rather than the first-party car API.

**Acquisition route:** the first-party API is suitable for vehicle identity, facts, price provenance and change detection. Complete leasing terms require either a provider-supplied source, an independently allowed FindLeasing source, or manual/static entry supplied by Kvalitetsbiler.

**Constraints and freshness:** the [robots file](https://www.kvalitetsbiler.dk/robots.txt) advertises a sitemap and does not disallow the first-party catalogue. That does not authorize calls to the separate FindLeasing endpoint, whose applicable robots rule blocks the listing route. Do not combine the allowed first-party vehicle API with the blocked third-party listing API.

**Fit:** defer as a covered provider until the access and data-source gap is closed; otherwise the MVP cannot produce trustworthy cash flows for its offers.

### Bertelsen Leasing: large, fast-changing catalogue behind an access barrier

Bertelsen's [private-leasing page](https://bertelsenleasing.dk/privatleasing/) confirms private flexleasing, while its [catalogue page](https://bertelsenleasing.dk/bilkatalog/) says it adds 10–20 European vehicles daily. FindLeasing attributed 634 financial records to it, the largest candidate set in the snapshot. Direct automated requests encountered a security block, so no stable first-party machine route was validated.

**Acquisition route:** ask Bertelsen for an allowed catalogue feed/API route. Its technical access barrier blocks the observed automated route, and its stated daily churn makes manual HTML reverse-engineering a fragile first step.

**Fit:** high-value second-wave provider, but not an MVP source until access and offer-term provenance are agreed.

## Required acquisition contract for every covered provider

An adapter is eligible for production only when its source audit records all of the following:

- **Scope evidence:** first-party proof that the specific offer is for a prospective lessee and a passenger car; never infer this from a provider-level marketing page or aggregator flag.
- **Access decision:** source owner, exact first-party boundary, last policy check, applicable robots result and terms, restrictions, and contact/decision log. Public first-party facts are allowed unless an applicable rule, term, access control, rate limit, or provider instruction explicitly prohibits the bounded use.
- **Identity:** provider id, provider offer/vehicle id, canonical source URL, and a deterministic source-specific key. Similar cars are not deduplicated into one leasing offer.
- **Provenance:** retrieval timestamp, any provider publication/update/effective dates, raw response hash, parser version, and exact source fields used for each normalized value.
- **Freshness:** low-frequency scheduled retrieval (initially once daily), conditional requests where supported, immediate expiry when a provider states an offer end date, and a visible stale state after 48 hours without a successful refresh. Remove from active results after two consecutive confirmed source absences; retain provenance for audit.
- **Completeness:** upfront payment, recurring payment, term, customer/VAT treatment, mandatory fees, mileage, residual-value obligation, inclusions/exclusions, and conditional costs are each either sourced or explicitly unknown. Never fill missing contract terms from a different offer or from generic provider copy.
- **Change safety:** parser fixtures for representative pages, schema/selector failure alarms, record-count anomaly checks, and quarantine rather than publication when required fields change shape.
- **Content minimization:** store normalized facts and short evidence snippets, link to the original offer, and avoid republishing full descriptions or images unless separately permitted.

Run acquisition as an offline build step that emits versioned static JSON for the frontend. A static GitHub Pages deployment can then display the last successful snapshot without making cross-origin provider calls from users' browsers. If scheduled acquisition, retained evidence, or access controls outgrow CI, move only the collector/storage component to a VPS; this research found no need for a server-rendered public frontend.

## Staged provider audit

1. Record source audits for Clevr Car, Fleasing, and Terminalen under ADR-0001. Use only providers with an `allowed` decision; a feed remains preferable when offered but is not required when the bounded public first-party source has no applicable opt-out.
2. Build throwaway extraction fixtures for one active and one removed offer from each pilot source. Verify field lineage and disappearance behaviour before calling any provider covered.
3. Contact Kvalitetsbiler and Bertelsen in parallel for feed access. Kvalitetsbiler's blocker is contract-term ownership; Bertelsen's is automated access and high churn.
4. Audit the remaining FindLeasing candidates by descending private-filter volume. For each, first prove private passenger-car scope, then classify its route as documented feed, first-party JSON, first-party HTML, third-party embed, or manual-only.
5. Publish a coverage statement listing only audited covered providers, last successful refresh per provider, and excluded/blocked providers with the reason. Do not state a percentage of the Danish market until the denominator has an independently defensible definition.

## Uncertainties that remain

- The FindLeasing endpoints are undocumented; counts and field semantics were observed, not guaranteed.
- This bounded audit did not verify all 98 private-filter provider records against first-party sites. The staged audit is part of making each provider covered, not post-launch cleanup.
- This research did not establish every provider's current access decision. Robots observations are technical signals, not legal advice; each covered provider still needs the bounded terms, access-control, and robots review required by ADR-0001.
- FindLeasing's 4,495 records include non-passenger inventory and records marked for both private and business use, so the true private passenger-car offer count is lower and presently unknown.
