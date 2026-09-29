import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAsync, useDebouncedValue } from "../hooks/useAsync";
import { inventoryApi, inventoryExports, productsApi } from "../api/endpoints";
import { ApiError } from "../api/client";
import { LowStockBadge, MovementBadge } from "../components/Badges";
import { Field, Select, TextArea } from "../components/Fields";
import { Pagination } from "../components/Pagination";
import { useToast } from "../components/Toasts";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { formatDateTime, formatMoney, formatQuantityChange } from "../utils/format";
import type { Product, StockOperationResult } from "../types";

type Tab = "operations" | "movements" | "low-stock";

export function InventoryPage() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const tab: Tab =
    tabParam === "movements" || tabParam === "low-stock" ? (tabParam as Tab) : "operations";

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">Warehouse</div>
          <h1>Inventory</h1>
          <p className="subtitle">Stock operations are recorded as movements and keep a full audit trail.</p>
        </div>
        <div className="page-actions">
          <button
            type="button"
            className="btn"
            onClick={() => inventoryExports.movementsCsv().catch((err) => toast.error(err.message))}
          >
            Export movements CSV
          </button>
        </div>
      </div>

      <div className="tabs">
        <button
          type="button"
          className={`tab${tab === "operations" ? " tab-active" : ""}`}
          onClick={() => setSearchParams({})}
        >
          Stock Operations
        </button>
        <button
          type="button"
          className={`tab${tab === "movements" ? " tab-active" : ""}`}
          onClick={() => setSearchParams({ tab: "movements" })}
        >
          Movements
        </button>
        <button
          type="button"
          className={`tab${tab === "low-stock" ? " tab-active" : ""}`}
          onClick={() => setSearchParams({ tab: "low-stock" })}
        >
          Low Stock
        </button>
      </div>

      {tab === "operations" && <OperationsTab />}
      {tab === "movements" && <MovementsTab />}
      {tab === "low-stock" && <LowStockTab />}
    </div>
  );
}

// ---------------------------------------------------------------- operations

