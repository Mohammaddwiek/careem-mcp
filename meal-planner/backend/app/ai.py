"""Claude picks and explains the meal plan; code keeps everything safety-critical.

Claude only sees recipes that already passed the allergy, diet and appliance filters, so it can't
introduce an allergen; quantities, product ids, prices and the cart stay in code. Any failure
(no credentials, network, refusal, invalid ids) returns None and the caller uses the rule-based plan.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic
from pydantic import BaseModel, Field

from .planner import Prefs, Resolved

log = logging.getLogger("meal-planner.ai")
MODEL = os.environ.get("MEAL_PLANNER_MODEL", "claude-opus-5-5")

SYSTEM = """You plan home cooking for a meal-prep app built on Careem Quik grocery delivery in Dubai.

You get the user's household, goal, budget, pantry and any notes in their own words, plus a list of
candidate recipes. Every candidate already fits their allergies, diet and kitchen appliances, so
you never need to second-guess safety; pick only from the candidates, by id.

Choose the requested number of breakfasts and mains. Good plans:
- follow the user's notes and goal first (saving money: low cost per serving and items on deal;
  protein: high protein per serving; speed: short cooking time; balance: a mix);
- reuse ingredients across recipes so less goes to waste, and use what is already in the pantry;
- lean on today's Careem Quik deals where they fit;
- stay inside the budget (cost per serving times servings is a fair estimate) and vary cuisines.

Write a two-sentence summary of why this plan suits them, addressed to them, and one short sentence
per recipe saying why it is in the plan (mention a deal, a pantry item or their note when true).
Plain, warm language; no exclamation marks; no health or medical claims."""


class Pick(BaseModel):
    recipe_id: str
    reason: str = Field(description="One short sentence, under 20 words, on why this recipe is in the plan.")


class AIPlan(BaseModel):
    summary: str = Field(description="Two sentences, addressed to the user.")
    breakfasts: list[Pick]
    mains: list[Pick]


def available() -> bool:
    if os.environ.get("MEAL_PLANNER_AI", "").lower() in ("0", "off", "false"):
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or os.environ.get("ANTHROPIC_PROFILE"))


_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # A slow answer shouldn't stall the UI: give up after 45 s and use the rule-based plan.
        _client = anthropic.Anthropic(timeout=45.0, max_retries=1)
    return _client


def _candidate(r: Resolved) -> dict[str, Any]:
    return {
        "id": r.recipe.id, "name": r.recipe.name, "meal": r.recipe.slot, "cuisine": r.recipe.cuisine,
        "minutes": r.recipe.minutes, "cost_per_serving_aed": round(r.cost, 2),
        "protein_g": round(r.protein, 1), "kcal": round(r.kcal),
        "on_deal": r.deals, "pantry_items_used": r.pantry_hits,
        "ingredients": sorted({p.name for _, p in r.lines}),
    }


def choose(candidates: list[Resolved], prefs: Prefs, wanted: dict[str, int], pantry_names: list[str]) -> dict[str, Any] | None:
    """Ask Claude for the plan. Returns {"summary", "picks": {slot: [ids]}, "reasons": {id: text}} or None."""
    if not available() or not candidates:
        return None
    request = {
        "household": {"people": prefs.people, "days": prefs.days, "meals_each_day": prefs.meals,
                      "cook_once_eat_twice": prefs.batch_cook},
        "goal": prefs.goal, "weekly_budget_aed": prefs.budget, "pantry": pantry_names,
        "their_notes": prefs.notes or None,
        "choose": {"breakfasts": wanted.get("breakfast", 0), "mains": wanted.get("main", 0)},
        "servings_per_recipe": prefs.people * (2 if prefs.batch_cook else 1),
        "candidates": [_candidate(r) for r in candidates],
    }
    try:
        response = client().beta.messages.parse(
            model=MODEL,
            max_tokens=4000,
            system=SYSTEM,
            messages=[{"role": "user", "content": json.dumps(request, ensure_ascii=False)}],
            output_format=AIPlan,
            output_config={"effort": "low"},  # a short pick-and-explain task: keep the wait short
            cache_control={"type": "ephemeral"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIConnectionError as e:
        log.warning("Claude unreachable, using rule-based plan: %s", e)
        return None
    except anthropic.APIStatusError as e:
        log.warning("Claude error %s, using rule-based plan: %s", e.status_code, e.message)
        return None
    if response.stop_reason == "refusal" or response.parsed_output is None:
        log.warning("Claude gave no usable plan (stop_reason=%s), using rule-based plan", response.stop_reason)
        return None
    return validate(response.parsed_output, candidates, wanted)


def validate(plan: AIPlan, candidates: list[Resolved], wanted: dict[str, int]) -> dict[str, Any] | None:
    """Keep only ids that are real candidates for the right meal, without duplicates."""
    by_id = {r.recipe.id: r for r in candidates}
    picks: dict[str, list[str]] = {}
    reasons: dict[str, str] = {}
    for slot, chosen in (("breakfast", plan.breakfasts), ("main", plan.mains)):
        ids: list[str] = []
        for p in chosen:
            r = by_id.get(p.recipe_id)
            if r is None or r.recipe.slot != slot or p.recipe_id in ids:
                log.info("ignoring Claude pick %r for %s", p.recipe_id, slot)
                continue
            ids.append(p.recipe_id)
            reasons[p.recipe_id] = p.reason.strip()
        picks[slot] = ids[: wanted.get(slot, 0)]
    if not any(picks.values()):
        return None
    return {"summary": plan.summary.strip(), "picks": picks, "reasons": reasons}
