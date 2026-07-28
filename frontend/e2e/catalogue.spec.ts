import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

import type { CataloguePresentation } from "../src/presentation";

const builtPresentation = JSON.parse(
  readFileSync(new URL("../../var/site/projection.json", import.meta.url), "utf8"),
) as CataloguePresentation;

async function servePresentation(
  page: Page,
  presentation: CataloguePresentation,
) {
  await page.route("**/projection.json", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(presentation),
    }),
  );
}

function presentationWithSeveralOffers(): CataloguePresentation {
  const terminalenOffer = builtPresentation.offers[0];
  const fleasingOffer = structuredClone(terminalenOffer);
  fleasingOffer.offerIdentity = "fleasing:bmw-i4";
  fleasingOffer.provider = "Fleasing";
  fleasingOffer.vehicleSpecification = {
    ...fleasingOffer.vehicleSpecification,
    value: "BMW i4 M50",
  };
  fleasingOffer.supportedLeasingForm = {
    ...fleasingOffer.supportedLeasingForm,
    value: "financial",
  };
  fleasingOffer.residualRiskAllocation = {
    ...fleasingOffer.residualRiskAllocation,
    value: "lessee",
  };
  fleasingOffer.advertisedMonthlyPayment = {
    ...fleasingOffer.advertisedMonthlyPayment,
    valueDkk: 5995,
  };
  fleasingOffer.upfrontCashRequirement = {
    ...fleasingOffer.upfrontCashRequirement,
    valueDkk: 54990,
  };
  fleasingOffer.termMonths = {
    ...fleasingOffer.termMonths,
    value: 24,
  };
  fleasingOffer.annualMileageKm = {
    ...fleasingOffer.annualMileageKm,
    value: 15000,
  };

  const secondTerminalenOffer = structuredClone(terminalenOffer);
  secondTerminalenOffer.offerIdentity = "terminalen:toyota-yaris";
  secondTerminalenOffer.vehicleSpecification = {
    ...secondTerminalenOffer.vehicleSpecification,
    value: "Toyota Yaris Active",
  };
  secondTerminalenOffer.advertisedMonthlyPayment = {
    ...secondTerminalenOffer.advertisedMonthlyPayment,
    valueDkk: 2995,
  };
  secondTerminalenOffer.upfrontCashRequirement = {
    ...secondTerminalenOffer.upfrontCashRequirement,
    valueDkk: 9995,
  };
  secondTerminalenOffer.annualMileageKm = {
    ...secondTerminalenOffer.annualMileageKm,
    value: 15000,
  };

  return {
    ...builtPresentation,
    offers: [terminalenOffer, fleasingOffer, secondTerminalenOffer],
  };
}

const viewports = [
  { name: "desktop", width: 1280, height: 720 },
  { name: "mobile", width: 390, height: 844 },
];

for (const viewport of viewports) {
  test(`${viewport.name} completed artifact shows an evidence-backed offer`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await page.goto("/");

    await expect(
      page.getByRole("heading", {
        name: "Hyundai IONIQ 5 Essential 84 kWh",
      }),
    ).toBeVisible();
    await expect(page.getByText("3.795 kr.", { exact: true })).toBeVisible();
    await expect(page.getByText("15.990 kr.", { exact: true })).toBeVisible();
    await expect(page.getByText("152.610 kr.", { exact: true })).toBeVisible();
    await expect(page.getByText("4.239 kr.", { exact: true })).toBeVisible();
    const catalogue = page.getByRole("region", { name: "Katalogtilbud" });
    await expect(
      catalogue.getByText("36 måneder", { exact: true }),
    ).toBeVisible();
    await expect(
      catalogue.getByText("10.000 km", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Bilen afleveres til udbyderen ved normalt udløb", {
        exact: true,
      }),
    ).toBeVisible();

    await page.getByText("Se beregning og kildegrundlag").click();
    await expect(page.getByText("Førstegangsydelse 15.990 kr.")).toBeVisible();
    await expect(
      page.getByText("Månedlig ydelse 3.795 kr. i 36 måneder."),
    ).toBeVisible();

    const hasPageOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(hasPageOverflow).toBe(false);

    if (viewport.name === "mobile") {
      await expect(page.locator(".facts")).toHaveCSS(
        "grid-template-columns",
        "324px",
      );
    }
  });
}

test("invalid startup data is rejected safely", async ({ page }) => {
  await page.route("**/projection.json", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        schemaVersion: "catalogue-presentation/v1",
        offers: [{ provider: "Misleading provider" }],
      }),
    }),
  );

  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Kataloget kan ikke vises" }),
  ).toBeVisible();
  await expect(page.getByText("Misleading provider")).toHaveCount(0);
});

