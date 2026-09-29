import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAsync } from "../hooks/useAsync";
import { customersApi, ordersApi, productsApi } from "../api/endpoints";
import { ApiError } from "../api/client";
import { Field, Select } from "../components/Fields";
import { useToast } from "../components/Toasts";
import { formatMoney } from "../utils/format";
import type { Product } from "../types";

interface LineDraft {
  key: number;
  productId: string;
  quantity: string;
}

let lineKey = 0;
function newLine(): LineDraft {
  lineKey += 1;
  return { key: lineKey, productId: "", quantity: "1" };
}

export function OrderNewPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const customers = useAsync(() => customersApi.list({ page_size: 100 }), []);
  const products = useAsync(() => productsApi.list({ page: 1, page_size: 100, is_active: true }), []);

  const [customerId, setCustomerId] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([newLine()]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const productById = (id: string): Product | undefined =>
    products.data?.items.find((p: Product) => String(p.id) === id);

  const total = lines.reduce((sum, line) => {
    const product = productById(line.productId);
    const quantity = Number(line.quantity);
    if (!product || !Number.isInteger(quantity) || quantity <= 0) return sum;
    return sum + product.unit_price * quantity;
  }, 0);

  const setLine = (key: number, patch: Partial<LineDraft>) => {
    setLines((current) => current.map((line) => (line.key === key ? { ...line, ...patch } : line)));
  };

  const submit = async () => {
    setError(null);
    if (!customerId) {
      setError("Select a customer.");
      return;
    }
    const items = lines
      .filter((line) => line.productId)
      .map((line) => ({ product_id: Number(line.productId), quantity: Number(line.quantity) }));
    if (items.length === 0) {
      setError("Add at least one product line.");
      return;
    }
    for (const item of items) {
      if (!Number.isInteger(item.quantity) || item.quantity <= 0) {
        setError("Every line needs a quantity of 1 or more.");
        return;
      }
    }
    setSubmitting(true);
    try {
      const order = await ordersApi.create(Number(customerId), items);
      toast.success(`Draft order ${order.order_number} created.`);
      navigate(`/orders/${order.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create order.");
      setSubmitting(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">
            <Link to="/orders">Orders</Link> / New
          </div>
          <h1>New order</h1>
          <p className="subtitle">
            The order is saved as a draft. Stock is deducted only when you confirm it.
          </p>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          {error && <div className="form-error">{error}</div>}
          <div className="form-grid">
            <Field label="Customer" required>
              <Select
                value={customerId}
                onChange={setCustomerId}
                options={[
                  { value: "", label: "— Select customer —" },
                  ...(customers.data?.items ?? []).map((c) => ({ value: String(c.id), label: c.name })),
                ]}
              />
            </Field>
          </div>

          <h2 style={{ margin: "18px 0 10px" }}>Items</h2>
          <div className="order-items-editor">
            {lines.map((line) => {
              const product = productById(line.productId);
              const quantity = Number(line.quantity);
              const lineTotal =
                product && Number.isInteger(quantity) && quantity > 0 ? product.unit_price * quantity : 0;
              return (
                <div
                  key={line.key}
                  className="form-grid"
                  style={{ alignItems: "end", marginBottom: 10 }}
                >
                  <Field label="Product" required>
                    <Select
                      value={line.productId}
                      onChange={(value) => setLine(line.key, { productId: value })}
                      options={[
                        { value: "", label: "— Select product —" },
                        ...(products.data?.items ?? []).map((p: Product) => ({
                          value: String(p.id),
                          label: `${p.sku} · ${p.name} (${formatMoney(p.unit_price)}, stock ${p.stock_quantity})`,
                        })),
                      ]}
                    />
                  </Field>
                  <Field label="Quantity" required>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      step={1}
                      value={line.quantity}
                      onChange={(event) => setLine(line.key, { quantity: event.target.value })}
                    />
                  </Field>
                  <Field label="Line total">
                    <input className="input" value={formatMoney(lineTotal)} disabled />
                  </Field>
                  <div style={{ paddingBottom: 12 }}>
                    <button
                      type="button"
                      className="btn btn-danger-outline"
                      disabled={lines.length === 1}
                      onClick={() => setLines((current) => current.filter((item) => item.key !== line.key))}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
            <button type="button" className="btn" onClick={() => setLines((current) => [...current, newLine()])}>
              + Add line
            </button>
            <div>
              <span className="muted" style={{ marginRight: 12 }}>
                Order total: <strong style={{ fontSize: 17, color: "var(--text)" }}>{formatMoney(total)}</strong>
              </span>
              <button type="button" className="btn btn-primary" onClick={submit} disabled={submitting}>
                {submitting ? "Creating…" : "Create draft order"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
