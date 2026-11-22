# Live catalog + editable cart for the local careem-mcp server (short design)

Status: approved in conversation 2026-11-22 ("go with A … make the cost changeable … edit
everything in your cart … 60–80 Quik products … do it").

## Why

The meal-planner app (approach A: a FastAPI backend calls the Careem tools in a fixed order;
Claude plans and matches) needs a believable grocery world. The stock sandbox has 8 Quik SKUs, and
its cart, price and checkout responses are fixed (always milk ×2 / eggs / sourdough, AED 45.50),
so a meal plan can't be priced or ordered. This change makes our local server answer the grocery
tools from a real-looking catalog and a cart that remembers what is put in it.

## Goals

- About 70 Quik products with AED prices, pack sizes, nutrition per 100 g/ml, allergen and diet
  tags, around 6 deals and 2 out of stock (avocado `4000106` stays out of stock).
- `search_groceries_items`, `groceries_get_items_details` and `search_groceries_get_all_deals`
  answer from the catalog.
- One persistent Quik basket (`6000002`, merchant `40001`) that every grocery cart tool reads and
  edits: create, add, add batch, update count, delete lines, delete basket, get, price, checkout.
- The price is calculated: items (with deal discounts) + AED 4.00 delivery + AED 1.50 service.
  Checkout charges that total and rejects a stale total.

## Non-goals

- Changing the default behaviour. Everything sits behind `--live-cart` (env
  `CAREEM_MCP_LIVE_CART=1`); without it the server still passes the 17 spec tests unchanged.
- Food baskets, Careem Shops merchants, rides, Box: unchanged canned scenarios.
- Multi-user state: one user (the fixture persona), one basket.
- Auto-applied grocery promos: the fixture grocery price has none, so savings come only from
  item deals (`total_saving`).

## Anti-goals

- Responses that break a tool's `outputSchema`. Every live response is validated in tests.
- Losing the failure scenarios. A forced scenario, or a matched scenario whose response carries
  an `error`, is returned as canned, so "outside service area", "upstream down" and the rest can
  still be rehearsed. Calls for a non-Quik `merchant_id` are canned too.

## Approaches considered

1. **Static edits to the scenario files**: change the numbers by hand. Rejected: it's still one
   fixed number, not tied to the cart.
2. **More scenarios and match rules**: rejected, because templates can only echo arguments and
   `cart_get_basket_price` receives no items, so it can't add anything up.
3. **Live handlers in our server (chosen)**: for the grocery tools, take the canned
   happy-path response as the skeleton (so every field the client sees keeps production's shape)
   and replace the lines, counts and prices with values from the catalog and the stored basket.

## Design

- `careem-mcp-python/catalog/quik.json`: the product list. Per product: id, name, unit text,
  pack size, price, optional original price (deal), category (id, name, parent), search keywords,
  allergens, diet tags, nutrition, availability, stock.
- `careem_mcp/live.py`: catalog loading, keyword search, and the basket store (persisted to
  `.run/cart.json`, seeded with the fixture basket milk ×2 / eggs / sourdough so the default total
  is still AED 45.50), plus one handler per live tool. Each handler gets the arguments and the
  rendered canned response and returns the live response.
- `server.py`: after choosing a scenario, if live mode is on, the tool has a handler, the scenario
  wasn't forced, the canned response has no `error`, and the merchant is Quik (or none), it calls
  the handler.
- Search: case-insensitive match of each term against the name and keywords (a trailing "s"/"es"
  is ignored); one group per term; filters `on_discount`, `previously_ordered` (the fixture's usual
  items), `careem_recommended`, `limit`, `page`.
- Cart semantics: create and add **add** to existing lines; out of stock and unknown ids are
  reported per line and not added; asking for more than the stock adds what's available.
  `cart_update_item` with count 0 removes the line. Deleting every line or the basket empties it,
  and then `cart_get_quik_basket` returns the canned "cart does not exist yet" answer.
- Checkout: an empty basket → the canned "basket not found" response; `total_price` differing from
  the live total by more than AED 0.01 → the canned `price-changed` (409) response; otherwise the
  card, cash or wallet scenario with `amount` set to the live total, and the basket is emptied.
- CLI: `cart` (show lines and total), `cart reset` (back to the seed basket), `cart clear` (empty).

## Left to the builder

The exact product list and numbers, keyword lists, and how out-of-stock lines appear in each
response (following the canned out-of-stock scenarios' shapes).
