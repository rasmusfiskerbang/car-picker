import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

import type { CatalogueDataset } from "../src/catalogue-dataset";

const validDataset = JSON.parse(
  readFileSync(
    new URL(
      "../../tests/fixtures/browser-catalogue-dataset.json",
      import.meta.url,
    ),
    "utf8",
    ),
) as CatalogueDataset;

const comparisonDataset: CatalogueDataset = {
  ...validDataset,
  offers: [
    validDataset.offers[0],
    {
      ...validDataset.offers[0],
      offerIdentity: "terminalen:demo:two",
      canonicalOfferUrl: "https://example.test/terminalen/demo-two",
      vehicleSpecification: {
        ...validDataset.offers[0].vehicleSpecification,
        model: "Two",
      },
    },
  ],
};

async function serveDataset(page: Page, dataset: unknown) {
  await page.route("**/catalogue-dataset.json", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(dataset),
    }),
  );
}

function visibleNavigation(page: Page) {
  return page.locator('nav[aria-label="Primær navigation"]:visible');
}

async function expectCompleteLandingComposition(page: Page) {
  await expect(page.locator(".shell-context-band")).toContainText(
    "Afgrænset, neutralt katalog",
  );
  await expect(page.locator(".shell-context-band")).toContainText(
    "Data fra 31. juli 2026",
  );
  await expect(
    page.getByRole("heading", {
      name: "Sammenlign aftalen, ikke kun månedsprisen.",
    }),
  ).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(3);
  await expect(page.getByRole("heading", { name: "Se, hvad der faktisk er med" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sammenlign de samme fakta" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kontrollér vilkårene selv" })).toBeVisible();
  await expect(
    page.getByText("Start i et dateret katalog fra navngivne udbydere", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Sæt månedsydelse, startbetaling, beregnet total", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Læs hvordan aftalen slutter, og åbn altid", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(page.getByText("1 tilbud er klar til sammenligning")).toBeVisible();
  await expect(page.getByText("Fra 1 aktiv udbyder")).toBeVisible();
  await expect(page.getByText("ingen anbefalinger")).toBeVisible();
  await expect(page.getByRole("link", { name: "Se alle 1 tilbud" })).toBeVisible();

  const navigation = visibleNavigation(page);
  await expect(navigation.getByRole("link")).toHaveCount(3);
  await expect(navigation.getByRole("link").allTextContents()).resolves.toEqual([
    "Tilbud",
    "Sammenlign",
    "Udbydere",
  ]);
  await expect(navigation.getByRole("link", { name: "Tilbud" })).toHaveAttribute(
    "href",
    /#\/catalogue(?:$|\?)/,
  );
  await expect(navigation.getByRole("link", { name: "Sammenlign" })).toHaveAttribute(
    "href",
    /#\/compare(?:$|\?)/,
  );
  await expect(navigation.getByRole("link", { name: "Udbydere" })).toHaveAttribute(
    "href",
    /#\/providers$/,
  );

  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <= window.innerWidth &&
        document.body.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
}

async function expectSequentialKeyboardNavigation(page: Page) {
  const destinationNames = ["Tilbud", "Sammenlign", "Udbydere"];
  const destinations = [/#\/catalogue/, /#\/compare/, /#\/providers/];

  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Sammenlign aftalen, ikke kun månedsprisen.",
    }),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Bilvalg — gå til forsiden" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", {
      name: "Sammenlign aftalen, ikke kun månedsprisen.",
    }),
  ).toBeVisible();

  for (const [index, destinationName] of destinationNames.entries()) {
    await page.goto("/");
    await expect(
      page.getByRole("heading", {
        name: "Sammenlign aftalen, ikke kun månedsprisen.",
      }),
    ).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("link", { name: "Bilvalg — gå til forsiden" }),
    ).toBeFocused();

    const navigation = visibleNavigation(page);
    for (let tab = 0; tab <= index; tab += 1) {
      await page.keyboard.press("Tab");
    }
    const destination = navigation.getByRole("link", { name: destinationName });
    await expect(destination).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(destinations[index]);
  }

  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Sammenlign aftalen, ikke kun månedsprisen.",
    }),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Bilvalg — gå til forsiden" }),
  ).toBeFocused();
  for (let tab = 0; tab < destinationNames.length; tab += 1) {
    await page.keyboard.press("Tab");
  }
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Se alle 1 tilbud" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#\/catalogue(?:$|\?)/);
}

