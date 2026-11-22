"""Meal planning: pick recipes for the user's constraints, then split ingredients into have/need."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .products import Product
from .recipes import RECIPES, Recipe

GOALS = ("balanced", "save", "protein", "quick")
SLOT_PLANS = {"dinner": ("dinner",), "lunch_dinner": ("lunch", "dinner"), "all": ("breakfast", "lunch", "dinner")}


@dataclass
class Prefs:
    pantry: set[int] = field(default_factory=set)
    appliances: set[str] = field(default_factory=lambda: {"stove"})
    allergens: set[str] = field(default_factory=set)
    diet: str = "any"  # any, vegetarian, vegan, gluten_free
    people: int = 2
    days: int = 5
    meals: str = "dinner"  # dinner, lunch_dinner, all
    budget: float = 250.0
    goal: str = "balanced"
    batch_cook: bool = True  # cook once, eat twice
    keep: list[str] = field(default_factory=list)  # recipe ids to keep (when swapping one meal)
    exclude: list[str] = field(default_factory=list)


@dataclass
class Resolved:
    recipe: Recipe
    lines: list[tuple[Any, Product]]  # (Ingredient, chosen product)
    swaps: list[dict[str, Any]]
    cost: float  # per serving, proportional
    kcal: float
    protein: float
    carbs: float
    fat: float
    deals: list[str]
    pantry_hits: int


def resolve(recipe: Recipe, facts: dict[int, Product], prefs: Prefs) -> tuple[Resolved | None, str | None]:
    """Choose a product per ingredient (falling back to its alternative when out of stock) and check
    the user's constraints. Returns (resolved, None) or (None, reason)."""
    if not set(recipe.appliances) <= prefs.appliances:
        return None, "needs " + ", ".join(sorted(set(recipe.appliances) - prefs.appliances))
    lines, swaps = [], []
    for ing in recipe.ingredients:
        p = facts.get(ing.product_id)
        if p is None or not p.available:
            alt = facts.get(ing.alt) if ing.alt else None
            if alt is None or not alt.available:
                return None, f"{ing.name} is out of stock"
            swaps.append({"ingredient": ing.name, "from": p.name if p else ing.name, "to": alt.name,
                          "reason": f"{p.name if p else ing.name} is out of stock on Careem Quik"})
            p = alt
        lines.append((ing, p))
    blocked = set(prefs.allergens) | ({"gluten"} if prefs.diet == "gluten_free" else set())
    for ing, p in lines:
        if p.allergens & blocked:
            return None, f"{p.name} contains {', '.join(sorted(p.allergens & blocked))}"
        if prefs.diet in ("vegan", "vegetarian") and prefs.diet not in p.diet:
            return None, f"{p.name} is not {prefs.diet}"
    cost = sum(ing.amount / p.pack_amount * p.price for ing, p in lines)
    nut = {k: sum(p.grams(ing.amount) * p.nutrition.get(k, 0) / 100 for ing, p in lines) for k in ("kcal", "protein", "carbs", "fat")}
    return Resolved(
        recipe=recipe, lines=lines, swaps=swaps, cost=cost, deals=sorted({p.name for _, p in lines if p.original}),
        pantry_hits=sum(1 for _, p in lines if p.id in prefs.pantry), **nut,
    ), None


def score(r: Resolved, goal: str) -> float:
    base = {
        "save": -1.0 * r.cost,
        "protein": 0.25 * r.protein - 0.05 * r.cost,
        "quick": -0.12 * r.recipe.minutes - 0.05 * r.cost,
        "balanced": 0.06 * r.protein - 0.3 * r.cost - 0.02 * r.recipe.minutes,
    }[goal if goal in GOALS else "balanced"]
    return base + 1.2 * len(r.deals) + 0.8 * r.pantry_hits


def shopping_list(picks: list[tuple[Resolved, int]], pantry: set[int]) -> tuple[list[dict], list[dict]]:
    """Aggregate ingredients over picks (recipe, servings) into whole packs. Returns (have, need)."""
    totals: dict[int, dict[str, Any]] = {}
    for r, servings in picks:
        for ing, p in r.lines:
            # a swapped-in product is searched by its own name, not the out-of-stock ingredient's term
            term = ing.term if p.id == ing.product_id else p.name
            t = totals.setdefault(p.id, {"product": p, "amount": 0.0, "for": [], "term": term})
            if p.id == ing.product_id:
                t["term"] = ing.term  # prefer a recipe's own term when one exists
            t["amount"] += ing.amount * servings
            if r.recipe.name not in t["for"]:
                t["for"].append(r.recipe.name)
    have, need = [], []
    for pid, t in sorted(totals.items(), key=lambda kv: (kv[1]["product"].category, kv[1]["product"].name)):
        p: Product = t["product"]
        row = {"product": p.to_json(), "term": t["term"], "amount": round(t["amount"], 1),
               "amount_unit": p.pack_unit, "for": t["for"]}
        if pid in pantry:
            have.append(row)
        else:
            packs = max(1, math.ceil(t["amount"] / p.pack_amount - 1e-9))
            need.append({**row, "packs": packs, "line_total": round(packs * p.price, 2),
                         "saving": round(packs * (p.original - p.price), 2) if p.original else 0.0})
    return have, need


