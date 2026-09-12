import { expect, test, type Locator, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

import {
  parseCatalogueDataset,
  type CatalogueDataset,
  type CatalogueOffer,
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
const offerNames = ["One", "Two", "Three", "Four", "Five"];

function availableAmount(amountDkk: number): CatalogueOffer["calculatedTotal"] {
  return { state: "available", value: { amountDkk } };
}

function comparisonOffer(position: number): CatalogueOffer {
  const monthlyAmount = 1_000 + position * 100;
  const termMonths = position + 1;
  const baseCashFlowStream = Array.from({ length: termMonths }, (_, index) => ({
    ...baseEvent,
    key: `compare-${position + 1}-lease-${index + 1}`,
    month: index + 1,
    amount: { state: "known" as const, value: monthlyAmount },
  }));
  const total = monthlyAmount * termMonths;

  return {
    ...baseDataset.offers[0],
    offerIdentity: `terminalen:comparison:${position + 1}`,
    vehicleSpecification: {
      ...baseDataset.offers[0].vehicleSpecification,
      model: `Compare ${offerNames[position]}`,
    },
    termMonths,
    baseCashFlowStream,
    calculatedTotal: availableAmount(total),
    calculatedMonthlyTotal: availableAmount(monthlyAmount),
  };
}

const unavailableOffer: CatalogueOffer = {
  ...comparisonOffer(0),
  offerIdentity: "terminalen:comparison:5",
  vehicleSpecification: {
    ...comparisonOffer(0).vehicleSpecification,
    model: "Compare Five",
  },
  termMonths: 2,
  baseCashFlowStream: [
    {
      ...baseEvent,
      key: "compare-five-lease-1",
      month: 1,
      amount: { state: "known", value: 1_400 },
    },
    {
      ...baseEvent,
      key: "compare-five-lease-2",
      month: 2,
      amount: { state: "unclear" },
    },
  ],
  calculatedTotal: {
    state: "unavailable",
    reasons: [
      {
        code: "fact_unavailable",
        field: "baseCashFlowStream.amount",
        eventKey: "compare-five-lease-2",
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
        eventKey: "compare-five-lease-2",
        factState: "unclear",
      },
    ],
  },
};

const comparisonDataset: CatalogueDataset = {
  ...baseDataset,
  offers: [
    comparisonOffer(0),
    comparisonOffer(1),
    comparisonOffer(2),
    comparisonOffer(3),
    unavailableOffer,
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

function identity(position: number): string {
  return `terminalen:comparison:${position}`;
}

function compareUrl(positions: readonly number[]): string {
  return `/#/compare?${positions
    .map((position) => `offers=${encodeURIComponent(identity(position))}`)
    .join("&")}`;
}

function offerHeading(position: number): string {
  return `Demo Compare ${offerNames[position - 1]} Base`;
}

function offerColumnName(position: number): string {
  return `Kontantstrøm for ${offerHeading(position)}`;
}

function columnSuffix(count: number): string {
  if (count === 1) return "";
  return "s";
}

function chartName(count: number): string {
  return `Fælles søjlediagram for ${count} tilbud`;
}

function comparisonFactRow(table: Locator, label: string): Locator {
  return table
    .getByRole("rowheader", { name: label, exact: true })
    .locator("..");
}

function dkk(amount: number): string {
  return `${new Intl.NumberFormat("da-DK").format(amount)} kr.`;
}

function expectedVehicleValue(label: string, position: number): string {
  const values: Record<string, string> = {
    Mærke: "Demo",
    Model: `Compare ${offerNames[position - 1]}`,
    Variant: "Base",
    Modelår: "2025",
    Førstegangsregistrering: "Ikke relevant for denne aftale",
    Karrosseri: "Hatchback",
    Kilometertal: "0 km",
    Drivmiddel: "Forbrænding",
    Brændstof: "Benzin",
    Brændstoføkonomi: "20 km/l",
    Batterikapacitet: "Ikke relevant for denne aftale",
    "WLTP-rækkevidde": "Ikke relevant for denne aftale",
    "Maksimal ladeeffekt": "Ikke relevant for denne aftale",
    "Ladetid fra 10 til 80 %": "Ikke relevant for denne aftale",
  };
  return values[label];
}

function expectedContractValue(label: string, position: number): string {
  const monthlyAmount = position === 5 ? 1_400 : 1_000 + (position - 1) * 100;
  const totalAmount = [1_000, 2_200, 3_600, 5_200][position - 1];
  const values: Record<string, string> = {
    Leasingform: "Operationel privatleasing",
    "Udbyderens formbetegnelse": "Privatleasing",
    "Fuld løbetid": `${position === 5 ? 2 : position} måneder`,
    "Kilometer om året": "10.000 km",
    "Normal afslutning": "Bilen afleveres til udbyderen ved normalt udløb",
    Restværdirisiko: "Udbyderen bærer restværdirisikoen",
    "Annonceret samlet betaling": "Ikke oplyst af udbyderen",
    "Nominelt basisudlæg":
      position === 5
        ? "Kan ikke beregnes: Kan ikke afgøres ud fra kilden (compare-five-lease-2)"
        : dkk(totalAmount),
    "Nominelt månedligt gennemsnit":
      position === 5
        ? "Kan ikke beregnes: Kan ikke afgøres ud fra kilden (compare-five-lease-2)"
        : dkk(monthlyAmount),
    "Månedlig betaling": dkk(monthlyAmount),
    "Kontant behov ved start":
      "Ingen betaling ved start er dokumenteret i datasættet.",
  };
  return values[label];
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  for (const positions of [[1], [2, 1], [5, 2, 4, 1, 3]] as const) {
    test(`${viewport.name} Offer Comparison renders ${positions.length} ordered Offer column${columnSuffix(positions.length)}`, async ({
      page,
    }) => {
      await page.setViewportSize(viewport);
      await serveDataset(page, comparisonDataset);
      await page.goto(compareUrl(positions));

      await expect(
        page.getByRole("heading", { name: "Sammenlign tilbud" }),
      ).toBeVisible();
      const comparisonTable = page.getByRole("table", {
        name: "Sammenligning af tilbud",
      });
      await expect(comparisonTable).toBeVisible();
      await expect(
        page.getByRole("table", { name: "Sammenligningsfakta" }),
      ).toHaveCount(0);
      await expect(
        comparisonTable.getByRole("columnheader").getByRole("link"),
      ).toHaveCount(positions.length);
      await expect(
        comparisonTable.getByRole("columnheader").getByRole("link"),
      ).toHaveText(positions.map(offerHeading));
      await expect(
        page.getByRole("figure", { name: chartName(positions.length) }),
      ).toHaveCount(1);
      await expect(page.getByText("0 kr.", { exact: true })).toBeVisible();
      const sourceLinks = page.getByRole("link", {
        name: /Åbn den kanoniske tilbudskilde/,
      });
      await expect(sourceLinks).toHaveCount(positions.length);
      await expect(sourceLinks.first()).toHaveAttribute("target", "_blank");
      await expect(sourceLinks.first()).toHaveAttribute(
        "rel",
        "noreferrer noopener",
      );
      for (const position of positions) {
        await expect(
          page.getByRole("region", { name: offerColumnName(position) }),
        ).toBeVisible();
        await expect(
          page.getByRole("list", {
            name: `Tilgængelig kontantstrøm for ${offerHeading(position)}`,
          }),
        ).toHaveCount(1);
        await expect(
          page.getByRole("table", {
            name: `Basiskontantstrøm i DKK for ${offerHeading(position)}`,
          }),
        ).toHaveCount(1);
      }
      await expect(
        comparisonTable.getByRole("rowheader", { name: "Mærke" }),
      ).toHaveCount(1);
      await expect(
        comparisonTable.getByRole("rowheader", { name: "Leasingform" }),
      ).toHaveCount(1);
      await expect(
        comparisonTable.getByRole("rowheader", { name: "Serviceordninger" }),
      ).toHaveCount(1);
      for (const label of [
        "Mærke",
        "Model",
        "Variant",
        "Modelår",
        "Førstegangsregistrering",
        "Karrosseri",
        "Kilometertal",
        "Drivmiddel",
        "Brændstof",
        "Brændstoføkonomi",
        "Batterikapacitet",
        "WLTP-rækkevidde",
        "Maksimal ladeeffekt",
        "Ladetid fra 10 til 80 %",
      ]) {
        await expect(
          comparisonFactRow(comparisonTable, label).getByRole("cell"),
        ).toHaveText(
          positions.map((position) => expectedVehicleValue(label, position)),
        );
      }
      for (const label of [
        "Leasingform",
        "Udbyderens formbetegnelse",
        "Fuld løbetid",
        "Kilometer om året",
        "Normal afslutning",
        "Restværdirisiko",
        "Annonceret samlet betaling",
        "Nominelt basisudlæg",
        "Nominelt månedligt gennemsnit",
        "Månedlig betaling",
        "Kontant behov ved start",
      ]) {
        await expect(
          comparisonFactRow(comparisonTable, label).getByRole("cell"),
        ).toHaveText(
          positions.map((position) => expectedContractValue(label, position)),
        );
      }
      await expect(
        comparisonFactRow(comparisonTable, "Serviceordninger").getByRole(
          "cell",
        ),
      ).toHaveText(
        positions.map(
          () => "Ingen serviceordning er registreret i datasættet.",
        ),
      );
      await expect(
        page.getByRole("img", { name: "Visuel kontantstrøm i DKK" }),
      ).toHaveCount(1);
      await expect(page.getByText("Forskellig", { exact: true })).toHaveCount(
        0,
      );
    });
  }
}

test("Offer Comparison keeps unknown cash-flow facts factual and accessible", async ({
  page,
}) => {
  await serveDataset(page, comparisonDataset);
  await page.goto(compareUrl([5, 1]));

  await expect(
    page.getByText("Kan ikke afgøres ud fra kilden").first(),
  ).toBeVisible();
  await expect(
    page.getByRole("list", {
      name: "Tilgængelig kontantstrøm for Demo Compare Five Base",
    }),
  ).toContainText("Måned 2");
  await expect(page.getByText(/beløb .* vises ikke som nul/)).toBeVisible();
  const chart = page.getByRole("figure", {
    name: "Fælles søjlediagram for 2 tilbud",
  });
  await chart.locator("svg.ts-chart").focus();
  await expect(chart.locator('[role="status"].ts-chart-tooltip')).toBeVisible();
});

test("Offer Comparison renders the shared chart through TanStack's accessible surface", async ({
  page,
}) => {
  await serveDataset(page, comparisonDataset);
  await page.goto(compareUrl([2, 1]));

  const chart = page.getByRole("figure", {
    name: "Fælles søjlediagram for 2 tilbud",
  });
  const visualChart = chart.locator("svg.ts-chart");
  await expect(visualChart).toHaveCount(1);
  await expect(visualChart).toHaveAttribute("tabindex", "0");
  await expect(chart.getByText("Beløb (DKK)", { exact: true })).toBeVisible();
  await expect(
    chart.getByText("Demo Compare Two Base · betaling", { exact: true }),
  ).toBeVisible();
  await expect(
    chart.getByText("Demo Compare One Base · modtaget beløb", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("table", { name: /Basiskontantstrøm i DKK for/ }),
  ).toHaveCount(2);
});

test("Offer Comparison adds an Offer through ordered URL history", async ({
  page,
}) => {
  await serveDataset(page, comparisonDataset);
  await page.goto(compareUrl([1]));

  await page
    .getByRole("combobox", { name: "Tilføj tilbud" })
    .selectOption(identity(2));
  await page.getByRole("button", { name: "Tilføj tilbud" }).click();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Acomparison%3A1&offers=terminalen%3Acomparison%3A2$/,
  );
  await page.reload();
  await expect(page.getByRole("columnheader").getByRole("link")).toHaveCount(2);
  await page.goBack();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Acomparison%3A1$/,
  );
  await page.goForward();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Acomparison%3A1&offers=terminalen%3Acomparison%3A2$/,
  );
});

test("Offer Comparison selection remains URL-owned through reload and history", async ({
  page,
}) => {
  await serveDataset(page, comparisonDataset);
  await page.goto("/#/catalogue");

  await page.getByLabel("Vælg Demo Compare One Base til sammenligning").check();
  await expect(
    page.getByRole("link", { name: "Sammenlign valgte tilbud" }),
  ).toBeVisible();
  await page.getByLabel("Vælg Demo Compare Two Base til sammenligning").check();
  await page.getByRole("link", { name: "Sammenlign valgte tilbud" }).click();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Acomparison%3A1&offers=terminalen%3Acomparison%3A2$/,
  );
  await expect(
    page.getByRole("table").getByRole("columnheader").getByRole("link"),
  ).toHaveText(["Demo Compare One Base", "Demo Compare Two Base"]);

  await page.reload();
  await expect(page.getByRole("figure", { name: chartName(2) })).toHaveCount(1);
  await page
    .getByRole("button", {
      name: "Fjern Demo Compare Two Base fra valgte tilbud",
    })
    .click();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Acomparison%3A1$/,
  );
  await expect(
    page.getByRole("table").getByRole("columnheader").getByRole("link"),
  ).toHaveText(["Demo Compare One Base"]);

  await page.goBack();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Acomparison%3A1&offers=terminalen%3Acomparison%3A2$/,
  );
  await page.goForward();
  await expect(page).toHaveURL(
    /#\/compare\?offers=terminalen%3Acomparison%3A1$/,
  );
});

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`${viewport.name} Offer Comparison contains scrolling and remains keyboard operable`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await serveDataset(page, comparisonDataset);
    await page.goto(compareUrl([5, 2, 4, 1, 3]));

    const comparisonRegion = page.getByRole("region", {
      name: "Sammenligning af tilbud",
    });
    const comparisonTable = page.getByRole("table", {
      name: "Sammenligning af tilbud",
    });
    const offerLinks = comparisonTable
      .getByRole("columnheader")
      .getByRole("link");
    const firstOfferLink = offerLinks.first();
    const lastOfferLink = offerLinks.last();
    await expect(comparisonRegion).toHaveCSS("overflow-x", "auto");
    await comparisonRegion.focus();
    await expect(comparisonRegion).toBeFocused();
    await page.keyboard.press("End");
    await expect(lastOfferLink).toBeInViewport();
    await page.keyboard.press("Home");
    await expect(firstOfferLink).toBeInViewport();

    await page.mouse.wheel(0, 700);
    await expect(firstOfferLink).toBeInViewport();

    const documentLayout = await page.evaluate(() => {
      const width = window.innerWidth;
      const htmlWidth = document.documentElement.scrollWidth;
      const bodyWidth = document.body.scrollWidth;
      return {
        bodyWidth,
        htmlWidth,
        safe: htmlWidth <= width && bodyWidth <= width,
        viewportWidth: width,
      };
    });
    expect(documentLayout.safe, JSON.stringify(documentLayout)).toBe(true);
  });
}
