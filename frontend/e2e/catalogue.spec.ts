import { expect, test } from "@playwright/test";

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

    await page.getByText("Se beregning og kildegrundlag").click();
    await expect(page.getByText("Førstegangsydelse 15.990 kr.")).toBeVisible();
    await expect(
      page.getByText("Månedlig ydelse 3.795 kr. i 36 måneder."),
    ).toBeVisible();

    const hasPageOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(hasPageOverflow).toBe(false);
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
