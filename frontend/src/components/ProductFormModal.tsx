import { useMemo, useState } from "react";
import { Field, Select, TextArea, TextInput } from "../components/Fields";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toasts";
import { ApiError } from "../api/client";
import { productsApi } from "../api/endpoints";
import type { Category, Product, Supplier } from "../types";

interface ProductFormModalProps {
  open: boolean;
  product: Product | null; // null = create
  categories: Category[];
  suppliers: Supplier[];
  onClose: () => void;
  onSaved: (product: Product) => void;
}

interface FormState {
  sku: string;
  name: string;
  description: string;
  category_id: string;
  supplier_id: string;
  unit_price: string;
  cost_price: string;
  stock_quantity: string;
  low_stock_threshold: string;
  is_active: boolean;
}

function emptyState(): FormState {
  return {
    sku: "",
    name: "",
    description: "",
    category_id: "",
    supplier_id: "",
    unit_price: "",
    cost_price: "",
    stock_quantity: "0",
    low_stock_threshold: "0",
    is_active: true,
  };
}

function fromProduct(product: Product): FormState {
  return {
    sku: product.sku,
    name: product.name,
    description: product.description ?? "",
    category_id: product.category_id ? String(product.category_id) : "",
    supplier_id: product.supplier_id ? String(product.supplier_id) : "",
    unit_price: String(product.unit_price),
    cost_price: product.cost_price === null ? "" : String(product.cost_price),
    stock_quantity: String(product.stock_quantity),
    low_stock_threshold: String(product.low_stock_threshold),
    is_active: product.is_active,
  };
}

export function ProductFormModal({
  open,
  product,
  categories,
  suppliers,
  onClose,
  onSaved,
}: ProductFormModalProps) {
  const toast = useToast();
  const editing = product !== null;
  const [form, setForm] = useState<FormState>(() => (product ? fromProduct(product) : emptyState()));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Reset form whenever a different product (or create mode) is opened.
  const key = useMemo(() => (product ? `edit-${product.id}` : "create"), [product]);
  const [lastKey, setLastKey] = useState("");
  if (open && key !== lastKey) {
    setLastKey(key);
    setForm(product ? fromProduct(product) : emptyState());
    setErrors({});
    setServerError(null);
  }

  const set = <K extends keyof FormState>(field: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => (current[field] ? { ...current, [field]: "" } : current));
  };

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    if (!form.sku.trim()) next.sku = "SKU is required.";
    if (!form.name.trim()) next.name = "Name is required.";
    if (form.unit_price === "" || Number(form.unit_price) < 0) next.unit_price = "Unit price must be 0 or more.";
    if (form.cost_price !== "" && Number(form.cost_price) < 0) next.cost_price = "Cost price must be 0 or more.";
    if (!editing) {
      const stock = Number(form.stock_quantity);
      if (!Number.isInteger(stock) || stock < 0) next.stock_quantity = "Initial stock must be a whole number ≥ 0.";
    }
    if (Number(form.low_stock_threshold) < 0) next.low_stock_threshold = "Threshold must be 0 or more.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async () => {
    setServerError(null);
    if (!validate()) return;
    const body: Record<string, unknown> = {
      sku: form.sku.trim().toUpperCase(),
      name: form.name.trim(),
      description: form.description.trim() || null,
      category_id: form.category_id ? Number(form.category_id) : null,
      supplier_id: form.supplier_id ? Number(form.supplier_id) : null,
      unit_price: form.unit_price,
      cost_price: form.cost_price === "" ? null : form.cost_price,
      low_stock_threshold: Number(form.low_stock_threshold),
      is_active: form.is_active,
    };
    if (!editing) body.stock_quantity = Number(form.stock_quantity);

    setSubmitting(true);
    try {
      const saved = editing
        ? await productsApi.update(product!.id, body)
        : await productsApi.create(body);
      toast.success(editing ? "Product updated." : "Product created.");
      onSaved(saved);
    } catch (err) {
      if (err instanceof ApiError) setServerError(err.message);
      else setServerError("Failed to save product.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <Modal title={editing ? `Edit product — ${product!.sku}` : "New product"} open onClose={onClose} wide>
      {serverError && <div className="form-error">{serverError}</div>}
      <div className="form-grid">
        <Field label="SKU" required error={errors.sku}>
          <TextInput value={form.sku} onChange={(v) => set("sku", v)} placeholder="e.g. LMP-1001" />
        </Field>
        <Field label="Name" required error={errors.name}>
          <TextInput value={form.name} onChange={(v) => set("name", v)} placeholder="Product name" />
        </Field>
        <Field label="Category">
          <Select
            value={form.category_id}
            onChange={(v) => set("category_id", v)}
            options={[
              { value: "", label: "— None —" },
              ...categories.map((c) => ({ value: String(c.id), label: c.name })),
            ]}
          />
        </Field>
        <Field label="Supplier">
          <Select
            value={form.supplier_id}
            onChange={(v) => set("supplier_id", v)}
            options={[
              { value: "", label: "— None —" },
              ...suppliers.map((s) => ({ value: String(s.id), label: s.name })),
            ]}
          />
        </Field>
        <Field label="Unit price" required error={errors.unit_price}>
          <TextInput type="number" min={0} step="0.01" value={form.unit_price} onChange={(v) => set("unit_price", v)} />
        </Field>
        <Field label="Cost price" error={errors.cost_price} hint="Used for inventory value">
          <TextInput type="number" min={0} step="0.01" value={form.cost_price} onChange={(v) => set("cost_price", v)} />
        </Field>
        {!editing && (
          <Field label="Initial stock" error={errors.stock_quantity} hint="Stock changes are tracked as movements">
            <TextInput type="number" min={0} step={1} value={form.stock_quantity} onChange={(v) => set("stock_quantity", v)} />
          </Field>
        )}
        <Field label="Low stock threshold" error={errors.low_stock_threshold}>
          <TextInput
            type="number"
            min={0}
            step={1}
            value={form.low_stock_threshold}
            onChange={(v) => set("low_stock_threshold", v)}
          />
        </Field>
        <div className="span-2">
          <Field label="Description">
            <TextArea value={form.description} onChange={(v) => set("description", v)} rows={2} />
          </Field>
        </div>
        <div className="span-2 checkbox-row">
          <input
            id="product-active"
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => set("is_active", event.target.checked)}
          />
          <label htmlFor="product-active">Active (available for ordering)</label>
        </div>
      </div>
      <div className="modal-actions">
        <button type="button" className="btn" onClick={onClose} disabled={submitting}>
          Cancel
        </button>
        <button type="button" className="btn btn-primary" onClick={submit} disabled={submitting}>
          {submitting ? "Saving…" : editing ? "Save changes" : "Create product"}
        </button>
      </div>
    </Modal>
  );
}