test.describe("application shell and landing page", () => {
  test("loads the validated Dataset at the root and presents the accepted landing composition", async ({
    page,
  }) => {
    await serveDataset(page, validDataset);
    await page.goto("/");

    await expect(
      page.getByRole("heading", {
        name: "Sammenlign aftalen, ikke kun månedsprisen.",
      }),
    ).toBeVisible();
    await expect(page.getByText("Afgrænset, neutralt katalog")).toBeVisible();
    await expect(page.getByText("Data fra 31. juli 2026")).toBeVisible();
    await expect(page.getByText("1 tilbud er klar til sammenligning")).toBeVisible();
    await expect(page.getByText("Fra 1 aktiv udbyder")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Se, hvad der faktisk er med" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sammenlign de samme fakta" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kontrollér vilkårene selv" })).toBeVisible();
    await expect(page.getByText("ingen anbefalinger")).toBeVisible();
    await expect(page.getByRole("link", { name: "Se alle 1 tilbud" })).toHaveCount(1);

    const navigation = page.locator('nav[aria-label="Primær navigation"]:visible');
    await expect(navigation.getByRole("link")).toHaveCount(3);
    await expect(navigation.getByRole("link").allTextContents()).resolves.toEqual([
      "Tilbud",
      "Sammenlign",
      "Udbydere",
    ]);
    await expect(page.getByRole("link", { name: "Bilvalg — gå til forsiden" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Forside", exact: true })).toHaveCount(0);

    await expect(navigation.getByRole("link", { name: "Tilbud" })).toHaveAttribute(
      "href",
      /#\/catalogue/,
    );
    await expect(navigation.getByRole("link", { name: "Sammenlign" })).toHaveAttribute(
      "href",
      /#\/compare/,
    );
    await expect(navigation.getByRole("link", { name: "Udbydere" })).toHaveAttribute(
      "href",
      /#\/providers/,
    );
  });

  test("primary navigation reaches each hash destination", async ({ page }) => {
    await serveDataset(page, validDataset);
    await page.goto("/");

    const navigation = page.locator('nav[aria-label="Primær navigation"]:visible');
    await navigation.getByRole("link", { name: "Tilbud" }).click();
    await expect(page).toHaveURL(/#\/catalogue/);

    await page.goto("/");
    await navigation.getByRole("link", { name: "Sammenlign" }).click();
    await expect(page).toHaveURL(/#\/compare/);
    await expect(
      page.getByRole("heading", { name: "Sammenlign tilbud" }),
    ).toBeVisible();

    await page.goto("/");
    await navigation.getByRole("link", { name: "Udbydere" }).click();
    await expect(page).toHaveURL(/#\/providers/);
    await expect(page.getByRole("heading", { name: "Udbydere" })).toBeVisible();
  });

  test("preserves selected offers in compare URL state across navigation and reload", async ({
    page,
  }) => {
    await serveDataset(page, comparisonDataset);
    await page.goto("/#/catalogue");

    await page.getByLabel("Vælg Demo One Base til sammenligning").check();
    await page.getByLabel("Vælg Demo Two Base til sammenligning").check();

    const compareLink = page.getByRole("link", { name: "Sammenlign 2 tilbud" });
    await expect(compareLink).toHaveAttribute(
      "href",
      /#\/compare\?.*offers=.*terminalen.*demo.*one.*terminalen.*demo.*two/,
    );
    const primaryCompareLink = visibleNavigation(page).getByRole("link", {
      name: "Sammenlign",
    });
    await expect(primaryCompareLink).toHaveAttribute(
      "href",
      /#\/compare\?.*offers=.*terminalen.*demo.*one.*terminalen.*demo.*two/,
    );
    await primaryCompareLink.click();
    await expect(page).toHaveURL(
      /#\/compare\?.*offers=.*terminalen.*demo.*one.*terminalen.*demo.*two/,
    );
    await expect(page.getByRole("heading", { name: "Sammenlign tilbud" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Demo One Base" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Demo Two Base" })).toBeVisible();

    await page.reload();
    await expect(page.getByRole("columnheader", { name: "Demo One Base" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Demo Two Base" })).toBeVisible();

    await page.goBack();
    await expect(page).toHaveURL(
      /#\/catalogue\?.*offers=.*terminalen.*demo.*one.*terminalen.*demo.*two/,
    );
    await expect(
      page.getByLabel("Vælg Demo One Base til sammenligning"),
    ).toBeChecked();
    await expect(
      page.getByLabel("Vælg Demo Two Base til sammenligning"),
    ).toBeChecked();

    await page.goForward();
    await expect(page).toHaveURL(
      /#\/compare\?.*offers=.*terminalen.*demo.*one.*terminalen.*demo.*two/,
    );
    await expect(page.getByRole("columnheader", { name: "Demo Two Base" })).toBeVisible();

    const sharedUrl = page.url();
    await page.goto(sharedUrl);
    await expect(page.getByRole("columnheader", { name: "Demo One Base" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Demo Two Base" })).toBeVisible();
  });

  test("keeps offer detail as its explicit shell destination", async ({ page }) => {
    await serveDataset(page, validDataset);
    await page.goto("/#/offers/terminalen%3Ademo%3Aone");

    await expect(page.locator(".shell-page-title")).toHaveText("Tilbuddet");
    await expect(
      page.getByRole("heading", {
        name: "Demo One Base",
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "Sammenlign aftalen, ikke kun månedsprisen.",
      }),
    ).toHaveCount(0);

    await page.goto("/#/offers/does-not-exist");
    await expect(page.locator(".shell-page-title")).toHaveText("Tilbuddet");
    await expect(
      page.getByRole("heading", {
        name: "Tilbuddet findes ikke i dette katalog",
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "Sammenlign aftalen, ikke kun månedsprisen.",
      }),
    ).toHaveCount(0);

    await page.goto("/#/unknown");
    await expect(
      page.getByRole("heading", {
        name: "Sammenlign aftalen, ikke kun månedsprisen.",
      }),
    ).toHaveCount(0);
  });

  test("fails closed before shell composition for invalid Dataset data", async ({
    page,
  }) => {
    await serveDataset(page, {
      schemaVersion: "catalogue-dataset/v2",
      offers: [{ providerId: "untrusted" }],
    });
    await page.goto("/");

    await expect(
      page.getByRole("heading", { name: "Kataloget kan ikke vises" }),
    ).toHaveCount(1);
    await expect(page.getByRole("alert")).toHaveCount(1);
    await expect(page.locator("nav")).toHaveCount(0);
    await expect(page.getByRole("link")).toHaveCount(0);
    await expect(page.getByText("untrusted", { exact: false })).toHaveCount(0);
  });

  test("fails closed before shell composition when Dataset data is unavailable", async ({
    page,
  }) => {
    await page.route("**/catalogue-dataset.json", (route) =>
      route.fulfill({ status: 503, body: "unavailable" }),
    );
    await page.goto("/");

    await expect(
      page.getByRole("heading", { name: "Kataloget kan ikke vises" }),
    ).toHaveCount(1);
    await expect(page.getByRole("alert")).toHaveCount(1);
    await expect(page.locator("nav")).toHaveCount(0);
  });
});

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`${viewport.name} composition is complete and overflow-safe`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await serveDataset(page, validDataset);
    await page.goto("/");

    await expectCompleteLandingComposition(page);
  });

  test(`${viewport.name} shell supports sequential keyboard navigation`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await serveDataset(page, validDataset);
    await page.goto("/");

    await expectSequentialKeyboardNavigation(page);
  });
}
