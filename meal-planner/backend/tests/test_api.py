"""Backend tests against a real careem-mcp server in live mode (started per test module)."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
MCP_DIR = ROOT / "careem-mcp-python"
MCP_PY = MCP_DIR / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
GYM = (25.0702, 55.143)
LONDON = (51.5074, -0.1278)
ALL_KITCHEN = ["oven", "stovetop", "air_fryer", "microwave", "toaster", "blender", "slow_cooker"]


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


def plan(client, **answers):
    r = client.post("/api/plan", json=answers)
    assert r.status_code == 200, r.text
    return r.json()


def lines_for(p):
    return [{"catalog_item_id": str(n["product"]["id"]), "keyword": n["term"], "quantity": n["packs"]} for n in p["need"]]


def test_bootstrap(client):
    b = client.get("/api/bootstrap").json()
    assert b["user"]["name"] == "Leonardo" and b["serviceable"] is True
    assert [a["title"] for a in b["addresses"]][:3] == ["Home", "Work", "Gym"]
    assert len(b["deals"]) == 6 and len(b["products"]) > 50 and b["usuals"]
    assert set(b["appliances"]) == set(ALL_KITCHEN)


def test_outside_service_area(client):
    b = client.get("/api/bootstrap", params={"lat": LONDON[0], "lng": LONDON[1]}).json()
    assert b["serviceable"] is False and b["products"] == []


def test_portions_scale_quantities(client):
    one = plan(client, adults=1, kids=0, days=[0, 1], budget=5000)
    family = plan(client, adults=1, kids=2, days=[0, 1], budget=5000)
    assert one["portions"] == 1 and family["portions"] == 2
    assert [r["id"] for r in one["recipes"]] == [r["id"] for r in family["recipes"]]
    a1 = {n["product"]["id"]: n["amount"] for n in one["need"]}
    a2 = {n["product"]["id"]: n["amount"] for n in family["need"]}
    assert all(a2[k] == pytest.approx(2 * a1[k]) for k in a1)
    for r in family["recipes"]:
        assert r["servings"] == 2 * sum(1 for s in family["schedule"] if s["recipe"] == r["id"])


def test_meals_and_days(client):
    p = plan(client, meals=["breakfast", "dinner", "snacks"], days=[0, 2, 4], appliances=ALL_KITCHEN, budget=5000)
    assert [d["name"] for d in p["days"]] == ["Monday", "Wednesday", "Friday"]
    assert len(p["schedule"]) == 9
    slot_of = {r["id"]: r["slot"] for r in p["recipes"]}
    for s in p["schedule"]:
        assert slot_of[s["recipe"]] == {"breakfast": "breakfast", "dinner": "main", "snacks": "snack"}[s["meal"]]


def test_batch_cook_halves_the_recipes(client):
    plain = plan(client, days=[0, 1, 2, 3])
    batch = plan(client, days=[0, 1, 2, 3], vibes=["batch"])
    assert len(plain["recipes"]) == 4 and len(batch["recipes"]) == 2
    assert sum(s["leftovers"] for s in batch["schedule"]) == 2


def test_appliances_are_strict(client):
    p = plan(client, appliances=["microwave"], meals=["breakfast", "dinner"], days=[0, 1])
    assert p["recipes"] and all(set(r["appliances"]) <= {"microwave"} for r in p["recipes"])
    slow = plan(client, appliances=["slow_cooker"], days=[0])
    assert slow["recipes"][0]["appliances"] == ["slow_cooker"]


def test_strict_diets(client):
    vegan = plan(client, diets=["vegan"], appliances=ALL_KITCHEN, meals=["breakfast", "dinner", "snacks"], days=[0, 1, 2])
    assert vegan["recipes"] and all("vegan" in n["product"]["diet"] for n in vegan["need"] + vegan["have"])
    pesc = plan(client, diets=["pescatarian"], appliances=ALL_KITCHEN, days=[0, 1, 2, 3, 4, 5, 6])
    assert not {4000143, 4000144, 4000146, 4000147} & {n["product"]["id"] for n in pesc["need"]}
    keto = plan(client, diets=["keto"], appliances=ALL_KITCHEN, days=[0, 1])
    assert all(r["per_serving"]["carbs"] <= 20 for r in keto["recipes"])


def test_allergies_and_dislikes(client):
    p = plan(client, allergens=["gluten", "dairy", "peanuts"], dislikes=["Chicken", "Mushroom", "Bell peppers"],
             appliances=ALL_KITCHEN, meals=["breakfast", "lunch", "dinner", "snacks"], days=[0, 1, 2])
    assert p["recipes"]
    for n in p["need"] + p["have"]:
        assert not {"gluten", "dairy", "peanuts"} & set(n["product"]["allergens"])
        name = n["product"]["name"].lower().replace("black pepper", "")
        assert "chicken" not in name and "mushroom" not in name and "pepper" not in name
    for n in p["need"]:
        if n["match"]["status"] == "alternative":
            assert not {"gluten", "dairy", "peanuts"} & set(n["match"]["suggested"]["allergens"])


def test_pantry_split_and_live_match(client):
    p = plan(client, pantry=[4000160, 4000130], days=[0, 1, 2, 3, 4], adults=2, budget=400)
    have_ids = {h["product"]["id"] for h in p["have"]}
    need_ids = {n["product"]["id"] for n in p["need"]}
    assert have_ids <= {4000160, 4000130} and not have_ids & need_ids
    assert sum(1 for n in p["need"] if n["match"]["status"] == "matched") >= len(p["need"]) - 1
    assert p["estimate"] == round(sum(n["line_total"] for n in p["need"]), 2)


def test_recipes_carry_steps_and_ingredients(client):
    for r in plan(client, days=[0, 1])["recipes"]:
        assert r["steps"] and all(s["text"] for s in r["steps"])
        assert all(i["amount"] > 0 and i["unit"] in ("g", "ml", "pcs") for i in r["ingredients"])


def test_out_of_stock_ingredient_is_swapped_and_matched(client):
    p = plan(client, keep=["salmon-traybake"], days=[0, 1])
    salmon = next(r for r in p["recipes"] if r["id"] == "salmon-traybake")
    assert salmon["swaps"] and salmon["swaps"][0]["to"].startswith("Chicken")
    chicken = next(n for n in p["need"] if n["product"]["id"] == 4000143)
    assert chicken["match"]["status"] == "matched"


def test_estimate_and_tight_budget(client):
    body = {"days": [0, 1, 2, 3, 4, 5, 6], "adults": 4, "meals": ["lunch", "dinner"], "appliances": ALL_KITCHEN}
    est = client.post("/api/estimate", json=body).json()["estimate"]
    assert est > 0
    tight = plan(client, **body, budget=round(est * 0.6), prioritize_deals=True)
    assert tight["estimate"] < est


def test_bad_answers_are_rejected(client):
    assert client.post("/api/plan", json={"adults": 0, "kids": 0}).status_code == 400
    assert client.post("/api/plan", json={"days": []}).status_code == 400


def test_cart_price_edit_and_guarded_checkout(client):
    p = plan(client, days=[0, 1])
    lines = lines_for(p)
    cart = client.post("/api/cart", json={"mode": "replace", "lines": lines}).json()
    assert cart["basket"]["count"] == sum(l["quantity"] for l in lines)
    assert cart["total"] == pytest.approx(p["estimate"] + 5.5)
    line = cart["basket"]["lines"][0]
    cart2 = client.patch("/api/cart/line", json={"item_uuid": line["item_uuid"], "catalog_item_id": line["catalog_item_id"],
                                                 "count": line["count"] + 1}).json()
    assert cart2["total"] > cart["total"]
    assert client.post("/api/checkout", json={"total_price": cart2["total"], "payment_type": "wallet"}).status_code == 400
    assert client.get("/api/cart").json()["basket"] is not None
    r = client.post("/api/checkout", json={"total_price": cart2["total"] + 3, "payment_type": "wallet", "confirmed": True}).json()
    assert "409" in r["error"]
    r = client.post("/api/checkout", json={"lat": GYM[0], "lng": GYM[1], "total_price": cart2["total"],
                                           "payment_type": "wallet", "confirmed": True}).json()
    assert r.get("error") and r["message"].startswith("Careem Quik doesn't deliver")
    ok = client.post("/api/checkout", json={"total_price": cart2["total"], "payment_type": "wallet", "confirmed": True}).json()
    assert "error" not in ok and ok["checkout"]["masterInvoiceReference"]
    assert client.get("/api/cart").json()["basket"] is None
    t = client.get("/api/track").json()
    assert t["activity_type"] == "groceries" and t["current_eta_minutes"] > 0


def test_payment_declined_renders_as_error(client):
    cart = client.post("/api/cart", json={"mode": "replace", "lines": lines_for(plan(client, days=[0]))}).json()
    r = client.post("/api/checkout", json={"total_price": cart["total"], "payment_type": "card", "payment_id": 4000002,
                                           "confirmed": True}).json()
    assert "402" in r["error"] and r["message"].startswith("Your card was declined")
    assert client.get("/api/cart").json()["basket"] is not None


def test_cart_requires_lines(client):
    assert client.post("/api/cart", json={"lines": []}).status_code == 400


# ---------------------------------------------------------------- Claude (stubbed: no network in tests)


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


def answer(summary, breakfasts, mains, snacks=()):
    from app import ai

    def pick(ids):
        return [ai.Pick(recipe_id=i, reason=f"because {i}") for i in ids]

    result = ai.AIPlan(summary=summary, breakfasts=pick(breakfasts), mains=pick(mains), snacks=pick(snacks))
    return lambda _: SimpleNamespace(stop_reason="end_turn", parsed_output=result)


def test_claude_picks_are_used_with_reasons(client, monkeypatch):
    parse = fake_client(monkeypatch, answer("A spicy, cheap week.", [], ["lentil-dal", "chickpea-curry", "bolognese"]))
    p = plan(client, days=[0, 1, 2], notes="we love spicy food", adults=1, kids=2)
    assert p["ai"] == {"used": True, "summary": "A spicy, cheap week."}
    assert [r["id"] for r in p["recipes"]] == ["lentil-dal", "chickpea-curry", "bolognese"]
    assert p["recipes"][0]["why"] == "because lentil-dal"
    sent = parse.calls[0]
    assert sent["model"] == "claude-opus-5-5" and sent["fallbacks"] == "default"
    assert sent["output_config"] == {"effort": "low"}
    req = json.loads(sent["messages"][0]["content"])
    assert req["their_notes"] == "we love spicy food" and req["choose"] == {"breakfasts": 0, "mains": 3, "snacks": 0}
    assert req["household"]["portions_per_meal"] == 2 and req["days"] == ["Monday", "Tuesday", "Wednesday"]


def test_claude_only_sees_safe_candidates(client, monkeypatch):
    parse = fake_client(monkeypatch, answer("ok", ["pb-smoothie"], ["shrimp-noodles"], ["apple-pb"]))
    p = plan(client, allergens=["peanuts", "shellfish"], appliances=ALL_KITCHEN, meals=["breakfast", "dinner", "snacks"], days=[0, 1])
    sent_ids = {c["id"] for c in json.loads(parse.calls[0]["messages"][0]["content"])["candidates"]}
    assert not {"pb-smoothie", "shrimp-noodles", "apple-pb", "pb-banana-toast"} & sent_ids
    assert not {"pb-smoothie", "shrimp-noodles", "apple-pb"} & {r["id"] for r in p["recipes"]}


def test_invalid_claude_answer_falls_back_to_rules(client, monkeypatch):
    fake_client(monkeypatch, answer("nonsense", ["not-a-recipe"], ["also-not-one"]))
    p = plan(client, days=[0, 1, 2])
    assert p["ai"]["used"] is False and p["recipes"]


def test_refusal_falls_back_to_rules(client, monkeypatch):
    fake_client(monkeypatch, lambda _: SimpleNamespace(stop_reason="refusal", parsed_output=None))
    assert plan(client, days=[0, 1])["ai"]["used"] is False


def test_claude_errors_fall_back_to_rules(client, monkeypatch):
    import anthropic

    def boom(kwargs):
        raise anthropic.APIConnectionError(message="offline", request=None)

    fake_client(monkeypatch, boom)
    assert plan(client, days=[0, 1])["ai"]["used"] is False


def test_no_credentials_means_no_claude_call(client, monkeypatch):
    for v in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(v, raising=False)
    from app import ai
    monkeypatch.setattr(ai, "client", lambda: pytest.fail("must not call Claude without credentials"))
    assert plan(client, days=[0])["ai"]["used"] is False
    assert client.get("/api/bootstrap").json()["ai_available"] is False


def test_swap_and_estimate_do_not_call_claude(client, monkeypatch):
    parse = fake_client(monkeypatch, answer("x", [], ["lentil-dal"]))
    plan(client, days=[0, 1], keep=["lentil-dal"], exclude=["bolognese"])
    client.post("/api/estimate", json={"days": [0, 1]})
    assert parse.calls == []