test("search and filters narrow the catalogue without reordering offers", async ({
  page,
}) => {
  await servePresentation(page, presentationWithSeveralOffers());
  await page.goto("/");

  const offerHeadings = page
    .getByRole("region", { name: "Katalogtilbud" })
    .getByRole("heading", { level: 2 });
  await expect(offerHeadings).toHaveText([
    "Hyundai IONIQ 5 Essential 84 kWh",
    "BMW i4 M50",
    "Toyota Yaris Active",
  ]);

  await page
    .getByLabel("Søg i køretøjsspecifikation eller dækket udbyder")
    .fill("Terminalen");
  await expect(offerHeadings).toHaveText([
    "Hyundai IONIQ 5 Essential 84 kWh",
    "Toyota Yaris Active",
  ]);

  await page.getByRole("button", { name: "Nulstil filtre" }).click();
  await page
    .getByLabel("Filtrér køretøjsspecifikation")
    .fill("BMW");
  await expect(offerHeadings).toHaveText(["BMW i4 M50"]);

  await page.getByRole("button", { name: "Nulstil filtre" }).click();
  await page.getByLabel("Leasingform").selectOption("financial");
  await expect(offerHeadings).toHaveText(["BMW i4 M50"]);

  await page.getByRole("button", { name: "Nulstil filtre" }).click();
  await page.getByLabel("Restværdirisiko").selectOption("provider");
  await expect(offerHeadings).toHaveText([
    "Hyundai IONIQ 5 Essential 84 kWh",
    "Toyota Yaris Active",
  ]);

  await page.getByRole("button", { name: "Nulstil filtre" }).click();
  await page.getByLabel("Maks. kontant behov ved start").fill("20000");
  await expect(offerHeadings).toHaveText([
    "Hyundai IONIQ 5 Essential 84 kWh",
    "Toyota Yaris Active",
  ]);

  await page.getByRole("button", { name: "Nulstil filtre" }).click();
  await page.getByLabel("Fuld løbetid").selectOption("24");
  await expect(offerHeadings).toHaveText(["BMW i4 M50"]);

  await page.getByRole("button", { name: "Nulstil filtre" }).click();
  await page.getByLabel("Mindst kilometer om året").fill("15000");
  await expect(offerHeadings).toHaveText([
    "BMW i4 M50",
    "Toyota Yaris Active",
  ]);

  await page.getByRole("button", { name: "Nulstil filtre" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.locator(".card-header").evaluateAll((headers) =>
      headers.every((header) => getComputedStyle(header).display === "block"),
    ),
  ).toBe(true);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    ),
  ).toBe(false);
});

test("empty results stay scoped and retain the neutral-ranking explanation", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Søg i køretøjsspecifikation eller dækket udbyder")
    .fill("findes ikke");

  await expect(
    page.getByRole("heading", {
      name: "Ingen tilbud matcher i det aktive katalog",
    }),
  ).toBeVisible();
  await expect(page.getByText("Ingen personlig rangering.")).toBeVisible();
  await expect(
    page.getByText("Den faste kilderækkefølge er ikke en anbefaling.", {
      exact: false,
    }),
  ).toBeVisible();
});

test("freshness and bounded coverage remain visible with quarantined counts", async ({
  page,
}) => {
  const presentation = structuredClone(builtPresentation);
  presentation.coverage.providers[0].quarantinedCandidateCount = 2;
  await servePresentation(page, presentation);
  await page.goto("/");

  await expect(
    page.getByText(/Katalogdatasæt genereret 22\. juli 2026/).first(),
  ).toBeVisible();
  await expect(
    page.getByText("Tilbud kan være ændret eller udløbet siden.", {
      exact: false,
    }).first(),
  ).toBeVisible();
  const coverage = page.getByRole("region", {
    name: "Dækning af det aktive katalog",
  });
  await expect(coverage.getByText("Terminalen", { exact: true })).toBeVisible();
  await expect(
    coverage.getByText("Terminalen model price page", { exact: true }),
  ).toBeVisible();
  await expect(
    coverage.getByText("2 karantænesatte katalogkandidater", { exact: true }),
  ).toBeVisible();
  await expect(coverage).toContainText("ikke hele det danske marked");
  const disclaimer = page.locator(".persistent-disclaimer");
  await expect(disclaimer).toBeInViewport();
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
  await expect(disclaimer).toBeInViewport();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  expect(
    await page.evaluate(() => {
      const coverageBottom = document
        .querySelector(".coverage")!
        .getBoundingClientRect().bottom;
      const disclaimerTop = document
        .querySelector(".persistent-disclaimer")!
        .getBoundingClientRect().top;
      return coverageBottom <= disclaimerTop;
    }),
  ).toBe(true);
});

test("an unavailable headline amount gives the precise blocking explanation", async ({
  page,
}) => {
  const presentation = structuredClone(builtPresentation);
  const offer = presentation.offers[0];
  offer.nominalBaseOutlay = {
    state: "not_stated",
    calculation: offer.nominalBaseOutlay.calculation,
    blockingFacts: ["Obligatorisk slutbetaling er ikke oplyst."],
  };
  await servePresentation(page, presentation);
  await page.goto("/");

  const fact = page.locator(".fact-row", {
    hasText: "Nominelt basisudlæg",
  });
  await expect(fact).toContainText("Kan ikke beregnes");
  await expect(fact).toContainText(
    "Obligatorisk slutbetaling er ikke oplyst.",
  );
});
