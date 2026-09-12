import { expect, test, type Locator, type Page } from "@playwright/test";

async function visibleLink(
  page: Page,
  name: string | RegExp,
): Promise<Locator> {
  const links = page.getByRole("link", { name }).all();
  for (const link of await links) {
    if (await link.isVisible()) return link;
  }
  throw new Error(`No visible link found for ${String(name)}`);
}

async function expectNoDocumentOverflow(page: Page) {
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <= window.innerWidth &&
        document.body.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
}

async function expectLanding(page: Page) {
  await expect(
    page.getByRole("heading", {
      name: "Sammenlign aftalen, ikke kun månedsprisen.",
    }),
  ).toBeVisible();
  await expect(page.getByText("Afgrænset, neutralt katalog")).toBeVisible();
  await expect(page.getByText("Data fra 31. juli 2026")).toBeVisible();
  await expect(
    page.getByText("1 tilbud er klar til sammenligning"),
  ).toBeVisible();
  await expect(page.getByText("Fra 1 aktiv udbyder")).toBeVisible();
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`${viewport.name} completed static Site supports the five-route journey`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expectLanding(page);

    const catalogueCallToAction = await visibleLink(page, "Se alle 1 tilbud");
    await catalogueCallToAction.click();
    await expect(page).toHaveURL(/#\/catalogue$/);
    await expect(
      page.getByRole("heading", { name: "Leasingtilbud" }),
    ).toBeVisible();

    const filterSurface =
      viewport.name === "mobile"
        ? await (async () => {
            await page.getByRole("button", { name: "Åbn filtre" }).click();
            return page.getByRole("dialog", { name: "Filtre" });
          })()
        : page;
    const search = filterSurface.getByLabel(
      "Søg i køretøjsspecifikation eller dækket udbyder",
    );
    await search.fill("Demo");
    await filterSurface
      .getByLabel("Udbyder", { exact: true })
      .selectOption("terminalen");
    await filterSurface.getByLabel("Leasingform").selectOption("operational");
    await filterSurface.getByLabel("Køretøjstype").selectOption("combustion");
    await filterSurface.getByLabel("Sortér tilbud").selectOption("monthly");
    if (viewport.name === "mobile") {
      await filterSurface.getByRole("button", { name: "Vis 1 tilbud" }).click();
    }
    await expect(
      page.getByRole("heading", { name: "Demo One Base" }),
    ).toBeVisible();
    await expect(page).toHaveURL(
      /#\/catalogue\?search=Demo&provider=terminalen&leasingForm=operational&vehicleKind=combustion&sort=monthly$/,
    );

    await page.reload();
    await expect(
      page.getByLabel("Søg i køretøjsspecifikation eller dækket udbyder"),
    ).toHaveValue("Demo");
    await expect(page.getByLabel("Sortér tilbud")).toHaveValue("monthly");

    await page.getByLabel("Vælg Demo One Base til sammenligning").check();
    const detailLink = page.getByRole("link", {
      name: "Se detaljer for Demo One Base",
    });
    await detailLink.click();
    await expect(page).toHaveURL(
      /#\/offers\/terminalen%3Ademo%3Aone\?offers=terminalen%3Ademo%3Aone$/,
    );
    await expect(
      page.getByRole("heading", { name: "Demo One Base" }),
    ).toBeVisible();
    await expect(
      page.getByRole("img", { name: "Billede ikke tilgængeligt" }),
    ).toBeVisible();
    for (const heading of [
      "Køretøj",
      "Aftale",
      "Service",
      "Kontantstrøm",
      "Kilde",
    ]) {
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    }
    await expect(
      page.getByRole("region", { name: "Køretøj" }).getByRole("definition"),
    ).toHaveText([
      "Demo",
      "One",
      "Base",
      "2025",
      "Ikke relevant for denne aftale",
      "Hatchback",
      "0 km",
      "Forbrænding",
      "Benzin",
      "20 km/l",
    ]);
    await expect(
      page.getByRole("region", { name: "Aftale" }).getByRole("definition"),
    ).toHaveText([
      "Operationel privatleasing",
      "Privatleasing",
      "1 måneder",
      "10.000 km",
      "Bilen afleveres til udbyderen ved normalt udløb",
      "Udbyderen bærer restværdirisikoen",
      "Ikke oplyst af udbyderen",
      "1.000 kr.",
      "1.000 kr.",
      "Ingen betaling ved start er dokumenteret i datasættet.",
    ]);
    await expect(
      page.getByText("Ikke oplyst af udbyderen", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Ikke relevant for denne aftale", { exact: true }),
    ).toBeVisible();

    const sourceUrl = "https://example.test/terminalen/demo";
    await page.context().route(sourceUrl, (route) =>
      route.fulfill({
        contentType: "text/html",
        body: "<!doctype html><title>Source</title>",
      }),
    );
    const sourceLink = page.getByRole("link", {
      name: "Åbn den kanoniske tilbudskilde",
    });
    await expect(sourceLink).toHaveAttribute("href", sourceUrl);
    const popupPromise = page.waitForEvent("popup");
    await sourceLink.click();
    const popup = await popupPromise;
    await expect(popup).toHaveURL(sourceUrl);
    await popup.close();
    await page.context().unroute(sourceUrl);

    await page.getByRole("link", { name: "Tilbage til kataloget" }).click();
    await expect(page).toHaveURL(
      /#\/catalogue\?offers=terminalen%3Ademo%3Aone$/,
    );
    await expect(
      page.getByLabel("Vælg Demo One Base til sammenligning"),
    ).toBeChecked();

    await page.getByRole("link", { name: "Sammenlign 1 tilbud" }).click();
    await expect(page).toHaveURL(/#\/compare\?offers=terminalen%3Ademo%3Aone$/);
    await expect(
      page.getByRole("heading", { name: "Sammenlign tilbud" }),
    ).toBeVisible();
    await expect(
      page.getByRole("figure", { name: "Fælles søjlediagram for 1 tilbud" }),
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Demo One Base" }),
    ).toBeVisible();

    await page.reload();
    await expect(
      page.getByRole("columnheader", { name: "Demo One Base" }),
    ).toBeVisible();
    await page.goBack();
    await expect(page).toHaveURL(
      /#\/catalogue\?offers=terminalen%3Ademo%3Aone$/,
    );
    await expect(
      page.getByLabel("Vælg Demo One Base til sammenligning"),
    ).toBeChecked();
    await page.goForward();
    await expect(page).toHaveURL(/#\/compare\?offers=terminalen%3Ademo%3Aone$/);

    const providersLink = await visibleLink(page, "Udbydere");
    await providersLink.click();
    await expect(page).toHaveURL(
      /#\/providers\?offers=terminalen%3Ademo%3Aone$/,
    );
    await expect(
      page.getByRole("heading", { name: "Udbydere i det aktive katalog" }),
    ).toBeVisible();
    const providerCatalogueLink = page.getByRole("link", {
      name: "Se 1 katalogtilbud fra Terminalen",
    });
    await expect(providerCatalogueLink).toHaveAttribute(
      "href",
      /#\/catalogue\?provider=terminalen&offers=terminalen%3Ademo%3Aone$/,
    );
    await providerCatalogueLink.click();
    await expect(page).toHaveURL(
      /#\/catalogue\?provider=terminalen&offers=terminalen%3Ademo%3Aone$/,
    );
    await expect(
      page.getByRole("heading", { name: "Demo One Base" }),
    ).toBeVisible();
    await expectNoDocumentOverflow(page);
  });
}

test("the completed Site fails closed before shell composition when Catalogue startup is unavailable", async ({
  page,
}) => {
  await page.route("**/catalogue-dataset.json", (route) =>
    route.fulfill({ status: 503, body: "unavailable" }),
  );
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Kataloget kan ikke vises" }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(
    "Ingen katalogtilbud vises.",
  );
  await expect(page.getByRole("navigation")).toHaveCount(0);
  await expect(page.getByRole("link")).toHaveCount(0);
});
