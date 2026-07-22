# Car picker

The production tracer bullet builds a static Danish catalogue from a
schema-versioned canonical catalogue dataset:

```sh
python3 -m car_picker build-site --dataset var/catalogue-dataset.json --output site
python3 -m http.server --directory site 4173
```

`var/` and `site/` are generated local outputs and are intentionally ignored by Git.
The browser validates `projection.json` at startup before it renders any offer facts.
