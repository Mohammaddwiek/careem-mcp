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
