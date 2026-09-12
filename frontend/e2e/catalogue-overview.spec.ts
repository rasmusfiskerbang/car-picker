import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

import {
  parseCatalogueDataset,
  type CatalogueDataset,
  type CatalogueOffer,
} from "../src/catalogue-dataset";

const validDataset = parseCatalogueDataset(
  JSON.parse(
    readFileSync(
      new URL(
        "../../tests/fixtures/browser-catalogue-dataset.json",
        import.meta.url,
      ),
      "utf8",
    ),
  ),
);

const baseOffer = validDataset.offers[0];
const sharedVehicle = baseOffer.vehicleSpecification;

const electricVehicle: CatalogueOffer["vehicleSpecification"] = {
  make: sharedVehicle.make,
  model: "Electric",
  trim: sharedVehicle.trim,
  modelYear: sharedVehicle.modelYear,
  firstRegistrationYear: sharedVehicle.firstRegistrationYear,
  bodyStyle: sharedVehicle.bodyStyle,
  odometerKm: sharedVehicle.odometerKm,
  kind: "battery_electric",
  batteryCapacity: {
    state: "known",
    value: { valueKwh: 64, basis: "usable" },
  },
  wltpRangeKm: { state: "known", value: 420 },
  maxChargingPower: {
    state: "known",
    value: { valueKw: 150, kind: "dc" },
  },
  chargingTime10To80Minutes: { state: "known", value: 28 },
};

function availableAmount(amountDkk: number): CatalogueOffer["calculatedTotal"] {
  return { state: "available", value: { amountDkk } };
}

function offerWith(
  monthlyDkk: number,
  changes: Partial<CatalogueOffer>,
): CatalogueOffer {
  const event = baseOffer.baseCashFlowStream[0];
  return {
    ...baseOffer,
    ...changes,
    baseCashFlowStream: [
      {
        ...event,
        amount: { state: "known", value: monthlyDkk },
      },
    ],
    calculatedTotal: availableAmount(monthlyDkk),
    calculatedMonthlyTotal: availableAmount(monthlyDkk),
  };
}

const overviewDataset: CatalogueDataset = {
  ...validDataset,
  providers: [
    ...validDataset.providers,
    {
      id: "fleasing",
      name: "Fleasing",
      url: "https://www.fleasing.dk/",
      status: "active",
    },
  ],
  offers: [
    offerWith(1000, {
      imageUrls: ["https://assets.terminalen.dk/media/demo-one.jpg"],
    }),
    offerWith(1500, {
      offerIdentity: "fleasing:demo:electric",
      providerId: "fleasing",
      canonicalOfferUrl: "https://www.fleasing.dk/demo-electric",
      vehicleSpecification: electricVehicle,
      supportedLeasingForm: "financial",
      imageUrls: ["https://images.untrusted.test/demo-electric.jpg"],
    }),
    offerWith(1300, {
      offerIdentity: "fleasing:demo:flex",
      providerId: "fleasing",
      canonicalOfferUrl: "https://www.fleasing.dk/demo-flex",
      supportedLeasingForm: "flex",
      vehicleSpecification: {
        ...sharedVehicle,
        model: "Flex",
      },
      imageUrls: [],
    }),
    offerWith(500, {
      offerIdentity: "terminalen:demo:two",
      canonicalOfferUrl: "https://example.test/terminalen/demo-two",
      vehicleSpecification: {
        ...sharedVehicle,
        model: "Two",
      },
      imageUrls: ["https://images.untrusted.test/demo-two.jpg"],
      termMonths: 24,
    }),
  ],
};

const selectionDataset: CatalogueDataset = {
  ...overviewDataset,
  offers: Array.from({ length: 6 }, (_, position) =>
    offerWith(1000 + position, {
      offerIdentity: `terminalen:selection:${position + 1}`,
      vehicleSpecification: {
        ...sharedVehicle,
        model: `Selection ${position + 1}`,
      },
      imageUrls: [],
    }),
  ),
};

