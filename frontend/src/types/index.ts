export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Category {
  id: number;
  name: string;
  description: string | null;
  product_count: number;
  created_at: string;
}

export interface Supplier {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  notes: string | null;
  product_count: number;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  notes: string | null;
  order_count: number;
  created_at: string;
  updated_at: string;
}

export interface CategoryBrief {
  id: number;
  name: string;
}

export interface SupplierRef {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  notes: string | null;
  product_count: number;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  category_id: number | null;
  supplier_id: number | null;
  unit_price: number;
  cost_price: number | null;
  stock_quantity: number;
  low_stock_threshold: number;
  is_active: boolean;
  is_low_stock: boolean;
  category: CategoryBrief | null;
  supplier: SupplierRef | null;
  created_at: string;
  updated_at: string;
}

export type MovementType = "IN" | "OUT" | "ADJUSTMENT";

export interface StockMovement {
  id: number;
  product_id: number;
  product: { id: number; sku: string; name: string; unit_price: number } | null;
  movement_type: MovementType;
  quantity: number;
  stock_after: number;
  reference_type: string | null;
  reference_id: number | null;
  note: string | null;
  created_at: string;
}

export interface StockOperationResult {
  movement_type: string;
  product_id: number;
  sku: string;
  name: string;
  previous_quantity: number;
  new_quantity: number;
  change: number;
  movement_id: number;
}

export type OrderStatus = "draft" | "confirmed" | "completed" | "cancelled";

export interface OrderItem {
  id: number;
  product_id: number;
  product: { id: number; sku: string; name: string; unit_price: number };
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface CustomerBrief {
  id: number;
  name: string;
  email: string | null;
}

export interface Order {
  id: number;
  order_number: string;
  customer_id: number;
  customer: CustomerBrief;
  status: OrderStatus;
  total_amount: number;
  items: OrderItem[];
  created_at: string;
  updated_at: string;
}

export interface OrderListItem {
  id: number;
  order_number: string;
  customer_id: number;
  customer: CustomerBrief;
  status: OrderStatus;
  total_amount: number;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProductImportSummary {
  total_rows: number;
  imported: number;
  skipped: number;
  errors: { row: number; message: string }[];
}

export interface DashboardSummary {
  total_products: number;
  active_products: number;
  low_stock_products: number;
  inventory_value: number;
  total_orders: number;
  confirmed_orders: number;
  completed_orders: number;
  sales_amount: number;
  recent_orders: OrderListItem[];
  low_stock_list: Product[];
  recent_movements: StockMovement[];
}
