/**
 * The core business chain, verified end-to-end in a real browser:
 *
 *   Create Product -> Stock In -> Stock Out -> Create Draft Order ->
 *   Confirm Order -> inventory decreases -> Cancel Order -> inventory restores
 *
 * Runs against a dedicated empty database (see global-setup); the backend
 * auto-migrates on startup, so no local data is required.
 */
import { expect, test } from "@playwright/test";
import {
  createCustomerViaApi,
  currentStockStat,
  expectToast,
  getProductViaApi,
} from "./helpers";

const SKU = "E2E-LAMP";

test.describe.serial("core business flow", () => {
  let customerName = "";
  let orderId = 0;

  test("create product via UI with initial stock", async ({ page }) => {
    await page.goto("/products");
    await page.getByRole("button", { name: "New Product" }).click();

    await page.getByLabel("SKU").fill(SKU);
    await page.getByLabel("Name").fill("E2E Desk Lamp");
    await page.getByLabel("Unit price").fill("30.00");
    await page.getByLabel("Cost price").fill("15.00");
    await page.getByLabel("Initial stock").fill("10");
    await page.getByLabel("Low stock threshold").fill("4");
    await page.getByRole("button", { name: "Create product" }).click();

    await expectToast(page, "Product created.");
    const row = page.getByRole("row").filter({ hasText: SKU });
    await expect(row).toBeVisible();
    await expect(row).toContainText("10");
  });

  test("stock in increases stock and records a movement", async ({ page, request }) => {
    const product = await getProductViaApi(request, SKU);
    await page.goto(`/products/${product.id}`);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("E2E Desk Lamp");

    await page.getByRole("button", { name: "Stock In" }).click();
    await page.getByRole("spinbutton", { name: "Quantity" }).fill("5");
    await page.getByRole("button", { name: "Apply" }).click();
    await expectToast(page, `${SKU}: 10 → 15`);
    await expect(currentStockStat(page)).toContainText("15");

    await expect(
      page.locator("tbody tr").filter({ hasText: "Stock In" }).filter({ hasText: "+5" }),
    ).toBeVisible();
  });

  test("stock out decreases stock and rejects going below zero", async ({ page, request }) => {
    const product = await getProductViaApi(request, SKU);
    await page.goto(`/products/${product.id}`);

    await page.getByRole("button", { name: "Stock Out" }).click();
    await page.getByRole("spinbutton", { name: "Quantity" }).fill("3");
    await page.getByRole("button", { name: "Apply" }).click();
    await expectToast(page, `${SKU}: 15 → 12`);
    await expect(currentStockStat(page)).toContainText("12");

    // requesting more than available -> explicit rejection, stock unchanged
    await page.getByRole("button", { name: "Stock Out" }).click();
    await page.getByRole("spinbutton", { name: "Quantity" }).fill("999");
    await page.getByRole("button", { name: "Apply" }).click();
    await expect(page.locator(".modal .field-error")).toContainText(/insufficient/i);
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(currentStockStat(page)).toContainText("12");
  });

  test("create draft order via UI", async ({ page, request }) => {
    const customer = await createCustomerViaApi(request, "E2E Customer");
    customerName = customer.name;
    const product = await getProductViaApi(request, SKU);

    await page.goto("/orders/new");
    await page.getByLabel("Customer").selectOption({ label: customerName });
    const line = page.getByTestId("order-line-0");
    await line.getByLabel("Product").selectOption({ value: String(product.id) });
    await line.getByLabel("Quantity").fill("4");
    await expect(page.getByText("Order total:")).toContainText("$120.00"); // 4 x 30.00

    await page.getByRole("button", { name: "Create draft order" }).click();
    await page.waitForURL(/\/orders\/\d+/);
    orderId = Number(page.url().match(/\/orders\/(\d+)/)?.[1]);

    await expect(page.getByRole("heading", { level: 1 })).toContainText("Draft");
    await expect(page.getByText("Total:")).toContainText("$120.00");

    const after = await getProductViaApi(request, SKU);
    expect(after.stock_quantity).toBe(12); // a draft reserves nothing
  });

  test("confirm order deducts stock and writes an OUT movement", async ({ page, request }) => {
    await page.goto(`/orders/${orderId}`);
    await page.getByRole("button", { name: "Confirm order" }).click();
    await expectToast(page, "confirmed — stock deducted");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Confirmed");

    const product = await getProductViaApi(request, SKU);
    await page.goto(`/products/${product.id}`);
    await expect(currentStockStat(page)).toContainText("8"); // 12 - 4
    const out = page.locator("tbody tr").filter({ hasText: "Stock Out" }).first();
    await expect(out).toContainText(/order #\d+/);
    await expect(out).toContainText("-4");
  });

  test("cancel confirmed order restores stock with an IN movement", async ({ page, request }) => {
    await page.goto(`/orders/${orderId}`);
    await page.getByRole("button", { name: "Cancel order" }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText(/stock will be restored/i);
    await dialog.getByRole("button", { name: "Cancel order" }).click();

    await expectToast(page, "cancelled");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Cancelled");

    const product = await getProductViaApi(request, SKU);
    await page.goto(`/products/${product.id}`);
    await expect(currentStockStat(page)).toContainText("12"); // restored
    const restore = page.locator("tbody tr").filter({ hasText: "Stock In" }).first();
    await expect(restore).toContainText("+4");
    await expect(restore).toContainText(/restored/i);
  });
});
