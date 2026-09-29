import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAsync, useDebouncedValue } from "../hooks/useAsync";
import { categoriesApi, productsApi, suppliersApi } from "../api/endpoints";
import { ApiError } from "../api/client";
import { ActiveBadge, LowStockBadge } from "../components/Badges";
import { Field, Select, TextInput } from "../components/Fields";
import { Pagination } from "../components/Pagination";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { ProductFormModal } from "../components/ProductFormModal";
import { useToast } from "../components/Toasts";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { downloadFile } from "../api/client";
import { formatMoney } from "../utils/format";
import type { Category, Product, Supplier } from "../types";

export function ProductsPage() {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search);
  const [categoryId, setCategoryId] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Product | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Product | null>(null);
  const [deleting, setDeleting] = useState(false);

  const categories = useAsync(() => categoriesApi.list({ page_size: 100 }), []);
  const suppliers = useAsync(() => suppliersApi.list({ page_size: 100 }), []);
  const products = useAsync(
    () =>
      productsApi.list({
        page,
        page_size: 10,
        search: debouncedSearch || undefined,
        category_id: categoryId ? Number(categoryId) : null,
        supplier_id: supplierId ? Number(supplierId) : null,
        is_active: activeFilter === "" ? null : activeFilter === "active",
        low_stock: lowStockOnly ? true : null,
        sort_by: sortBy,
        sort_dir: sortDir,
      }),
    [page, debouncedSearch, categoryId, supplierId, activeFilter, lowStockOnly, sortBy, sortDir],
  );

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, categoryId, supplierId, activeFilter, lowStockOnly]);

  const onSort = (column: string) => {
    if (sortBy === column) {
      setSortDir((dir) => (dir === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(column);
      setSortDir("asc");
    }
  };

  const arrow = (column: string) => (sortBy === column ? (sortDir === "asc" ? " ▲" : " ▼") : "");

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await productsApi.remove(deleteTarget.id);
      toast.success(`Product ${deleteTarget.sku} deleted.`);
      setDeleteTarget(null);
      products.refetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Delete failed.");
    } finally {
      setDeleting(false);
    }
  };

  const toggleActive = async (product: Product) => {
    try {
      await productsApi.update(product.id, { is_active: !product.is_active });
      toast.success(product.is_active ? `Product ${product.sku} deactivated.` : `Product ${product.sku} activated.`);
      products.refetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Update failed.");
    }
  };

  const data = products.data;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">Catalog</div>
          <h1>Products</h1>
          <p className="subtitle">{data ? `${data.total} products` : "Manage your product catalog."}</p>
        </div>
        <div className="page-actions">
          <button
            type="button"
            className="btn"
            onClick={() => downloadFile("/products/export.csv", "products.csv").catch((err) => toast.error(err.message))}
          >
            Export CSV
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => {
              const input = document.createElement("input");
              input.type = "file";
              input.accept = ".csv";
              input.onchange = async () => {
                const file = input.files?.[0];
                if (!file) return;
                try {
                  const summary = await productsApi.importCsv(file);
                  toast.success(`Imported ${summary.imported}, skipped ${summary.skipped}.`);
                  products.refetch();
                } catch (err) {
                  toast.error(err instanceof ApiError ? err.message : "Import failed.");
                }
              };
              input.click();
            }}
          >
            Import CSV
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setEditTarget(null);
              setFormOpen(true);
            }}
          >
            New Product
          </button>
        </div>
      </div>

      <div className="filter-bar">
        <Field label="Search">
          <TextInput
            value={search}
            onChange={(v) => setSearch(v)}
            placeholder="Name or SKU…"
          />
        </Field>
        <Field label="Category">
          <Select
            value={categoryId}
            onChange={setCategoryId}
            options={[
              { value: "", label: "All categories" },
              ...(categories.data?.items ?? []).map((c: Category) => ({ value: String(c.id), label: c.name })),
            ]}
          />
        </Field>
        <Field label="Supplier">
          <Select
            value={supplierId}
            onChange={setSupplierId}
            options={[
              { value: "", label: "All suppliers" },
              ...(suppliers.data?.items ?? []).map((s: Supplier) => ({ value: String(s.id), label: s.name })),
            ]}
          />
        </Field>
        <Field label="Status">
          <Select
            value={activeFilter}
            onChange={setActiveFilter}
            options={[
              { value: "", label: "All" },
              { value: "active", label: "Active only" },
              { value: "inactive", label: "Inactive only" },
            ]}
          />
        </Field>
        <div className="checkbox-row">
          <input
            id="low-stock-filter"
            type="checkbox"
            checked={lowStockOnly}
            onChange={(event) => setLowStockOnly(event.target.checked)}
          />
          <label htmlFor="low-stock-filter">Low stock only</label>
        </div>
      </div>

      <div className="card">
        {products.loading ? (
          <LoadingState />
        ) : products.error ? (
          <ErrorState error={products.error} onRetry={products.refetch} />
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            title="No products found"
            hint="Adjust the filters or create your first product."
            action={
              <button type="button" className="btn btn-primary" onClick={() => setFormOpen(true)}>
                New Product
              </button>
            }
          />
        ) : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th className="sortable" onClick={() => onSort("sku")}>SKU{arrow("sku")}</th>
                    <th className="sortable" onClick={() => onSort("name")}>Name{arrow("name")}</th>
                    <th>Category</th>
                    <th>Supplier</th>
                    <th className="sortable num" onClick={() => onSort("unit_price")}>Price{arrow("unit_price")}</th>
                    <th className="sortable num" onClick={() => onSort("stock_quantity")}>Stock{arrow("stock_quantity")}</th>
                    <th>Status</th>
                    <th className="actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((product) => (
                    <tr key={product.id}>
                      <td className="mono">{product.sku}</td>
                      <td>
                        <Link to={`/products/${product.id}`}>{product.name}</Link>
                        <div className="inline-badges" style={{ marginTop: 4 }}>
                          <LowStockBadge stock={product.stock_quantity} threshold={product.low_stock_threshold} />
                        </div>
                      </td>
                      <td>{product.category?.name ?? <span className="muted">—</span>}</td>
                      <td>{product.supplier?.name ?? <span className="muted">—</span>}</td>
                      <td className="num">{formatMoney(product.unit_price)}</td>
                      <td className="num">{product.stock_quantity}</td>
                      <td>
                        <ActiveBadge active={product.is_active} />
                      </td>
                      <td className="actions">
                        <Link className="btn btn-sm" to={`/products/${product.id}`}>
                          View
                        </Link>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => {
                            setEditTarget(product);
                            setFormOpen(true);
                          }}
                        >
                          Edit
                        </button>
                        <button type="button" className="btn btn-sm" onClick={() => toggleActive(product)}>
                          {product.is_active ? "Deactivate" : "Activate"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-danger-outline"
                          onClick={() => setDeleteTarget(product)}
                        >
                          Delete
                        </button>
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

      <ProductFormModal
        open={formOpen}
        product={editTarget}
        categories={categories.data?.items ?? []}
        suppliers={suppliers.data?.items ?? []}
        onClose={() => setFormOpen(false)}
        onSaved={() => {
          setFormOpen(false);
          products.refetch();
        }}
      />

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete product"
        message={
          deleteTarget
            ? `Delete "${deleteTarget.name}" (${deleteTarget.sku})? Products with stock movements or order history cannot be deleted and must be deactivated instead.`
            : ""
        }
        confirmLabel="Delete"
        danger
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