function OperationsTab() {
  
  const [search, setSearch] = useState("");
  const debounced = useDebouncedValue(search);
  const [productId, setProductId] = useState("");
  const [op, setOp] = useState<"IN" | "OUT" | "ADJUST">("IN");
  const [quantity, setQuantity] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<StockOperationResult | null>(null);

  const products = useAsync(
    () => productsApi.list({ page: 1, page_size: 100, is_active: true, search: debounced || undefined }),
    [debounced],
  );

  useEffect(() => {
    setProductId("");
  }, [debounced]);

  const selected = products.data?.items.find((p: Product) => String(p.id) === productId) ?? null;

  const submit = async () => {
    setError(null);
    if (!selected) {
      setError("Select a product first.");
      return;
    }
    const parsed = Number(quantity);
    if (!quantity || !Number.isInteger(parsed)) {
      setError("Enter a whole number.");
      return;
    }
    if (op !== "ADJUST" && parsed <= 0) {
      setError("Quantity must be greater than 0.");
      return;
    }
    if (op === "ADJUST" && parsed < 0) {
      setError("Counted quantity cannot be negative.");
      return;
    }
    setSubmitting(true);
    try {
      const trimmed = note.trim();
      const outcome =
        op === "IN"
          ? await inventoryApi.stockIn(selected.id, parsed, trimmed || null)
          : op === "OUT"
            ? await inventoryApi.stockOut(selected.id, parsed, trimmed || null)
            : await inventoryApi.stockAdjust(selected.id, parsed, trimmed || null);
      setResult(outcome);
      setQuantity("");
      setNote("");
      products.refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Operation failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="two-col">
      <div className="card">
        <div className="card-header">
          <h2>New stock operation</h2>
        </div>
        <div className="card-body">
          {result && (
            <div className="result-banner">
              {result.movement_type === "ADJUSTMENT" ? "Adjusted" : result.movement_type === "IN" ? "Stocked in" : "Stocked out"}{" "}
              <strong>{selected?.sku}</strong>: {result.previous_quantity} → <strong>{result.new_quantity}</strong>{" "}
              (movement #{result.movement_id})
            </div>
          )}
          {error && <div className="form-error">{error}</div>}
          <Field label="Search product (SKU or name)">
            <input
              className="input"
              value={search}
              placeholder="Type to filter active products…"
              onChange={(event) => setSearch(event.target.value)}
            />
          </Field>
          <Field label="Product" required>
            <Select
              value={productId}
              onChange={setProductId}
              disabled={products.loading}
              options={[
                { value: "", label: products.loading ? "Loading products…" : "— Select product —" },
                ...(products.data?.items ?? []).map((p: Product) => ({
                  value: String(p.id),
                  label: `${p.sku} · ${p.name} (stock ${p.stock_quantity})`,
                })),
              ]}
            />
          </Field>
          <div className="form-grid">
            <Field label="Operation">
              <Select
                value={op}
                onChange={(value) => setOp(value as "IN" | "OUT" | "ADJUST")}
                options={[
                  { value: "IN", label: "Stock In" },
                  { value: "OUT", label: "Stock Out" },
                  { value: "ADJUST", label: "Adjustment" },
                ]}
              />
            </Field>
            <Field label={op === "ADJUST" ? "Counted quantity (new total)" : "Quantity"} required>
              <input
                className="input"
                type="number"
                min={op === "ADJUST" ? 0 : 1}
                step={1}
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
              />
            </Field>
            <div className="span-2">
              <Field label="Note">
                <TextArea value={note} onChange={setNote} rows={2} placeholder="Optional reference…" />
              </Field>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" className="btn btn-primary" onClick={submit} disabled={submitting}>
              {submitting ? "Applying…" : "Apply operation"}
            </button>
            {selected && (
              <Link className="btn" to={`/products/${selected.id}`}>
                View product detail
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>How stock works</h2>
        </div>
        <div className="card-body muted" style={{ lineHeight: 1.7 }}>
          <p>
            <strong>Stock In</strong> adds quantity (purchases, returns to stock).
          </p>
          <p>
            <strong>Stock Out</strong> removes quantity and is rejected if it would drive stock below zero.
          </p>
          <p>
            <strong>Adjustment</strong> sets the stock to an absolute counted quantity (cycle counts, corrections).
          </p>
          <p>
            Every operation writes a <strong>StockMovement</strong> in the same database transaction as the stock
            change — the history under <em>Movements</em> is always complete.
          </p>
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- movements

function MovementsTab() {
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(1);

  const movements = useAsync(
    () => inventoryApi.movements({ page, page_size: 15, movement_type: typeFilter || null }),
    [page, typeFilter],
  );
  const data = movements.data;

  return (
    <div className="card">
      <div className="card-header">
        <h2>Stock movements</h2>
        <div style={{ width: 200 }}>
          <Select
            value={typeFilter}
            onChange={(value) => {
              setTypeFilter(value);
              setPage(1);
            }}
            options={[
              { value: "", label: "All types" },
              { value: "IN", label: "Stock In" },
              { value: "OUT", label: "Stock Out" },
              { value: "ADJUSTMENT", label: "Adjustment" },
            ]}
          />
        </div>
      </div>
      {movements.loading ? (
        <LoadingState />
      ) : movements.error ? (
        <ErrorState error={movements.error} onRetry={movements.refetch} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState title="No movements" hint="Stock operations and confirmed orders will appear here." />
      ) : (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Product</th>
                  <th>Type</th>
                  <th className="num">Change</th>
                  <th className="num">Stock after</th>
                  <th>Reference</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((movement) => (
                  <tr key={movement.id}>
                    <td className="muted">{formatDateTime(movement.created_at)}</td>
                    <td>
                      <Link to={`/products/${movement.product_id}`}>
                        {movement.product?.name ?? `#${movement.product_id}`}
                      </Link>
                      <div className="mono muted" style={{ fontSize: 12 }}>
                        {movement.product?.sku}
                      </div>
                    </td>
                    <td>
                      <MovementBadge type={movement.movement_type} />
                    </td>
                    <td className="num">{formatQuantityChange(movement.movement_type, movement.quantity)}</td>
                    <td className="num">{movement.stock_after}</td>
                    <td>
                      {movement.reference_type === "order" && movement.reference_id ? (
                        <Link to={`/orders/${movement.reference_id}`} className="mono">
                          order #{movement.reference_id}
                        </Link>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td className="muted">{movement.note ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={data.page} totalPages={data.total_pages} total={data.total} onChange={setPage} />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- low stock

function LowStockTab() {
  const low = useAsync(() => inventoryApi.lowStock(), []);

  return (
    <div className="card">
      <div className="card-header">
        <h2>Low stock products</h2>
        <span className="muted">stock ≤ low stock threshold, active products</span>
      </div>
      {low.loading ? (
        <LoadingState />
      ) : low.error ? (
        <ErrorState error={low.error} onRetry={low.refetch} />
      ) : !low.data || low.data.length === 0 ? (
        <EmptyState title="Nothing is low on stock" hint="All active products are above their threshold." />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th>Category</th>
                <th className="num">Current stock</th>
                <th className="num">Threshold</th>
                <th>Status</th>
                <th className="num">Unit price</th>
                <th className="actions">Action</th>
              </tr>
            </thead>
            <tbody>
              {low.data.map((product) => (
                <tr key={product.id}>
                  <td>
                    <Link to={`/products/${product.id}`}>{product.name}</Link>
                  </td>
                  <td className="mono">{product.sku}</td>
                  <td>{product.category?.name ?? <span className="muted">—</span>}</td>
                  <td className="num">{product.stock_quantity}</td>
                  <td className="num">{product.low_stock_threshold}</td>
                  <td>
                    <LowStockBadge stock={product.stock_quantity} threshold={product.low_stock_threshold} />
                  </td>
                  <td className="num">{formatMoney(product.unit_price)}</td>
                  <td className="actions">
                    <Link className="btn btn-sm" to={`/products/${product.id}`}>
                      Restock
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
