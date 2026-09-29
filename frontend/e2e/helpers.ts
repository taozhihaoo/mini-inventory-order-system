/**
 * Shared helpers for E2E tests. API helpers go through the frontend's own
 * /api proxy, exactly like the browser does.
 */
import type { APIRequestContext, Page } from "@playwright/test";

export async function createCustomerViaApi(request: APIRequestContext, name: string) {
  const response = await request.post("/api/customers", {
    data: { name, email: `${name.toLowerCase().replace(/\s+/g, "")}@example.com` },
  });
  if (!response.ok()) throw new Error(`createCustomer failed: ${response.status()}`);
  return (await response.json()) as { id: number; name: string };
}

export async function getProductViaApi(request: APIRequestContext, sku: string) {
  const response = await request.get(`/api/products?search=${encodeURIComponent(sku)}`);
  if (!response.ok()) throw new Error(`product search failed: ${response.status()}`);
  const text = await response.text();
  const page = JSON.parse(text) as {
    items: { id: number; sku: string; stock_quantity: number }[];
    total: number;
  };
  const match = page.items.find((item) => item.sku === sku);
  if (!match) throw new Error(`product ${sku} not found (total=${page.total}, body=${text.slice(0, 300)})`);
  return match;
}

export async function createLowStockProductViaApi(
  request: APIRequestContext,
  sku: string,
  name: string,
) {
  const response = await request.post("/api/products", {
    data: {
      sku,
      name,
      unit_price: "9.90",
      stock_quantity: 2,
      low_stock_threshold: 5,
    },
  });
  if (!response.ok()) throw new Error(`createLowStockProduct failed: ${response.status()}`);
  return (await response.json()) as { id: number; sku: string };
}

/** Reads the "Current stock" figure on the product detail page. */
export function currentStockStat(page: Page) {
  return page.locator(".detail-stat").filter({ hasText: "Current stock" });
}

/** Wait for and assert the newest toast message. */
export async function expectToast(page: Page, text: string | RegExp) {
  const toasts = page.getByRole("status");
  await toasts.getByText(text).waitFor({ state: "visible", timeout: 7000 });
}
