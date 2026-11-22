"""Live mode: a Quik catalog and one editable, priced basket behind the grocery tools.

See docs/superpowers/specs/2026-11-22-live-catalog-cart-design.md. Handlers take the canned
happy-path response as a skeleton (so every field keeps production's shape) and replace lines,
counts and prices with values from the catalog and the stored basket.
"""

from __future__ import annotations

import copy
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

QUIK_MERCHANT = 40001
BASKET_ID = 6000002
USER_ID = 900000001
DELIVERY_FEE = 4.0
SERVICE_FEE = 1.5
MEDIA = "https://careem-catalog-media.media.careem.com"
SEED_LINES = [
    {"item_uuid": "7c2d9e10-2222-4b8f-8d02-000000000001", "catalog_item_id": "4000101", "count": 2},
    {"item_uuid": "7c2d9e10-2222-4b8f-8d02-000000000002", "catalog_item_id": "4000102", "count": 1},
    {"item_uuid": "7c2d9e10-2222-4b8f-8d02-000000000003", "catalog_item_id": "4000103", "count": 1},
]
SEED_VERSION = 3
STOPWORDS = {"fresh", "the", "a", "an", "of", "and", "for", "some", "g", "kg", "ml", "l", "pack", "pcs", "x"}
ALLERGEN_LABELS = {
    "gluten": "Gluten", "dairy": "Milk", "egg": "Egg", "peanuts": "Peanuts", "tree_nuts": "Tree nuts",
    "soy": "Soy", "fish": "Fish", "shellfish": "Shellfish", "sesame": "Sesame",
}
DIET_LABELS = {"vegan": "Vegan", "vegetarian": "Vegetarian", "gluten_free": "Gluten free", "halal": "Halal"}


def r2(x: float) -> float:
    return round(x + 0.0, 2)


# ---------------------------------------------------------------- catalog


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    unit: str
    pack_amount: float
    pack_unit: str
    price: float
    original: float | None
    category: dict[str, Any]
    keywords: tuple[str, ...]
    allergens: tuple[str, ...]
    diet: tuple[str, ...]
    nutrition: dict[str, float]
    available: bool
    stock: int
    recommended: bool
    master: str

    @property
    def discount(self) -> float:
        return r2(self.original - self.price) if self.original else 0.0

    @property
    def discount_pct(self) -> int:
        return round(100 * self.discount / self.original) if self.original else 0

    @property
    def image(self) -> str:
        return f"{MEDIA}/quik/{self.master}.png"

    @property
    def upc(self) -> str:
        return "6290000" + str(self.id)[1:]


