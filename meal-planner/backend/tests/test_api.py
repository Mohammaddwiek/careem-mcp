"""Backend tests against a real careem-mcp server in live mode (started per test module)."""

from __future__ import annotations

import json
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


# ---------------------------------------------------------------- Claude (stubbed: no network in tests)

from types import SimpleNamespace


class FakeParse:
    """Stands in for client.beta.messages.parse: records the call, returns a canned response."""

    def __init__(self, respond):
        self.respond, self.calls = respond, []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.respond(kwargs)


def fake_client(monkeypatch, respond):
    from app import ai
    parse = FakeParse(respond)
    monkeypatch.setattr(ai, "client", lambda: SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse))))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    return parse


def answer(summary, breakfasts, mains):
    from app import ai
    plan = ai.AIPlan(summary=summary, breakfasts=[ai.Pick(recipe_id=i, reason=f"because {i}") for i in breakfasts],
                     mains=[ai.Pick(recipe_id=i, reason=f"because {i}") for i in mains])
    return lambda _: SimpleNamespace(stop_reason="end_turn", parsed_output=plan)


def test_claude_picks_are_used_with_reasons(client, monkeypatch):
    parse = fake_client(monkeypatch, answer("A spicy, cheap week.", [], ["lentil-dal", "chickpea-curry", "bolognese"]))
    p = plan(client, days=5, people=2, notes="we love spicy food")
    assert p["ai"] == {"used": True, "summary": "A spicy, cheap week."}
    assert [r["id"] for r in p["recipes"]] == ["lentil-dal", "chickpea-curry", "bolognese"]
    assert p["recipes"][0]["why"] == "because lentil-dal"
    sent = parse.calls[0]
    assert sent["model"] == "claude-opus-5-5" and sent["fallbacks"] == "default"
    assert sent["output_config"] == {"effort": "low"}
    req = json.loads(sent["messages"][0]["content"])
    assert req["their_notes"] == "we love spicy food" and req["choose"] == {"breakfasts": 0, "mains": 3}


def test_claude_only_sees_safe_candidates(client, monkeypatch):
    parse = fake_client(monkeypatch, answer("ok", ["pb-smoothie"], ["shrimp-noodles"]))
    p = plan(client, allergens=["peanuts", "shellfish"], appliances=["stove", "blender"], meals="all", days=2)
    sent_ids = {c["id"] for c in json.loads(parse.calls[0]["messages"][0]["content"])["candidates"]}
    assert "pb-smoothie" not in sent_ids and "shrimp-noodles" not in sent_ids
    # even if Claude names an unsafe recipe, it never reaches the plan
    assert not {"pb-smoothie", "shrimp-noodles"} & {r["id"] for r in p["recipes"]}


def test_invalid_claude_answer_falls_back_to_rules(client, monkeypatch):
    fake_client(monkeypatch, answer("nonsense", ["not-a-recipe"], ["also-not-one"]))
    p = plan(client, days=3)
    assert p["ai"]["used"] is False and p["recipes"]


def test_refusal_falls_back_to_rules(client, monkeypatch):
    fake_client(monkeypatch, lambda _: SimpleNamespace(stop_reason="refusal", parsed_output=None))
    p = plan(client, days=3)
    assert p["ai"]["used"] is False and p["recipes"]


def test_claude_errors_fall_back_to_rules(client, monkeypatch):
    import anthropic

    def boom(kwargs):
        raise anthropic.APIConnectionError(message="offline", request=None)

    fake_client(monkeypatch, boom)
    assert plan(client, days=3)["ai"]["used"] is False


def test_no_credentials_means_no_claude_call(client, monkeypatch):
    for v in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(v, raising=False)
    from app import ai
    monkeypatch.setattr(ai, "client", lambda: pytest.fail("must not call Claude without credentials"))
    assert plan(client, days=2)["ai"]["used"] is False
    assert client.get("/api/bootstrap").json()["ai_available"] is False


def test_swap_does_not_call_claude(client, monkeypatch):
    parse = fake_client(monkeypatch, answer("x", [], ["lentil-dal"]))
    plan(client, days=2, keep=["lentil-dal"], exclude=["bolognese"])
    assert parse.calls == []
