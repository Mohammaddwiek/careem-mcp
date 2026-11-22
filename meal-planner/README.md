# Prep with Careem Quik (meal planner)

Plan meals around what's in your kitchen, then order only what's missing from Careem Quik.

- `backend/`: FastAPI. Plans meals (`app/planner.py`, 20 recipes in `app/recipes.py`) using product
  facts from careem-mcp, and calls the Careem tools in a fixed order. Mutating tools only run from
  explicit button presses; checkout also needs `confirmed: true` and is never retried.
- `web/`: Vite + React + TypeScript, styled from the design tokens in `web/src/styles/tokens.css`.

## Run it

Each in its own terminal, from the repo root:

```powershell
.\careem-mcp-python\careem-mcp.ps1 start --live-cart
```

```powershell
meal-planner\backend\.venv\Scripts\python -m uvicorn app.main:app --app-dir meal-planner/backend --port 8001
```

```powershell
npm --prefix meal-planner/web run dev
```

Open http://localhost:5173. Add `?dev` to the URL to get the London test address (outside the
Careem Quik area) and a test card that declines.

First-time setup: `python -m venv meal-planner/backend/.venv`, then
`meal-planner\backend\.venv\Scripts\python -m pip install -r meal-planner/backend/requirements.txt`,
and `npm --prefix meal-planner/web install`.

Before a demo: `.\careem-mcp-python\careem-mcp.ps1 cart clear` so the cart starts empty.

## Tests

```powershell
meal-planner\backend\.venv\Scripts\python -m pytest meal-planner/backend
```

```powershell
npm --prefix meal-planner/web run build
```

The backend tests start their own careem-mcp server in live mode and cover planning, allergens,
pantry split, out-of-stock swaps, budget, cart edits, the checkout guard, stale totals, the
delivery-area error and a declined card.
