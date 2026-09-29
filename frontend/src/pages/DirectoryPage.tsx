import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useAsync, useDebouncedValue } from "../hooks/useAsync";
import { ApiError } from "../api/client";
import { Field, TextArea, TextInput } from "../components/Fields";
import { Modal } from "../components/Modal";
import { Pagination } from "../components/Pagination";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { useToast } from "../components/Toasts";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { formatDate } from "../utils/format";

export interface DirectoryEntity {
  id: number;
  name: string;
  email?: string | null;
  phone?: string | null;
  notes?: string | null;
  description?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface DirectoryField {
  key: "name" | "email" | "phone" | "notes" | "description";
  label: string;
  type: "text" | "email" | "textarea";
  required?: boolean;
  span?: boolean;
}

interface DirectoryPageProps {
  title: string;
  breadcrumb: string;
  subtitle: string;
  entityName: string;
  countField: string | null;
  countLabel: string;
  fields: DirectoryField[];
  extraColumn?: ReactNode;
  api: {
    list: (params: { page?: number; page_size?: number; search?: string }) => Promise<{ items: DirectoryEntity[]; total: number; page: number; page_size: number; total_pages: number }>;
    create: (body: Record<string, unknown>) => Promise<DirectoryEntity>;
    update: (id: number, body: Record<string, unknown>) => Promise<DirectoryEntity>;
    remove: (id: number) => Promise<void>;
  };
}

interface FormState {
  name: string;
  email: string;
  phone: string;
  notes: string;
  description: string;
}

const EMPTY_FORM: FormState = { name: "", email: "", phone: "", notes: "", description: "" };

export function DirectoryPage({
  title,
  breadcrumb,
  subtitle,
  entityName,
  countField,
  countLabel,
  fields,
  api,
}: DirectoryPageProps) {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search);
  const [page, setPage] = useState(1);

  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<DirectoryEntity | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<DirectoryEntity | null>(null);
  const [deleting, setDeleting] = useState(false);

  const list = useAsync(() => api.list({ page, page_size: 10, search: debouncedSearch || undefined }), [page, debouncedSearch]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  const openCreate = () => {
    setEditTarget(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setFormOpen(true);
  };

  const openEdit = (entity: DirectoryEntity) => {
    setEditTarget(entity);
    setForm({
      name: entity.name,
      email: entity.email ?? "",
      phone: entity.phone ?? "",
      notes: entity.notes ?? "",
      description: entity.description ?? "",
    });
    setFormError(null);
    setFormOpen(true);
  };

  const submit = async () => {
    setFormError(null);
    if (!form.name.trim()) {
      setFormError("Name is required.");
      return;
    }
    const body: Record<string, unknown> = { name: form.name.trim() };
    for (const field of fields) {
      if (field.key === "name") continue;
      const value = form[field.key].trim();
      body[field.key] = value === "" ? null : value;
    }
    setSubmitting(true);
    try {
      if (editTarget) {
        await api.update(editTarget.id, body);
        toast.success(`${entityName} updated.`);
      } else {
        await api.create(body);
        toast.success(`${entityName} created.`);
      }
      setFormOpen(false);
      list.refetch();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to save.");
    } finally {
      setSubmitting(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.remove(deleteTarget.id);
      toast.success(`${entityName} "${deleteTarget.name}" deleted.`);
      setDeleteTarget(null);
      list.refetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Delete failed.");
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  };

  const data = list.data;
  const hasDescription = fields.some((f) => f.key === "description");

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">{breadcrumb}</div>
          <h1>{title}</h1>
          <p className="subtitle">{data ? `${data.total} record${data.total === 1 ? "" : "s"}` : subtitle}</p>
        </div>
        <div className="page-actions">
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            New {entityName}
          </button>
        </div>
      </div>

      <div className="filter-bar">
        <Field label="Search">
          <TextInput value={search} onChange={setSearch} placeholder="Search…" />
        </Field>
      </div>

      <div className="card">
        {list.loading ? (
          <LoadingState />
        ) : list.error ? (
          <ErrorState error={list.error} onRetry={list.refetch} />
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            title={`No ${entityName.toLowerCase()}s found`}
            hint={debouncedSearch ? "Try a different search." : `Create your first ${entityName.toLowerCase()}.`}
            action={
              <button type="button" className="btn btn-primary" onClick={openCreate}>
                New {entityName}
              </button>
            }
          />
        ) : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    {hasDescription && <th>Description</th>}
                    <th>Email</th>
                    <th>Phone</th>
                    {countField && <th className="num">{countLabel}</th>}
                    <th>Created</th>
                    <th className="actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((entity) => (
                    <tr key={entity.id}>
                      <td>
                        <strong>{entity.name}</strong>
                        {entity.notes && (
                          <div className="muted" style={{ fontSize: 12, maxWidth: 320 }}>
                            {entity.notes}
                          </div>
                        )}
                      </td>
                      {hasDescription && <td className="muted">{entity.description ?? "—"}</td>}
                      <td>{entity.email ?? <span className="muted">—</span>}</td>
                      <td>{entity.phone ?? <span className="muted">—</span>}</td>
                      {countField && (
                        <td className="num">{String((entity as unknown as Record<string, number>)[countField] ?? 0)}</td>
                      )}
                      <td className="muted">{formatDate(entity.created_at)}</td>
                      <td className="actions">
                        <button type="button" className="btn btn-sm" onClick={() => openEdit(entity)}>
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-danger-outline"
                          onClick={() => setDeleteTarget(entity)}
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

      <Modal
        title={editTarget ? `Edit ${entityName.toLowerCase()} — ${editTarget.name}` : `New ${entityName.toLowerCase()}`}
        open={formOpen}
        onClose={() => setFormOpen(false)}
      >
        {formError && <div className="form-error">{formError}</div>}
        {fields.map((field) => (
          <Field key={field.key} label={field.label} required={field.required}>
            {field.type === "textarea" ? (
              <TextArea
                value={form[field.key]}
                onChange={(value) => setForm((current) => ({ ...current, [field.key]: value }))}
                rows={2}
              />
            ) : (
              <TextInput
                type={field.type}
                value={form[field.key]}
                onChange={(value) => setForm((current) => ({ ...current, [field.key]: value }))}
              />
            )}
          </Field>
        ))}
        <div className="modal-actions">
          <button type="button" className="btn" onClick={() => setFormOpen(false)} disabled={submitting}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary" onClick={submit} disabled={submitting}>
            {submitting ? "Saving…" : "Save"}
          </button>
        </div>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title={`Delete ${entityName.toLowerCase()}`}
        message={
          deleteTarget
            ? `Delete "${deleteTarget.name}"? Records that are referenced by products or orders cannot be deleted.`
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
