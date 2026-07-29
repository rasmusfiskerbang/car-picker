# Provider withdrawal

Use this procedure only after authenticating a withdrawal request against the
covered provider contact already on file.

1. Record the request and stop future retrieval immediately:

   ```sh
   uv run car-picker withdraw-provider \
     --provider Fleasing \
     --received-at 2026-07-28T10:00:00Z \
     --authentication-note "Authenticated against the provider contact on file."
   ```

   This atomically updates `config/provider-control.json`. Commit that change
   promptly. Do not put credentials, message contents, or provider offer data in
   the authentication note.

2. Run the complete refresh. The disabled provider is not contacted, and the
   replacement dataset contains no offers, quarantined candidates, evidence, or
   source metadata from it:

   ```sh
   uv run car-picker refresh-catalogue --dataset var/catalogue-dataset.json
   ```

3. Build the site separately:

   ```sh
   uv run car-picker build-site \
     --dataset var/catalogue-dataset.json \
     --output site
   ```

4. Inspect `config/provider-control.json`. The withdrawal record must contain
   `receivedAt`, `authenticationNote`, `retrievalDisabledAt`, `deadlineAt`,
   `refreshCompletedAt`, `siteBuildCompletedAt`, and `completedWithinDeadline`.
   A late build still removes the provider safely but exits unsuccessfully and
   records the missed 24-hour deadline. Commit the completed operational record.

The active dataset and site retain only the provider name and the time its
coverage ended. Never edit generated catalogue records or the completed static
artifact by hand.
