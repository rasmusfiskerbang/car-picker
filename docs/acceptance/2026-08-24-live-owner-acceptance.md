# Live owner acceptance — 24 August 2026

This is the dated owner gate for issue #86. The application commit, live
Dataset, static Site, and browser evidence below describe the same public
clean-room path. The acceptance record itself is version-controlled; generated
Dataset and Site files remain under the ignored `var/` boundary.

## Release decision

**Approved by the owner for the 2026-08-24 pre-transition gate.** This is a
bounded owner acceptance of the current live Dataset and Site. It is not a
post-transition consumer-credit legal approval; that conditional gate remains
pending until the date recorded below.

## Application, Dataset, and environments

- Application commit: `251f459c8b42c5250273dd1b1d443bc193ad9234`
- Dataset generation: `2026-08-24T07:16:31Z`
- Dataset SHA-256: `2230ded65e5d72c0ce7a687647bebf5c75e77907dcff5d817bcbae689ad34276`
- Provider counts: Fleasing 17; Terminalen 2
- Catalogue Offers: 19
- Quarantined Candidates: 138 (Fleasing 138; Terminalen 0)
- Provider Registry: Fleasing and Terminalen active; both current source
  audits record `allowed` and were checked on `2026-08-24`.
- Environment: Darwin 23.6.0 x86_64; Python 3.14.6; uv 0.11.29;
  Node v26.5.0; frontend package manager pnpm 11.9.0; Playwright Chromium
  installed by the locked frontend command.
- Owner-recorded desktop viewport: 1280 × 720 (historical owner evidence)
- Correction replay desktop viewport: 1440 × 900
- Mobile viewport: 390 × 844

## Source audits before live collection

The current source audits were confirmed before the live refresh:

- [Fleasing source audit](../source-audits/fleasing.md) — catalogue
  `https://fleasing.dk/biler/`, current detail URL shape
  `https://fleasing.dk/bil/?...&vid=...`, and supporting flexleasing page;
  public access remained allowed.
- [Terminalen source audit](../source-audits/terminalen.md) — Hyundai
  catalogue `https://www.terminalen.dk/nye-biler/hyundai`, exact model-price
  page paths, and same-origin page API; public access remained allowed.
- The source audits and ADR-0001 were dated `2026-08-24` before collection.
  No login, credential, robots-disallowed path, or third-party source was used.

The exact pre-refresh source checks and results were:

```text
curl --fail --silent --show-error --location --write-out '%{http_code} %{size_download}\n' --output /dev/null https://fleasing.dk/robots.txt
200 115
curl --fail --silent --show-error --location --write-out '%{http_code} %{size_download}\n' --output /dev/null https://fleasing.dk/biler/
200 283907
curl --fail --silent --show-error --location --write-out '%{http_code} %{size_download}\n' --output /dev/null https://fleasing.dk/flexleasing/
200 162844
curl --fail --silent --show-error --location --write-out '%{http_code} %{size_download}\n' --output /dev/null https://www.terminalen.dk/robots.txt
200 69
curl --fail --silent --show-error --location --write-out '%{http_code} %{size_download}\n' --output /dev/null https://www.terminalen.dk/nye-biler/hyundai
200 281324
curl --fail --silent --show-error --location --write-out '%{http_code} %{size_download}\n' --output /dev/null https://www.terminalen.dk/cookies
200 171067
curl --fail --silent --show-error --location --write-out '%{http_code} %{size_download}\n' --output /dev/null https://www.terminalen.dk/privatlivspolitik
200 247323
```

The robots results were also read directly:

```text
# https://fleasing.dk/robots.txt
User-agent: *
Disallow: /wp-admin/
Allow: /wp-admin/admin-ajax.php

Sitemap: https://fleasing.dk/sitemap_index.xml

# https://www.terminalen.dk/robots.txt
User-agent: *
Allow: /
Sitemap: https://www.terminalen.dk/sitemap.xml
```

## Complete live refresh

The first live attempt exposed a real current-source parser defect rather than
an access failure:

