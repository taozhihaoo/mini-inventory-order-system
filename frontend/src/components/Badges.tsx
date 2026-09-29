import type { OrderStatus } from "../types";

const ORDER_LABELS: Record<OrderStatus, string> = {
  draft: "Draft",
  confirmed: "Confirmed",
  completed: "Completed",
  cancelled: "Cancelled",
};

export function StatusBadge({ status }: { status: OrderStatus | string }) {
  const label = ORDER_LABELS[status as OrderStatus] ?? status;
  return <span className={`badge badge-${status}`}>{label}</span>;
}

export function MovementBadge({ type }: { type: string }) {
  const label = type === "ADJUSTMENT" ? "Adjust" : type === "IN" ? "Stock In" : "Stock Out";
  return <span className={`badge badge-${type.toLowerCase()}`}>{label}</span>;
}

export function LowStockBadge({ stock, threshold }: { stock: number; threshold: number }) {
  if (stock > threshold) return null;
  return <span className="badge badge-low">{stock === 0 ? "Out of stock" : "Low"}</span>;
}

export function ActiveBadge({ active }: { active: boolean }) {
  return active ? (
    <span className="badge badge-completed">Active</span>
  ) : (
    <span className="badge badge-inactive">Inactive</span>
  );
}
