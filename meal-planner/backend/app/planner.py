"""Meal planning: pick recipes for the user's answers, then split ingredients into have/need.

Hard rules (never broken): kitchen appliances, allergies, the strict diets (vegetarian, vegan,
pescatarian, keto) and dislikes. Everything else (high-protein, GLP-1 friendly, anti-inflammatory,
Mediterranean, Mexican and the vibes) changes a recipe's score.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .products import Product
from .recipes import RECIPES, Recipe

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MEALS = ("breakfast", "lunch", "dinner", "snacks")
POOL_FOR_MEAL = {"breakfast": "breakfast", "lunch": "main", "dinner": "main", "snacks": "snack"}
STRICT_DIETS = {"vegetarian", "vegan", "pescatarian", "keto"}
KETO_CARBS_G = 20
SYNONYMS = {"cilantro": "coriander", "ground beef": "beef", "aubergine": "eggplant", "prawn": "shrimp",
            "bell peppers": "bell pepper", "courgette": "zucchini"}


@dataclass
class Prefs:
    adults: int = 1
    kids: int = 0
    meals: set[str] = field(default_factory=lambda: {"dinner"})
    days: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    appliances: set[str] = field(default_factory=lambda: {"stovetop", "oven"})
    diets: set[str] = field(default_factory=set)
    vibes: set[str] = field(default_factory=set)
    allergens: set[str] = field(default_factory=set)
    dislikes: list[str] = field(default_factory=list)
    pantry: set[int] = field(default_factory=set)
    budget: float = 250.0
    prioritize_deals: bool = False  # the budget looks tight: lean harder on deals and cheap recipes
    notes: str = ""  # free text for Claude, e.g. "we love spicy food"
    keep: list[str] = field(default_factory=list)  # recipe ids to keep (when swapping one meal)
    exclude: list[str] = field(default_factory=list)

    @property
    def portions(self) -> float:
        """Adults eat a full portion, kids half."""
        return self.adults + 0.5 * self.kids

    @property
    def batch_cook(self) -> bool:
        return "batch" in self.vibes


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


def _words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z]+", text.lower()):
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out


def disliked(prefs: Prefs, *names: str) -> str | None:
    """The dislike that matches any of these names, if any ("Bell peppers" matches "Bell pepper")."""
    have = set().union(*(_words(n) for n in names))
    for d in prefs.dislikes:
        key = SYNONYMS.get(d.lower().strip(), d.lower().strip())
        want = _words(key)
        if want and want <= have:
            return d
    return None


def resolve(recipe: Recipe, facts: dict[int, Product], prefs: Prefs) -> tuple[Resolved | None, str | None]:
    """Choose a product per ingredient (its alternative when out of stock) and check every hard rule.
    Returns (resolved, None) or (None, reason)."""
    if not recipe.fits_kitchen(prefs.appliances):
        return None, "needs an appliance you don't have"
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
    for ing, p in lines:
        hit = p.allergens & prefs.allergens
        if hit:
            return None, f"{p.name} contains {', '.join(sorted(hit))}"
        d = disliked(prefs, ing.name, p.name, ing.term) or (
            next((x for x in prefs.dislikes if x.lower() in ("fish", "shellfish") and x.lower() in p.allergens), None))
        if d:
            return None, f"has {d.lower()}, which you don't like"
        veggie = bool({"vegetarian", "vegan"} & p.diet)
        if "vegan" in prefs.diets and "vegan" not in p.diet:
            return None, f"{p.name} is not vegan"
        if "vegetarian" in prefs.diets and not veggie:
            return None, f"{p.name} is not vegetarian"
        if "pescatarian" in prefs.diets and not (veggie or {"fish", "shellfish"} & p.allergens):
            return None, f"{p.name} is not pescatarian"
    cost = sum(ing.amount / p.pack_amount * p.price for ing, p in lines)
    nut = {k: sum(p.grams(ing.amount) * p.nutrition.get(k, 0) / 100 for ing, p in lines) for k in ("kcal", "protein", "carbs", "fat")}
    if "keto" in prefs.diets and nut["carbs"] > KETO_CARBS_G:
        return None, f"{round(nut['carbs'])} g carbs a serving is too many for keto"
    return Resolved(
        recipe=recipe, lines=lines, swaps=swaps, cost=cost, deals=sorted({p.name for _, p in lines if p.original}),
        pantry_hits=sum(1 for _, p in lines if p.id in prefs.pantry), **nut,
    ), None


def score(r: Resolved, prefs: Prefs) -> float:
    rec, d, v = r.recipe, prefs.diets, prefs.vibes
    s = -0.25 * r.cost + 0.04 * r.protein - 0.02 * rec.minutes + 0.8 * r.pantry_hits + 1.2 * len(r.deals)
    if prefs.prioritize_deals:
        s += 1.5 * len(r.deals) - 0.35 * r.cost
    if "high_protein" in d:
        s += 0.2 * r.protein
    if "glp1" in d:
        s += 0.1 * r.protein + (1.5 if "fiber" in rec.tags else 0) - 0.004 * max(0.0, r.kcal - 550)
    for tag in ("anti_inflammatory", "mediterranean", "mexican"):
        if tag in d and tag in rec.tags:
            s += 2.5
    if "quick" in v:
        s += 2.0 if rec.minutes <= 20 else -0.05 * (rec.minutes - 20)
    for tag in ("one_pan", "family", "comfort", "fresh", "fiber", "takeout"):
        if tag in v and tag in rec.tags:
            s += 2.0
    return s


def shopping_list(picks: list[tuple[Resolved, float]], pantry: set[int]) -> tuple[list[dict], list[dict]]:
    """Aggregate ingredients over picks (recipe, servings) into whole packs. Returns (have, need)."""
    totals: dict[int, dict[str, Any]] = {}
    for r, servings in picks:
        for ing, p in r.lines:
            # a swapped-in product is searched by its own name, not the out-of-stock ingredient's term
            term = ing.term if p.id == ing.product_id else p.name
            t = totals.setdefault(p.id, {"product": p, "amount": 0.0, "for": [], "term": term})
            if p.id == ing.product_id:
                t["term"] = ing.term
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


Chooser = Callable[[list[Resolved], Prefs, dict[str, int], list[str]], dict[str, Any] | None]


def plan(facts: dict[int, Product], prefs: Prefs, chooser: Chooser | None = None) -> dict[str, Any]:
    days = sorted({d for d in prefs.days if 0 <= d <= 6}) or [0]
    meals = [m for m in MEALS if m in prefs.meals] or ["dinner"]
    resolved: dict[str, Resolved] = {}
    excluded: list[dict[str, str]] = []
    needed = {POOL_FOR_MEAL[m] for m in meals}
    for recipe in RECIPES:
        if recipe.id in prefs.exclude or recipe.slot not in needed:
            continue
        r, why = resolve(recipe, facts, prefs)
        if r:
            resolved[recipe.id] = r
        else:
            excluded.append({"recipe": recipe.name, "reason": why or ""})

    pools = {pool: [m for m in meals if POOL_FOR_MEAL[m] == pool] for pool in ("breakfast", "main", "snack")}

    def unique_for(pool: str) -> int:
        n = len(days) * len(pools[pool])
        return math.ceil(n / 2) if prefs.batch_cook else n

    # Claude (when available) picks among the recipes that passed every hard rule; code does the rest
    ai = chooser(list(resolved.values()), prefs, {p: unique_for(p) for p in pools if pools[p]},
                 sorted(facts[i].name for i in prefs.pantry if i in facts)) if chooser else None
    protected = set(prefs.keep) | {k for ids in (ai or {}).get("picks", {}).values() for k in ids}

    schedule: list[dict[str, Any]] = []
    servings: dict[str, float] = {}
    chosen: list[str] = []
    missing: list[str] = []
    for pool, pool_meals in pools.items():
        if not pool_meals:
            continue
        occurrences = len(days) * len(pool_meals)
        candidates = [r for r in resolved.values() if r.recipe.slot == pool]
        if not candidates:
            missing.append(pool)
            continue
        first = list(prefs.keep) + ((ai or {}).get("picks", {}).get(pool) or [])
        picks = [resolved[k] for k in dict.fromkeys(first) if k in resolved and resolved[k].recipe.slot == pool]
        picks = picks[: unique_for(pool)]
        used = {p.id for r in picks for _, p in r.lines}
        while len(picks) < unique_for(pool):
            fresh = [r for r in candidates if r not in picks]
            if not fresh:  # fewer recipes than meals: repeat the best ones
                picks += picks[: unique_for(pool) - len(picks)]
                break
            best = max(fresh, key=lambda r: score(r, prefs) + 0.5 * sum(1 for _, p in r.lines if p.id in used))
            picks.append(best)
            used |= {p.id for _, p in best.lines}
        # each pick covers consecutive meals (cook once, eat twice when batch cooking)
        per = [occurrences // len(picks) + (1 if i < occurrences % len(picks) else 0) for i in range(len(picks))]
        order = [r for r, n in zip(picks, per) for _ in range(n)]
        for i, r in enumerate(order):
            d, m = divmod(i, len(pool_meals))
            schedule.append({"day": days[d], "day_name": DAY_NAMES[days[d]], "meal": pool_meals[m], "recipe": r.recipe.id,
                             "leftovers": i > 0 and order[i - 1] is r})
            servings[r.recipe.id] = servings.get(r.recipe.id, 0) + prefs.portions
            if r.recipe.id not in chosen:
                chosen.append(r.recipe.id)

    def estimate_for(ids: list[str], serv: dict[str, float]) -> tuple[list, list, float]:
        have, need = shopping_list([(resolved[k], serv[k]) for k in ids], prefs.pantry)
        return have, need, round(sum(n["line_total"] for n in need), 2)

    have, need, estimate = estimate_for(chosen, servings)
    # over budget: swap the priciest recipe for a cheaper unused one while that lowers the total
    for _ in range(8):
        if estimate <= prefs.budget:
            break
        improved = False
        for k in sorted(chosen, key=lambda k: -resolved[k].cost):
            if k in protected:  # the user's kept meals and Claude's picks aren't swapped behind their back
                continue
            slot = resolved[k].recipe.slot
            for alt in sorted((r for r in resolved.values() if r.recipe.slot == slot and r.recipe.id not in chosen), key=lambda r: r.cost):
                trial = [alt.recipe.id if c == k else c for c in chosen]
                trial_serv = {**{c: servings[c] for c in chosen if c != k}, alt.recipe.id: servings[k]}
                _, _, trial_est = estimate_for(trial, trial_serv)
                if trial_est < estimate:
                    chosen, servings = trial, trial_serv
                    for s in schedule:
                        if s["recipe"] == k:
                            s["recipe"] = alt.recipe.id
                    have, need, estimate = estimate_for(chosen, servings)
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break

    return {
        "portions": prefs.portions,
        "days": [{"day": d, "name": DAY_NAMES[d]} for d in days],
        "meals": meals,
        "schedule": schedule,
        "recipes": [{**recipe_json(resolved[k], servings[k], prefs), "why": (ai or {}).get("reasons", {}).get(k)} for k in chosen],
        "have": have,
        "need": need,
        "estimate": estimate,
        "saving": round(sum(n["saving"] for n in need), 2),
        "budget": prefs.budget,
        "over_budget": estimate > prefs.budget,
        "excluded": excluded,
        "missing": missing,
        "ai": {"used": ai is not None, "summary": ai["summary"] if ai else None},
    }


def recipe_json(r: Resolved, servings: float, prefs: Prefs) -> dict[str, Any]:
    rec = r.recipe
    return {
        "id": rec.id, "name": rec.name, "slot": rec.slot, "minutes": rec.minutes, "cuisine": rec.cuisine,
        "blurb": rec.blurb, "appliances": rec.appliances_for(prefs.appliances), "tags": sorted(rec.tags),
        "servings": round(servings, 1),
        "per_serving": {"kcal": round(r.kcal), "protein": round(r.protein, 1), "carbs": round(r.carbs, 1),
                        "fat": round(r.fat, 1), "cost": round(r.cost, 2)},
        "deals": r.deals, "swaps": r.swaps,
        "ingredients": [{"name": ing.name, "product_id": p.id, "product": p.name, "amount": ing.amount,
                         "unit": p.pack_unit} for ing, p in r.lines],
        "steps": [{"text": s.text, "minutes": s.minutes} for s in rec.steps],
    }
