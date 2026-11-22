"""HTTP API for the meal planner. Calls careem-mcp tools in a fixed order (approach A).

Read-only tools run freely. Mutating tools run only from explicit endpoints the UI calls on a
button press; checkout additionally requires `confirmed: true` and is never retried.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import planner
from .mcp import MCPClient, MCPError
from .products import Product, from_details
from .recipes import ALL_PRODUCT_IDS, APPLIANCES

QUIK = 40001
BASKET_ID = 6000002
HOME = (25.0866, 55.1474)
TEST_ADDRESS = {"id": "TEST-LONDON", "title": "London (test)", "subTitle": "Outside the Careem Quik area",
                "latitude": 51.5074, "longitude": -0.1278, "test": True}
ALLERGENS = ["gluten", "dairy", "egg", "peanuts", "tree_nuts", "soy", "fish", "shellfish", "sesame"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
app = FastAPI(title="Careem Quik meal planner")
mcp = MCPClient(os.environ.get("CAREEM_MCP_URL", "http://127.0.0.1:8787/mcp"))
_facts: dict[str, Any] = {"at": 0.0, "data": {}}


@app.exception_handler(MCPError)
async def mcp_failed(_: Request, exc: MCPError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


# ---------------------------------------------------------------- helpers


def facts(lat: float, lng: float, extra: set[int] | None = None, max_age: float = 20.0) -> dict[int, Product]:
    """Product facts for every recipe product (plus extra ids), from groceries_get_items_details."""
    ids = sorted(set(ALL_PRODUCT_IDS) | (extra or set()))
    cached: dict[int, Product] = _facts["data"]
    if time.time() - _facts["at"] > max_age or not set(ids) <= cached.keys():
        fresh: dict[int, Product] = {}
        for i in range(0, len(ids), 20):
            out = mcp.call("groceries_get_items_details", {"merchant_id": QUIK, "item_ids": ids[i:i + 20],
                                                           "latitude": lat, "longitude": lng})
            for row in out.get("items") or []:
                if row.get("data"):
                    p = from_details(row["data"])
                    fresh[p.id] = p
        _facts.update(at=time.time(), data=fresh)
    return _facts["data"]


def search_item_json(it: dict[str, Any]) -> dict[str, Any]:
    price = it.get("price") or {}
    tags = it.get("tags") or []
    return {
        "id": it["id"], "name": it.get("item", ""), "unit": (it.get("description") or "").rpartition("(")[2].rstrip(")"),
        "price": price.get("total"), "original_price": price.get("original") if price.get("discount") else None,
        "deal_pct": price.get("discount_percentage") or 0, "available": it.get("is_available", True),
        "allergens": sorted(t[len("allergen_"):] for t in tags if isinstance(t, str) and t.startswith("allergen_")),
        "diet": sorted(t for t in tags if isinstance(t, str) and not t.startswith("allergen_")),
    }


def cart_json(env: dict[str, Any]) -> dict[str, Any]:
    """Normalize a basket envelope (cart_get_basket_price and friends) for the UI."""
    if env.get("error") or not env.get("basket"):
        return {"basket": None, "error": env.get("error")}
    b, money = env["basket"], env.get("price") or {}
    rows = []
    for row in money.get("breakdown") or []:
        rows.append({"label": row["label"]["title"], "amount": row["value"][0]["price"],
                     "kind": row["value"][0].get("type", "regular"), "note": (row.get("helper_msg") or {}).get("msg")})
    return {
        "basket": {
            "id": b["id"], "count": b.get("total_count", 0),
            "lines": [{"item_uuid": l["item_uuid"], "catalog_item_id": l["catalog_item_id"], "name": l.get("title_localized", ""),
                       "count": l["count"], "total": l["price"]["total"], "original": l["price"]["original"]}
                      for l in b.get("items") or []],
        },
        "breakdown": rows,
        "total": (money.get("price") or {}).get("total"),
        "saving": money.get("total_saving", 0),
        "promo": (money.get("promo_code") or {}).get("code"),
        "payment_method": env.get("payment_method"),
        "merchant": {"name": (env.get("merchant") or {}).get("name"), "eta": (env.get("merchant") or {}).get("eta_in_minutes")},
    }


def priced_cart(lat: float, lng: float) -> dict[str, Any]:
    return cart_json(mcp.call("cart_get_basket_price", {"merchant_id": QUIK, "latitude": lat, "longitude": lng}))


# ---------------------------------------------------------------- read-only routes


@app.get("/api/bootstrap")
def bootstrap(lat: float = HOME[0], lng: float = HOME[1]) -> dict[str, Any]:
    info = mcp.call("user_info", {"latitude": lat, "longitude": lng})
    service = mcp.call("is_grocery_area_serviceable", {"latitude": lat, "longitude": lng})
    serviceable = bool(service.get("serviceable")) and not service.get("error")
    usuals, deals, products = [], [], []
    if serviceable:
        top = mcp.call("search_groceries_get_top_user_items", {"latitude": lat, "longitude": lng})
        usuals = [search_item_json(i) for i in ((top.get("data") or {}).get("items") or [])]
        d = mcp.call("search_groceries_get_all_deals", {"latitude": lat, "longitude": lng})
        deals = [search_item_json(i) for g in d.get("groups") or [] for i in g.get("items") or []]
        products = sorted((p.to_json() for p in facts(lat, lng).values()), key=lambda p: (p["category"], p["name"]))
    user = info.get("user_info") or {}
    return {
        "user": {"name": user.get("given_name") or user.get("name") or "there", "currency": user.get("currency", "AED")},
        "addresses": [*(info.get("saved_bookmarks") or []), TEST_ADDRESS],
        "serviceable": serviceable,
        "service_error": service.get("error"),
        "usuals": usuals, "deals": deals, "products": products,
        "appliances": list(APPLIANCES), "allergens": ALLERGENS,
    }


@app.get("/api/search")
def search(q: str, lat: float = HOME[0], lng: float = HOME[1]) -> dict[str, Any]:
    out = mcp.call("search_groceries_items", {"search_terms": [q], "latitude": lat, "longitude": lng, "limit": 8})
    items = [search_item_json(i) for g in out.get("groups") or [] for i in g.get("items") or []]
    return {"items": items, "error": None if items else out.get("error")}


class PlanRequest(BaseModel):
    lat: float = HOME[0]
    lng: float = HOME[1]
    pantry: list[int] = []
    appliances: list[str] = ["stove"]
    allergens: list[str] = []
    diet: str = "any"
    people: int = Field(2, ge=1, le=8)
    days: int = Field(5, ge=1, le=7)
    meals: str = "dinner"
    budget: float = Field(250, ge=20, le=5000)
    goal: str = "balanced"
    batch_cook: bool = True
    keep: list[str] = []
    exclude: list[str] = []


@app.post("/api/plan")
def make_plan(req: PlanRequest) -> dict[str, Any]:
    prefs = planner.Prefs(
        pantry=set(req.pantry), appliances=set(req.appliances), allergens=set(req.allergens), diet=req.diet,
        people=req.people, days=req.days, meals=req.meals, budget=req.budget, goal=req.goal,
        batch_cook=req.batch_cook, keep=req.keep, exclude=req.exclude,
    )
    result = planner.plan(facts(req.lat, req.lng, set(req.pantry)), prefs)
    if not result["recipes"]:
        return {**result, "error": "No recipes fit these settings. Try allowing another appliance or fewer restrictions."}
    # match every needed ingredient to live Careem Quik inventory in one search call
    terms = list(dict.fromkeys(n["term"] for n in result["need"]))
    found = mcp.call("search_groceries_items", {"search_terms": terms, "latitude": req.lat, "longitude": req.lng, "limit": 5})
    groups = {g["name"]: [search_item_json(i) for i in g.get("items") or []] for g in found.get("groups") or []}
    for n in result["need"]:
        options = groups.get(n["term"], [])
        live = next((o for o in options if o["id"] == n["product"]["id"]), None)
        if live and live["available"]:
            n["match"] = {"status": "matched", "price": live["price"]}
        elif any(o["available"] for o in options):
            alt = next(o for o in options if o["available"])
            n["match"] = {"status": "alternative", "suggested": alt}
        else:
            n["match"] = {"status": "not_found"}
    result["searched_terms"] = len(terms)
    return result


@app.get("/api/cart")
def get_cart(lat: float = HOME[0], lng: float = HOME[1]) -> dict[str, Any]:
    out = mcp.call("cart_get_quik_basket", {"latitude": lat, "longitude": lng})
    if not out.get("basket"):
        return {"basket": None}
    return priced_cart(lat, lng)


@app.get("/api/track")
def track() -> dict[str, Any]:
    acts = mcp.call("get_activities", {"activity_status": "ongoing"})
    ongoing = [a for a in acts.get("ongoing_activities") or acts.get("activities") or [] if a.get("type") == "groceries"]
    ref = ongoing[0]["reference_id"] if ongoing else "order_9002"
    return mcp.call("track_activity", {"activity_type": "groceries", "reference_id": ref})


# ---------------------------------------------------------------- mutating routes (explicit user actions only)


class CartLine(BaseModel):
    catalog_item_id: str
    keyword: str
    quantity: int = Field(ge=1, le=50)
    price: float | None = None


class CartRequest(BaseModel):
    lat: float = HOME[0]
    lng: float = HOME[1]
    mode: str = "replace"  # replace an existing basket, or keep its items
    lines: list[CartLine]


@app.post("/api/cart")
def fill_cart(req: CartRequest) -> dict[str, Any]:
    if not req.lines:
        raise HTTPException(400, "Nothing to add.")
    if req.mode == "replace":
        mcp.call("cart_delete_basket", {"merchant_id": QUIK, "latitude": req.lat, "longitude": req.lng})
    created = mcp.call("create_grocery_cart_with_quantities", {
        "merchant_id": QUIK, "latitude": req.lat, "longitude": req.lng,
        "items": [l.model_dump(exclude_none=True) for l in req.lines],
    })
    if created.get("error"):
        return {"basket": None, "error": created["error"]}
    data = created.get("data") or {}
    return {**priced_cart(req.lat, req.lng), "failed_items": data.get("failed_items") or [],
            "payment_type": data.get("payment_type")}


class LineUpdate(BaseModel):
    lat: float = HOME[0]
    lng: float = HOME[1]
    item_uuid: str
    catalog_item_id: str
    count: int = Field(ge=0, le=50)


@app.patch("/api/cart/line")
def update_line(req: LineUpdate) -> dict[str, Any]:
    out = mcp.call("cart_update_item", {"merchant_id": QUIK, "latitude": req.lat, "longitude": req.lng,
                                        "item_uuid": req.item_uuid, "catalog_item_id": req.catalog_item_id, "count": req.count})
    if out.get("error"):
        return {**priced_cart(req.lat, req.lng), "error": out["error"]}
    return priced_cart(req.lat, req.lng)


class LineDelete(BaseModel):
    lat: float = HOME[0]
    lng: float = HOME[1]
    item_uuid: str


@app.post("/api/cart/line/delete")
def delete_line(req: LineDelete) -> dict[str, Any]:
    mcp.call("cart_delete_items", {"merchant_id": QUIK, "latitude": req.lat, "longitude": req.lng, "item_uuids": req.item_uuid})
    return get_cart(req.lat, req.lng)


class CheckoutRequest(BaseModel):
    lat: float = HOME[0]
    lng: float = HOME[1]
    total_price: float
    payment_type: str = "wallet"  # wallet, card, cash
    payment_id: int | None = None
    confirmed: bool = False


@app.post("/api/checkout")
def checkout(req: CheckoutRequest) -> dict[str, Any]:
    if req.confirmed is not True:
        raise HTTPException(400, "Checkout needs an explicit confirmation.")
    args: dict[str, Any] = {"basket_id": BASKET_ID, "total_price": req.total_price, "payment_type": req.payment_type,
                            "latitude": req.lat, "longitude": req.lng}
    if req.payment_id is not None:
        args["payment_id"] = req.payment_id
    out = mcp.call("cart_grocery_checkout", args)  # never retried: a timeout could still have placed the order
    if out.get("error"):
        out["message"] = checkout_message(out["error"])
    return out


def checkout_message(raw: str) -> str:
    """Plain-language version of a checkout failure; the raw text stays in `error`."""
    text = raw.lower()
    if "402" in text or "declin" in text:
        return "Your card was declined. Choose another payment method and try again."
    if "409" in text:
        return "The total changed since you reviewed it. Check the new total before placing the order."
    if "saved address" in text:
        return "This address isn't saved in Careem yet. Pick Home or Work, or save it in the Careem app first."
    if "doesn't deliver" in text or "delivery area" in text:
        return "Careem Quik doesn't deliver to this address. Pick another address."
    if "location" in text:
        return "We couldn't confirm your delivery address. Pick a saved address and try again."
    if "404" in text or "not found" in text:
        return "Your basket is empty or expired. Add the items again."
    return "The order didn't go through. Nothing was charged; you can try again."
