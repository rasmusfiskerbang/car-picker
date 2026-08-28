import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

import type { CatalogueDataset } from "../src/catalogue-dataset";

const builtDataset = JSON.parse(
  readFileSync(
    new URL("../../tests/fixtures/browser-catalogue-dataset.json", import.meta.url),
    "utf8",
  ),
) as CatalogueDataset;

async function serveDataset(page: Page, dataset: unknown) {
  await page.route("**/catalogue-dataset.json", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(dataset),
    }),
  );
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`${viewport.name} browser consumes the exact Catalogue Dataset`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await page.goto("/#/catalogue");

    await expect(
      page.getByRole("heading", { name: "Leasingtilbud" }),
    ).toBeVisible();
    if (viewport.name === "mobile") {
      await page.getByRole("button", { name: "Åbn filtre" }).click();
    }
    const filterSurface =
      viewport.name === "mobile"
        ? page.getByRole("dialog", { name: "Filtre" })
        : page;
    await expect(page.getByText("Terminalen", { exact: true }).first()).toBeVisible();
    await expect(
      page.locator(".fact-row").filter({ hasText: "Nominelt basisudlæg" }),
    ).toContainText("1.000 kr.");
    await expect(
      filterSurface.getByLabel("Søg i køretøjsspecifikation eller dækket udbyder"),
    ).toBeVisible();
    await expect(filterSurface.getByLabel("Udbyder", { exact: true })).toBeVisible();
    await expect(filterSurface.getByLabel("Leasingform")).toBeVisible();
    await expect(filterSurface.getByLabel("Køretøjstype")).toBeVisible();
    await expect(filterSurface.getByLabel("Sortér tilbud")).toBeVisible();
    await filterSurface
      .getByLabel("Søg i køretøjsspecifikation eller dækket udbyder")
      .fill("not a vehicle");
    await expect(
      page.getByRole("heading", { name: "Ingen tilbud matcher i det aktive katalog" }),
    ).toBeVisible();
    await filterSurface.getByRole("button", { name: "Nulstil filtre" }).click();
    await expect(page.getByRole("heading", { name: "Demo One Base" })).toBeVisible();
    const resultSummary =
      viewport.name === "mobile"
        ? page.locator(".catalogue-mobile-toolbar .catalogue-result-summary")
        : page.locator(".catalogue-results .catalogue-result-summary");
    await expect(resultSummary).toHaveText("1 tilbud");
    await expect(page.locator(".catalogue-sidebar .filters label")).toHaveCount(5);
    await expect(page.locator(".offer-card .calculation")).toHaveCount(0);
    await expect(page.getByText("Katalogpost:", { exact: false })).toHaveCount(0);
    await expect(page.getByText("projection.json", { exact: false })).toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth,
      ),
    ).toBe(false);
  });
}

test("invalid, partial, and incompatible startup data fail closed", async ({
  page,
}) => {
  await serveDataset(page, {
    schemaVersion: "catalogue-dataset/v2",
    offers: [{ providerId: "misleading" }],
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Kataloget kan ikke vises" }),
  ).toBeVisible();
  await expect(page.getByText("misleading", { exact: false })).toHaveCount(0);

  await serveDataset(page, { schemaVersion: "catalogue-dataset/v1" });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Kataloget kan ikke vises" }),
  ).toBeVisible();
});

test("validated identity lookup is used before detail and comparison pages", async ({
  page,
}) => {
  await serveDataset(page, builtDataset);
  await page.goto("/#/catalogue");

  await page.getByRole("link", { name: "Se detaljer for Demo One Base" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Demo One Base",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("table", { name: "Basiskontantstrøm i DKK" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Åbn den kanoniske tilbudskilde" }),
  ).toHaveAttribute("href", builtDataset.offers[0].canonicalOfferUrl);

  await page.goto("/#/catalogue");
  await page.getByLabel("Vælg Demo One Base til sammenligning").check();
  await expect(
    page.getByRole("link", { name: "Sammenlign 1 tilbud" }),
  ).toBeVisible();
});
