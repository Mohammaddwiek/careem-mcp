# Live catalog + editable cart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Behind `--live-cart`, the local careem-mcp server answers the grocery search tools from a
~70-product Quik catalog and keeps one editable, calculated-price Quik basket.

**Architecture:** `careem_mcp/live.py` holds the catalog, the basket store (persisted JSON) and one
handler per live tool. `server.py` calls a handler after scenario selection when live mode applies;
the handler takes the rendered canned response as a skeleton and replaces lines, counts and prices.

**Tech Stack:** Python 3.14, mcp 2.3.0 (low-level Server), jsonschema, pytest, httpx.

**Spec:** `docs/superpowers/specs/2026-11-22-live-catalog-cart-design.md`

## Global Constraints

- Default (no flag) behaviour unchanged: `tests/test_acceptance.py` (17 tests) must keep passing.
- Live mode on with `--live-cart` or env `CAREEM_MCP_LIVE_CART=1`; catalog path `--catalog`
  (default `catalog/quik.json`); state `--cart-state` (default `.run/cart.json`).
- Quik merchant `40001`, basket `6000002`, user `900000001`, currency AED, delivery 4.00, service 1.50.
- Seed basket: `4000101` ×2, `4000102` ×1, `4000103` ×1 → subtotal 40.00, total 45.50.
- Product ids `4000101`–`4000108` keep the fixture names and prices; `4000106` avocado out of stock;
  `4000108` coffee is AED 40.00 → 32.00 (20% off).
- Canned passthrough: forced scenario, canned response containing a truthy `error`, or a
  `merchant_id` other than null/40001.
- Every live response validates against the tool's `outputSchema`.
- No observable string contains "mock", "sandbox", "sbx", "fake", "dummy", "example.com".

## Review Focus

1. Quantities as floats or 0/negative in create/add (`quantity: 0`) → line skipped, not a crash.
2. Price after deal items: `total_saving` equals the sum of item discounts; totals rounded to 2 dp.
3. Checkout with a total off by float noise (45.499999) → accepted (tolerance 0.01).
4. Corrupt or missing `.run/cart.json` → falls back to the seed basket, no crash.
5. `cart_delete_items` with a comma-separated `item_uuids` string containing spaces → each uuid removed.

---

### Task 1: Catalog

**Files:**
- Create: `careem-mcp-python/catalog/quik.json`
- Create: `careem-mcp-python/careem_mcp/live.py` (catalog part)
- Test: `careem-mcp-python/tests/test_live.py`

**Interfaces:**
- Produces: `Product` dataclass (`id:int, name:str, unit:str, price:float, original:float|None,
  category:dict, keywords:list[str], allergens:list[str], diet:list[str], nutrition:dict,
  available:bool, stock:int, recommended:bool, image:str`, property `discount -> float`,
  `discount_pct -> int`); `load_catalog(path) -> dict[int, Product]`;
  `search(catalog, term, *, on_discount=False, previously_ordered=False, recommended=False) -> list[Product]`.

- [ ] Tests: `test_catalog_size_and_fixture_ids` (60–80 products; 4000101 name/price 6.75;
  4000106 unavailable; 4000108 price 32.0 original 40.0); `test_search_plural_and_keywords`
  (`search(c,"tomatoes")` and `"tomato"` both non-empty; `"chicken breast"` hits a chicken item;
  `"unicorn"` empty); `test_search_filters` (on_discount → all have original).
- [ ] Write the catalog: ~70 products across produce, meat & fish, dairy & eggs, bakery, pantry
  (rice, pasta, oils, spices, canned), frozen, drinks; ~6 deals; 2 unavailable.
- [ ] Implement; run `pytest tests/test_live.py -k catalog or search`; commit.

### Task 2: Basket store and pricing

**Files:** Modify `careem_mcp/live.py`; Test `tests/test_live.py`

**Interfaces:**
- Produces: `Basket` with `lines: list[dict(item_uuid, catalog_item_id:str, count:int)]`,
  `load(path) / save()`, `add(product, count) -> str (uuid)`, `set_count(uuid, count) -> bool`,
  `remove(uuids) -> list[str] missing`, `clear()`, `reset()` (seed);
  `price(basket, catalog) -> dict(subtotal, original, saving, delivery, service, total)`.

- [ ] Tests: `test_seed_total_45_50`; `test_add_merges_and_prices` (add 4000108 ×1 → subtotal
  72.00, saving 8.00, total 77.50); `test_set_count_zero_removes`; `test_corrupt_state_falls_back`.
- [ ] Implement; run; commit.

### Task 3: Live handlers + server hook

**Files:** Modify `careem_mcp/live.py`, `careem_mcp/server.py`; Test `tests/test_live.py`

**Interfaces:**
- Produces: `LiveMode(catalog_path, state_path)` with `handle(tool, args, canned) -> dict | None`
  (None ⇒ use canned) and `TOOLS: set[str]`. Tools: `search_groceries_items`,
  `groceries_get_items_details`, `search_groceries_get_all_deals`,
  `create_grocery_cart_with_quantities`, `cart_get_quik_basket`, `cart_get_basket`,
  `cart_get_basket_price`, `cart_add_item`, `cart_add_items`, `cart_update_item`,
  `cart_delete_items`, `cart_delete_basket`, `cart_grocery_checkout`.
- Server: `--live-cart`, `--catalog`, `--cart-state` flags; skeletons for envelope tools come from
  the canned `cart_get_quik_basket` / `quik-basket` response with `page` set to the tool's page.

- [ ] Tests (server started with `--live-cart`, temp state; helper validates each result against
  the tool's outputSchema): `test_live_search` (chicken → items, groups named by term);
  `test_live_details_allergens` (nutrition table + allergen info present);
  `test_live_deals` (6 deal items grouped by category); `test_live_cart_flow`
  (create with 3 items → price total = computed; update count; delete line; price changes);
  `test_live_out_of_stock_and_unknown` (4000106 / 4000199 reported, not added);
  `test_checkout_rejects_stale_total_then_succeeds` (wrong total → error 409 text; right total →
  amount equals total; basket then empty → `cart_get_quik_basket` has error);
  `test_live_errors_still_canned` (latitude 0 search → canned error); Review Focus tests 1, 3, 5.
- [ ] Implement handlers; run all tests (`pytest tests`), both files green; commit.

### Task 4: CLI + docs + run

**Files:** Modify `careem_mcp/cli.py`, `careem-mcp-python/README.md`

- [ ] `cart`, `cart reset`, `cart clear` commands (operate on the state file);
  `start` passes `--live-cart` through extras.
- [ ] Restart the server with `start --live-cart`; verify `claude mcp get careem-mcp` connected;
  commit.
