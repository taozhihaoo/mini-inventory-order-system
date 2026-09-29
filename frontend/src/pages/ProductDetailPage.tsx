import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAsync } from "../hooks/useAsync";
import { categoriesApi, productsApi, suppliersApi } from "../api/endpoints";
import { ActiveBadge, LowStockBadge, MovementBadge, StatusBadge } from "../components/Badges";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { ProductFormModal } from "../components/ProductFormModal";
import { StockOpModal } from "../components/StockOpModal";
import { useToast } from "../components/Toasts";
import { ErrorState, LoadingState } from "../components/States";
import { ApiError } from "../api/client";
import { formatDateTime, formatMoney, formatQuantityChange } from "../utils/format";

type StockOpKind = "IN" | "OUT" | "ADJUST";

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const productId = Number(id);
  const toast = useToast();
  const navigate = useNavigate();

  const [formOpen, setFormOpen] = useState(false);
  const [stockOpKind, setStockOpKind] = useState<StockOpKind | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const categories = useAsync(() => categoriesApi.list({ page_size: 100 }), []);
  const suppliers = useAsync(() => suppliersApi.list({ page_size: 100 }), []);
  const product = useAsync(() => productsApi.get(productId), [productId]);
  const movements = useAsync(
    () => productsApi.movements(productId),
    [productId, product.data?.stock_quantity],
  );
  const orders = useAsync(() => productsApi.orders(productId), [productId]);

  if (product.loading) return <LoadingState label="Loading product…" />;
  if (product.error) return <ErrorState error={product.error} onRetry={product.refetch} />;
  const data = product.data;
  if (!data) return null;

  const stockValue = data.cost_price === null ? null : data.cost_price * data.stock_quantity;

  const confirmDelete = async () => {
    setDeleting(true);
    try {
      await productsApi.remove(data.id);
      toast.success(`Product ${data.sku} deleted.`);
      navigate("/products");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Delete failed.");
      setDeleting(false);
      setDeleteOpen(false);
    }
  };

  const onStockDone = () => {
    setStockOpKind(null);
    product.refetch();
    movements.refetch();
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">
            <Link to="/products">Products</Link> / {data.sku}
          </div>
          <h1>
            {data.name}{" "}
            <span className="inline-badges" style={{ verticalAlign: "middle" }}>
              <LowStockBadge stock={data.stock_quantity} threshold={data.low_stock_threshold} />
              <ActiveBadge active={data.is_active} />
            </span>
          </h1>
          <p className="subtitle mono">{data.sku}</p>
        </div>
        <div className="page-actions">
          <button type="button" className="btn" onClick={() => setStockOpKind("IN")}>
            Stock In
          </button>
          <button type="button" className="btn" onClick={() => setStockOpKind("OUT")}>
            Stock Out
          </button>
          <button type="button" className="btn" onClick={() => setStockOpKind("ADJUST")}>
            Adjust
          </button>
          <button type="button" className="btn" onClick={() => setFormOpen(true)}>
            Edit
          </button>
          <button type="button" className="btn btn-danger-outline" onClick={() => setDeleteOpen(true)}>
            Delete
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <dl className="kv-list">
            <dt>Description</dt>
            <dd>{data.description ?? <span className="muted">—</span>}</dd>
            <dt>Category</dt>
            <dd>{data.category?.name ?? <span className="muted">—</span>}</dd>
            <dt>Supplier</dt>
            <dd>{data.supplier?.name ?? <span className="muted">—</span>}</dd>
            <dt>Unit price</dt>
            <dd>{formatMoney(data.unit_price)}</dd>
            <dt>Cost price</dt>
            <dd>{formatMoney(data.cost_price)}</dd>
            <dt>Created / Updated</dt>
            <dd>
              {formatDateTime(data.created_at)} / {formatDateTime(data.updated_at)}
            </dd>
          </dl>
          <div className="detail-stats">
            <div className="detail-stat">
              <div className="stat-label">Current stock</div>
              <div className="stat-value">{data.stock_quantity}</div>
            </div>
            <div className="detail-stat">
              <div className="stat-label">Low stock threshold</div>
              <div className="stat-value">{data.low_stock_threshold}</div>
            </div>
            <div className="detail-stat">
              <div className="stat-label">Stock value (cost)</div>
              <div className="stat-value">{stockValue === null ? "—" : formatMoney(stockValue)}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Stock movements</h2>
        </div>
        {movements.loading ? (
          <LoadingState />
        ) : movements.error ? (
          <ErrorState error={movements.error} onRetry={movements.refetch} />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th className="num">Change</th>
                  <th className="num">Stock after</th>
                  <th>Reference</th>
                  <th>Note</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {(movements.data?.items ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={6} className="muted" style={{ textAlign: "center" }}>
                      No stock movements yet.
                    </td>
                  </tr>
                ) : (
                  (movements.data?.items ?? []).map((movement) => (
                    <tr key={movement.id}>
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
                      <td className="muted">{formatDateTime(movement.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Recent orders containing this product</h2>
        </div>
        {orders.loading ? (
          <LoadingState />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Customer</th>
                  <th>Status</th>
                  <th className="num">Total</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {(orders.data ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={5} className="muted" style={{ textAlign: "center" }}>
                      No orders yet.
                    </td>
                  </tr>
                ) : (
                  (orders.data ?? []).map((order) => (
                    <tr key={order.id}>
                      <td>
                        <Link to={`/orders/${order.id}`} className="mono">
                          {order.order_number}
                        </Link>
                      </td>
                      <td>{order.customer.name}</td>
                      <td>
                        <StatusBadge status={order.status} />
                      </td>
                      <td className="num">{formatMoney(order.total_amount)}</td>
                      <td className="muted">{formatDateTime(order.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ProductFormModal
        open={formOpen}
        product={data}
        categories={categories.data?.items ?? []}
        suppliers={suppliers.data?.items ?? []}
        onClose={() => setFormOpen(false)}
        onSaved={() => {
          setFormOpen(false);
          product.refetch();
        }}
      />

      <StockOpModal
        product={stockOpKind ? data : null}
        initialOp={stockOpKind ?? "IN"}
        onClose={() => setStockOpKind(null)}
        onDone={onStockDone}
      />

      <ConfirmDialog
        open={deleteOpen}
        title="Delete product"
        message={`Delete "${data.name}" (${data.sku})? Products with stock movements or order history cannot be deleted.`}
        confirmLabel="Delete"
        danger
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteOpen(false)}
      />
    </div>
  );
}
