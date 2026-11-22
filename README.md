# careem-mcp

Careem Builders '26 project: **Prep**, a meal-prep planner that plans a week around what's in your
kitchen and orders only what's missing from Careem Quik, with an explicit confirmation before checkout.

| Folder | What it is |
| --- | --- |
| [`careem-mcp-python/`](careem-mcp-python/) | Local Careem MCP server built from the official sandbox spec. `--live-cart` adds an 87-product Quik catalog and a real, editable, priced basket. |
| [`meal-planner/`](meal-planner/) | The app: FastAPI backend (planner, 32 recipes, optional Claude planning) and a React web UI (10-step onboarding, plan, recipes, cart, checkout, tracking). |
| [`careem-mcp-sandbox/`](careem-mcp-sandbox/) | The official no-code sandbox package, unchanged. |
| [`docs/`](docs/) | Careem agent playbook, design tokens, brainstorm, designs and plans. |

## Run it (Windows PowerShell, from this folder)

```powershell
.\careem-mcp-python\careem-mcp.ps1 start --live-cart
```

```powershell
meal-planner\backend\.venv\Scripts\python -m uvicorn app.main:app --app-dir meal-planner/backend --port 8001
```

```powershell
npm --prefix meal-planner/web run dev
```

Open http://localhost:5173 (add `?dev` for a test address outside the Quik area and a card that declines).
First-time setup for each part is in [careem-mcp-python/README.md](careem-mcp-python/README.md) and
[meal-planner/README.md](meal-planner/README.md).

## Tests

```powershell
careem-mcp-python\.venv\Scripts\python -m pytest careem-mcp-python
```

```powershell
meal-planner\backend\.venv\Scripts\python -m pytest meal-planner/backend
```

```powershell
npm --prefix meal-planner/web run build
```
