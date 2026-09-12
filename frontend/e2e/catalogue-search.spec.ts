import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

import {
  canonicalizeCatalogueSearch,
  catalogueSearchWithOffers,
  matchesCatalogueSearch,
  validateCatalogueSearch,
} from "../src/catalogue-search";
import {
  indexCatalogueDataset,
  parseCatalogueDataset,
} from "../src/catalogue-dataset";

const dataset = parseCatalogueDataset(
  JSON.parse(
    readFileSync(
      new URL("../../tests/fixtures/browser-catalogue-dataset.json", import.meta.url),
      "utf8",
    ),
  ),
);
const index = indexCatalogueDataset({
  ...dataset,
  offers: [
    ...dataset.offers,
    {
      ...dataset.offers[0],
      offerIdentity: "terminalen:demo:financial",
      supportedLeasingForm: "financial",
    },
    {
      ...dataset.offers[0],
      offerIdentity: "terminalen:demo:flex",
      supportedLeasingForm: "flex",
    },
  ],
});

test("the catalogue search seam drops invalid values and preserves canonical state", () => {
  expect(
    validateCatalogueSearch({
      offers: ["terminalen:demo:one", "terminalen:demo:one", ""],
      search: "  BMW  ",
      provider: "terminalen",
      leasingForm: "unsupported",
      vehicleKind: "unsupported",
      sort: "monthly",
      maxUpfront: "not-a-number",
    }),
  ).toEqual({
    offers: ["terminalen:demo:one"],
    search: "BMW",
    provider: "terminalen",
    sort: "monthly",
  });
});

test("selection updates retain catalogue filters as one shareable search object", () => {
  expect(
    catalogueSearchWithOffers(
      {
        search: "BMW",
        provider: "terminalen",
        leasingForm: "operational",
        vehicleKind: "combustion",
        sort: "monthly",
      },
      ["terminalen:demo:one"],
    ),
  ).toEqual({
    search: "BMW",
    provider: "terminalen",
    leasingForm: "operational",
    vehicleKind: "combustion",
    sort: "monthly",
    offers: ["terminalen:demo:one"],
  });
});

test("leasing form filters match financial and flex as distinct states", () => {
  const financial = index.offersByIdentity.get("terminalen:demo:financial");
  const flex = index.offersByIdentity.get("terminalen:demo:flex");

  expect(financial).toBeDefined();
  expect(flex).toBeDefined();
  expect(matchesCatalogueSearch(financial!, index, { leasingForm: "financial" })).toBe(true);
  expect(matchesCatalogueSearch(flex!, index, { leasingForm: "financial" })).toBe(false);
  expect(matchesCatalogueSearch(financial!, index, { leasingForm: "flex" })).toBe(false);
  expect(matchesCatalogueSearch(flex!, index, { leasingForm: "flex" })).toBe(true);
});

test("catalogue URL state keeps ordered live selections within the five-offer limit", () => {
  expect(
    canonicalizeCatalogueSearch(
      {
        offers: [
          "terminalen:demo:financial",
          "stale:offer",
          "terminalen:demo:financial",
          "terminalen:demo:flex",
          "terminalen:demo:one",
          "terminalen:demo:flex",
          "terminalen:demo:one",
        ],
        search: "  BMW ",
        sort: "monthly",
      },
      index,
    ),
  ).toEqual({
    offers: [
      "terminalen:demo:financial",
      "terminalen:demo:flex",
      "terminalen:demo:one",
    ],
    search: "BMW",
    sort: "monthly",
  });
});
