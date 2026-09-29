/**
 * E2E global teardown: remove the dedicated test database so no test
 * data is left behind. On Windows the backend webServer may still hold a
 * file handle briefly — a locked file is tolerated (the next run's
 * global-setup deletes it anyway).
 */
import { existsSync, unlinkSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DB_PATH = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "backend", "e2e.db");

export default function globalTeardown() {
  if (!existsSync(DB_PATH)) return;
  try {
    unlinkSync(DB_PATH);
  } catch {
    // tolerated: next run's global-setup removes it
  }
}
