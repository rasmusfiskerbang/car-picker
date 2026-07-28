# Car picker

The production tracer bullet builds a static Danish catalogue from a
schema-versioned canonical catalogue dataset:

```sh
python3 -m car_picker refresh-catalogue --dataset var/catalogue-dataset.json
python3 -m car_picker build-site --dataset var/catalogue-dataset.json --output site
python3 -m car_picker serve-site --site site --port 4173
```

`var/` and `site/` are generated local outputs and are intentionally ignored by Git.
The browser validates `projection.json` at startup before it renders any offer facts.
`build-site` exports and verifies the completed artifact atomically; `serve-site` binds it on
`0.0.0.0` for local-network acceptance and uses hash routing, so the same artifact works on
GitHub Pages without a runtime backend.

The Fleasing refresh is limited to its designated first-party catalogue and linked
detail pages. See `docs/source-audits/fleasing.md` before using it against the live
source.
