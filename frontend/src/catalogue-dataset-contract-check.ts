import type { CatalogueDataset } from "./generated/catalogue-dataset";

export function acceptGeneratedCatalogueDataset(
  dataset: CatalogueDataset,
): CatalogueDataset {
  return dataset;
}

// The generated declaration must reject a partial Dataset at compile time.
// @ts-expect-error — a browser Dataset cannot omit its required contract fields.
const partialCatalogueDataset: CatalogueDataset = {
  schemaVersion: "catalogue-dataset/v1",
};

void partialCatalogueDataset;

// The generated discriminated root type must reject unsupported versions too.
// @ts-expect-error — the generated Dataset union only permits its schema const.
acceptGeneratedCatalogueDataset({ schemaVersion: "catalogue-dataset/v2" });