async function serveDataset(page: Page, dataset: unknown) {
  await page.route("**/catalogue-dataset.json", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(dataset),
    }),
  );
}

test.describe("catalogue overview", () => {
  test("owns search, filters, and sorting in validated URL state", async ({
    page,
  }) => {
    await serveDataset(page, overviewDataset);
    await page.goto("/#/catalogue");

    await page
      .getByLabel("Søg i køretøjsspecifikation eller dækket udbyder")
      .fill("Electric");
    await page.getByLabel("Udbyder", { exact: true }).selectOption("fleasing");
    await page.getByLabel("Leasingform").selectOption("financial");
    await page.getByLabel("Køretøjstype").selectOption("battery_electric");
    await page.getByLabel("Sortér tilbud").selectOption("monthly");

    await expect(page).toHaveURL(
      /#\/catalogue\?.*search=Electric.*provider=fleasing.*leasingForm=financial.*vehicleKind=battery_electric.*sort=monthly/,
    );
    await expect(
      page.getByRole("heading", { name: "Demo Electric Base" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Demo One Base" }),
    ).toHaveCount(0);

    await page.reload();
    await expect(
      page.getByLabel("Søg i køretøjsspecifikation eller dækket udbyder"),
    ).toHaveValue("Electric");
    await expect(page.getByLabel("Udbyder", { exact: true })).toHaveValue(
      "fleasing",
    );
    await expect(page.getByLabel("Leasingform")).toHaveValue("financial");
    await expect(page.getByLabel("Køretøjstype")).toHaveValue(
      "battery_electric",
    );
    await expect(page.getByLabel("Sortér tilbud")).toHaveValue("monthly");

    await page.goBack();
    await expect(page.getByLabel("Sortér tilbud")).toHaveValue("source");
    await page.goForward();
    await expect(page.getByLabel("Sortér tilbud")).toHaveValue("monthly");
    await expect(
      page.getByRole("heading", { name: "Demo Electric Base" }),
    ).toBeVisible();
  });

  test("shows multiple offers in the selected sort order", async ({ page }) => {
    await serveDataset(page, overviewDataset);
    await page.goto("/#/catalogue");

    const offerHeadings = page.getByRole("article").getByRole("heading");
    await expect(offerHeadings).toHaveText([
      "Demo One Base",
      "Demo Electric Base",
      "Demo Flex Base",
      "Demo Two Base",
    ]);
    await page.getByLabel("Sortér tilbud").selectOption("monthly");
    await expect(offerHeadings).toHaveText([
      "Demo Two Base",
      "Demo One Base",
      "Demo Flex Base",
      "Demo Electric Base",
    ]);
  });

  test("keeps URL-owned selections while quarantine discards offer filters", async ({
    page,
  }) => {
    await serveDataset(page, validDataset);
    await page.goto(
      "/#/catalogue?search=Demo&provider=terminalen&leasingForm=operational&vehicleKind=combustion&sort=monthly&view=quarantined&offers=terminalen%3Ademo%3Aone",
    );

    await expect(page).toHaveURL(
      /#\/catalogue\?provider=terminalen&view=quarantined&offers=terminalen%3Ademo%3Aone$/,
    );
    await expect(
      page.getByRole("heading", {
        name: "Karantænesatte kandidater",
        exact: true,
      }),
    ).toBeVisible();

    await page.getByRole("link", { name: "Tilbage til katalogtilbud" }).click();
    await expect(page).toHaveURL(
      /#\/catalogue\?provider=terminalen&offers=terminalen%3Ademo%3Aone$/,
    );
    await expect(
      page.getByLabel("Vælg Demo One Base til sammenligning"),
    ).toBeChecked();
    await expect(
      page.getByRole("link", { name: "Sammenlign 1 tilbud" }),
    ).toBeVisible();
  });

  test("canonicalizes invalid URL state against the loaded dataset", async ({
    page,
  }) => {
    await serveDataset(page, overviewDataset);
    await page.goto(
      "/#/catalogue?search=%20Electric%20&provider=unknown&leasingForm=unsupported&vehicleKind=battery_electric&sort=unsupported&offers=fleasing%3Ademo%3Aelectric&offers=stale%3Aoffer&offers=fleasing%3Ademo%3Aelectric&unknown=remove",
    );

    await expect(page).toHaveURL(
      /#\/catalogue\?search=Electric&vehicleKind=battery_electric&offers=fleasing%3Ademo%3Aelectric$/,
    );
    await expect(
      page.getByRole("heading", { name: "Demo Electric Base" }),
    ).toBeVisible();

    await page
      .getByLabel("Søg i køretøjsspecifikation eller dækket udbyder")
      .fill("Two");
    await page.goBack();
    await expect(
      page.getByLabel("Søg i køretøjsspecifikation eller dækket udbyder"),
    ).toHaveValue("Electric");
    await page.goForward();
    await expect(
      page.getByLabel("Søg i køretøjsspecifikation eller dækket udbyder"),
    ).toHaveValue("Two");
    await page.reload();
    await expect(
      page.getByLabel("Søg i køretøjsspecifikation eller dækket udbyder"),
    ).toHaveValue("Two");
  });

  test("uses a restrained desktop sidebar and a complete keyboard mobile sheet", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await serveDataset(page, overviewDataset);
    await page.goto("/#/catalogue");

    await expect(
      page.getByRole("heading", { name: "Leasingtilbud" }),
    ).toBeVisible();
    const sidebar = page.locator(".catalogue-sidebar");
    await expect(sidebar).toBeVisible();
    await expect(
      sidebar.getByLabel("Søg i køretøjsspecifikation eller dækket udbyder"),
    ).toBeVisible();
    await expect(sidebar.getByLabel("Udbyder", { exact: true })).toBeVisible();
    await expect(sidebar.getByLabel("Leasingform")).toBeVisible();
    await expect(sidebar.getByLabel("Køretøjstype")).toBeVisible();
    await expect(sidebar.getByLabel("Sortér tilbud")).toBeVisible();
    await expect(
      sidebar.getByLabel("Filtrér køretøjsspecifikation"),
    ).toHaveCount(0);
    await expect(
      sidebar.getByLabel("Maks. kontant behov ved start"),
    ).toHaveCount(0);
    await expect(sidebar.getByLabel("Fuld løbetid")).toHaveCount(0);
    await expect(sidebar.getByLabel("Mindst kilometer om året")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Åbn filtre" })).toBeHidden();

    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator(".catalogue-sidebar")).toBeHidden();
    const openFilters = page.getByRole("button", { name: "Åbn filtre" });
    await expect(openFilters).toBeVisible();
    await openFilters.focus();
    await page.keyboard.press("Enter");

    const filterSheet = page.getByRole("dialog", { name: "Filtre" });
    await expect(filterSheet).toBeVisible();
    await expect(page.locator("main.catalogue-page")).toHaveAttribute("inert");
    await expect(
      page.getByRole("button", { name: "Nulstil filtre" }),
    ).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("button", { name: "Luk filtre" }),
    ).toBeFocused();
    for (let step = 0; step < 5; step += 1) {
      await page.keyboard.press("Tab");
      await expect
        .poll(() =>
          page.evaluate(
            () => document.activeElement?.closest('[role="dialog"]') !== null,
          ),
        )
        .toBe(true);
    }
    await page.keyboard.press("Shift+Tab");
    await expect
      .poll(() =>
        page.evaluate(
          () => document.activeElement?.closest('[role="dialog"]') !== null,
        ),
      )
      .toBe(true);
    await page.keyboard.press("Escape");
    await expect(filterSheet).toBeHidden();
    await expect(openFilters).toBeFocused();
    await expect(page.locator("main.catalogue-page")).not.toHaveAttribute(
      "inert",
    );
  });

  test("keeps material facts visible with audited image fallback and source action", async ({
    page,
  }) => {
    const imageRequests: string[] = [];
    page.on("request", (request) => {
      if (request.resourceType() === "image") imageRequests.push(request.url());
    });
    await serveDataset(page, overviewDataset);
    await page.route(
      "https://assets.terminalen.dk/media/demo-one.jpg",
      (route) =>
        route.fulfill({
          contentType: "image/svg+xml",
          body: '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#35513c" /></svg>',
        }),
    );
    await page.goto("/#/catalogue");

    const imageCard = page
      .getByRole("article")
      .filter({ has: page.getByRole("heading", { name: "Demo One Base" }) });
    await expect(imageCard).toHaveCount(1);
    await expect(imageCard.locator("img")).toHaveAttribute(
      "src",
      "https://assets.terminalen.dk/media/demo-one.jpg",
    );
    await expect(imageCard.locator("img")).toHaveAttribute("loading", "lazy");
    await expect(imageCard.locator("img")).toHaveAttribute(
      "referrerpolicy",
      "no-referrer",
    );
    await expect(imageCard.locator(".offer-card-facts")).toHaveCount(1);
    await expect(
      imageCard.locator(".offer-card-facts > .fact-row"),
    ).toHaveCount(6);
    await expect(imageCard.locator(".calculation")).toHaveCount(0);
    await expect(imageCard.getByText("1.000 kr.").first()).toBeVisible();
    await expect(
      imageCard
        .locator(".offer-card-footer")
        .getByRole("link", { name: "Åbn hos Terminalen" }),
    ).toHaveAttribute("href", "https://example.test/terminalen/demo");

    const fallbackCard = page.getByRole("article").filter({
      has: page.getByRole("heading", { name: "Demo Electric Base" }),
    });
    await expect(
      fallbackCard.getByRole("img", { name: "Billede ikke tilgængeligt" }),
    ).toBeVisible();
    await expect(
      fallbackCard.getByText("Fleasing", { exact: true }).first(),
    ).toBeVisible();
    await expect(fallbackCard.getByText("1.500 kr.").first()).toBeVisible();
    await expect(
      fallbackCard.getByRole("link", { name: "Åbn hos Fleasing" }),
    ).toHaveAttribute("href", "https://www.fleasing.dk/demo-electric");
    expect(imageRequests).toEqual([
      "https://assets.terminalen.dk/media/demo-one.jpg",
    ]);
  });

  test("canonicalizes and disables a sixth ordered selection", async ({
    page,
  }) => {
    await serveDataset(page, selectionDataset);
    await page.goto(
      "/#/catalogue?offers=terminalen%3Aselection%3A1&offers=stale%3Aoffer&offers=terminalen%3Aselection%3A1&offers=terminalen%3Aselection%3A2&offers=terminalen%3Aselection%3A3&offers=terminalen%3Aselection%3A4&offers=terminalen%3Aselection%3A5&offers=terminalen%3Aselection%3A6",
    );

    await expect(page).toHaveURL(
      /#\/catalogue\?offers=terminalen%3Aselection%3A1&offers=terminalen%3Aselection%3A2&offers=terminalen%3Aselection%3A3&offers=terminalen%3Aselection%3A4&offers=terminalen%3Aselection%3A5$/,
    );
    await expect(
      page.getByLabel("Vælg Demo Selection 6 Base til sammenligning"),
    ).toBeDisabled();
    await expect(
      page.getByLabel("Vælg Demo Selection 5 Base til sammenligning"),
    ).toBeChecked();
  });

  test("describes zero matches as a bounded catalogue result", async ({
    page,
  }) => {
    await serveDataset(page, overviewDataset);
    await page.goto("/#/catalogue?search=DoesNotExist");

    await expect(
      page.getByRole("heading", {
        name: "Ingen tilbud matcher i det aktive katalog",
      }),
    ).toBeVisible();
    await expect(
      page.getByText("Det betyder ikke, at der ikke findes andre tilbud.", {
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.locator(".empty-state").getByText(/hele det danske marked/),
    ).toHaveCount(0);
  });
});
