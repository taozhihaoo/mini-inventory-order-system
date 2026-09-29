/**
 * E2E global setup: guarantee a dedicated, reproducible test database.
 *
 * Playwright starts the backend webServer BEFORE globalSetup, and on
 * Windows the running backend holds a lock on the SQLite file — so the
 * database file itself cannot be deleted here. Instead:
 *
 * - if the file does not exist yet, the backend creates + migrates it on
 *   startup (first run);
 * - if it exists, all application rows are cleared through sqlite3 while
 *   the schema and alembic_version stay in place.
 *
 * Tests then create their own data through the UI/API, so runs never
 * depend on a developer's local shopstock.db.
 */
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DB_PATH = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "backend", "e2e.db");

const PYTHON =
  process.platform === "win32"
    ? join(dirname(fileURLToPath(import.meta.url)), "..", "..", "backend", ".venv", "Scripts", "python.exe")
    : join(dirname(fileURLToPath(import.meta.url)), "..", "..", "backend", ".venv", "bin", "python");

const CLEAR_SQL = `
import sqlite3
conn = sqlite3.connect(r"{db}")
for table in ["stock_movements", "order_items", "orders", "products", "customers", "suppliers", "categories"]:
    conn.execute(f"DELETE FROM {table}")
conn.commit()
conn.close()
print("e2e database cleared")
`.replace("{db}", DB_PATH);

export default function globalSetup() {
  if (!existsSync(DB_PATH)) {
    console.log("e2e: fresh database will be created by the backend on startup");
    return;
  }
  const result = spawnSync(PYTHON, ["-c", CLEAR_SQL], { stdio: "inherit" });
  if (result.status !== 0) {
    throw new Error(`e2e: failed to clear the test database (exit ${result.status})`);
  }
}
