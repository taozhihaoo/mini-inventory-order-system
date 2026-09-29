import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAsync } from "../hooks/useAsync";
import { ordersApi } from "../api/endpoints";
import { ApiError } from "../api/client";
import { StatusBadge } from "../components/Badges";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { useToast } from "../components/Toasts";
import { ErrorState, LoadingState } from "../components/States";
import { formatDateTime, formatMoney } from "../utils/format";

type Action = "cancel" | "complete" | null;

export function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const orderId = Number(id);
  const toast = useToast();

  const [pendingAction, setPendingAction] = useState<Action>(null);
  const [acting, setActing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const order = useAsync(() => ordersApi.get(orderId), [orderId]);

  if (order.loading) return <LoadingState label="Loading order…" />;
  if (order.error) return <ErrorState error={order.error} onRetry={order.refetch} />;
  const data = order.data;
  if (!data) return null;

  const runAction = async (kind: "confirm" | "cancel" | "complete") => {
    setActing(true);
    setActionError(null);
    try {
      if (kind === "confirm") {
        await ordersApi.confirm(data.id);
        toast.success(`Order ${data.order_number} confirmed — stock deducted.`);
      } else if (kind === "cancel") {
        await ordersApi.cancel(data.id);
        toast.success(`Order ${data.order_number} cancelled.`);
      } else {
        await ordersApi.complete(data.id);
        toast.success(`Order ${data.order_number} completed.`);
      }
      setPendingAction(null);
      order.refetch();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Action failed.";
      setActionError(message);
      toast.error(message);
    } finally {
      setActing(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">
            <Link to="/orders">Orders</Link> / {data.order_number}
          </div>
          <h1>
            <span className="mono">{data.order_number}</span>{" "}
            <span className="inline-badges" style={{ verticalAlign: "middle" }}>
              <StatusBadge status={data.status} />
            </span>
          </h1>
          <p className="subtitle">
            {data.customer.name} · created {formatDateTime(data.created_at)}
          </p>
        </div>
        <div className="page-actions">
          {data.status === "draft" && (
            <button type="button" className="btn btn-primary" onClick={() => runAction("confirm")} disabled={acting}>
              Confirm order
            </button>
          )}
          {data.status === "confirmed" && (
            <button type="button" className="btn btn-primary" onClick={() => runAction("complete")} disabled={acting}>
              Complete order
            </button>
          )}
          {(data.status === "draft" || data.status === "confirmed") && (
            <button
              type="button"
              className="btn btn-danger-outline"
              onClick={() => setPendingAction("cancel")}
              disabled={acting}
            >
              Cancel order
            </button>
          )}
        </div>
      </div>

      {actionError && <div className="form-error">{actionError}</div>}

      {data.status === "draft" && (
        <div className="result-banner" style={{ background: "var(--warning-soft)", borderColor: "#f2d9ac", color: "var(--warning)" }}>
          This order is a draft — stock is reserved only after you confirm it.
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h2>Items</h2>
          <div>
            Total: <strong style={{ fontSize: 16 }}>{formatMoney(data.total_amount)}</strong>
          </div>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product</th>
                <th className="num">Quantity</th>
                <th className="num">Unit price</th>
                <th className="num">Line total</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id}>
                  <td className="mono">{item.product.sku}</td>
                  <td>
                    <Link to={`/products/${item.product_id}`}>{item.product.name}</Link>
                  </td>
                  <td className="num">{item.quantity}</td>
                  <td className="num">{formatMoney(item.unit_price)}</td>
                  <td className="num">{formatMoney(item.line_total)}</td>
                </tr>
              ))}
              <tr>
                <td colSpan={4} style={{ textAlign: "right", fontWeight: 600 }}>
                  Total amount
                </td>
                <td className="num" style={{ fontWeight: 700 }}>
                  {formatMoney(data.total_amount)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Details</h2>
        </div>
        <div className="card-body">
          <dl className="kv-list">
            <dt>Order number</dt>
            <dd className="mono">{data.order_number}</dd>
            <dt>Customer</dt>
            <dd>
              {data.customer.name} <span className="muted">{data.customer.email ? `· ${data.customer.email}` : ""}</span>
            </dd>
            <dt>Status</dt>
            <dd>
              <StatusBadge status={data.status} />
            </dd>
            <dt>Total amount</dt>
            <dd>{formatMoney(data.total_amount)}</dd>
            <dt>Created</dt>
            <dd>{formatDateTime(data.created_at)}</dd>
            <dt>Last updated</dt>
            <dd>{formatDateTime(data.updated_at)}</dd>
          </dl>
        </div>
      </div>

      <ConfirmDialog
        open={pendingAction === "cancel"}
        title="Cancel order"
        message={
          data.status === "confirmed"
            ? `Cancel confirmed order ${data.order_number}? The reserved stock will be restored and IN movements recorded.`
            : `Cancel draft order ${data.order_number}? No stock is affected.`
        }
        confirmLabel="Cancel order"
        danger
        loading={acting}
        onConfirm={() => runAction("cancel")}
        onCancel={() => setPendingAction(null)}
      />
    </div>
  );
}
