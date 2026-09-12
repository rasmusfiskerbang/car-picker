import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

import {
  addOffer,
  clearOfferSelection,
  parseOfferSelectionSearch,
  reconcileOfferSelection,
  removeOffer,
  toggleOffer,
} from "../src/offer-selection-search";
import {
  indexCatalogueDataset,
  parseCatalogueDataset,
} from "../src/catalogue-dataset";
import type { CatalogueDataset } from "../src/catalogue-dataset";

const dataset = parseCatalogueDataset(
  JSON.parse(
    readFileSync(
      new URL("../../tests/fixtures/browser-catalogue-dataset.json", import.meta.url),
      "utf8",
    ),
  ),
);
const index = indexCatalogueDataset(dataset);
const liveOffer = dataset.offers[0].offerIdentity;

const selectionDataset: CatalogueDataset = {
  ...dataset,
  offers: ["One", "Two", "Three", "Four", "Five", "Six"].map((model) => ({
    ...dataset.offers[0],
    offerIdentity: `terminalen:selection:${model.toLowerCase()}`,
    vehicleSpecification: {
      ...dataset.offers[0].vehicleSpecification,
      model: `Selection ${model}`,
    },
    imageUrls: [],
  })),
};

async function serveDataset(page: Page, value: unknown) {
  await page.route("**/catalogue-dataset.json", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(value),
    }),
  );
}

test("Offer Selection parses ordered URL state and reconciles it with the loaded Dataset", () => {
  const parsed = parseOfferSelectionSearch({
    offers: [liveOffer, " stale:offer ", liveOffer, "", "another:offer"],
  });

  expect(parsed).toEqual([liveOffer, "stale:offer", "another:offer"]);
  expect(reconcileOfferSelection(parsed, index)).toEqual([liveOffer]);
});

test("Offer Selection mutations stay duplicate-free, ordered, and capped", () => {
  const firstFive = ["one", "two", "three", "four", "five"];

  expect(addOffer(firstFive, "five")).toEqual(firstFive);
  expect(addOffer(firstFive, "six")).toEqual(firstFive);
  expect(toggleOffer(firstFive, "three")).toEqual([
    "one",
    "two",
    "four",
    "five",
  ]);
  expect(toggleOffer(firstFive, "new")).toEqual(firstFive);
  expect(removeOffer(firstFive, "two")).toEqual([
    "one",
    "three",
    "four",
    "five",
  ]);
  expect(clearOfferSelection()).toEqual([]);
});