def plan(facts: dict[int, Product], prefs: Prefs) -> dict[str, Any]:
    slots = SLOT_PLANS.get(prefs.meals, SLOT_PLANS["dinner"])
    resolved: dict[str, Resolved] = {}
    excluded: list[dict[str, str]] = []
    for recipe in RECIPES:
        if recipe.id in prefs.exclude:
            continue
        r, why = resolve(recipe, facts, prefs)
        if r:
            resolved[recipe.id] = r
        else:
            excluded.append({"recipe": recipe.name, "reason": why or ""})

    schedule: list[dict[str, Any]] = []
    servings: dict[str, int] = {}
    chosen: list[str] = []
    for slot in ("breakfast", "main"):
        wanted = [s for s in slots if (s == "breakfast") == (slot == "breakfast")]
        if not wanted:
            continue
        occurrences = prefs.days * len(wanted)
        unique = math.ceil(occurrences / 2) if prefs.batch_cook else occurrences
        pool = [r for r in resolved.values() if r.recipe.slot == slot]
        picks = [resolved[k] for k in prefs.keep if k in resolved and resolved[k].recipe.slot == slot]
        used_products = {p.id for r in picks for _, p in r.lines}
        while len(picks) < unique and pool:
            options = [r for r in pool if r not in picks] or pool
            best = max(options, key=lambda r: score(r, prefs.goal) + 0.5 * sum(1 for _, p in r.lines if p.id in used_products))
            picks.append(best)
            used_products |= {p.id for _, p in best.lines}
        if not picks:
            continue
        # spread occurrences over the days: each pick covers consecutive meals (cook once, eat twice)
        per = [occurrences // len(picks) + (1 if i < occurrences % len(picks) else 0) for i in range(len(picks))]
        order = [r for r, n in zip(picks, per) for _ in range(n)]
        for i, r in enumerate(order):
            day, slot_name = divmod(i, len(wanted))
            schedule.append({"day": day + 1, "slot": wanted[slot_name], "recipe": r.recipe.id})
            servings[r.recipe.id] = servings.get(r.recipe.id, 0) + prefs.people
            if r.recipe.id not in chosen:
                chosen.append(r.recipe.id)

    picks_with_servings = [(resolved[k], servings[k]) for k in chosen]
    have, need = shopping_list(picks_with_servings, prefs.pantry)
    estimate = round(sum(n["line_total"] for n in need), 2)

    # over budget: swap the priciest recipe for a cheaper unused one while that lowers the total
    for _ in range(6):
        if estimate <= prefs.budget:
            break
        improved = False
        for k in sorted(chosen, key=lambda k: -resolved[k].cost):
            if k in prefs.keep:
                continue
            slot = resolved[k].recipe.slot
            for alt in sorted((r for r in resolved.values() if r.recipe.slot == slot and r.recipe.id not in chosen), key=lambda r: r.cost):
                trial = [alt.recipe.id if c == k else c for c in chosen]
                trial_servings = {**{c: servings.get(c, 0) for c in chosen}, alt.recipe.id: servings[k]}
                _, trial_need = shopping_list([(resolved[c], trial_servings[c]) for c in trial], prefs.pantry)
                trial_est = round(sum(n["line_total"] for n in trial_need), 2)
                if trial_est < estimate:
                    chosen = trial
                    servings[alt.recipe.id] = servings.pop(k)
                    for s in schedule:
                        if s["recipe"] == k:
                            s["recipe"] = alt.recipe.id
                    estimate = trial_est
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break

    picks_with_servings = [(resolved[k], servings[k]) for k in chosen]
    have, need = shopping_list(picks_with_servings, prefs.pantry)
    estimate = round(sum(n["line_total"] for n in need), 2)
    return {
        "schedule": schedule,
        "recipes": [recipe_json(resolved[k], servings[k]) for k in chosen],
        "have": have,
        "need": need,
        "estimate": estimate,
        "saving": round(sum(n["saving"] for n in need), 2),
        "budget": prefs.budget,
        "over_budget": estimate > prefs.budget,
        "excluded": excluded,
    }


def recipe_json(r: Resolved, servings: int) -> dict[str, Any]:
    rec = r.recipe
    return {
        "id": rec.id, "name": rec.name, "slot": rec.slot, "minutes": rec.minutes, "cuisine": rec.cuisine,
        "blurb": rec.blurb, "appliances": list(rec.appliances), "servings": servings,
        "per_serving": {"kcal": round(r.kcal), "protein": round(r.protein, 1), "carbs": round(r.carbs, 1),
                        "fat": round(r.fat, 1), "cost": round(r.cost, 2)},
        "deals": r.deals, "swaps": r.swaps,
        "ingredients": [{"name": ing.name, "product_id": p.id, "product": p.name,
                         "amount": ing.amount, "unit": p.pack_unit} for ing, p in r.lines],
    }
