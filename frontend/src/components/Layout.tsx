import { NavLink, Outlet } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/products", label: "Products" },
  { to: "/inventory", label: "Inventory" },
  { to: "/orders", label: "Orders" },
  { to: "/customers", label: "Customers" },
  { to: "/suppliers", label: "Suppliers" },
  { to: "/categories", label: "Categories" },
];

export function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="7" width="18" height="14" rx="2" />
              <path d="M7 7V5a5 5 0 0 1 10 0v2" />
            </svg>
          </span>
          <span className="brand-name">ShopStock</span>
        </div>
        <nav className="nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-item${isActive ? " nav-item-active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">Small Business Inventory &amp; Orders</div>
      </aside>
      <main className="main-area">
        <Outlet />
      </main>
    </div>
  );
}
