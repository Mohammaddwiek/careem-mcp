"""Backend tests against a real careem-mcp server in live mode (started per test module)."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
MCP_DIR = ROOT / "careem-mcp-python"
MCP_PY = MCP_DIR / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
GYM = (25.0702, 55.143)
LONDON = (51.5074, -0.1278)


def _port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    run = tmp_path_factory.mktemp("mcp")
    overrides = run / "overrides.json"
    overrides.write_text("{}")
    port = _port()
    proc = subprocess.Popen(
        [str(MCP_PY), "-m", "careem_mcp.server", "--port", str(port), "--live-cart",
         "--overrides", str(overrides), "--cart-state", str(run / "cart.json")],
        cwd=MCP_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(100):
        if proc.poll() is not None:
            pytest.fail("careem-mcp exited")
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    os.environ["CAREEM_MCP_URL"] = f"http://127.0.0.1:{port}/mcp"
    from fastapi.testclient import TestClient

    from app import main

    main.mcp = main.MCPClient(os.environ["CAREEM_MCP_URL"])
    main._facts.update(at=0.0, data={})
    with TestClient(main.app) as c:
        c.overrides = overrides
        yield c
    proc.kill()
    proc.wait()


def plan(client, **prefs):
    r = client.post("/api/plan", json=prefs)
    assert r.status_code == 200, r.text
    return r.json()


def test_bootstrap(client):
    b = client.get("/api/bootstrap").json()
    assert b["user"]["name"] == "Leonardo" and b["serviceable"] is True
    assert [a["title"] for a in b["addresses"]][:3] == ["Home", "Work", "Gym"]
    assert len(b["deals"]) == 6 and len(b["products"]) > 50 and b["usuals"]


def test_outside_service_area(client):
    b = client.get("/api/bootstrap", params={"lat": LONDON[0], "lng": LONDON[1]}).json()
    assert b["serviceable"] is False and b["products"] == []


def test_plan_respects_allergies_diet_and_appliances(client):
    p = plan(client, allergens=["gluten", "dairy"], diet="vegan", appliances=["stove"], days=3, people=1)
    assert p["recipes"], p
    for r in p["recipes"]:
        assert set(r["appliances"]) <= {"stove"}
    for n in p["need"] + p["have"]:
        assert not {"gluten", "dairy"} & set(n["product"]["allergens"])
        assert "vegan" in n["product"]["diet"]


def test_plan_pantry_split_and_live_match(client):
    p = plan(client, pantry=[4000160, 4000130], days=5, people=2, budget=400)
    have_ids = {h["product"]["id"] for h in p["have"]}
    need_ids = {n["product"]["id"] for n in p["need"]}
    assert have_ids <= {4000160, 4000130} and not have_ids & need_ids
    assert all(n["match"]["status"] in ("matched", "alternative", "not_found") for n in p["need"])
    assert sum(1 for n in p["need"] if n["match"]["status"] == "matched") >= len(p["need"]) - 1
    assert p["estimate"] == round(sum(n["line_total"] for n in p["need"]), 2)
    assert len(p["schedule"]) == 5


def test_out_of_stock_ingredient_is_swapped(client):
    p = plan(client, keep=["salmon-traybake"], appliances=["stove", "oven"], days=2)
    salmon = next(r for r in p["recipes"] if r["id"] == "salmon-traybake")
    assert salmon["swaps"] and salmon["swaps"][0]["to"].startswith("Chicken")


def test_budget_tries_cheaper_recipes(client):
    rich = plan(client, days=7, people=4, budget=5000, goal="protein")
    tight = plan(client, days=7, people=4, budget=rich["estimate"] * 0.6, goal="protein")
    assert tight["estimate"] < rich["estimate"]


def test_cart_price_edit_and_guarded_checkout(client):
    p = plan(client, days=2, people=1)
    lines = [{"catalog_item_id": str(n["product"]["id"]), "keyword": n["term"], "quantity": n["packs"]} for n in p["need"]]
    cart = client.post("/api/cart", json={"mode": "replace", "lines": lines}).json()
    assert cart["basket"]["count"] == sum(l["quantity"] for l in lines)
    assert cart["total"] == pytest.approx(p["estimate"] + 5.5)

    line = cart["basket"]["lines"][0]
    cart2 = client.patch("/api/cart/line", json={"item_uuid": line["item_uuid"], "catalog_item_id": line["catalog_item_id"],
                                                 "count": line["count"] + 1}).json()
    assert cart2["total"] > cart["total"]

    # no confirmation → refused, nothing placed
    r = client.post("/api/checkout", json={"total_price": cart2["total"], "payment_type": "wallet"})
    assert r.status_code == 400
    assert client.get("/api/cart").json()["basket"] is not None

    # stale total → business error from Careem, basket still there
    r = client.post("/api/checkout", json={"total_price": cart2["total"] + 3, "payment_type": "wallet", "confirmed": True}).json()
    assert "409" in r["error"]

    # outside the delivery area (Gym) → error, basket still there
    r = client.post("/api/checkout", json={"lat": GYM[0], "lng": GYM[1], "total_price": cart2["total"],
                                           "payment_type": "wallet", "confirmed": True}).json()
    assert r.get("error")

    ok = client.post("/api/checkout", json={"total_price": cart2["total"], "payment_type": "wallet", "confirmed": True}).json()
    assert "error" not in ok and ok["checkout"]["masterInvoiceReference"]
    assert client.get("/api/cart").json()["basket"] is None
    t = client.get("/api/track").json()
    assert t["activity_type"] == "groceries" and t["current_eta_minutes"] > 0


def test_payment_declined_renders_as_error(client):
    p = plan(client, days=1, people=1)
    lines = [{"catalog_item_id": str(n["product"]["id"]), "keyword": n["term"], "quantity": n["packs"]} for n in p["need"]]
    cart = client.post("/api/cart", json={"mode": "replace", "lines": lines}).json()
    r = client.post("/api/checkout", json={"total_price": cart["total"], "payment_type": "card", "payment_id": 4000002,
                                           "confirmed": True}).json()
    assert "402" in r["error"] and r["message"].startswith("Your card was declined")
    assert client.get("/api/cart").json()["basket"] is not None


def test_cart_requires_lines(client):
    assert client.post("/api/cart", json={"lines": []}).status_code == 400


def test_swapped_ingredient_is_searched_by_its_replacement(client):
    p = plan(client, keep=["salmon-traybake"], appliances=["stove", "oven"], days=2, people=1)
    chicken = next(n for n in p["need"] if n["product"]["id"] == 4000143)
    assert chicken["match"]["status"] == "matched", chicken
