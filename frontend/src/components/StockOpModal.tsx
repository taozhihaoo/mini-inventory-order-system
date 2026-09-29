import { useState } from "react";
import { Modal } from "./Modal";
import { Field, TextArea, Select } from "./Fields";
import { inventoryApi } from "../api/endpoints";
import { ApiError } from "../api/client";
import { useToast } from "./Toasts";
import type { Product, StockOperationResult } from "../types";

type OpKind = "IN" | "OUT" | "ADJUST";

interface StockOpModalProps {
  product: Product | null;
  initialOp?: OpKind;
  onClose: () => void;
  onDone: (result: StockOperationResult) => void;
}

const OP_OPTIONS = [
  { value: "IN", label: "Stock In (add quantity)" },
  { value: "OUT", label: "Stock Out (remove quantity)" },
  { value: "ADJUST", label: "Adjustment (set counted quantity)" },
];

export function StockOpModal({ product, initialOp = "IN", onClose, onDone }: StockOpModalProps) {
  const toast = useToast();
  const [op, setOp] = useState<OpKind>(initialOp);
  const [quantity, setQuantity] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // The component stays mounted while closed (product === null); re-initialize
  // the form each time it opens so the operation matches the clicked button.
  const [openKey, setOpenKey] = useState("");
  const nextOpenKey = product ? `${product.id}:${initialOp}` : "";
  if (product && nextOpenKey !== openKey) {
    setOpenKey(nextOpenKey);
    setOp(initialOp);
    setQuantity("");
    setNote("");
    setError(null);
  }

  if (!product) return null;

  const quantityLabel = op === "ADJUST" ? "Counted quantity (new total)" : "Quantity";

  const submit = async () => {
    setError(null);
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
      const trimmedNote = note.trim();
      const result =
        op === "IN"
          ? await inventoryApi.stockIn(product.id, parsed, trimmedNote || null)
          : op === "OUT"
            ? await inventoryApi.stockOut(product.id, parsed, trimmedNote || null)
            : await inventoryApi.stockAdjust(product.id, parsed, trimmedNote || null);
      toast.success(`${product.sku}: ${result.previous_quantity} → ${result.new_quantity}`);
      onDone(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Operation failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title={`Stock operation — ${product.sku}`} open onClose={onClose}>
      <div className="form-grid">
        <Field label="Product">
          <input className="input" value={`${product.name}`} disabled />
        </Field>
        <Field label="Current stock">
          <input className="input" value={String(product.stock_quantity)} disabled />
        </Field>
        <Field label="Operation type">
          <Select value={op} onChange={(value) => setOp(value as OpKind)} options={OP_OPTIONS} />
        </Field>
        <Field label={quantityLabel} required error={error}>
          <input
            className="input"
            type="number"
            min={op === "ADJUST" ? 0 : 1}
            step={1}
            value={quantity}
            placeholder={op === "ADJUST" ? "e.g. 12" : "e.g. 5"}
            onChange={(event) => setQuantity(event.target.value)}
          />
        </Field>
        <div className="span-2">
          <Field label="Note">
            <TextArea value={note} onChange={setNote} rows={2} placeholder="Optional reference, e.g. PO-2041" />
          </Field>
        </div>
      </div>
      <div className="modal-actions">
        <button type="button" className="btn" onClick={onClose} disabled={submitting}>
          Cancel
        </button>
        <button type="button" className="btn btn-primary" onClick={submit} disabled={submitting}>
          {submitting ? "Applying…" : "Apply"}
        </button>
      </div>
    </Modal>
  );
}