```text
uv run --locked car-picker --workspace . --json catalogue refresh
{"catalogueOfferCount":2,"generatedAt":"2026-08-24T06:47:00Z","kind":"catalogue-refresh","providerIds":["fleasing","terminalen"],"quarantinedCandidateCount":155}
```

The 155 quarantined Fleasing candidates included the current DB9 detail with
`candidate-shape.vehicle-kind-unknown`; the source HTML had moved the fuel
fact into `div.vehicle-page-short-specs`. The first narrow parser update used
`fleasing-html-v6`, with a public adapter regression fixture and test. The
final application correction also preserves the exact source wording as
`fleasing-html-v7`. No candidate was manually admitted.

After that fix, one complete live refresh was run against both audited
providers:

```text
uv run --locked car-picker --workspace . --json catalogue refresh
{
  "catalogueOfferCount": 19,
  "generatedAt": "2026-08-24T07:16:31Z",
  "kind": "catalogue-refresh",
  "providerIds": [
    "fleasing",
    "terminalen"
  ],
  "quarantinedCandidateCount": 138
}
```

The final result admits the required roles: 17 Fleasing financial offers and
two Terminalen operational offers. The fixed live identities were:

| Role | Exact Offer Identity | Canonical source | Selected facts |
| --- | --- | --- | --- |
| Fleasing financial | `fleasing:442795427:private-8f745634e8cf` | `https://fleasing.dk/bil/?aston-martin-db9-volante-aut&vid=442795427` | Aston Martin DB9 Volante aut.; 12 months; 15,865 DKK/month; 142,813 DKK upfront; residual-risk allocation unclear; third-party buyer at normal end |
| Terminalen operational | `terminalen:HY_IONIQ5_NE_DK_IONIQ5_MY27:private-e25cc77f6e4b` | `https://www.terminalen.dk/nye-biler/hyundai/hyundai-ioniq-5/pris-og-udstyr` | Hyundai IONIQ 5; 36 months; 10,000 km/year; 2,795 DKK/month; 49,995 DKK upfront; return to provider; provider bears residual risk |
| Important unknown | `fleasing:771869804:private-e4d3ad141ff6` | `https://fleasing.dk/bil/?aston-martin-db11-v8-volante-aut&vid=771869804` | Aston Martin DB11 V8 Volante aut.; 12 months; 16,755 DKK/month; 173,750 DKK upfront; residual-risk allocation remains unclear |

## Independent source and arithmetic spot-checks

The live source pages were independently checked after the audit and before
the owner journeys:

```text
curl --fail --silent --show-error --location 'https://fleasing.dk/bil/?aston-martin-db9-volante-aut&vid=442795427' | rg -o -m 12 'Aston Martin DB9|Brændstof:</b> Benzin|15[.]865 kr[.]|142[.]813 kr[.]|12 måneders privatleasing|Restværdi kr[.] 624[.]750'
Aston Martin DB9
Brændstof:</b> Benzin
15.865 kr.
142.813 kr.
Aston Martin DB9
Restværdi kr. 624.750
12 måneders privatleasing

curl --fail --silent --show-error --location 'https://www.terminalen.dk/nye-biler/hyundai/hyundai-ioniq-5/pris-og-udstyr' | rg -o -m 12 '2[.]795 kr[.]?/md[.]?|49[.]995 kr[.]|151[.]395 kr[.]|1[.]000 kr[.]|36 mdr[.]|10[.]000 km'
2.795 kr./md.
49.995 kr.
36 mdr.
151.395 kr.
10.000 km
1.000 kr.
```

The independently recomputed cash flows were:

- Fleasing DB9: `142,813 + (15,865 × 12) = 333,193 DKK`; then
  `333,193 ÷ 12 = 27,766.08 DKK`.
- Terminalen IONIQ 5: `49,995 + (2,795 × 36) + 1,000 = 151,615 DKK`.
  The source advertises `151,395 DKK`, so the source-versus-reconstruction
  difference is `220 DKK`; neither amount was silently substituted for the
  other. The month-36 1,000 DKK event remains visible in the cash-flow stream.

