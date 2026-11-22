"""Live catalog + editable cart (docs/superpowers/specs/2026-11-22-live-catalog-cart-design.md)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from careem_mcp import live

PROJECT = Path(__file__).resolve().parent.parent
CATALOG = PROJECT / "catalog" / "quik.json"


@pytest.fixture(scope="module")
def catalog():
    return live.load_catalog(CATALOG)


# ---------------------------------------------------------------- Task 1: catalog + search


def test_catalog_size_and_fixture_ids(catalog):
    assert 60 <= len(catalog) <= 80
    milk = catalog[4000101]
    assert milk.name == "Fresh Farm Full Cream Milk 1L" and milk.price == 6.75
    assert catalog[4000106].available is False
    coffee = catalog[4000108]
    assert coffee.price == 32.0 and coffee.original == 40.0
    assert coffee.discount == 8.0 and coffee.discount_pct == 20
    assert sum(1 for p in catalog.values() if p.original) == 6


def test_search_plural_and_keywords(catalog):
    assert live.search(catalog, "tomatoes") and live.search(catalog, "tomato")
    assert live.search(catalog, "tomatoes")[0].id == 4000126
    assert live.search(catalog, "chicken breast")[0].id == 4000143
    assert live.search(catalog, "boneless skinless chicken breast")[0].id == 4000143
    assert live.search(catalog, "milk")[0].id in (4000101, 4000110)
    assert live.search(catalog, "unicorn") == []
    assert live.search(catalog, "  ") == []


def test_search_filters(catalog):
    deals = live.search(catalog, "pasta", on_discount=True)
    assert [p.id for p in deals] == [4000156]
    assert all(p.recommended for p in live.search(catalog, "rice", recommended=True))
    usual = live.search(catalog, "milk", previously_ordered=True, usual_ids={4000101})
    assert [p.id for p in usual] == [4000101]


# ---------------------------------------------------------------- Task 2: basket + pricing


def test_seed_total_45_50(tmp_path, catalog):
    b = live.Basket(tmp_path / "cart.json")
    assert [(l["catalog_item_id"], l["count"]) for l in b.lines] == [("4000101", 2), ("4000102", 1), ("4000103", 1)]
    p = live.price(b, catalog)
    assert (p["subtotal"], p["delivery"], p["service"], p["total"], p["saving"]) == (40.0, 4.0, 1.5, 45.5, 0.0)


def test_add_merges_and_prices(tmp_path, catalog):
    b = live.Basket(tmp_path / "cart.json")
    u1 = b.add(catalog[4000108], 1)
    u2 = b.add(catalog[4000108], 1)
    assert u1 == u2 and b.line(u1)["count"] == 2
    b.set_count(u1, 1)
    p = live.price(b, catalog)
    assert (p["subtotal"], p["original"], p["saving"], p["total"]) == (72.0, 80.0, 8.0, 77.5)
    assert json.loads((tmp_path / "cart.json").read_text())["lines"][-1]["count"] == 1


def test_set_count_zero_removes_and_remove_many(tmp_path, catalog):
    b = live.Basket(tmp_path / "cart.json")
    first, second = b.lines[0]["item_uuid"], b.lines[1]["item_uuid"]
    assert b.set_count(first, 0) is True and b.line(first) is None
    assert b.set_count("nope", 3) is False
    assert b.remove([second, "missing-uuid"]) == ["missing-uuid"]
    assert len(b.lines) == 1


def test_add_ignores_non_positive(tmp_path, catalog):
    b = live.Basket(tmp_path / "cart.json")
    assert b.add(catalog[4000126], 0) is None
    assert len(b.lines) == 3


def test_corrupt_state_falls_back(tmp_path, catalog):
    path = tmp_path / "cart.json"
    path.write_text("{not json")
    assert live.price(live.Basket(path), catalog)["total"] == 45.5


def test_clear_and_reset(tmp_path, catalog):
    b = live.Basket(tmp_path / "cart.json")
    b.clear()
    assert b.lines == [] and live.price(b, catalog)["total"] == 0.0
    b.reset()
    assert live.price(b, catalog)["total"] == 45.5


# ---------------------------------------------------------------- Task 3: live tools over MCP

import socket
import subprocess
import sys
import time

import httpx
from jsonschema import Draft202012Validator

from careem_mcp import spec
from test_acceptance import RawClient

HOME = {"latitude": 25.0866, "longitude": 55.1474}
Q = {"merchant_id": 40001, **HOME}
SCHEMAS = {name: tf.definition.get("outputSchema") for name, tf in spec.load_all(PROJECT / "spec").items()}


@pytest.fixture()
def live_client(tmp_path):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "-m", "careem_mcp.server", "--port", str(port), "--live-cart",
         "--overrides", str(tmp_path / "overrides.json"), "--cart-state", str(tmp_path / "cart.json")],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        if proc.poll() is not None:
            pytest.fail(f"server exited with code {proc.returncode}")
        try:
            if httpx.get(base + "/health", timeout=0.5).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("server did not become healthy")
    c = RawClient(base + "/mcp")
    c.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    c.notify("notifications/initialized")

    def call(tool, args):
        r = c.call(tool, args)
        assert r["isError"] is False, r
        sc = r["structuredContent"]
        errors = [e.message for e in Draft202012Validator(SCHEMAS[tool]).iter_errors(sc)]
        assert errors == [], (tool, errors[:3])
        return sc

    yield call
    proc.kill()
    proc.wait()


def total(call):
    return call("cart_get_basket_price", Q)["price"]["price"]["total"]


def test_live_search(live_client):
    r = live_client("search_groceries_items", {"search_terms": ["chicken breast", "tomatoes", "unicorn"], **HOME})
    assert [g["name"] for g in r["groups"]] == ["chicken breast", "tomatoes"]
    assert r["groups"][0]["items"][0]["id"] == 4000143
    assert r["groups"][0]["items"][0]["price"]["total"] == 32.0
    deals = live_client("search_groceries_items", {"search_terms": ["pasta"], "on_discount": True, **HOME})
    assert [i["id"] for i in deals["groups"][0]["items"]] == [4000156]


def test_live_details_allergens(live_client):
    r = live_client("groceries_get_items_details", {**Q, "item_ids": [4000170, 4000199]})
    soy = r["items"][0]["data"]
    assert {a["key"]: a["value_localized"] for a in soy["attributes"]}["allergens"] == "Soy, Gluten"
    assert soy["additional_attributes"][0]["items"][1]["primary_text_localized"] == "8 g"
    assert r["items"][1] == {"item_id": 4000199, "error": "item not found at this merchant"}


def test_live_deals(live_client):
    r = live_client("search_groceries_get_all_deals", HOME)
    assert sum(len(g["items"]) for g in r["groups"]) == 6


def test_live_cart_flow(live_client):
    assert total(live_client) == 45.5
    live_client("cart_delete_basket", Q)
    r = live_client("create_grocery_cart_with_quantities", {**Q, "items": [
        {"keyword": "chicken", "catalog_item_id": "4000143", "quantity": 2},
        {"keyword": "rice", "catalog_item_id": "4000152", "quantity": 1},
        {"keyword": "spinach", "catalog_item_id": "4000133", "quantity": 1},
    ]})
    assert r["data"]["current_basket"]["price"]["net_total"] == 91.5  # 64 + 19.5 + 8
    assert "failed_items" not in r["data"]
    price = live_client("cart_get_basket_price", Q)
    assert price["price"]["price"]["total"] == 97.0 and price["price"]["total_saving"] == 14.0
    rice = next(l for l in price["basket"]["items"] if l["catalog_item_id"] == "4000152")
    live_client("cart_update_item", {**Q, "item_uuid": rice["item_uuid"], "catalog_item_id": "4000152", "count": 2})
    assert total(live_client) == 116.5
    spinach = next(l for l in price["basket"]["items"] if l["catalog_item_id"] == "4000133")
    r = live_client("cart_delete_items", {**Q, "item_uuids": f" {spinach['item_uuid']} "})
    assert r["success"] is True and total(live_client) == 108.5
    r = live_client("cart_add_items", {**Q, "items": [{"catalog_item_id": "4000160", "count": 1}, {"catalog_item_id": "4000148", "count": 1}]})
    assert [x["success"] for x in r["results"]] == [True, False]
    assert total(live_client) == 134.5


def test_live_out_of_stock_unknown_and_zero(live_client):
    live_client("cart_delete_basket", Q)
    r = live_client("create_grocery_cart_with_quantities", {**Q, "items": [
        {"keyword": "avocado", "catalog_item_id": "4000106", "quantity": 1},
        {"keyword": "oat milk", "catalog_item_id": "4000199", "quantity": 1},
        {"keyword": "eggs", "catalog_item_id": "4000102", "quantity": 0},
        {"keyword": "bulk eggs", "catalog_item_id": "4000102", "quantity": 40},
    ]})
    codes = [(f["keyword"], f["error_code"]) for f in r["data"]["failed_items"]]
    assert codes == [("avocado", "INSUFFICIENT_STOCK"), ("oat milk", "NOT_FOUND"), ("bulk eggs", "INSUFFICIENT_STOCK")]
    assert r["data"]["failed_items"][2]["added_quantity"] == 30
    assert [(i["catalog_item_id"], i["count"]) for i in r["data"]["current_basket"]["items"]] == [("4000102", 30)]


def test_checkout_rejects_stale_total_then_succeeds(live_client):
    t = total(live_client)
    stale = live_client("cart_grocery_checkout", {**HOME, "basket_id": 6000002, "total_price": t + 5, "payment_type": "wallet"})
    assert "409" in stale["error"]
    ok = live_client("cart_grocery_checkout", {**HOME, "basket_id": 6000002, "total_price": t - 0.000001, "payment_type": "card"})
    assert ok["amount"] == 45.5 and "error" not in ok
    empty = live_client("cart_get_quik_basket", HOME)
    assert empty["basket"] is None and "error" in empty


def test_live_errors_still_canned(live_client):
    r = live_client("search_groceries_items", {"search_terms": ["milk"], "latitude": 0, "longitude": 55.1})
    assert "error" in r
    r = live_client("cart_get_basket_price", {"merchant_id": 30104, **HOME})
    assert r["merchant"]["id"] == 30104  # food basket stays canned
