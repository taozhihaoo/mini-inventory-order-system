import { api, buildQuery, downloadFile } from "./client";

import type {
  Category,
  Customer,
  DashboardSummary,
  Order,
  OrderListItem,
  OrderStatus,
  Page,
  Product,
  ProductImportSummary,
  StockMovement,
  StockOperationResult,
  Supplier,
} from "../types";

// ---- Products -------------------------------------------------------------

export interface ProductFilters {
  page?: number;
  page_size?: number;
  search?: string;
  category_id?: number | null;
  supplier_id?: number | null;
  is_active?: boolean | null;
  low_stock?: boolean | null;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}

export const productsApi = {
  list: (filters: ProductFilters = {}) => api.get<Page<Product>>(`/products${buildQuery(filters)}`),
  get: (id: number) => api.get<Product>(`/products/${id}`),
  create: (body: Record<string, unknown>) => api.post<Product>("/products", body),
  update: (id: number, body: Record<string, unknown>) => api.put<Product>(`/products/${id}`, body),
  remove: (id: number) => api.delete<void>(`/products/${id}`),
  movements: (id: number, page = 1) =>
    api.get<Page<StockMovement>>(`/products/${id}/stock/movements?page=${page}`),
  orders: (id: number) => api.get<OrderListItem[]>(`/products/${id}/orders`),
  importCsv: (file: File) => api.upload<ProductImportSummary>("/products/import", file),
  exportCsv: () => downloadFile("/products/export.csv", "products.csv"),
};

// ---- Inventory ------------------------------------------------------------

export const inventoryApi = {
  stockIn: (productId: number, quantity: number, note: string | null) =>
    api.post<StockOperationResult>(`/products/${productId}/stock/in`, { quantity, note }),
  stockOut: (productId: number, quantity: number, note: string | null) =>
    api.post<StockOperationResult>(`/products/${productId}/stock/out`, { quantity, note }),
  stockAdjust: (productId: number, newQuantity: number, note: string | null) =>
    api.post<StockOperationResult>(`/products/${productId}/stock/adjust`, { new_quantity: newQuantity, note }),
  movements: (filters: { page?: number; page_size?: number; product_id?: number | null; movement_type?: string | null } = {}) =>
    api.get<Page<StockMovement>>(`/inventory/movements${buildQuery(filters)}`),
  lowStock: () => api.get<Product[]>("/inventory/low-stock"),
};

// ---- Categories / Suppliers / Customers -----------------------------------

export const categoriesApi = {
  list: (params: { page?: number; page_size?: number; search?: string } = {}) =>
    api.get<Page<Category>>(`/categories${buildQuery(params)}`),
  create: (body: Record<string, unknown>) => api.post<Category>("/categories", body),
  update: (id: number, body: Record<string, unknown>) => api.put<Category>(`/categories/${id}`, body),
  remove: (id: number) => api.delete<void>(`/categories/${id}`),
};

export const suppliersApi = {
  list: (params: { page?: number; page_size?: number; search?: string } = {}) =>
    api.get<Page<Supplier>>(`/suppliers${buildQuery(params)}`),
  create: (body: Record<string, unknown>) => api.post<Supplier>("/suppliers", body),
  update: (id: number, body: Record<string, unknown>) => api.put<Supplier>(`/suppliers/${id}`, body),
  remove: (id: number) => api.delete<void>(`/suppliers/${id}`),
};

export const customersApi = {
  list: (params: { page?: number; page_size?: number; search?: string } = {}) =>
    api.get<Page<Customer>>(`/customers${buildQuery(params)}`),
  create: (body: Record<string, unknown>) => api.post<Customer>("/customers", body),
  update: (id: number, body: Record<string, unknown>) => api.put<Customer>(`/customers/${id}`, body),
  remove: (id: number) => api.delete<void>(`/customers/${id}`),
};

// ---- Orders ---------------------------------------------------------------

export interface OrderFilters {
  page?: number;
  page_size?: number;
  search?: string;
  status?: OrderStatus | null;
  customer_id?: number | null;
  date_from?: string | null;
  date_to?: string | null;
}

export const ordersApi = {
  list: (filters: OrderFilters = {}) => api.get<Page<OrderListItem>>(`/orders${buildQuery(filters)}`),
  get: (id: number) => api.get<Order>(`/orders/${id}`),
  create: (customerId: number, items: { product_id: number; quantity: number }[]) =>
    api.post<Order>("/orders", { customer_id: customerId, items }),
  confirm: (id: number) => api.post<{ status: string }>(`/orders/${id}/confirm`),
  cancel: (id: number) => api.post<{ status: string }>(`/orders/${id}/cancel`),
  complete: (id: number) => api.post<{ status: string }>(`/orders/${id}/complete`),
  exportCsv: () => downloadFile("/orders/export.csv", "orders.csv"),
};

export const inventoryExports = {
  movementsCsv: () => downloadFile("/inventory/movements/export.csv", "stock_movements.csv"),
};

// ---- Dashboard ------------------------------------------------------------

export const dashboardApi = {
  summary: () => api.get<DashboardSummary>("/dashboard/summary"),
};