The final live Dataset SHA-256 was checked after refresh and matched the Site
copy:

```text
shasum -a 256 var/catalogue-dataset.json var/site/catalogue-dataset.json
2230ded65e5d72c0ce7a687647bebf5c75e77907dcff5d817bcbae689ad34276  var/catalogue-dataset.json
2230ded65e5d72c0ce7a687647bebf5c75e77907dcff5d817bcbae689ad34276  var/site/catalogue-dataset.json
```

## Site build, serve, and failure preservation

The final Site was built from the final live Dataset and served from the
approved static artifact seam:

```text
uv run --locked car-picker --workspace . site build
exit 0

uv run --locked car-picker --workspace . site inspect
Catalogue Site: /Users/rasmusfiskerbang/.codex/worktrees/issue86-20260824/car-picker/var/site
Generated at: 2026-08-24T07:16:31Z
Catalogue Offers: 19
Quarantined Candidates: 138

uv run --locked car-picker --workspace . site serve --port 4173
Serving completed static artifact on http://0.0.0.0:4173/
```

The served artifact loaded at `http://127.0.0.1:4173/`, reported 19 offers, and
served the same Dataset SHA shown above. Expected failure preservation was
rehearsed:

```text
uv run --locked pytest tests/test_catalogue_refresh_fail_closed.py tests/test_build_site.py tests/test_static_artifact.py -q
29 passed, 3 subtests passed in 157.07s (0:02:37)
```

The rehearsal covers failed refresh/build inputs, failed frontend generation,
and serve safety while preserving the previous safe artifact.

## #87 required viewport replay

The signed owner journey below remains truthful historical evidence at
1280 × 720; it is not relabeled as 1440 × 900. The #87 correction replay
uses the required #67 judgment viewport and the required mobile viewport on
the completed static Site. This is automated browser evidence, not a new owner
sign-off or a replacement for the accepted live Dataset gate:

```text
Working directory: <fresh or current checkout>/frontend
Command: pnpm test:e2e
Result: 59 passed; desktop projects use 1440 × 900 and mobile projects use 390 × 844
```

The owner sign-off above therefore remains historical pre-transition evidence;
the current correction record does not claim a second human sign-off.

## Owner journeys and defect dispositions

The live Site was exercised manually at the owner-recorded 1280 × 720 desktop
viewport and the 390 × 844 mobile viewport. The required 1440 × 900 desktop
viewport is covered by the automated correction replay above.

| Journey | Owner-recorded desktop 1280 × 720 | Mobile 390 × 844 | Disposition |
| --- | --- | --- | --- |
| Find constrained offers | Operationel + `IONIQ 5` returned 2 Terminalen offers; Finansiel + `DB9` returned 1 Fleasing offer; exact selected identities were retained in URL state | Filter sheet opened, returned the same 2/1 counts, and selected the same DB9 and IONIQ 5 identities | Pass |
| Compare headline amounts | Comparison retained both columns with advertised, calculated, monthly-average, and upfront rows; page horizontal overflow was false | Same facts were readable through the internal comparison scroller; page overflow was false, region `372px` wide with `672px` internal table | Pass |
| Explain risk, end, exposure, and unknowns | DB9 showed third-party-buyer end and unclear residual risk; IONIQ 5 showed return-to-provider and provider residual risk | Both detail routes retained the same contract facts and unknown states | Pass |
| Audit sources and cash flow | Source regions exposed the exact Fleasing and Terminalen URLs; cash-flow values matched the independent arithmetic | Source regions, cash-flow sections, and month/event facts remained available without page overflow | Pass |

Observed owner-journey desktop dimensions were `1280 × 720`; observed mobile
dimensions were `390 × 844`. The correction replay above covers the required
`1440 × 900` desktop judgment viewport. The final live run also confirmed the
comparison table had internal horizontal scrolling only on mobile and no
document-level horizontal overflow at either viewport.

Defects and dispositions:

