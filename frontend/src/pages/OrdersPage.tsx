import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAsync, useDebouncedValue } from "../hooks/useAsync";
import { customersApi, ordersApi } from "../api/endpoints";
import { StatusBadge } from "../components/Badges";
import { Field, Select, TextInput } from "../components/Fields";
import { Pagination } from "../components/Pagination";
import { useToast } from "../components/Toasts";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { formatDateTime, formatMoney } from "../utils/format";
import type { OrderStatus } from "../types";

export function OrdersPage() {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search);
  const [status, setStatus] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  const customers = useAsync(() => customersApi.list({ page_size: 100 }), []);
  const orders = useAsync(
    () =>
      ordersApi.list({
        page,
        page_size: 10,
        search: debouncedSearch || undefined,
        status: (status || null) as OrderStatus | null,
        customer_id: customerId ? Number(customerId) : null,
        date_from: dateFrom || null,
        date_to: dateTo || null,
      }),
    [page, debouncedSearch, status, customerId, dateFrom, dateTo],
  );

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, status, customerId, dateFrom, dateTo]);

  const data = orders.data;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">Sales</div>
          <h1>Orders</h1>
          <p className="subtitle">{data ? `${data.total} orders` : "Customer orders and their lifecycle."}</p>
        </div>
        <div className="page-actions">
          <button
            type="button"
            className="btn"
            onClick={() => ordersApi.exportCsv().catch((err) => toast.error(err.message))}
          >
            Export CSV
          </button>
          <Link className="btn btn-primary" to="/orders/new">
            New Order
          </Link>
        </div>
      </div>

      <div className="filter-bar">
        <Field label="Order number">
          <TextInput value={search} onChange={setSearch} placeholder="ORD-…" />
        </Field>
        <Field label="Status">
          <Select
            value={status}
            onChange={setStatus}
            options={[
              { value: "", label: "All statuses" },
              { value: "draft", label: "Draft" },
              { value: "confirmed", label: "Confirmed" },
              { value: "completed", label: "Completed" },
              { value: "cancelled", label: "Cancelled" },
            ]}
          />
        </Field>
        <Field label="Customer">
          <Select
            value={customerId}
            onChange={setCustomerId}
            options={[
              { value: "", label: "All customers" },
              ...(customers.data?.items ?? []).map((c) => ({ value: String(c.id), label: c.name })),
            ]}
          />
        </Field>
        <Field label="From date">
          <TextInput type="date" value={dateFrom} onChange={setDateFrom} />
        </Field>
        <Field label="To date">
          <TextInput type="date" value={dateTo} onChange={setDateTo} />
        </Field>
      </div>

      <div className="card">
        {orders.loading ? (
          <LoadingState />
        ) : orders.error ? (
          <ErrorState error={orders.error} onRetry={orders.refetch} />
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            title="No orders found"
            hint="Adjust the filters or create a new order."
            action={
              <Link className="btn btn-primary" to="/orders/new">
                New Order
              </Link>
            }
          />
        ) : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Order number</th>
                    <th>Customer</th>
                    <th className="num">Items</th>
                    <th className="num">Total</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th className="actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((order) => (
                    <tr key={order.id}>
                      <td>
                        <Link to={`/orders/${order.id}`} className="mono">
                          {order.order_number}
                        </Link>
                      </td>
                      <td>{order.customer.name}</td>
                      <td className="num">{order.item_count}</td>
                      <td className="num">{formatMoney(order.total_amount)}</td>
                      <td>
                        <StatusBadge status={order.status} />
                      </td>
                      <td className="muted">{formatDateTime(order.created_at)}</td>
                      <td className="actions">
                        <Link className="btn btn-sm" to={`/orders/${order.id}`}>
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={data.page} totalPages={data.total_pages} total={data.total} onChange={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
