# Careem Builders '26: AI meal planner + Quik grocery assistant (brainstorm)

Status: brainstorm, not a spec. No app code yet. Date: 2026-11-22.

**The idea:** you tell the app what's in your fridge, what appliances you have, your allergies and
diet, and your budget or goals. It builds a meal plan, works out exactly which ingredients are
missing, matches them to live Careem Quik stock and deals, and orders the whole list in one tap
after you confirm.

---

## 1. NeatEat, broken down

Sources: the [App Store listing](https://apps.apple.com/us/app/id6783742855) and the
[ScreensDesign teardown](https://screensdesign.com/showcase/neateat-meal-planner).

### What it sells

You pick a supermarket and a weekly budget. You get a week of simple meals and a priced shopping
list that comes in under that budget. It's rated 4.7★ from about 1.5K ratings and sits around
#10 in Food & Drink. There's a hard paywall: a free trial, then $7.99/week, $12.99/month or
$29.99–39.99/year.

### Features

| Area | What NeatEat does |
| --- | --- |
| Planning | Weekly plan built to a budget; calorie target with daily macros; Meal Prep Mode (cook once, eat for up to 5 days); food styles (Mexican, Thai, high-protein, GLP-1 friendly, anti-inflammatory, …); reset plan |
| Inputs | Eating preferences, allergies (stricter filtering since v4.2), kitchen appliances, dislikes (e.g. fish), family size (per the third-party teardown) |
| Pantry | AI fridge scan that suggests meals from what you already have |
| Shopping | Grocery list that merges duplicate ingredients, grouped by aisle; custom items |
| Recipes | Import from websites and social media (strips the blog text); scan a cookbook page; cookbooks; step-by-step cooking mode |
| Social | Household sharing with an invite code |
| Delivery | "Order your groceries online for delivery", **USA only** (v4.2); the partner isn't named |

### Where it falls short (from the visible reviews and the product itself)

1. **The budget is a guess.** One reviewer set $200, the app estimated $157, and they spent over
   $300. Its prices are estimates, not the store's real prices, fees and promos.
2. **It forgets what you bought.** The same reviewer says the app made a new plan that ignored
   the ingredients they had already bought. The plan and the purchases aren't connected.
3. **Diet filtering is shaky.** "High-protein" returned only keto recipes, and gluten-free
   suggestions were poor. Allergy checks run against recipe text, not the actual products.
4. **Scaling and measurements.** Scaling a recipe for two changed the ingredient amounts but not
   the instructions, and the measurements were odd. A shopping list in tablespoons doesn't match
   products sold in 500 g packs.
5. **Shopping is still a chore.** Outside the US you take the list to a store or a separate app.
   Nothing knows what's in stock, what's on offer, or what you usually buy.
6. **Generic recipes**, a hard paywall, and nothing local: no UAE stores, AED prices or regional
   dishes.

Our opening: every one of 1, 2, 3 (at the product level) and 5 is a **data problem that Careem
MCP solves**. NeatEat guesses prices, stock and history; we can read them.

---

## 2. What the Careem MCP gives us

From `careem-mcp-sandbox/spec/tools/` (42 tools) and `docs/careem-mcp/agent-playbook.md`.

### Grocery-side tools, mapped to the product

| Tool | What it gives us | Where it shows up |
| --- | --- | --- |
| `user_info` | Name, currency, saved addresses (Home/Work/Gym), routine and welcome suggestions per vertical | Onboarding with no form: "Deliver to Home, Marina Gate 1?" |
| `is_grocery_area_serviceable` | Does Quik deliver here? | First check; if no, offer a plan only, or Careem Shops |
| `search_groceries_get_top_user_items` | The user's usual Quik items (falls back to `top_picks`, `is_personalized: false`) | "Assumed pantry" (they buy eggs weekly, so they probably have some), plus plans built around food they already like |
| `search_groceries_get_all_deals` | Every current Quik deal, grouped by category, in cart-ready item shape | Deal-driven planning: pick recipes around what's discounted today |
| `search_groceries_items` | Search many terms in one call. Filters: `on_discount`, `previously_ordered`, `careem_recommended`, `max_delivery_minutes`, `limit`. Returns real ids, prices and `is_available`. Suggests Careem Shops merchants when Quik has nothing | The core "ingredient → product" step; the stock check; "your usual brand" picks |
| `groceries_get_items_details` | Up to 20 items at once: price, promos, availability, **nutrition and attributes, certifications**, variants (sizes) | Check allergens and diet against the actual product, not the recipe; pick the pack size that covers the quantity; macros from real labels |
| `global_search` | Careem Shops merchants (organic stores, supermarkets) and their items; Quik is excluded | Fallback for specialty ingredients (tahini, gluten-free flour, kombucha) |
| `create_grocery_cart_with_quantities` | Puts an already-resolved list into the Quik basket in one call; reports low stock, out of stock and unpriced items per line | The "one click" |
| `cart_get_quik_basket` | The user's current Quik basket, no merchant id needed | Don't silently merge with an existing basket: "You already have 4 items in your basket. Keep them?" |
| `cart_add_item(s)` / `cart_update_item` / `cart_delete_items` / `cart_delete_basket` | Edit lines (batch add is partial-success) | Swap or remove items on the review screen |
| `cart_get_basket_price` | Real total: subtotal + delivery + service − best promo (auto-applied) + resolved payment | **The real price against the budget**, before checkout. The playbook requires it before checkout |
| `cart_get_checkout_promos` | Available promos (lists them, never applies) | "Add AED 12 more to unlock free delivery" |
| `cart_grocery_checkout` | Places the Quik order; card returns a `deep_link` to finish payment; cash and wallet don't | Behind an explicit confirmation step |
| `get_activities` / `track_activity` | Order history (past/ongoing/upcoming, filterable by type); live tracking with `poll_after` | Live "your groceries are 12 min away" card; past Quik and Shops orders feed the pantry |
| `cart_reorder` | Rebuild a basket from a past order | "Repeat last week's plan" |
| `reverse_geocode` / `save_new_address` | Address from coordinates; save a bookmark | Onboarding when the user has no saved address |

### Food tools: a "lazy night" bonus?

`food_dish_search` / `food_dynamic_search` / `food_merchant_search` / `food_get_restaurant_menu`,
the cart tools for food, plus `food_get_scheduling_slots`.

**My call: one small hook, not a feature area.** On a plan day the user swipes "too tired to
cook", and we suggest a restaurant dish with similar macros from `food_dish_search` (a "chicken"
night becomes a grilled chicken bowl), then hand off to the normal food checkout. That shows we
know the whole Careem super-app, for about half a day of work. Anything bigger dilutes the
grocery story.

**Skip:** Box (parcel delivery), maps (only the Careem widget uses it), and rides.

### Constraints that shape the design

1. **The sandbox catalog is tiny.** Quik has 8 SKUs: milk, eggs (12), sourdough, bananas, water,
   avocado (always out of stock), Greek yogurt, and ground coffee (the only deal, 20% off). The
   only other stock is a few Careem Shops items: organic milk and eggs, kombucha.
   **Chicken, rice, tomatoes and the like don't exist.** A realistic weekly plan will mostly come
   back "not found" in the sandbox.
2. **The sandbox has no memory between calls, and its carts are fixed.**
   `create_grocery_cart_with_quantities` always returns the same milk ×2 / eggs / sourdough cart,
   and the price is always AED 45.50, whatever we send. A demo on the stock sandbox can't show
   *our* list being priced.
3. **We control the local server.** Scenario files are re-read on every call, so we could add
   our own SKUs and scenarios to *our copy* of the spec. That would make a weekly plan demo-able,
   but those items aren't production-identical.
4. **Golden rule from the playbook:** price the basket before checkout, send that exact total,
   confirm the contents, address and price with the user, and never blindly retry a checkout.
   A confirmation step isn't just good UX; it's the required behaviour.
5. **Many sequential calls.** A full grocery order is 6+ tool calls. Plan for latency: run
   searches in parallel, stream progress to the screen.

---

## 3. Roadmap brainstorm

### 3.1 The unfair advantage: what NeatEat can't do

1. **A budget you can trust.** The plan is priced from `cart_get_basket_price`: real fees, the
   best promo auto-applied, the exact AED total. "Your week: AED 187.50 of AED 200, delivery
   included." This hits NeatEat's worst review head on.
2. **Deal-driven meal planning.** We pull `search_groceries_get_all_deals` and the user's
   `previously_ordered` + `on_discount` items first, then choose recipes around what's cheap
   today. NeatEat plans first and prices afterwards; we price while we plan.
3. **Stock-aware swaps before you order.** `is_available: false` and low-stock lines trigger an
   automatic swap with a reason ("Avocado is out of stock, so we swapped in Greek yogurt for the
   toast topping"). Shown on the review screen, never applied silently.
4. **Allergy checks against the real product.** `groceries_get_items_details` returns nutrition,
   attributes and certifications for each SKU, so "gluten-free" is checked on the actual loaf
   we're putting in the cart. Macros come from real labels.
5. **Planning to delivery in one place.** One tap fills the Quik basket, a confirmation step,
   checkout, then a live tracker (`track_activity`) saying "15 min away". The next plan
   automatically counts what was just delivered as pantry. This fixes "it forgot what I bought".

### 3.2 Scope for the hackathon

**Must-have MVP (the live demo has to be flawless):**

- Onboarding from `user_info` (name, Home address) + `is_grocery_area_serviceable`, plus a short
  preferences form: allergies, diet, appliances, people, budget, days.
- Pantry input: a typed list or chips (with the "usual items" from
  `search_groceries_get_top_user_items` pre-ticked as "probably have").
- An LLM meal plan (3–7 days) that respects allergies and appliances, with merged quantities.
- Pantry diff, then **matching ingredients to products** (`search_groceries_items` with many
  terms in one call), choosing pack sizes that cover the quantity.
- A review screen: each line shows the product, price, and why it's there ("for Tue's omelette").
  Unmatched ingredients go in a "buy elsewhere / skip" bucket.
- `create_grocery_cart_with_quantities`, then `cart_get_basket_price`, then **a confirmation
  step** (items, address, payment, exact total against the budget), then `cart_grocery_checkout`.
- A tracking card from `get_activities` + `track_activity`.
- Graceful errors: Quik doesn't deliver here, out of stock, upstream down. The sandbox has a
  scenario for each, so we can rehearse them.

**Wow factor (pick one or two):**

- **A. Deal-first "beat my budget" mode.** A slider shows the plan reshuffling around today's
  deals, with "you saved AED X compared to regular price" from the real promo line. The most
  Careem-native and easiest to demo. *My first pick.*
- **B. Fridge photo to pantry.** Snap the fridge, a vision model lists the ingredients, and
  they become pantry chips. Strong on stage; risky with demo lighting. Keep a pre-shot photo as
  a backup.
- **C. Pick a restaurant dish instead on a "too tired" night** (food hook above). Cheap and
  memorable.

**Cut / post-hackathon:**

- Recipe import from URLs and social, cookbook scanning, cookbooks.
- Household sharing, accounts, a paywall.
- Meal prep mode, food style catalog, a full nutrition dashboard (show macros, don't build a
  tracker).
- Careem Shops multi-store baskets (keep only as a "found at Marina Fresh Market" hint).
- Scheduled delivery slots, a recurring weekly auto-order.
- Step-by-step cooking mode, timers.
- Our own SKU database or price estimates. **Careem is the only source of prices.**

### 3.3 The user journey from start to finish

```
1. Open app
   → user_info(lat,lng)                      name, Home address, currency
   → is_grocery_area_serviceable(lat,lng)    Quik delivers? (no → plan only)

2. Preferences (≈30 s)
   allergies · diet · appliances (oven/air fryer/microwave) · people · days · budget AED

3. Pantry
   → search_groceries_get_top_user_items     pre-tick "you usually buy: eggs, milk…"
   user adds/removes chips  (wow B: fridge photo → chips)

4. Plan
   → search_groceries_get_all_deals          deals fed into the planner (wow A)
   LLM: plan within constraints → recipes → merged ingredient quantities
   pantry diff → missing list (e.g. 9 ingredients)

5. Matching ingredients to products
   → search_groceries_items(search_terms=[…9], previously_ordered / on_discount)
   → groceries_get_items_details(ids)        allergens, nutrition, pack size, variants
   out of stock / allergen hit → propose a swap (shown, not silent)
   no match → "not on Quik" bucket (optional global_search hint)

6. Review screen
   lines with product · price · reason · swap button
   → cart_get_quik_basket                    existing basket? keep / replace

7. Fill the cart and price it
   → create_grocery_cart_with_quantities(merchant_id, items)
   → cart_get_basket_price(merchant_id)      subtotal + fees − promo = exact total

8. Confirmation step (required)
   "9 items · Home, Marina Gate 1 · Wallet · AED 187.50 of your AED 200 budget"
   [Place order]  [Edit]
   → cart_grocery_checkout(total_price = the priced total)
   card → open deep_link to finish payment; never auto-retry on a timeout

9. Track
   → get_activities(ongoing, groceries) → track_activity(groceries, reference_id), poll every poll_after
   "Omar is 12 min away" → when delivered, the bought items become pantry for next week
```

---

## 4. Open questions for you

1. **Sandbox or real Careem for the demo?** Will the judged demo run against our local sandbox
   or production careem-mcp (OAuth via Careem Identity)? On the stock sandbox only 8 grocery
   items exist and carts are fixed at AED 45.50, so either we demo a "breakfast for the week"
   plan that fits those SKUs, or we add our own catalog to our copy of the spec, which the
   judges might see as not real.
2. **Who's it for, in one sentence?** Budget-squeezed families (NeatEat's audience), gym and
   macro people, or busy professionals in Dubai who just want dinner sorted? This decides
   whether the hero number is AED saved, protein per day, or minutes saved, and which wow
   feature to build.
3. **What surface?** A ChatGPT/Claude-style chat app on the MCP (the Careem widget renders
   inside it), a standalone web or mobile app with its own UI that calls the MCP from a backend,
   or both? It changes how much UI we build and how the confirmation step looks.
4. **How far does "one click" go?** Should we stop at a filled, priced basket the user checks
   out in the Careem app, or place the order from our app (wallet/cash, or card via
   `deep_link`)? Placing the order is the stronger demo, but it carries the most risk.
5. **Team and time?** How many people, how many hours, and who's strong on frontend versus the
   LLM/agent side? That decides whether we can do both wow features or only one.
