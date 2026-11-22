"""Product facts read from Careem Quik item details (MCP), with pack-size parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

DIETS = {"vegan", "vegetarian", "gluten_free", "halal"}
# grams per piece, for products sold in pieces (nutrition is per 100 g)
PIECE_GRAMS = {4000102: 50, 4000106: 150, 4000121: 60, 4000122: 60, 4000136: 150, 4000139: 300}


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    unit: str
    pack_amount: float
    pack_unit: str  # g, ml or pcs
    price: float
    original: float | None
    available: bool
    allergens: frozenset[str]
    diet: frozenset[str]
    nutrition: dict[str, float]  # kcal, protein, carbs, fat per 100 g/ml
    category: str

    @property
    def deal_pct(self) -> int:
        return round(100 * (self.original - self.price) / self.original) if self.original else 0

    def grams(self, amount: float) -> float:
        return amount * PIECE_GRAMS.get(self.id, 100) if self.pack_unit == "pcs" else amount

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "unit": self.unit, "price": self.price,
            "original_price": self.original, "deal_pct": self.deal_pct, "available": self.available,
            "allergens": sorted(self.allergens), "diet": sorted(self.diet), "category": self.category,
        }


def parse_pack(text: str) -> tuple[float, str]:
    """'500 g' → (500, 'g'); '1.5 L' → (1500, 'ml'); '6 x 1.5 L' → (9000, 'ml'); '12 pcs' → (12, 'pcs')."""
    t = text.lower().replace("×", "x")
    m = re.match(r"\s*(\d+)\s*x\s*(.+)$", t)
    if m:
        amount, unit = parse_pack(m.group(2))
        return int(m.group(1)) * amount, unit
    m = re.match(r"\s*([\d.]+)\s*(kg|g|ml|l|pcs|pc)\b", t)
    if not m:
        return 1.0, "pcs"
    n, u = float(m.group(1)), m.group(2)
    return {"kg": (n * 1000, "g"), "g": (n, "g"), "l": (n * 1000, "ml"), "ml": (n, "ml")}.get(u, (n, "pcs"))


def _number(text: str) -> float:
    m = re.search(r"[\d.]+", text or "")
    return float(m.group()) if m else 0.0


def from_details(data: dict[str, Any]) -> Product:
    tags = {t.get("key", "") for t in data.get("tags") or []}
    unit = (data.get("unit_of_measure") or {}).get("value") or ""
    amount, punit = parse_pack(unit)
    nutrition: dict[str, float] = {}
    for block in data.get("additional_attributes") or []:
        if block.get("key") == "nutrition":
            for row in block.get("items") or []:
                key = {"energy": "kcal", "protein": "protein", "carbohydrates": "carbs", "fat": "fat"}.get(row.get("key"))
                if key:
                    nutrition[key] = _number(row.get("primary_text_localized", ""))
    price = data.get("price") or {}
    original = price.get("original") if (price.get("discount") or 0) > 0 else None
    return Product(
        id=data["id"], name=data.get("item", ""), unit=unit, pack_amount=amount, pack_unit=punit,
        price=float(price.get("total", 0)), original=float(original) if original else None,
        available=bool(data.get("is_available", True)),
        allergens=frozenset(t[len("allergen_"):] for t in tags if t.startswith("allergen_")),
        diet=frozenset(tags & DIETS), nutrition=nutrition,
        category=(data.get("core_category") or {}).get("parent_category_name", ""),
    )
