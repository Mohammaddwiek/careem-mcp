# Meal planner app on Careem Quik (short design)

Status: built from the user's brief of 2026-11-22 (four screens, safe checkout, tokens file
`careem_mcp_design_system_token_specification.md`) plus approach A chosen earlier.

## Intent

A meal-prep planner for anyone: the user says what is in their pantry, their appliances,
allergies, diet, budget and goal; the app plans meals, splits ingredients into "have" and "need",
matches the needs to live Careem Quik products and prices, fills the Quik basket on request and
checks out only after an explicit confirmation, then tracks the delivery.

## Decisions

- **Approach A:** FastAPI backend (`meal-planner/backend`) calls the local MCP server
  (`http://127.0.0.1:8787/mcp`, live mode) in a fixed order with a small JSON-RPC client. The
  browser never talks to MCP directly.
- **Planner (my call, no API key available):** deterministic, over a 20-recipe library whose
  ingredients are Quik product ids. Product facts (price, deal, allergens, diet tags, nutrition,
  pack size, stock) come from MCP (`groceries_get_items_details`, `search_groceries_get_all_deals`),
  not from local files. Scoring by goal (save money / high protein / quick / balanced), with
  bonuses for deal items, pantry items and ingredient overlap. A Claude call can replace or
  annotate it later.
- **Frontend:** Vite + React + TypeScript, plain CSS on the tokens file (`tokens.css`, dark default,
  light toggle), `motion` for springs and shared-layout morphs, `lucide-react` icons, fonts bundled
  with `@fontsource`.
- **Safety:** read-only tools run freely. `create_grocery_cart_with_quantities` and the cart edit
  tools run only from an explicit button press. `cart_grocery_checkout` runs only after a separate
  confirmation step in the sheet, sends the exact total from `cart_get_basket_price`, and is never
  retried automatically; the backend refuses a checkout request without `confirmed: true`.

## Screens

1. Setup: pantry (search + chips + "you usually buy" from `search_groceries_get_top_user_items`),
   kitchen appliances, allergies, diet, people, days, meals per day, budget, goal, delivery address
   (saved addresses from `user_info`; serviceability from `is_grocery_area_serviceable`).
2. Plan: meal cards (prep time, macros per serving, deal badges, swap one meal) and a live deals rail.
3. Have vs need: pantry items on one side; on the other, needed products matched with
   `search_groceries_items`, with packs, live price, deal, swaps for out-of-stock items, and an
   estimate against the budget.
4. Cart sheet: `create_grocery_cart_with_quantities` (replace or keep an existing basket),
   `cart_get_basket_price` breakdown, line edits, payment choice, confirmation gate, checkout,
   then the tracker from `get_activities` + `track_activity`.

## Errors shown in the UI

Outside the Quik area (London test address), out-of-stock items (avocado, salmon) swapped or
flagged, checkout outside delivery area (Gym address), stale total (409), payment declined
(forced scenario or declined test card), upstream outages.

## Signature moment

Adding to the cart: the "need" rows fly into the cart button (shared-layout morph), the button
count springs up. Reduced motion: instant.
