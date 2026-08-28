import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

import {
  CatalogueDatasetError,
  deriveCatalogueFacts,
  deriveOfferFacts,
  findOfferByIdentity,
  indexCatalogueDataset,
  loadCatalogueDataset,
  parseCatalogueDataset,
} from "../src/catalogue-dataset";
import {
  catalogueDatasetJsonSchema,
  catalogueDatasetSchemaVersion,
} from "../src/catalogue-dataset-schema";

const validDataset: unknown = JSON.parse(
  readFileSync(
    new URL("../../tests/fixtures/browser-catalogue-dataset.json", import.meta.url),
    "utf8",
  ),
);
const invalidCases = JSON.parse(
  readFileSync(
    new URL("../../tests/fixtures/browser-catalogue-invalid-cases.json", import.meta.url),
    "utf8",
  ),
) as Record<string, string>;

test("the Dataset seam validates, indexes, and derives shared factual values", () => {
  const dataset = parseCatalogueDataset(validDataset);
  const index = indexCatalogueDataset(dataset);

  expect(findOfferByIdentity(index, "terminalen:demo:one")).toBe(
    dataset.offers[0],
  );
  expect(findOfferByIdentity(index, "terminalen:missing:one")).toBeUndefined();
  expect(deriveOfferFacts(index, dataset.offers[0])).toMatchObject({
    providerName: "Terminalen",
    vehicleName: "Demo One Base",
    leasePaymentDkk: 1000,
    calculatedTotalDkk: 1000,
    calculatedMonthlyTotalDkk: 1000,
  });
  expect(deriveCatalogueFacts(dataset)).toEqual({
    generatedAt: "2026-07-31T10:00:00Z",
    providerCount: 1,
    activeProviderCount: 1,
    inactiveProviderCount: 0,
    offerCount: 1,
    quarantinedCandidateCount: 0,
  });
});

test("partial and incompatible data fail closed at the Dataset seam", () => {
  expect(() => parseCatalogueDataset({})).toThrow(CatalogueDatasetError);
  expect(() =>
    parseCatalogueDataset({
      ...(validDataset as Record<string, unknown>),
      schemaVersion: "catalogue-dataset/v2",
    }),
  ).toThrowError(expect.objectContaining({ kind: "incompatible" }));

  const withUnknownField = structuredClone(validDataset) as {
    offers: Array<Record<string, unknown>>;
  };
  withUnknownField.offers[0].unexpected = true;
  expect(() => parseCatalogueDataset(withUnknownField)).toThrowError(
    expect.objectContaining({ kind: "invalid" }),
  );
});

test("the generated schema and Zod reject the shared invalid constraint cases", () => {
  expect(catalogueDatasetSchemaVersion).toBe(
    catalogueDatasetJsonSchema.properties.schemaVersion.const,
  );

  for (const [caseName, fieldValue] of Object.entries(invalidCases)) {
    const invalid = structuredClone(validDataset) as {
      generatedAt: string;
      providers: Array<{ url: string }>;
      offers: Array<{ canonicalOfferUrl: string }>;
    };
    if (caseName === "invalidGeneratedAt") invalid.generatedAt = fieldValue;
    if (caseName === "invalidGeneratedAtCalendarDate") {
      invalid.generatedAt = fieldValue;
    }
    if (caseName === "invalidProviderUrl") invalid.providers[0].url = fieldValue;
    if (caseName === "invalidProviderCredentialsUrl") {
      invalid.providers[0].url = fieldValue;
    }
    if (caseName === "invalidOfferUrl") invalid.offers[0].canonicalOfferUrl = fieldValue;

    expect(() => parseCatalogueDataset(invalid)).toThrowError(
      expect.objectContaining({ kind: "invalid" }),
    );
  }
});

test("Dataset load failures retain their boundary classification", async () => {
  await expect(
    loadCatalogueDataset(async () => new Response("", { status: 503 })),
  ).rejects.toMatchObject({ kind: "unavailable" });
  await expect(
    loadCatalogueDataset(
      async () =>
        new Response("not-json", {
          headers: { "content-type": "application/json" },
        }),
    ),
  ).rejects.toMatchObject({ kind: "invalid" });
});
