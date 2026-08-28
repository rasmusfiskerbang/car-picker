import { expect, test, type Locator, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

import {
  parseCatalogueDataset,
  type CatalogueDataset,
} from "../src/catalogue-dataset";

const baseDataset = parseCatalogueDataset(
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

const baseEvent = baseDataset.offers[0].baseCashFlowStream[0];
const detailDataset: CatalogueDataset = {
  ...baseDataset,
  offers: [
    {
      ...baseDataset.offers[0],
      imageUrls: [
        "https://assets.terminalen.dk/media/demo-one.jpg",
        "https://assets.terminalen.dk/media/demo-one-side.jpg",
        "https://assets.terminalen.dk/media/demo-one-rear.jpg",
      ],
      baseCashFlowStream: [
        {
          ...baseEvent,
          key: "initial-payment",
          month: 0,
          kind: "initial_payment",
          amount: { state: "known", value: 5000 },
        },
        {
          ...baseEvent,
          key: "lease-payment-1",
          month: 1,
          kind: "lease_payment",
          amount: { state: "known", value: 1000 },
        },
      ],
      calculatedTotal: { state: "available", value: { amountDkk: 6000 } },
      calculatedMonthlyTotal: {
        state: "available",
        value: { amountDkk: 6000 },
      },
    },
  ],
};

const detailUnavailableDataset: CatalogueDataset = {
  ...detailDataset,
  offers: [
    {
      ...detailDataset.offers[0],
      baseCashFlowStream: [
        {
          ...detailDataset.offers[0].baseCashFlowStream[0],
          amount: { state: "unclear" },
        },
        {
          ...detailDataset.offers[0].baseCashFlowStream[1],
          amount: { state: "conflicting" },
        },
      ],
      calculatedTotal: {
        state: "unavailable",
        reasons: [
          {
            code: "fact_unavailable",
            field: "baseCashFlowStream.amount",
            eventKey: "initial-payment",
            factState: "unclear",
          },
        ],
      },
      calculatedMonthlyTotal: {
        state: "unavailable",
        reasons: [
          {
            code: "fact_unavailable",
            field: "baseCashFlowStream.amount",
            eventKey: "initial-payment",
            factState: "unclear",
          },
        ],
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

async function serveDetailImages(page: Page) {
  for (const [index, name] of [
    "demo-one",
    "demo-one-side",
    "demo-one-rear",
  ].entries()) {
    await page.route(
      `https://assets.terminalen.dk/media/${name}.jpg`,
      (route) =>
        route.fulfill({
          contentType: "image/svg+xml",
          body: `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400"><rect width="640" height="400" fill="hsl(${120 + index * 35} 30% 30%)" /></svg>`,
        }),
    );
  }
}

async function tabTo(page: Page, locator: Locator) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (
      await locator.evaluate((element) => element === document.activeElement)
    ) {
      return;
    }
    await page.keyboard.press("Tab");
  }
  throw new Error("Keyboard traversal did not reach the expected control.");
}

test.describe("Catalogue Offer detail", () => {
  test("takes one exact card identity through factual detail to its source", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await serveDataset(page, detailDataset);
    await serveDetailImages(page);
    await page.goto("/#/catalogue");

    const card = page
      .getByRole("article")
      .filter({ has: page.getByRole("heading", { name: "Demo One Base" }) });
    const detailLink = card.getByRole("link", {
      name: "Se detaljer for Demo One Base",
    });
    await card
      .getByRole("checkbox", { name: "Vælg Demo One Base til sammenligning" })
      .check();
    await detailLink.focus();
    await expect(detailLink).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page).toHaveURL(
      /#\/offers\/terminalen%3Ademo%3Aone\?offers=terminalen%3Ademo%3Aone/,
    );
    await expect(
      page.getByRole("heading", { name: "Demo One Base" }),
    ).toBeVisible();
    await expect(
      page.getByRole("img", { name: "Demo One Base hos Terminalen" }),
    ).toBeVisible();
    await expect(page.getByText("1.000 kr.").first()).toBeVisible();
    await expect(page.getByText("5.000 kr.").first()).toBeVisible();
    await expect(
      page.getByRole("checkbox", {
        name: "Vælg Demo One Base til sammenligning",
      }),
    ).toBeChecked();

    const gallery = page.getByRole("region", {
      name: "Billeder af Demo One Base",
    });
    await expect(
      gallery.getByRole("button", { name: "Forrige billede" }),
    ).toBeVisible();
    await expect(
      gallery.getByRole("button", { name: "Næste billede" }),
    ).toBeVisible();
    await expect(
      gallery.getByRole("button", { name: /Vis billede/ }),
    ).toHaveCount(3);
    await expect(gallery.locator("img").first()).toHaveAttribute(
      "src",
      detailDataset.offers[0].imageUrls[0],
    );
    await gallery.getByRole("button", { name: "Næste billede" }).click();
    await expect(gallery.locator("img").first()).toHaveAttribute(
      "src",
      detailDataset.offers[0].imageUrls[1],
    );
    await gallery.getByRole("button", { name: "Vis billede 3 af 3" }).click();
    await expect(gallery.locator("img").first()).toHaveAttribute(
      "src",
      detailDataset.offers[0].imageUrls[2],
    );

    const contents = page.getByRole("navigation", { name: "Indhold på siden" });
    await expect(contents).toBeVisible();
    await expect(contents.getByRole("link")).toHaveCount(5);
    for (const label of [
      "Køretøj",
      "Aftale",
      "Service",
      "Kontantstrøm",
      "Kilde",
    ]) {
      await expect(contents.getByRole("link", { name: label })).toBeVisible();
    }

    await expect(page.getByRole("heading", { name: "Køretøj" })).toBeVisible();
    await expect(
      page.getByText("Ikke relevant for denne aftale"),
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Aftale" })).toBeVisible();
    await expect(page.getByText("Ikke oplyst af udbyderen")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Service" })).toBeVisible();
    await expect(
      page.getByText("Ingen serviceordning er registreret i datasættet."),
    ).toBeVisible();

    const cashFlow = page.getByRole("region", { name: "Basiskontantstrøm" });
    await expect(cashFlow).toBeVisible();
    await expect(
      cashFlow.locator(".cash-flow-visual").getByText("Førstegangsbetaling"),
    ).toBeVisible();
    await expect(
      cashFlow.locator(".cash-flow-visual").getByText("Månedlig betaling"),
    ).toBeVisible();
    await expect(cashFlow.getByRole("figure")).toBeVisible();
    await expect(
      cashFlow
        .getByRole("figure")
        .getByText("Måned 0 · ved start · 31. juli 2026", { exact: true }),
    ).toBeVisible();
    await expect(
      cashFlow
        .getByRole("figure")
        .getByText("Måned 1 · 31. august 2026", { exact: true }),
    ).toBeVisible();
    await expect(cashFlow.getByText("Betalinger i strømmen")).toBeVisible();
    await expect(cashFlow.getByText("Beregnet ved udløb")).toBeVisible();
    await expect(
      cashFlow.getByRole("list", { name: "Tilgængelig kontantstrøm" }),
    ).toBeVisible();
    await expect(
      cashFlow.getByRole("table", { name: "Basiskontantstrøm i DKK" }),
    ).toBeVisible();
    await expect(cashFlow.getByRole("table").locator("tbody tr")).toHaveCount(
      2,
    );
    await expect(
      cashFlow.getByRole("table").locator("tbody tr").nth(0),
    ).toContainText("Måned 0");
    await expect(
      cashFlow.getByRole("table").locator("tbody tr").nth(1),
    ).toContainText("Måned 1");

    const providerLink = page.getByRole("link", {
      name: "Åbn Terminalens websted",
    });
    const sourceLink = page.getByRole("link", {
      name: "Åbn den kanoniske tilbudskilde",
    });
    await expect(providerLink).toHaveAttribute(
      "href",
      detailDataset.providers[0].url,
    );
    await expect(sourceLink).toHaveAttribute(
      "href",
      detailDataset.offers[0].canonicalOfferUrl,
    );

    await page.getByRole("link", { name: "Tilbage til kataloget" }).click();
    await expect(page).toHaveURL(
      /#\/catalogue\?offers=terminalen%3Ademo%3Aone/,
    );
    await expect(
      page.getByRole("checkbox", {
        name: "Vælg Demo One Base til sammenligning",
      }),
    ).toBeChecked();
  });

  test("keeps state-specific unavailable facts and reaches the source by keyboard", async ({
    page,
  }) => {
    await serveDataset(page, detailUnavailableDataset);
    await page
      .context()
      .route(detailUnavailableDataset.offers[0].canonicalOfferUrl, (route) =>
        route.fulfill({
          contentType: "text/html",
          body: "<!doctype html><title>Canonical source fixture</title>",
        }),
      );
    await page.goto("/#/offers/terminalen%3Ademo%3Aone");

    await expect(page.locator(".detail-price-block")).toContainText(
      "Modstridende oplysninger i kilden",
    );
    await expect(page.locator("#contract")).toContainText(
      "Kan ikke afgøres ud fra kilden",
    );

    const sourceLink = page.getByRole("link", {
      name: "Åbn den kanoniske tilbudskilde",
    });
    await tabTo(page, sourceLink);
    await expect(sourceLink).toBeFocused();
    const popupPromise = page.waitForEvent("popup");
    await page.keyboard.press("Enter");
    const popup = await popupPromise;
    await expect(popup).toHaveURL(
      detailUnavailableDataset.offers[0].canonicalOfferUrl,
    );
    await popup.close();
  });

  test("keeps the ordered gallery usable when one image fails", async ({
    page,
  }) => {
    await serveDataset(page, detailDataset);
    await page.route(detailDataset.offers[0].imageUrls[0], (route) =>
      route.abort(),
    );
    await page.route(detailDataset.offers[0].imageUrls[1], (route) =>
      route.fulfill({
        contentType: "image/svg+xml",
        body: '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400"><rect width="640" height="400" fill="#35513c" /></svg>',
      }),
    );
    await page.route(detailDataset.offers[0].imageUrls[2], (route) =>
      route.fulfill({
        contentType: "image/svg+xml",
        body: '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400"><rect width="640" height="400" fill="#6b4f32" /></svg>',
      }),
    );
    await page.goto("/#/offers/terminalen%3Ademo%3Aone");

    const gallery = page.getByRole("region", {
      name: "Billeder af Demo One Base hos Terminalen",
    });
    await expect(
      gallery.getByRole("img", { name: "Billede ikke tilgængeligt" }),
    ).toBeVisible();
    await gallery.getByRole("button", { name: "Næste billede" }).click();
    await expect(
      gallery.getByRole("img", { name: "Demo One Base hos Terminalen" }),
    ).toHaveAttribute("src", detailDataset.offers[0].imageUrls[1]);
  });

  test("fails safely for an unknown or malformed Offer Identity", async ({
    page,
  }) => {
    await serveDataset(page, detailDataset);

    await page.goto("/#/offers/does-not-exist");
    await expect(
      page.getByRole("heading", {
        name: "Tilbuddet findes ikke i dette katalog",
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Åbn den kanoniske tilbudskilde" }),
    ).toHaveCount(0);

    await page.goto("/#/offers/%E0%A4%A");
    await expect(page.getByText("Not Found")).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Åbn den kanoniske tilbudskilde" }),
    ).toHaveCount(0);
  });

  for (const viewport of [
    { name: "desktop", width: 1440, height: 900 },
    { name: "mobile", width: 390, height: 844 },
  ]) {
    test(`${viewport.name} detail keeps all facts and avoids document overflow`, async ({
      page,
    }) => {
      await page.setViewportSize(viewport);
      await serveDataset(page, detailDataset);
      await page.goto("/#/offers/terminalen%3Ademo%3Aone");

      await expect(
        page.getByRole("heading", { name: "Demo One Base" }),
      ).toBeVisible();
      await expect(
        page.getByRole("heading", { name: "Køretøj" }),
      ).toBeVisible();
      await expect(page.getByRole("heading", { name: "Aftale" })).toBeVisible();
      await expect(
        page.getByRole("heading", { name: "Service" }),
      ).toBeVisible();
      await expect(
        page.getByRole("heading", { name: "Kontantstrøm" }),
      ).toBeVisible();
      await expect(page.getByRole("heading", { name: "Kilde" })).toBeVisible();
      if (viewport.name === "mobile") {
        const chart = page.getByRole("figure", {
          name: "Fælles søjlediagram for 1 tilbud",
        });
        const chartScroll = chart.getByLabel(
          "Rul for at se alle kalenderdatoer",
        );
        await expect(chart).toBeVisible();
        await expect(chartScroll).toBeVisible();
        await expect(chartScroll).toHaveAttribute("tabindex", "0");
        const chartLayout = await chartScroll.evaluate((element) => {
          const bounds = element.getBoundingClientRect();
          return {
            clientWidth: element.clientWidth,
            scrollWidth: element.scrollWidth,
            left: bounds.left,
            right: bounds.right,
            viewportWidth: window.innerWidth,
          };
        });
        expect(chartLayout.clientWidth).toBeGreaterThan(0);
        expect(chartLayout.scrollWidth).toBeGreaterThan(
          chartLayout.clientWidth,
        );
        expect(chartLayout.left).toBeGreaterThanOrEqual(0);
        expect(chartLayout.right).toBeLessThanOrEqual(
          chartLayout.viewportWidth,
        );
        await chartScroll.focus();
        await expect(chartScroll).toBeFocused();
        await chartScroll.hover();
        await page.mouse.wheel(240, 0);
        await expect
          .poll(() => chartScroll.evaluate((element) => element.scrollLeft))
          .toBeGreaterThan(0);
      }
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <= window.innerWidth &&
            document.body.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);
    });
  }
});