def load_catalog(path: Path) -> dict[int, Product]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: dict[int, Product] = {}
    for p in data["products"]:
        out[p["id"]] = Product(
            id=p["id"], name=p["name"], unit=p["unit"],
            pack_amount=p["pack"]["amount"], pack_unit=p["pack"]["unit"],
            price=p["price"], original=p.get("original_price"), category=p["category"],
            keywords=tuple(p.get("keywords", [])), allergens=tuple(p.get("allergens", [])),
            diet=tuple(p.get("diet", [])), nutrition=p.get("nutrition_per_100", {}),
            available=p.get("available", True), stock=p.get("stock", 99),
            recommended=p.get("recommended", False), master=p["master_product_id"],
        )
    return out


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("oes"):
        return word[:-2]
    if len(word) > 3 and word.endswith("es") and word[:-2].endswith(("sh", "ch", "x", "ss")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokens(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z]+", text.lower())]


def _phrase(text: str) -> str:
    return " ".join(_tokens(text))


def search(
    catalog: dict[int, Product],
    term: str,
    *,
    on_discount: bool = False,
    previously_ordered: bool = False,
    recommended: bool = False,
    usual_ids: set[int] | frozenset[int] = frozenset(),
) -> list[Product]:
    """Products matching a search term: every meaningful term word is in the product's name or
    keywords; failing that, any keyword phrase that appears inside the term. Best match first."""
    words = [w for w in _tokens(term) if w not in STOPWORDS]
    if not words:
        return []
    phrase = " ".join(words)
    padded = f" {phrase} "

    def ok(p: Product) -> bool:
        return (
            (not on_discount or bool(p.original))
            and (not previously_ordered or p.id in usual_ids)
            and (not recommended or p.recommended)
        )

    scored: list[tuple[tuple, Product]] = []
    for p in catalog.values():
        if not ok(p):
            continue
        vocab = set(_tokens(p.name))
        for k in p.keywords:
            vocab.update(_tokens(k))
        kw = [_phrase(k) for k in p.keywords]
        if set(words) <= vocab:
            rank = 0 if phrase in kw else (1 if kw and kw[0].split()[0] in words else 2)
        elif any(f" {k} " in padded for k in kw if k):
            longest = max(len(k) for k in kw if k and f" {k} " in padded)
            rank = 3 - min(longest, 99) / 100
        else:
            continue
        scored.append(((rank, not p.available, len(p.name), p.id), p))
    scored.sort(key=lambda s: s[0])
    return [p for _, p in scored]


# ---------------------------------------------------------------- basket


class Basket:
    """The user's single Quik basket, persisted as JSON. A missing or corrupt file means the seed."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lines: list[dict[str, Any]] = []
        self.version = SEED_VERSION
        self.load()

    def load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            lines = data["lines"]
            assert isinstance(lines, list)
            self.lines = [
                {"item_uuid": str(l["item_uuid"]), "catalog_item_id": str(l["catalog_item_id"]), "count": int(l["count"])}
                for l in lines
            ]
            self.version = int(data.get("version", SEED_VERSION))
        except (OSError, ValueError, KeyError, TypeError, AssertionError):
            self.lines = copy.deepcopy(SEED_LINES)
            self.version = SEED_VERSION

    def save(self) -> None:
        self.version += 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"version": self.version, "lines": self.lines}, indent=2) + "\n")

    def line(self, item_uuid: str) -> dict[str, Any] | None:
        return next((l for l in self.lines if l["item_uuid"] == item_uuid), None)

    def count_of(self, product_id: int) -> int:
        return sum(l["count"] for l in self.lines if l["catalog_item_id"] == str(product_id))

    def add(self, product: Product, count: int) -> str | None:
        if not isinstance(count, int) or count <= 0:
            return None
        for l in self.lines:
            if l["catalog_item_id"] == str(product.id):
                l["count"] += count
                self.save()
                return l["item_uuid"]
        new = {"item_uuid": str(uuid.uuid4()), "catalog_item_id": str(product.id), "count": count}
        self.lines.append(new)
        self.save()
        return new["item_uuid"]

    def set_count(self, item_uuid: str, count: int) -> bool:
        l = self.line(item_uuid)
        if l is None:
            return False
        if count <= 0:
            self.lines.remove(l)
        else:
            l["count"] = count
        self.save()
        return True

    def remove(self, item_uuids: list[str]) -> list[str]:
        """Remove lines; returns the uuids that were not in the basket."""
        missing = [u for u in item_uuids if self.line(u) is None]
        self.lines = [l for l in self.lines if l["item_uuid"] not in item_uuids]
        self.save()
        return missing

    def clear(self) -> None:
        self.lines = []
        self.save()

    def reset(self) -> None:
        self.lines = copy.deepcopy(SEED_LINES)
        self.save()


def line_price(product: Product, count: int) -> dict[str, float]:
    original = r2((product.original or product.price) * count)
    total = r2(product.price * count)
    return {"discount": r2(original - total), "original": original, "total": total}


def price(basket: Basket, catalog: dict[int, Product]) -> dict[str, float]:
    subtotal = original = 0.0
    for l in basket.lines:
        p = catalog.get(int(l["catalog_item_id"]))
        if p is None:
            continue
        lp = line_price(p, l["count"])
        subtotal += lp["total"]
        original += lp["original"]
    has_items = bool(basket.lines)
    delivery = DELIVERY_FEE if has_items else 0.0
    service = SERVICE_FEE if has_items else 0.0
    return {
        "subtotal": r2(subtotal), "original": r2(original), "saving": r2(original - subtotal),
        "delivery": delivery, "service": service, "total": r2(subtotal + delivery + service),
    }


# ---------------------------------------------------------------- response builders


def _price_obj(p: Product, *, with_type: bool = True) -> dict[str, Any]:
    original = p.original or p.price
    out: dict[str, Any] = {
        "original": original, "original_formatted": f"{original:.2f}",
        "discount": p.discount, "discount_percentage": p.discount_pct,
        "total": p.price, "total_formatted": f"{p.price:.2f}", "tax_percentage": 5,
    }
    if with_type:
        out["discount_type"] = "PERCENTAGE" if p.original else None
    elif p.original:
        out["discount_type"] = "PERCENTAGE"
    return out


def _search_tags(p: Product) -> list[str]:
    return list(p.diet) + [f"allergen_{a}" for a in p.allergens]


def search_item(p: Product) -> dict[str, Any]:
    badge = f"{p.discount_pct}% off" if p.original else None
    return {
        "id": p.id, "item": p.name, "item_localized": p.name, "upc": p.upc,
        "image_url": p.image, "images_urls": [p.image],
        "description": f"{p.name} ({p.unit})", "description_localized": f"{p.name} ({p.unit})",
        "price": _price_obj(p), "active": True, "link": f"{MEDIA}/quik/items/{p.id}",
        "attributes": [], "tags": _search_tags(p), "catalog_id": QUIK_MERCHANT,
        "view_only_promotion": None, "currency": {"code": "AED", "decimals": 2, "label": "AED"},
        "item_location": None, "master_product_id": p.master, "is_near_expiry": False,
        "is_ad": False, "ad_details": None, "is_available": p.available, "timing": None, "groups": [],
        "item_promotion": {"label": badge} if badge else None, "item_badge_localized": badge,
        "item_type": "REGULAR", "bundle_details": None,
        "superapp_link": f"careem://shops/merchant/{QUIK_MERCHANT}/item/{p.id}",
    }


def detail_item(p: Product) -> dict[str, Any]:
    per = "ml" if p.pack_unit == "ml" else "g"
    n = p.nutrition
    allergens = ", ".join(ALLERGEN_LABELS.get(a, a) for a in p.allergens) or "None declared"
    out: dict[str, Any] = {
        "id": p.id, "item": p.name, "item_localized": p.name, "upc": p.upc, "images_urls": [p.image],
        "description": f"{p.name} ({p.unit})", "description_localized": f"{p.name} ({p.unit})",
        "price": _price_obj(p, with_type=False), "active": True, "link": f"{MEDIA}/quik/items/{p.id}",
        "catalog_id": QUIK_MERCHANT, "currency": {"label_localized": "AED"},
        "unit_of_measure": {"value": p.unit, "value_localized": p.unit},
        "core_category": {
            "id": p.category["id"], "name": p.category["name"], "name_localized": p.category["name"],
            "parent_category_id": p.category["parent_id"], "parent_category_name": p.category["parent_name"],
            "parent_category_name_localized": p.category["parent_name"],
        },
        "image_url": p.image, "master_product_id": p.master, "is_near_expiry": False, "is_ad": False,
        "is_available": p.available, "item_type": "product",
        "additional_attributes": [{
            "key": "nutrition", "title_localized": f"Nutrition facts (per 100 {per})", "type": "table",
            "items": [
                {"key": "energy", "title_localized": "Energy", "primary_text_localized": f"{n.get('kcal', 0):g} kcal"},
                {"key": "protein", "title_localized": "Protein", "primary_text_localized": f"{n.get('protein_g', 0):g} g"},
                {"key": "carbohydrates", "title_localized": "Carbohydrates", "primary_text_localized": f"{n.get('carbs_g', 0):g} g"},
                {"key": "fat", "title_localized": "Fat", "primary_text_localized": f"{n.get('fat_g', 0):g} g"},
            ],
        }],
        "attributes": [
            {"key": "allergens", "title_localized": "Allergens", "value_localized": allergens},
            {"key": "pack_size", "title_localized": "Pack size", "value_localized": p.unit},
        ],
        "tags": [{"key": d, "text_localized": DIET_LABELS.get(d, d)} for d in p.diet]
        + [{"key": f"allergen_{a}", "text_localized": f"Contains {ALLERGEN_LABELS.get(a, a).lower()}"} for a in p.allergens],
    }
    if p.original:
        out["item_promotion"] = {"metadata": {"type": "DISCOUNT"}}
        out["item_badge_localized"] = f"{p.discount_pct}% off"
    return out


# ---------------------------------------------------------------- live mode

Skeleton = Callable[[str, str, dict[str, Any]], dict[str, Any]]

# Canned error scenarios triggered by item ids, search terms, counts or totals: live mode decides
# these from the catalog and basket instead. Every other canned error (bad coordinates, upstream
# down, …) is returned as-is so it stays rehearsable.
RECOMPUTED_ERRORS: dict[str, set[str]] = {
    "search_groceries_items": {"no-results", "partial-results"},
    "groceries_get_items_details": {"unknown-item"},
    "create_grocery_cart_with_quantities": {"avocado-out-of-stock", "unknown-item", "eggs-low-stock", "unpriced-item"},
    "cart_add_item": {"out-of-stock", "item-unavailable"},
    "cart_add_items": {"partial-out-of-stock"},
    "cart_update_item": {"out-of-stock", "line-not-found"},
    "cart_delete_items": {"item-not-found", "basket-emptied"},
    "cart_grocery_checkout": {"price-changed"},
}


class LiveMode:
    TOOLS = {
        "search_groceries_items", "groceries_get_items_details", "search_groceries_get_all_deals",
        "create_grocery_cart_with_quantities", "cart_get_quik_basket", "cart_get_basket",
        "cart_get_basket_price", "cart_add_item", "cart_add_items", "cart_update_item",
        "cart_delete_items", "cart_delete_basket", "cart_grocery_checkout",
    }

    def __init__(self, catalog_path: Path, state_path: Path, skeleton: Skeleton):
        self.catalog = load_catalog(catalog_path)
        self.state_path = Path(state_path)
        self.skeleton = skeleton
        usual = skeleton("search_groceries_get_top_user_items", "usuals", {})
        self.usual_ids = frozenset(i["id"] for i in (usual.get("data") or {}).get("items") or [])

    def basket(self) -> Basket:
        return Basket(self.state_path)  # re-read every call so CLI edits apply immediately

    def handle(self, tool: str, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any] | None:
        return getattr(self, "_" + tool)(args, canned)

    # ------------------------------------------------------------ catalog tools

    def _search_groceries_items(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        if canned.get("fallback") is not None:
            return canned  # Shops fallback for things Quik doesn't sell
        limit = args.get("limit") or 10
        page = max(args.get("page") or 1, 1)
        groups = []
        for term in args.get("search_terms") or []:
            hits = search(
                self.catalog, term,
                on_discount=bool(args.get("on_discount")),
                previously_ordered=bool(args.get("previously_ordered")),
                recommended=bool(args.get("careem_recommended")),
                usual_ids=self.usual_ids,
            )[(page - 1) * limit : page * limit]
            if hits:
                groups.append({"name": term, "items": [search_item(p) for p in hits]})
        if not groups:
            return self.skeleton("search_groceries_items", "no-results", args)
        out = self.skeleton("search_groceries_items", "generic-results", args)
        out.pop("current_basket", None)
        out["groups"] = groups
        return out

    def _groceries_get_items_details(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        ids = args.get("item_ids") or []
        if len(ids) > 20:
            return self.skeleton("groceries_get_items_details", "too-many-items", args)
        items = []
        for i in ids:
            p = self.catalog.get(i)
            items.append({"item_id": i, "data": detail_item(p)} if p else {"item_id": i, "error": "item not found at this merchant"})
        return {"page": canned.get("page", "groceries_get_items_details"), "items": items}

    def _search_groceries_get_all_deals(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        groups: dict[int, dict[str, Any]] = {}
        for p in sorted(self.catalog.values(), key=lambda p: p.id):
            if not p.original:
                continue
            c = p.category
            g = groups.setdefault(c["id"], {"id": c["id"], "name": c["name"], "name_localized": c["name"], "active": True, "items": []})
            g["items"].append(search_item(p))
        out = dict(canned)
        out["groups"] = list(groups.values())
        return out

    # ------------------------------------------------------------ basket envelope

    def _merchant(self) -> dict[str, Any]:
        return self.skeleton("cart_get_quik_basket", "quik-basket", {})["merchant"]

    def envelope(self, page: str, basket: Basket, args: dict[str, Any]) -> dict[str, Any]:
        out = self.skeleton("cart_get_quik_basket", "quik-basket", args)
        out["page"] = page
        b = out["basket"]
        lines = []
        for l in basket.lines:
            p = self.catalog.get(int(l["catalog_item_id"]))
            if p is None:
                continue
            lines.append({
                "item_uuid": l["item_uuid"], "catalog_item_id": l["catalog_item_id"], "comment": None,
                "count": l["count"], "options": None, "price": line_price(p, l["count"]),
                "careem_user_id": USER_ID, "title_localized": p.name, "image_url": f"{MEDIA}/items/{p.id}.png",
            })
        pr = price(basket, self.catalog)
        b.update({
            "items": lines, "count": len(lines), "total_count": sum(l["count"] for l in lines),
            "version": basket.version, "price": {"net_total": pr["subtotal"], "original": pr["original"]},
        })
        money = out["price"]
        rows = {"Subtotal": pr["subtotal"], "Delivery fee": pr["delivery"], "Service fee": pr["service"], "Total": pr["total"]}
        for row in money["breakdown"]:
            title = row["label"]["title"]
            if title in rows:
                row["value"][0]["price"] = rows[title]
        money["price"]["total"] = pr["total"]
        money["total_saving"] = pr["saving"]
        for fee in money["fees"]:
            fee["value"] = pr["delivery"] if fee["type"] == "delivery_fee" else pr["service"]
        return out

    def _empty(self, tool: str, scenario: str, args: dict[str, Any]) -> dict[str, Any]:
        out = self.skeleton(tool, scenario, args)
        if "merchant" in out:
            out["merchant"] = self._merchant()
        return out

    # ------------------------------------------------------------ basket tools

    def _cart_get_quik_basket(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        b = self.basket()
        if not b.lines:
            return self.skeleton("cart_get_quik_basket", "no-basket", args)
        return self.envelope(canned["page"], b, args)

    def _cart_get_basket(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        b = self.basket()
        if not b.lines:
            return self._empty("cart_get_basket", "no-basket", args)
        return self.envelope(canned["page"], b, args)

    def _cart_get_basket_price(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        b = self.basket()
        if not b.lines:
            return self._empty("cart_get_basket_price", "empty-basket", args)
        return self.envelope(canned["page"], b, args)

    def _addable(self, b: Basket, p: Product | None, count: int) -> int:
        if p is None or not p.available:
            return 0
        return max(0, min(count, p.stock - b.count_of(p.id)))

    def _cart_add_item(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        b = self.basket()
        p = self._product(args.get("catalog_item_id"))
        if p is None:
            return self.skeleton("cart_add_item", "item-unavailable", args)
        if not p.available:
            return self.skeleton("cart_add_item", "out-of-stock", args)
        b.add(p, self._addable(b, p, int(args.get("count") or 0)))
        return self.envelope(canned["page"], b, args)

    def _cart_add_items(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        b = self.basket()
        results = []
        for it in args.get("items") or []:
            cid = str(it.get("catalog_item_id"))
            p = self._product(cid)
            n = self._addable(b, p, int(it.get("count") or 0))
            if p is None:
                results.append({"catalog_item_id": cid, "item_uuid": str(uuid.uuid4()), "success": False,
                                "error": "item is not available at this merchant"})
            elif not p.available or n == 0:
                results.append({"catalog_item_id": cid, "item_uuid": str(uuid.uuid4()), "success": False,
                                "error": f"{p.name} is currently out of stock at Careem Quik Dubai Marina."})
            else:
                results.append({"catalog_item_id": cid, "item_uuid": b.add(p, n), "success": True})
        out = self.envelope(canned["page"], b, args)
        return {"page": out["page"], "results": results, **{k: v for k, v in out.items() if k != "page"}}

    def _cart_update_item(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        b = self.basket()
        line = b.line(str(args.get("item_uuid")))
        if line is None:
            return self.skeleton("cart_update_item", "line-not-found", args)
        p = self._product(line["catalog_item_id"])
        count = int(args.get("count") or 0)
        if p is not None and count > p.stock:
            return self.skeleton("cart_update_item", "out-of-stock", args)
        b.set_count(line["item_uuid"], count)
        return self.envelope(canned["page"], b, args)

    def _cart_delete_items(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        b = self.basket()
        uuids = [u.strip() for u in str(args.get("item_uuids") or "").split(",") if u.strip()]
        if not uuids or all(b.line(u) is None for u in uuids):
            return self.skeleton("cart_delete_items", "item-not-found", args)
        b.remove(uuids)
        if not b.lines:
            return self.skeleton("cart_delete_items", "basket-emptied", args)
        out = self.envelope(canned["page"], b, args)
        return {"page": out["page"], "success": True, **{k: v for k, v in out.items() if k != "page"}}

    def _cart_delete_basket(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        self.basket().clear()
        return canned

    def _cart_grocery_checkout(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        b = self.basket()
        if not b.lines:
            return self.skeleton("cart_grocery_checkout", "basket-not-found", args)
        total = price(b, self.catalog)["total"]
        if abs(float(args.get("total_price") or 0) - total) > 0.01:
            return self.skeleton("cart_grocery_checkout", "price-changed", args)
        base = {"cash": "cash-order", "wallet": "wallet-order"}.get(str(args.get("payment_type") or "").lower(), "card-order")
        out = self.skeleton("cart_grocery_checkout", base, {**args, "total_price": total})
        if "amount" in out:
            out["amount"] = total
        b.clear()  # the order now owns these items
        return out

    def _create_grocery_cart_with_quantities(self, args: dict[str, Any], canned: dict[str, Any]) -> dict[str, Any]:
        b = self.basket()
        data = copy.deepcopy(canned["data"])
        groups, failed = [], []
        for it in args.get("items") or []:
            keyword, qty = it.get("keyword", ""), int(it.get("quantity") or 0)
            p = self._product(it.get("catalog_item_id"))
            if qty <= 0:
                continue
            group = {"keyword": keyword, "quantity": qty, "items": []}
            if p is None:
                group["items"].append({"id": int(it["catalog_item_id"]) if str(it.get("catalog_item_id", "")).isdigit() else 0,
                                       "title": "", "image_url": "", "secondary_info": f"AED {float(it.get('price') or 0):.2f}",
                                       "price": float(it.get("price") or 0), "currency": "AED", "is_available": False})
                failed.append({"keyword": keyword, "requested_quantity": qty, "error_code": "NOT_FOUND", "error_message": "Item not found"})
            else:
                n = self._addable(b, p, qty)
                chosen = self._cart_item(p)
                if n > 0:
                    chosen["item_uuid"] = b.add(p, n)
                    group["quantity"] = n
                if n < qty:
                    f = {"keyword": keyword, "requested_quantity": qty, "error_code": "INSUFFICIENT_STOCK", "error_message": "Item is out of stock"}
                    if n > 0:
                        f.update({"max_available": n, "added_quantity": n})
                    failed.append(f)
                group["items"].append(chosen)
            for alt in it.get("alternatives") or []:
                ap = self._product(alt.get("catalog_item_id"))
                if ap is not None:
                    group["items"].append(self._cart_item(ap))
            groups.append(group)
        data["groups"] = groups
        data["unavailable_keywords"] = []
        data["basket_id"] = BASKET_ID
        data.pop("failed_items", None)
        if failed:
            data["failed_items"] = failed
        cb = data.get("current_basket") or {}
        pr = price(b, self.catalog)
        cb["price"] = {"net_total": pr["subtotal"], "original": pr["original"]}
        cb["items"] = [
            {"item_uuid": l["item_uuid"], "catalog_item_id": l["catalog_item_id"], "title_localized": p.name,
             "count": l["count"], "price": line_price(p, l["count"]), "active": True, "image_url": p.image}
            for l in b.lines if (p := self.catalog.get(int(l["catalog_item_id"]))) is not None
        ]
        data["current_basket"] = cb
        return {"page": canned["page"], "data": data}

    # ------------------------------------------------------------ helpers

    def _product(self, catalog_item_id: Any) -> Product | None:
        try:
            return self.catalog.get(int(str(catalog_item_id)))
        except ValueError:
            return None

    @staticmethod
    def _cart_item(p: Product) -> dict[str, Any]:
        return {"id": p.id, "title": p.name, "image_url": p.image, "secondary_info": f"AED {p.price:.2f}",
                "price": p.price, "currency": "AED", "is_available": p.available}
