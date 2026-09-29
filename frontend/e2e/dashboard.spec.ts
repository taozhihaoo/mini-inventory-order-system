import { expect, test } from "@playwright/test";

test.describe("Dashboard", () => {
  test("loads with stat cards and content sections", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "Dashboard" })).toBeVisible();

    for (const label of [
      "Total Products",
      "Low Stock",
      "Inventory Value",
      "Total Orders",
      "Sales Amount",
    ]) {
      await expect(page.locator(".stat-grid").getByText(label, { exact: true })).toBeVisible();
    }

    await expect(page.getByRole("heading", { name: "Recent Orders" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Low Stock" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recent Stock Movements" })).toBeVisible();
  });
});