- **Fleasing current detail markup:** the first live refresh quarantined
  current Fleasing candidates because fuel was nested in
  `vehicle-page-short-specs`. Disposition: fixed narrowly in the application
  commit named above, covered by `test_collects_vehicle_fuel_from_the_current_short_specs_shape`,
  and verified by the final 17 admitted Fleasing offers.
- **Terminalen advertised aggregate differs by 220 DKK:** the source total
  (`151,395`) and reconstructed total (`151,615`) are both retained and
  independently visible; the 1,000 DKK month-36 event is not invented or
  dropped. Disposition: accepted as an explicitly recorded source discrepancy
  for this owner gate, with no derived value presented as the provider's
  advertised total. It is a follow-up product-policy item if a future release
  requires a dedicated warning treatment.
- **Residual-value and vehicle facts marked unknown/not stated:** DB9/DB11
  residual-risk allocation and Terminalen vehicle details remain visibly
  unknown where the source does not establish them. Disposition: expected,
  factual, and accepted; no value was fabricated.
- **Layout or navigation defects:** none observed in the representative
  desktop/mobile journeys; page-level overflow checks were false and source
  navigation remained available.

## Verification matrix

The locked matrix was run after the application commit and the frontend
fixture runs were kept outside the final live artifact. Results:

| Command | Result |
| --- | --- |
| `uv sync --locked --dev` | Resolved 21 packages; checked 20 |
| `uv run --locked ruff format --check .` | 109 files already formatted |
| `uv run --locked ruff check .` | All checks passed |
| `uv run --locked ty check car_picker tests` | All checks passed |
| `uv run --locked pytest tests/test_fleasing_adapter.py tests/test_acceptance_record.py -q` | 15 passed, 2 subtests passed |
| `uv run --locked pytest` | 164 passed |
| `uv run --locked pytest tests/test_fleasing_adapter.py tests/test_collection.py tests/test_production_composition.py -q` | 43 passed, 7 subtests passed |
| `uv run --locked pytest tests/test_catalogue_refresh_contracts.py tests/test_catalogue_contract.py -q` | Included in the full suite; passed |
| `uv run --locked pytest tests/test_clean_room_cutover.py tests/test_cutover_corrections.py -q` | Included in the full suite; passed |
| `cd frontend && pnpm install --frozen-lockfile` | Already up to date; pnpm 11.9.0 in the frontend workspace |
| `cd frontend && pnpm generate-contract` | Completed |
| `cd frontend && pnpm generate-routes` | Completed |
| `cd frontend && pnpm typecheck` | Completed |
| `cd frontend && pnpm test:module` | 4 passed |
| `cd frontend && pnpm build` | Vite build completed; 1,827 modules transformed |
| `cd frontend && pnpm exec playwright install chromium` | Completed |
| `cd frontend && pnpm test:e2e` | 59 passed |
| `uv run --locked car-picker --workspace . site build` | Exit 0 from final live Dataset |
| `uv run --locked car-picker --workspace . site inspect` | 19 offers; 138 quarantined; generation `2026-08-24T07:16:31Z` |
| `uv run --locked car-picker history-check --repository .` | Repository history check passed |
| `uv run --locked car-picker legal-check --repository .` | Pre-transition gate reported; post-transition revalidation pending |

The full Python-suite result after the source-wording correction is 164 passed.
The acceptance-record test is intentionally narrow and verifies the required
identifiers, counts, commands, legal horizon, and dated sign-off.

## Legal gate

The current date is `2026-08-24`, before the configured consumer-credit change
horizon of `2026-11-20`. The exact repository gate result was:

```text
uv run --locked car-picker legal-check --repository .
Legal gate: change horizon 2026-11-20; post-transition revalidation is pending.
```

`config/consumer-credit-legal-review.json` remains at
`"revalidation": null`. No current-law or guidance revalidation was claimed
before the date gate, and no post-transition changes were required in this
acceptance pass. Revalidate official consumer-credit law and guidance, apply
resulting changes, and obtain a new owner sign-off on or after `2026-11-20`.

## Owner-only sign-off

- Owner name: Rasmus Fisker Bang
- Signed on: 2026-08-24
- Decision: approved for this pre-transition live owner acceptance gate
