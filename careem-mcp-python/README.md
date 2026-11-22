# careem-mcp (Python)

Local careem-mcp server built from `spec/` (a copy of `../careem-mcp-sandbox/spec`), following
`spec/BUILD.md`. It answers every tool call from the scenario files and makes no network calls.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## CLI

Use `careem-mcp.ps1` / `careem-mcp.cmd` on Windows or `./careem-mcp.sh` in a POSIX shell.

| Command | What it does |
| --- | --- |
| `start` / `stop` / `status` | run the HTTP server in the background on `http://127.0.0.1:8787/mcp` |
| `logs [-n 50]` | tail `.run/server.log` (one line per tool call: tool, scenario, args) |
| `scenarios [tool]` | list scenarios and their match rules |
| `scenario <tool> <name>` | force a scenario (writes `.run/overrides.json`); omit `<name>` to clear |
| `reset` | clear all forced scenarios |
| `check` | render every scenario and validate it against the tool's output schema |

| `start --live-cart` | start with the live catalog and editable basket (below) |
| `cart` / `cart reset` / `cart clear` | show the live basket and total / restore the starting basket / empty it |

## Live mode (`--live-cart`)

The stock spec answers every cart call with the same milk/eggs/sourdough basket at AED 45.50.
With `--live-cart` (or `CAREEM_MCP_LIVE_CART=1`) the grocery tools work on real data instead:

- `catalog/quik.json`: 80 Quik products (AED price, pack size, nutrition per 100 g/ml, allergens,
  diet tags); 6 deals and 2 out of stock (avocado `4000106`, salmon `4000148`). Edit it freely;
  the server reads it at start-up.
- `search_groceries_items`, `groceries_get_items_details`, `search_groceries_get_all_deals` answer
  from the catalog (details carry the nutrition table, an `allergens` attribute and diet/allergen tags).
- One Quik basket (`6000002`, stored in `.run/cart.json`) that `create_grocery_cart_with_quantities`,
  `cart_add_item(s)`, `cart_update_item` (count 0 removes), `cart_delete_items`, `cart_delete_basket`,
  `cart_get_quik_basket`, `cart_get_basket` and `cart_get_basket_price` all read and change.
  Total = items (after deals) + AED 4.00 delivery + AED 1.50 service.
- `cart_grocery_checkout` charges that total, answers the canned 409 if `total_price` is stale,
  and empties the basket.
- Failure scenarios still work: bad coordinates, upstream outages, forced scenarios and non-Quik
  merchants return the canned answers.

Other transports: `GET /sse` (legacy SSE), `python -m careem_mcp.server --stdio`.
Health: `GET /health`. Settings: `--port`, `--spec-dir`, `--overrides`, `--widget-domain`,
`--allowed-host` (for tunnels), `--no-output-schema`, `--no-meta`, or the `CAREEM_MCP_*` env vars.

## Tests

```powershell
.venv\Scripts\python -m pytest tests
```

Covers acceptance tests 1-12 from `spec/BUILD.md` §7 against a real server on a free port.

## Connect

```powershell
claude mcp add --transport http careem-mcp http://127.0.0.1:8787/mcp
```
