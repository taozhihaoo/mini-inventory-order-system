export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const normalized = iso.endsWith("Z") ? iso : `${iso}Z`; // backend stores naive UTC
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(normalized));
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const normalized = iso.endsWith("Z") ? iso : `${iso}Z`;
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(normalized));
}

export function formatQuantityChange(movementType: string, quantity: number): string {
  if (movementType === "IN") return `+${quantity}`;
  if (movementType === "OUT") return `-${quantity}`;
  return quantity > 0 ? `+${quantity}` : `${quantity}`;
}
