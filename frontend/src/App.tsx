import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ToastProvider } from "./components/Toasts";
import { DashboardPage } from "./pages/DashboardPage";
import { ProductsPage } from "./pages/ProductsPage";
import { ProductDetailPage } from "./pages/ProductDetailPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { SuppliersPage } from "./pages/SuppliersPage";
import { CustomersPage } from "./pages/CustomersPage";
import { InventoryPage } from "./pages/InventoryPage";
import { OrdersPage } from "./pages/OrdersPage";
import { OrderNewPage } from "./pages/OrderNewPage";
import { OrderDetailPage } from "./pages/OrderDetailPage";

function NotFound() {
  return (
    <div className="page">
      <div className="page-header">
        <h1>Page not found</h1>
      </div>
      <p className="muted">
        The page you requested does not exist. <Link to="/">Back to dashboard</Link>.
      </p>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="products" element={<ProductsPage />} />
            <Route path="products/:id" element={<ProductDetailPage />} />
            <Route path="inventory" element={<InventoryPage />} />
            <Route path="orders" element={<OrdersPage />} />
            <Route path="orders/new" element={<OrderNewPage />} />
            <Route path="orders/:id" element={<OrderDetailPage />} />
            <Route path="customers" element={<CustomersPage />} />
            <Route path="suppliers" element={<SuppliersPage />} />
            <Route path="categories" element={<CategoriesPage />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </ToastProvider>
    </BrowserRouter>
  );
}
