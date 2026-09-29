# Portfolio Demo Script

Every step below was executed against the real running application (see
`docs/screenshots/` for captured evidence). All data is fictional.

```bash
# 1. Start (two terminals)
cd backend  && .venv/Scripts/uvicorn app.main:app --reload    # http://localhost:8000
cd frontend && npm run dev                                    # http://localhost:5173

# 2. Seed demo data
cd backend && python -m app.seed --reset
```

3. **Dashboard** — open `http://localhost:5173/`: stat cards, recent orders,
   low-stock list, recent movements.
4. **Create product** — Products → *New Product*: SKU `DEMO-100`, name
   `Demo Widget`, unit price `19.90`, initial stock `10`, threshold `4`.
5. **Stock In** — open the product detail → *Stock In* → quantity `5`, note
   `PO-2041` → stock 10 → 15, movement recorded.
6. **Create order** — Orders → *New Order*: pick a customer, add `DEMO-100`
   quantity `3` → *Create draft order*.
7. **Confirm order** — order detail → *Confirm order*: status → Confirmed,
   stock 15 → 12, `Stock Out` movement referencing the order appears.
8. **Verify stock drop** — the product page shows the OUT movement linked to
   the order number.
9. **Cancel order** — order detail → *Cancel order* → confirm dialog →
   status Cancelled, stock restored 12 → 15, `Stock In` movement recorded.
10. **Low stock** — Inventory → *Low Stock* tab: products at/below threshold
    (the seed includes an out-of-stock item).
11. **Export CSV** — Products → *Export CSV* (also: Orders export, Inventory →
    Export movements CSV).
12. **API docs** — `http://localhost:8000/docs` (Swagger UI) and
    `backend/scripts/verify_api.py` for an automated end-to-end check:

```bash
cd backend && .venv/Scripts/python.exe scripts/verify_api.py http://127.0.0.1:8000
```
