"""A short, in-memory record of every Careem MCP call, for the "Behind the scenes" panel.

Each call is tagged with the app step that caused it (set per request by the API middleware), so
the panel can show how one tap in the app turns into a sequence of MCP tool calls.
"""

from __future__ import annotations

import contextvars
import itertools
import threading
import time
from collections import deque
from typing import Any

# which app step the current request belongs to ("Building your plan", ...)
stage: contextvars.ContextVar[str] = contextvars.ContextVar("stage", default="App")

# what each tool does, in plain words, and whether it changes something for the customer
TOOLS: dict[str, tuple[str, bool]] = {
    "user_info": ("Who is the customer, plus their saved addresses", False),
    "is_grocery_area_serviceable": ("Does Careem Quik deliver to this address?", False),
    "search_groceries_get_top_user_items": ("What this customer usually buys on Quik", False),
    "search_groceries_get_all_deals": ("Today's Careem Quik deals", False),
    "groceries_get_items_details": ("Prices, stock, allergens and nutrition for products", False),
    "search_groceries_items": ("Match ingredients to real Quik products", False),
    "create_grocery_cart_with_quantities": ("Put the whole list into the Quik basket", True),
    "cart_get_quik_basket": ("Read the customer's current Quik basket", False),
    "cart_get_basket_price": ("Fees, discounts and the final total", False),
    "cart_update_item": ("Change a quantity in the basket", True),
    "cart_delete_items": ("Remove an item from the basket", True),
    "cart_delete_basket": ("Empty the basket before refilling it", True),
    "cart_grocery_checkout": ("Place the order", True),
    "get_activities": ("Find the customer's ongoing orders", False),
    "track_activity": ("Live delivery status and ETA", False),
}

_events: deque[dict[str, Any]] = deque(maxlen=300)
_seq = itertools.count(1)
_lock = threading.Lock()


def _summary(tool: str, out: dict[str, Any]) -> str:
    """One short line on what came back."""
    if out.get("error"):
        return str(out["error"])[:120]
    try:
        if tool == "user_info":
            u = out.get("user_info") or {}
            return f"{u.get('name', 'customer')}, {len(out.get('saved_bookmarks') or [])} saved addresses"
        if tool == "is_grocery_area_serviceable":
            return "Delivers here" if out.get("serviceable") else "Outside the Quik area"
        if tool == "search_groceries_get_top_user_items":
            return f"{len((out.get('data') or {}).get('items') or [])} usual items"
        if tool == "search_groceries_get_all_deals":
            return f"{sum(len(g.get('items') or []) for g in out.get('groups') or [])} deals"
        if tool == "groceries_get_items_details":
            return f"{len(out.get('items') or [])} products"
        if tool == "search_groceries_items":
            groups = out.get("groups") or []
            return f"{len(groups)} terms matched, {sum(len(g.get('items') or []) for g in groups)} products"
        if tool == "create_grocery_cart_with_quantities":
            cb = (out.get("data") or {}).get("current_basket") or {}
            return f"Basket now has {len(cb.get('items') or [])} lines"
        if tool == "cart_get_quik_basket" and not (out.get("basket") or {}).get("items"):
            return "No basket yet"
        if tool in ("cart_get_basket_price", "cart_get_quik_basket", "cart_update_item", "cart_delete_items"):
            total = ((out.get("price") or {}).get("price") or {}).get("total")
            lines = len((out.get("basket") or {}).get("items") or [])
            return f"{lines} lines" + (f", total AED {total:.2f}" if total is not None else "")
        if tool == "cart_delete_basket":
            return "Basket emptied"
        if tool == "cart_grocery_checkout":
            inv = (out.get("checkout") or {}).get("masterInvoiceReference")
            return f"Order {inv} placed" if inv else "Order placed"
        if tool == "get_activities":
            return f"{len(out.get('ongoing_activities') or [])} ongoing activities"
        if tool == "track_activity":
            return f"{out.get('title') or out.get('status')}, {out.get('current_eta_minutes')} min away"
    except Exception:  # a summary must never break a call
        pass
    return "OK"


def record(tool: str, args: dict[str, Any], out: dict[str, Any] | None, error: str | None, ms: float) -> None:
    what, mutating = TOOLS.get(tool, ("", False))
    if out and tool == "cart_get_quik_basket" and "does not exist" in str(out.get("error", "")):
        out = {"basket": {}}  # an empty cart is a normal answer, not a failure
    event = {
        "seq": next(_seq), "at": time.time(), "stage": stage.get(), "tool": tool, "what": what,
        "mutating": mutating, "ms": round(ms), "args": args,
        "ok": error is None and not (out or {}).get("error"),
        "result": error or _summary(tool, out or {}),
    }
    with _lock:
        _events.append(event)


def since(after: int) -> list[dict[str, Any]]:
    with _lock:
        return [e for e in _events if e["seq"] > after]