test("Offer Selection follows the prospective lessee across routes, reload, and history", async ({
  page,
}) => {
  await serveDataset(page, selectionDataset);
  await page.goto("/#/catalogue?search=Selection");

  await page.getByLabel("Vælg Demo Selection One Base til sammenligning").check();
  await page.getByLabel("Vælg Demo Selection Two Base til sammenligning").check();

  const tray = page.getByRole("complementary", { name: "Valgte tilbud" });
  await page.goBack();
  await expect(page).toHaveURL(
    /#\/catalogue\?search=Selection&offers=terminalen%3Aselection%3Aone$/,
  );
  await expect(
    page.getByLabel("Vælg Demo Selection One Base til sammenligning"),
  ).toBeChecked();
  await expect(
    page.getByLabel("Vælg Demo Selection Two Base til sammenligning"),
  ).not.toBeChecked();
  await expect(tray).toContainText("1 tilbud valgt");
  await page.goForward();
  await expect(page).toHaveURL(
    /#\/catalogue\?search=Selection&offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Atwo$/,
  );
  await expect(
    page.getByLabel("Vælg Demo Selection One Base til sammenligning"),
  ).toBeChecked();
  await expect(
    page.getByLabel("Vælg Demo Selection Two Base til sammenligning"),
  ).toBeChecked();
  await expect(tray).toContainText("2 tilbud valgt");
  await expect(tray.getByRole("button", { name: "Ryd valgte tilbud" })).toBeVisible();

  await page
    .getByRole("link", { name: "Se detaljer for Demo Selection One Base" })
    .click();
  await expect(page).toHaveURL(
    /#\/offers\/terminalen%3Aselection%3Aone\?offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Atwo/,
  );
  await expect(page.getByLabel("Søg i køretøjsspecifikation eller dækket udbyder")).toHaveCount(0);
  await expect(
    page.getByLabel("Vælg Demo Selection One Base til sammenligning"),
  ).toBeChecked();

  await page.getByRole("link", { name: "Tilbage til kataloget" }).click();
  await expect(page).toHaveURL(/#\/catalogue\?offers=/);
  await page.getByLabel("Vælg Demo Selection Three Base til sammenligning").check();
  await page
    .getByRole("link", { name: "Se detaljer for Demo Selection One Base" })
    .click();
  await expect(page).toHaveURL(
    /offers\/terminalen%3Aselection%3Aone\?offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Atwo&offers=terminalen%3Aselection%3Athree/,
  );

  await page.getByRole("link", { name: "Tilbage til kataloget" }).click();
  await expect(
    page.getByLabel("Søg i køretøjsspecifikation eller dækket udbyder"),
  ).toHaveValue("");
  await expect(
    page.getByLabel("Vælg Demo Selection One Base til sammenligning"),
  ).toBeChecked();
  await expect(
    page.getByLabel("Vælg Demo Selection Two Base til sammenligning"),
  ).toBeChecked();
  await expect(
    page.getByLabel("Vælg Demo Selection Three Base til sammenligning"),
  ).toBeChecked();

  await page.goBack();
  await expect(page).toHaveURL(
    /offers\/terminalen%3Aselection%3Aone\?offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Atwo&offers=terminalen%3Aselection%3Athree/,
  );
  await expect(page.getByRole("complementary", { name: "Valgte tilbud" })).toContainText(
    "3 tilbud valgt",
  );
  await page.goForward();
  await expect(page).toHaveURL(/#\/catalogue\?offers=/);
  await expect(
    page.getByLabel("Vælg Demo Selection Three Base til sammenligning"),
  ).toBeChecked();

  await page.getByRole("link", { name: "Sammenlign valgte tilbud" }).click();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Atwo&offers=terminalen%3Aselection%3Athree/,
  );
  await page.reload();
  await expect(page.getByRole("complementary", { name: "Valgte tilbud" })).toContainText(
    "3 tilbud valgt",
  );

  await page
    .getByRole("button", { name: "Fjern Demo Selection Two Base fra valgte tilbud" })
    .click();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Athree/,
  );
  await expect(page.getByRole("complementary", { name: "Valgte tilbud" })).toContainText(
    "2 tilbud valgt",
  );
  await page.goBack();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Atwo&offers=terminalen%3Aselection%3Athree$/,
  );
  await expect(page.getByRole("complementary", { name: "Valgte tilbud" })).toContainText(
    "3 tilbud valgt",
  );
  await page.goForward();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Athree$/,
  );
  await page.getByRole("button", { name: "Ryd valgte tilbud" }).click();
  await expect(page.getByRole("complementary", { name: "Valgte tilbud" })).toHaveCount(0);
  await expect(page).toHaveURL(/#\/compare$/);
  await page.goBack();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Athree$/,
  );
  await expect(page.getByRole("complementary", { name: "Valgte tilbud" })).toContainText(
    "2 tilbud valgt",
  );
  await page.goForward();
  await expect(page).toHaveURL(/#\/compare$/);
  await expect(page.getByRole("complementary", { name: "Valgte tilbud" })).toHaveCount(0);
});

test("Offer Selection replaces malformed URL state after Dataset reconciliation", async ({
  page,
}) => {
  await serveDataset(page, selectionDataset);
  await page.goto("/#/catalogue");
  await page.goto(
    "/#/offers/terminalen%3Aselection%3Aone?offers=terminalen%3Aselection%3Aone&offers=stale%3Aoffer&offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Atwo&offers=terminalen%3Aselection%3Athree&offers=terminalen%3Aselection%3Afour&offers=terminalen%3Aselection%3Afive&offers=terminalen%3Aselection%3Asix",
  );

  await expect(page).toHaveURL(
    /#\/offers\/terminalen%3Aselection%3Aone\?offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Atwo&offers=terminalen%3Aselection%3Athree&offers=terminalen%3Aselection%3Afour&offers=terminalen%3Aselection%3Afive$/,
  );
  await expect(page.getByRole("complementary", { name: "Valgte tilbud" })).toContainText(
    "5 tilbud valgt",
  );
  await page.goBack();
  await expect(page).toHaveURL(/#\/catalogue$/);

  await page.goto(
    "/#/providers?offers=terminalen%3Aselection%3Aone&offers=stale%3Aoffer&offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Atwo&offers=terminalen%3Aselection%3Athree&offers=terminalen%3Aselection%3Afour&offers=terminalen%3Aselection%3Afive&offers=terminalen%3Aselection%3Asix",
  );
  await expect(page).toHaveURL(
    /#\/providers\?offers=terminalen%3Aselection%3Aone&offers=terminalen%3Aselection%3Atwo&offers=terminalen%3Aselection%3Athree&offers=terminalen%3Aselection%3Afour&offers=terminalen%3Aselection%3Afive$/,
  );
  await expect(page.getByRole("complementary", { name: "Valgte tilbud" })).toContainText(
    "5 tilbud valgt",
  );
});
