import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { createLowStockProductViaApi, createCustomerViaApi, getProductViaApi } from "./helpers";

test.describe("inventory views & exports", () => {
  test("low stock view lists at/below-threshold products", async ({ page, request }) => {
    const low = await createLowStockProductViaApi(request, "E2E-LOW-1", "E2E Low Stock Item");

    await page.goto("/inventory?tab=low-stock");
    const row = page.getByRole("row").filter({ hasText: low.sku });
    await expect(row).toBeVisible();
    await expect(row).toContainText("Low");
    await expect(row).toContainText("2");
    await expect(row).toContainText("5");
  });

  test("healthy products do not appear in the low stock view", async ({ page, request }) => {
    await page.goto("/inventory?tab=low-stock");
    // E2E-LAMP ended at stock 12 with threshold 4 — not low
    await expect(page.getByRole("row").filter({ hasText: "E2E-LAMP" })).toHaveCount(0);
  });

  test("products CSV export downloads and contains the created product", async ({
    page,
    request,
  }, testInfo) => {
    testInfo.setTimeout(30_000);
    await page.goto("/products");

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Export CSV" }).click(),
    ]);
    const path = await download.path();
    expect(path, "browser must provide a download path").toBeTruthy();
    const content = readFileSync(path!, "utf8");

    expect(content.split("\n")[0]).toContain("sku,name,category");
    expect(content).toContain("E2E-LAMP");
  });

  test("orders CSV export contains the order line", async ({ page, request }, testInfo) => {
    testInfo.setTimeout(30_000);
    // ensure a deterministic order exists (created by the core flow when it
    // runs; recreated here if this spec runs standalone)
    const ordersResponse = await request.get("/api/orders?page_size=1");
    const orders = (await ordersResponse.json()) as { total: number };
    if (orders.total === 0) {
      const customer = await createCustomerViaApi(request, "E2E Fallback");
      const lamp = await getProductViaApi(request, "E2E-LAMP");
      await request.post("/api/orders", {
        data: {
          customer_id: customer.id,
          items: [{ product_id: lamp.id, quantity: 1 }],
        },
      });
    }

    await page.goto("/orders");
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Export CSV" }).click(),
    ]);
    const content = readFileSync((await download.path())!, "utf8");
    expect(content).toContain("order_number,order_date,customer,status,product_sku");
    expect(content).toContain("E2E-LAMP");
  });
});
