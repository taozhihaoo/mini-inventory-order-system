import { suppliersApi } from "../api/endpoints";
import { DirectoryPage } from "./DirectoryPage";

const FIELDS = [
  { key: "name", label: "Name", type: "text", required: true },
  { key: "email", label: "Email", type: "email" },
  { key: "phone", label: "Phone", type: "text" },
  { key: "notes", label: "Notes", type: "textarea" },
] as const;

export function SuppliersPage() {
  return (
    <DirectoryPage
      title="Suppliers"
      breadcrumb="Catalog"
      subtitle="Where your products come from."
      entityName="Supplier"
      countField="product_count"
      countLabel="Products"
      fields={[...FIELDS]}
      api={{
        list: (params) => suppliersApi.list(params),
        create: (body) => suppliersApi.create(body),
        update: (id, body) => suppliersApi.update(id, body),
        remove: (id) => suppliersApi.remove(id),
      }}
    />
  );
}
