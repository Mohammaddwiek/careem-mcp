"""Recipe library. Ingredient amounts are per serving, in the Quik product's pack unit (g, ml, pcs).

`term` is what we search Careem Quik for; `alt` is the product to use when the first choice is
out of stock. Facts about products (price, allergens, nutrition, stock) come from the MCP server.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Ingredient:
    product_id: int
    amount: float
    name: str
    term: str
    alt: int | None = None


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    slot: str  # "breakfast" or "main"
    minutes: int
    appliances: tuple[str, ...]
    cuisine: str
    blurb: str
    ingredients: tuple[Ingredient, ...] = field(default_factory=tuple)


I = Ingredient
EGG, MILK, YOG, LABNEH, CHEDDAR, MOZZ, HALLOUMI, FETA, PARM, BUTTER, CREAM = (
    4000102, 4000101, 4000107, 4000111, 4000112, 4000113, 4000114, 4000115, 4000116, 4000117, 4000118)
SOURDOUGH, WHOLEMEAL, GF_BREAD, PITA, WRAPS = 4000103, 4000119, 4000120, 4000121, 4000122
BANANA, AVOCADO, APPLE, LEMON, BLUEB = 4000104, 4000106, 4000123, 4000124, 4000125
TOMATO, CHERRY, CUCUMBER, ONION, GARLIC, POTATO, SWEETPOT = 4000126, 4000127, 4000128, 4000129, 4000130, 4000131, 4000132
SPINACH, BROCCOLI, CARROT, PEPPER, ZUCCHINI, MUSHROOM, LETTUCE = 4000133, 4000134, 4000135, 4000136, 4000137, 4000138, 4000139
CORIANDER, PARSLEY, GINGER = 4000140, 4000141, 4000142
CHICKEN, THIGH, BEEF, LAMB, SALMON, SHRIMP, TUNA = 4000143, 4000144, 4000146, 4000147, 4000148, 4000149, 4000150
RICE, BROWN_RICE, OATS, QUINOA, SPAGHETTI, PENNE, GF_PASTA, NOODLES = (
    4000152, 4000153, 4000154, 4000155, 4000156, 4000157, 4000158, 4000159)
OLIVE_OIL, SUN_OIL, CHOPPED, CHICKPEAS, LENTILS, COCONUT, PB, ALMONDS, TAHINI, HONEY, SOY, PASSATA = (
    4000160, 4000161, 4000162, 4000163, 4000164, 4000165, 4000166, 4000167, 4000168, 4000169, 4000170, 4000171)
SALT, BLACK_PEPPER, CUMIN, PAPRIKA, FLOUR, FROZEN_VEG, PEAS, ALMOND_MILK = (
    4000172, 4000173, 4000174, 4000175, 4000176, 4000177, 4000178, 4000179)

RECIPES: tuple[Recipe, ...] = (
    Recipe("shakshuka", "Shakshuka with feta and pita", "main", 25, ("stove",), "Levantine",
           "Eggs poached in a spiced tomato and pepper sauce.", (
               I(EGG, 2, "Eggs", "eggs"), I(CHOPPED, 200, "Chopped tomatoes", "chopped tomatoes"),
               I(ONION, 50, "Red onion", "onion"), I(PEPPER, 0.5, "Bell pepper", "bell pepper"),
               I(GARLIC, 5, "Garlic", "garlic"), I(CUMIN, 2, "Cumin", "cumin"), I(PAPRIKA, 2, "Paprika", "paprika"),
               I(OLIVE_OIL, 10, "Olive oil", "olive oil"), I(FETA, 30, "Feta", "feta"), I(PITA, 1, "Pita bread", "pita"))),
    Recipe("chicken-rice-bowl", "Garlic soy chicken rice bowl", "main", 30, ("stove",), "Asian",
           "Seared chicken breast, basmati and broccoli with a soy-garlic glaze.", (
               I(CHICKEN, 150, "Chicken breast", "chicken breast"), I(RICE, 75, "Basmati rice", "basmati rice"),
               I(BROCCOLI, 100, "Broccoli", "broccoli"), I(GARLIC, 5, "Garlic", "garlic"),
               I(SOY, 15, "Soy sauce", "soy sauce"), I(OLIVE_OIL, 10, "Olive oil", "olive oil"))),
    Recipe("airfryer-thighs", "Air-fried paprika chicken with sweet potato", "main", 35, ("air_fryer",), "Modern",
           "Crispy chicken thighs, sweet potato wedges and a lemony spinach salad.", (
               I(THIGH, 180, "Chicken thighs", "chicken thigh"), I(SWEETPOT, 200, "Sweet potato", "sweet potato"),
               I(SPINACH, 40, "Baby spinach", "spinach"), I(LEMON, 25, "Lemon", "lemon"),
               I(OLIVE_OIL, 10, "Olive oil", "olive oil"), I(PAPRIKA, 2, "Paprika", "paprika"))),
    Recipe("bolognese", "Spaghetti bolognese", "main", 40, ("stove",), "Italian",
           "Slow-simmered beef and tomato sauce over spaghetti.", (
               I(BEEF, 125, "Beef mince", "beef mince"), I(SPAGHETTI, 100, "Spaghetti", "spaghetti"),
               I(PASSATA, 150, "Tomato passata", "passata"), I(ONION, 50, "Red onion", "onion"),
               I(GARLIC, 5, "Garlic", "garlic"), I(CARROT, 50, "Carrot", "carrot"),
               I(PARM, 10, "Parmesan", "parmesan"), I(OLIVE_OIL, 10, "Olive oil", "olive oil"))),
    Recipe("lentil-dal", "Coconut red lentil dal", "main", 30, ("stove",), "Indian",
           "Creamy red lentils with ginger and cumin, served with basmati.", (
               I(LENTILS, 80, "Red lentils", "red lentils"), I(COCONUT, 100, "Coconut milk", "coconut milk"),
               I(CHOPPED, 100, "Chopped tomatoes", "chopped tomatoes"), I(ONION, 50, "Red onion", "onion"),
               I(GARLIC, 5, "Garlic", "garlic"), I(GINGER, 5, "Ginger", "ginger"), I(CUMIN, 3, "Cumin", "cumin"),
               I(RICE, 60, "Basmati rice", "basmati rice"))),
    Recipe("chickpea-curry", "Chickpea and spinach curry", "main", 25, ("stove",), "Indian",
           "Chickpeas and spinach in a spiced coconut tomato sauce with brown rice.", (
               I(CHICKPEAS, 200, "Chickpeas", "chickpeas"), I(SPINACH, 50, "Baby spinach", "spinach"),
               I(COCONUT, 100, "Coconut milk", "coconut milk"), I(CHOPPED, 100, "Chopped tomatoes", "chopped tomatoes"),
               I(ONION, 50, "Red onion", "onion"), I(GINGER, 5, "Ginger", "ginger"), I(CUMIN, 3, "Cumin", "cumin"),
               I(BROWN_RICE, 60, "Brown rice", "brown rice"))),
    Recipe("overnight-oats", "Blueberry overnight oats", "breakfast", 5, (), "Breakfast",
           "Oats soaked in yogurt and milk, topped with blueberries, honey and almonds.", (
               I(OATS, 50, "Rolled oats", "oats"), I(YOG, 100, "Greek yogurt", "greek yogurt"),
               I(MILK, 100, "Milk", "milk", alt=ALMOND_MILK), I(BLUEB, 50, "Blueberries", "blueberries"),
               I(HONEY, 10, "Honey", "honey"), I(ALMONDS, 15, "Almonds", "almonds"))),
    Recipe("halloumi-traybake", "Halloumi and vegetable traybake", "main", 35, ("oven",), "Mediterranean",
           "Roasted halloumi, peppers, zucchini and cherry tomatoes over quinoa.", (
               I(HALLOUMI, 100, "Halloumi", "halloumi"), I(ZUCCHINI, 150, "Zucchini", "zucchini"),
               I(PEPPER, 1, "Bell pepper", "bell pepper"), I(ONION, 50, "Red onion", "onion"),
               I(CHERRY, 100, "Cherry tomatoes", "cherry tomatoes"), I(OLIVE_OIL, 15, "Olive oil", "olive oil"),
               I(QUINOA, 60, "Quinoa", "quinoa"))),
    Recipe("tuna-pasta", "Lemony tuna pasta salad", "main", 20, ("stove",), "Mediterranean",
           "Penne with tuna, cherry tomatoes, cucumber and a yogurt-lemon dressing.", (
               I(PENNE, 90, "Penne", "penne"), I(TUNA, 80, "Tuna", "tuna"), I(CHERRY, 80, "Cherry tomatoes", "cherry tomatoes"),
               I(CUCUMBER, 80, "Cucumber", "cucumber"), I(YOG, 30, "Greek yogurt", "greek yogurt"), I(LEMON, 15, "Lemon", "lemon"))),
    Recipe("salmon-traybake", "Roast salmon with potatoes and broccoli", "main", 35, ("oven",), "Modern",
           "Salmon fillet roasted with baby potatoes and broccoli.", (
               I(SALMON, 130, "Salmon fillet", "salmon", alt=CHICKEN), I(POTATO, 200, "Potatoes", "potatoes"),
               I(BROCCOLI, 100, "Broccoli", "broccoli"), I(LEMON, 20, "Lemon", "lemon"),
               I(OLIVE_OIL, 10, "Olive oil", "olive oil"))),
    Recipe("shrimp-noodles", "Ginger shrimp rice noodles", "main", 20, ("stove",), "Asian",
           "Quick stir-fried shrimp with rice noodles, peppers and carrot.", (
               I(SHRIMP, 120, "Shrimp", "shrimp"), I(NOODLES, 80, "Rice noodles", "rice noodles"),
               I(PEPPER, 0.5, "Bell pepper", "bell pepper"), I(CARROT, 50, "Carrot", "carrot"),
               I(SOY, 15, "Soy sauce", "soy sauce"), I(GINGER, 5, "Ginger", "ginger"), I(SUN_OIL, 10, "Sunflower oil", "sunflower oil"))),
    Recipe("avocado-toast", "Avocado toast with eggs", "breakfast", 10, ("stove",), "Breakfast",
           "Sourdough, smashed avocado and soft eggs.", (
               I(SOURDOUGH, 100, "Sourdough", "sourdough"), I(EGG, 2, "Eggs", "eggs"),
               I(AVOCADO, 1, "Avocado", "avocado", alt=LABNEH), I(LEMON, 10, "Lemon", "lemon"))),
    Recipe("beef-wraps", "Smoky beef and pepper wraps", "main", 20, ("stove",), "Mexican",
           "Paprika beef, peppers and cheddar rolled in whole wheat wraps.", (
               I(BEEF, 100, "Beef mince", "beef mince"), I(WRAPS, 2, "Tortilla wraps", "tortilla wraps"),
               I(PEPPER, 0.5, "Bell pepper", "bell pepper"), I(ONION, 40, "Red onion", "onion"),
               I(LETTUCE, 0.25, "Romaine lettuce", "lettuce"), I(CHEDDAR, 30, "Cheddar", "cheddar"),
               I(PAPRIKA, 2, "Paprika", "paprika"))),
    Recipe("lamb-stew", "Lamb, chickpea and potato stew", "main", 60, ("stove",), "Levantine",
           "Cumin-spiced lamb stew with chickpeas, carrots and potatoes.", (
               I(LAMB, 125, "Lamb cubes", "lamb"), I(CHICKPEAS, 100, "Chickpeas", "chickpeas"),
               I(CHOPPED, 150, "Chopped tomatoes", "chopped tomatoes"), I(ONION, 60, "Red onion", "onion"),
               I(CARROT, 60, "Carrot", "carrot"), I(CUMIN, 3, "Cumin", "cumin"), I(POTATO, 150, "Potatoes", "potatoes"))),
    Recipe("mug-omelette", "Microwave spinach mushroom omelette", "breakfast", 5, ("microwave",), "Breakfast",
           "A two-minute omelette in a mug with spinach, mushrooms and cheddar.", (
               I(EGG, 2, "Eggs", "eggs"), I(SPINACH, 20, "Baby spinach", "spinach"),
               I(MUSHROOM, 40, "Mushrooms", "mushrooms"), I(CHEDDAR, 20, "Cheddar", "cheddar"), I(MILK, 20, "Milk", "milk"))),
    Recipe("pb-smoothie", "Peanut butter banana smoothie", "breakfast", 5, ("blender",), "Breakfast",
           "Banana, peanut butter and oats blended with almond milk.", (
               I(BANANA, 120, "Banana", "banana"), I(PB, 20, "Peanut butter", "peanut butter"),
               I(OATS, 30, "Rolled oats", "oats"), I(ALMOND_MILK, 200, "Almond milk", "almond milk"))),
    Recipe("gf-mushroom-pasta", "Creamy mushroom and spinach fusilli", "main", 20, ("stove",), "Italian",
           "Gluten-free fusilli in a garlic cream sauce with mushrooms and spinach.", (
               I(GF_PASTA, 90, "Gluten-free fusilli", "gluten free pasta"), I(MUSHROOM, 100, "Mushrooms", "mushrooms"),
               I(SPINACH, 40, "Baby spinach", "spinach"), I(CREAM, 60, "Cooking cream", "cooking cream"),
               I(GARLIC, 5, "Garlic", "garlic"), I(PARM, 10, "Parmesan", "parmesan"))),
    Recipe("quinoa-chicken-salad", "Quinoa chicken salad with feta", "main", 25, ("stove",), "Mediterranean",
           "Warm quinoa, grilled chicken, cucumber, tomatoes, feta and parsley.", (
               I(QUINOA, 60, "Quinoa", "quinoa"), I(CHICKEN, 120, "Chicken breast", "chicken breast"),
               I(CUCUMBER, 80, "Cucumber", "cucumber"), I(CHERRY, 80, "Cherry tomatoes", "cherry tomatoes"),
               I(FETA, 30, "Feta", "feta"), I(LEMON, 15, "Lemon", "lemon"), I(OLIVE_OIL, 10, "Olive oil", "olive oil"),
               I(PARSLEY, 10, "Parsley", "parsley"))),
    Recipe("tuna-potatoes", "Microwave jacket potato with tuna", "main", 15, ("microwave",), "Modern",
           "Fluffy jacket potatoes with tuna, yogurt and cheddar.", (
               I(POTATO, 300, "Potatoes", "potatoes"), I(TUNA, 80, "Tuna", "tuna"),
               I(YOG, 50, "Greek yogurt", "greek yogurt"), I(CHEDDAR, 20, "Cheddar", "cheddar"))),
    Recipe("veg-fried-rice", "Vegetable egg fried rice", "main", 20, ("stove",), "Asian",
           "Basmati fried with eggs, peas, mixed vegetables and soy.", (
               I(RICE, 80, "Basmati rice", "basmati rice"), I(EGG, 1, "Eggs", "eggs"),
               I(FROZEN_VEG, 100, "Frozen mixed vegetables", "frozen vegetables"), I(PEAS, 40, "Peas", "peas"),
               I(SOY, 15, "Soy sauce", "soy sauce"), I(SUN_OIL, 10, "Sunflower oil", "sunflower oil"))),
)

BY_ID = {r.id: r for r in RECIPES}
ALL_PRODUCT_IDS = sorted({i.product_id for r in RECIPES for i in r.ingredients} | {i.alt for r in RECIPES for i in r.ingredients if i.alt})
APPLIANCES = ("stove", "oven", "air_fryer", "microwave", "blender")
