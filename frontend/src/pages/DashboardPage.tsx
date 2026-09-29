import { Link } from "react-router-dom";
import { useAsync } from "../hooks/useAsync";
import { dashboardApi } from "../api/endpoints";
import { StatusBadge, MovementBadge, LowStockBadge } from "../components/Badges";
import { LoadingState, ErrorState } from "../components/States";
import { formatMoney, formatNumber, formatDateTime, formatQuantityChange } from "../utils/format";

export function DashboardPage() {
  const { data, loading, error, refetch } = useAsync(() => dashboardApi.summary(), []);

  if (loading) return <LoadingState label="Loading dashboard…" />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (!data) return null;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">Dashboard</div>
          <h1>Dashboard</h1>
          <p className="subtitle">Overview of inventory and sales activity.</p>
        </div>
        <div className="page-actions">
          <Link className="btn btn-primary" to="/orders/new">
            New Order
          </Link>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard label="Total Products" value={formatNumber(data.total_products)} note={`${data.active_products} active`} />
        <StatCard label="Low Stock" value={formatNumber(data.low_stock_products)} note="need restocking" warning />
        <StatCard label="Inventory Value" value={formatMoney(data.inventory_value)} note="at cost price" />
        <StatCard label="Total Orders" value={formatNumber(data.total_orders)} note={`${data.confirmed_orders} confirmed`} />
        <StatCard label="Completed Orders" value={formatNumber(data.completed_orders)} />
        <StatCard label="Sales Amount" value={formatMoney(data.sales_amount)} note="confirmed + completed" success />
      </div>

      <div className="two-col">
        <div className="card">
          <div className="card-header">
            <h2>Recent Orders</h2>
            <Link to="/orders">View all</Link>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Customer</th>
                  <th>Status</th>
                  <th className="num">Total</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_orders.map((order) => (
                  <tr key={order.id}>
                    <td>
                      <Link to={`/orders/${order.id}`} className="mono">
                        {order.order_number}
                      </Link>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {formatDateTime(order.created_at)}
                      </div>
                    </td>
                    <td>{order.customer.name}</td>
                    <td>
                      <StatusBadge status={order.status} />
                    </td>
                    <td className="num">{formatMoney(order.total_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2>Low Stock</h2>
            <Link to="/inventory?tab=low-stock">View all</Link>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th className="num">Stock</th>
                  <th className="num">Threshold</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.low_stock_list.map((product) => (
                  <tr key={product.id}>
                    <td>
                      <Link to={`/products/${product.id}`}>{product.name}</Link>
                    </td>
                    <td className="mono">{product.sku}</td>
                    <td className="num">{product.stock_quantity}</td>
                    <td className="num">{product.low_stock_threshold}</td>
                    <td>
                      <LowStockBadge stock={product.stock_quantity} threshold={product.low_stock_threshold} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header">
          <h2>Recent Stock Movements</h2>
          <Link to="/inventory?tab=movements">View all</Link>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Type</th>
                <th className="num">Change</th>
                <th className="num">Stock After</th>
                <th>Note</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_movements.map((movement) => (
                <tr key={movement.id}>
                  <td>
                    <Link to={`/products/${movement.product_id}`}>
                      {movement.product?.name ?? `#${movement.product_id}`}
                    </Link>
                  </td>
                  <td>
                    <MovementBadge type={movement.movement_type} />
                  </td>
                  <td className="num">{formatQuantityChange(movement.movement_type, movement.quantity)}</td>
                  <td className="num">{movement.stock_after}</td>
                  <td className="muted">{movement.note ?? "—"}</td>
                  <td className="muted">{formatDateTime(movement.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  note,
  warning,
  success,
}: {
  label: string;
  value: string;
  note?: string;
  warning?: boolean;
  success?: boolean;
}) {
  return (
    <div className={`stat-card${warning ? " stat-warning" : ""}${success ? " stat-success" : ""}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {note && <div className="stat-note">{note}</div>}
    </div>
  );
}
