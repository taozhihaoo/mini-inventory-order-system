import { customersApi } from "../api/endpoints";
import { DirectoryPage } from "./DirectoryPage";

const FIELDS = [
  { key: "name", label: "Name", type: "text", required: true },
  { key: "email", label: "Email", type: "email" },
  { key: "phone", label: "Phone", type: "text" },
  { key: "notes", label: "Notes", type: "textarea" },
] as const;

export function CustomersPage() {
  return (
    <DirectoryPage
      title="Customers"
      breadcrumb="Sales"
      subtitle="People and businesses you sell to."
      entityName="Customer"
      countField="order_count"
      countLabel="Orders"
      fields={[...FIELDS]}
      api={{
        list: (params) => customersApi.list(params),
        create: (body) => customersApi.create(body),
        update: (id, body) => customersApi.update(id, body),
        remove: (id) => customersApi.remove(id),
      }}
    />
  );
}
