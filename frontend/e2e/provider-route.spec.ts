import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

import {
  parseCatalogueDataset,
  type CatalogueDataset,
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

const scopedDataset: CatalogueDataset = parseCatalogueDataset({
  ...validDataset,
  providers: [
    validDataset.providers[0],
    {
      id: "deferred-provider",
      name: "Udskudt Provider",
      url: "https://deferred.example.test/",
      status: "inactive",
      reason: "deferred",
      explanation: "Kilden afventer ejerens næste vurdering.",
    },
    {
      id: "blocked-provider",
      name: "Blokeret Provider",
      url: "https://blocked.example.test/",
      status: "inactive",
      reason: "blocked",
      explanation: "Den offentlige kilde kan ikke indgå i denne udgivelse.",
    },
  ],
  quarantinedCandidates: [
    {
      offerIdentity: "terminalen:demo:quarantined",
      providerId: "terminalen",
      canonicalSourceUrl: "https://example.test/terminalen/quarantined",
      reasons: [
        {
          criterion: "supported_leasing_form",
          state: "unclear",
          code: "catalogue.leasing-form-unclear",
          evidence: [
            {
              sourceUrl: "https://example.test/terminalen/quarantined",
              excerpt: "Leasingformen fremgår ikke tydeligt.",
            },
          ],
        },
      ],
    },
  ],
});

async function serveDataset(page: Page, dataset: unknown) {
  await page.route("**/catalogue-dataset.json", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(dataset),
    }),
  );
}

test("the served Dataset exposes bounded Provider scope and returns to its Catalogue", async ({
  page,
}) => {
  await page.goto("/#/providers");

  await expect(
    page.getByRole("heading", { name: "Udbydere i det aktive katalog" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Udbyderregister" }),
  ).toBeVisible();

  const terminalenRow = page.getByRole("row").filter({ hasText: "Terminalen" });
  await expect(terminalenRow).toContainText("Aktiv");
  const catalogueLink = terminalenRow.getByRole("link", {
    name: "Se 1 katalogtilbud fra Terminalen",
  });
  await expect(catalogueLink).toHaveAttribute(
    "href",
    /#\/catalogue\?provider=terminalen$/,
  );

  await catalogueLink.click();
  await expect(page).toHaveURL(/#\/catalogue\?provider=terminalen$/);
  await expect(
    page.getByRole("heading", { name: "Leasingtilbud" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Demo One Base" }),
  ).toBeVisible();
});

test("Provider state and Dataset-derived counts stay truthful through Catalogue navigation", async ({
  page,
}) => {
  await serveDataset(page, scopedDataset);
  await page.goto("/#/providers?offers=terminalen%3Ademo%3Aone");

  const terminalenRow = page.getByRole("row").filter({ hasText: "Terminalen" });
  await expect(terminalenRow).toContainText("Aktiv");
  await expect(
    terminalenRow.getByRole("link", {
      name: "Se 1 katalogtilbud fra Terminalen",
    }),
  ).toBeVisible();
  const quarantineLink = terminalenRow.getByRole("link", {
    name: "Se 1 karantænesat kandidat fra Terminalen",
  });
  await expect(quarantineLink).toHaveAttribute(
    "href",
    /#\/catalogue\?provider=terminalen&view=quarantined&offers=terminalen%3Ademo%3Aone$/,
  );

  const deferredRow = page
    .getByRole("row")
    .filter({ hasText: "Udskudt Provider" });
  await expect(deferredRow).toContainText("Inaktiv · Udskudt");
  await expect(deferredRow).toContainText(
    "Kilden afventer ejerens næste vurdering.",
  );
  await expect(deferredRow.getByRole("link", { name: /katalogtilbud/ })).toHaveCount(
    0,
  );

  await quarantineLink.click();
  await expect(page).toHaveURL(
    /#\/catalogue\?provider=terminalen&view=quarantined&offers=terminalen%3Ademo%3Aone$/,
  );
  await expect(
    page.getByRole("heading", { name: "Karantænesatte kandidater" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "terminalen:demo:quarantined" }),
  ).toBeVisible();
  await expect(page.getByText("Leasingform", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Kan ikke afgøres ud fra kilden", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Åbn kandidatens førstehåndskilde" }),
  ).toHaveAttribute("href", "https://example.test/terminalen/quarantined");

  await page.getByRole("link", { name: "Tilbage til katalogtilbud" }).click();
  await expect(page).toHaveURL(
    /#\/catalogue\?provider=terminalen&offers=terminalen%3Ademo%3Aone$/,
  );
  await expect(
    page.getByRole("heading", { name: "Demo One Base" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Vælg Demo One Base til sammenligning"),
  ).toBeChecked();
});

test("Provider hash selection is validated, reloadable, and history-safe", async ({
  page,
}) => {
  await serveDataset(page, scopedDataset);
  await page.goto("/#/providers?provider=missing&unexpected=drop");
  await expect(page).toHaveURL(/#\/providers$/);

  const terminalenLink = page.getByRole("link", {
    name: "Vælg Terminalen",
  });
  await terminalenLink.click();
  await expect(page).toHaveURL(/#\/providers\?provider=terminalen$/);
  await expect(terminalenLink).toHaveAttribute("aria-current", "page");

  await page.reload();
  await expect(page).toHaveURL(/#\/providers\?provider=terminalen$/);
  await expect(terminalenLink).toHaveAttribute("aria-current", "page");

  await page.goBack();
  await expect(page).toHaveURL(/#\/providers$/);
  await page.goForward();
  await expect(page).toHaveURL(/#\/providers\?provider=terminalen$/);
  await expect(terminalenLink).toHaveAttribute("aria-current", "page");
});

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`${viewport.name} Provider Overview is keyboard and overflow safe`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await serveDataset(page, scopedDataset);
    await page.goto("/#/providers");

    if (viewport.name === "desktop") {
      await expect(page.getByRole("table")).toBeVisible();
    } else {
      await expect(page.getByRole("table")).toBeHidden();
      await expect(
        page.getByRole("article").filter({ hasText: "Blokeret Provider" }),
      ).toBeVisible();
    }

    const terminalenLink = page.getByRole("link", {
      name: "Vælg Terminalen",
    });
    await terminalenLink.focus();
    await expect(terminalenLink).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/#\/providers\?provider=terminalen$/);
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth <= window.innerWidth &&
          document.body.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  });
}
