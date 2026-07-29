# Consumer-credit release revalidation

The owner must not release the comparison on or after 20 November 2026 using
legal assumptions that have not been revalidated against then-current official
law and guidance.

The version-controlled record is
`config/consumer-credit-legal-review.json`. Before the change horizon it
deliberately contains:

```json
{
  "schemaVersion": "consumer-credit-legal-review/v1",
  "changeHorizon": "2026-11-20",
  "revalidation": null
}
```

`null` means the post-transition review has not happened. Do not fill it before
20 November 2026 and do not treat current research as a prediction of the rules
that will then apply.

## Release validation

The normal owner validation includes the legal gate:

```sh
uv run car-picker validate \
  --dataset var/catalogue-dataset.json \
  --repository .
```

It evaluates today's date by default. A future planned release can be checked
only when that date arrives; there is no date override that can backdate the
gate. Before the horizon, validation reports the dated horizon and pending
review. On or after the horizon, validation fails until the completed record is
committed without local changes.

## Complete the review on or after the horizon

At review time:

1. Find the then-current official statutory text governing consumer-credit
   classification and then-current official regulatory guidance governing
   disclosures. Do not rely on this repository's pre-transition research,
   search snippets, third-party summaries, or an undated saved copy.
2. Record at least one `official_law` source and one `official_guidance` source.
   For each, capture its title, publishing authority, HTTPS URL, date checked,
   effective-from date, and effective-to date when one exists.
3. Record separate conclusions for consumer-credit classification and
   disclosure rules. State the implementation impact explicitly, including
   “no application change required” only when the reviewed sources support that
   conclusion.
4. Implement and test any required application or operating changes. The legal
   record never silently changes how catalogue offers are classified or shown.
5. Add the dated owner sign-off, commit the code and record together, then rerun
   `validate`.

Replace `revalidation: null` with this shape, using conclusions and sources from
the actual review rather than the illustrative text:

```json
{
  "reviewedOn": "2026-11-20",
  "sources": [
    {
      "kind": "official_law",
      "title": "Then-current official statutory title",
      "publisher": "Publishing authority",
      "url": "https://official-source.example/law",
      "checkedOn": "2026-11-20",
      "effectiveFrom": "2026-11-20",
      "effectiveTo": null
    },
    {
      "kind": "official_guidance",
      "title": "Then-current official guidance title",
      "publisher": "Publishing authority",
      "url": "https://official-source.example/guidance",
      "checkedOn": "2026-11-20",
      "effectiveFrom": "2026-11-20",
      "effectiveTo": null
    }
  ],
  "consumerCreditClassificationConclusion": "Review conclusion with its scope.",
  "disclosureRulesConclusion": "Review conclusion with its scope.",
  "implementationImpact": "Required code, data, copy, test, and operating changes.",
  "ownerSignOff": {
    "name": "Owner name",
    "signedOn": "2026-11-20"
  }
}
```

Validation rejects missing or extra fields, non-HTTPS source URLs, missing law
or guidance coverage, checks dated before the horizon or after review, sources
whose effective interval does not include the review date, a review dated before
the horizon, and sign-off before review or after release. If the official
position remains unclear, do not sign off or release.
