import { categoriesApi } from "../api/endpoints";
import { DirectoryPage } from "./DirectoryPage";

const FIELDS = [
  { key: "name", label: "Name", type: "text", required: true },
  { key: "description", label: "Description", type: "textarea" },
] as const;

export function CategoriesPage() {
  return (
    <DirectoryPage
      title="Categories"
      breadcrumb="Catalog"
      subtitle="Group products for filtering and reporting."
      entityName="Category"
      countField="product_count"
      countLabel="Products"
      fields={[...FIELDS]}
      api={{
        list: (params) => categoriesApi.list(params),
        create: (body) => categoriesApi.create(body),
        update: (id, body) => categoriesApi.update(id, body),
        remove: (id) => categoriesApi.remove(id),
      }}
    />
  );
}
