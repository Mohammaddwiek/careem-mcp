"""Recipe library. Ingredient amounts are per serving, in the Quik product's pack unit (g, ml, pcs).

`term` is what we search Careem Quik for; `alt` is the product to use when the first choice is out
of stock. Product facts (price, allergens, nutrition, stock) come from the MCP server.

`appliances` lists what a recipe needs; each entry is one appliance or a tuple of alternatives
(("stovetop", "slow_cooker") means either works). Diet fit (vegetarian, vegan, pescatarian, keto)
is computed from the products and nutrition, not tagged by hand; `tags` carry the softer traits.
"""

from __future__ import annotations

from dataclasses import dataclass, field

APPLIANCES = ("oven", "stovetop", "air_fryer", "microwave", "toaster", "blender", "slow_cooker")
TAGS = ("one_pan", "family", "comfort", "fresh", "fiber", "takeout", "anti_inflammatory", "mediterranean", "mexican")


@dataclass(frozen=True)
class Ingredient:
    product_id: int
    amount: float
    name: str
    term: str
    alt: int | None = None


@dataclass(frozen=True)
class Step:
    text: str
    minutes: int | None = None  # offers a timer in the UI


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    slot: str  # breakfast, main or snack
    minutes: int
    appliances: tuple[str | tuple[str, ...], ...]
    cuisine: str
    blurb: str
    ingredients: tuple[Ingredient, ...] = field(default_factory=tuple)
    steps: tuple[Step, ...] = field(default_factory=tuple)
    tags: frozenset[str] = frozenset()

    def fits_kitchen(self, owned: set[str]) -> bool:
        return all((need in owned) if isinstance(need, str) else bool(set(need) & owned) for need in self.appliances)

    def appliances_for(self, owned: set[str]) -> list[str]:
        """The appliances this cook will use, picking the first owned alternative."""
        out = []
        for need in self.appliances:
            options = (need,) if isinstance(need, str) else need
            out.append(next((a for a in options if a in owned), options[0]))
        return out


I, S = Ingredient, Step
T = lambda *t: frozenset(t)  # noqa: E731

EGG, MILK, YOG, LABNEH, CHEDDAR, MOZZ, HALLOUMI, FETA, PARM, BUTTER, CREAM = (
    4000102, 4000101, 4000107, 4000111, 4000112, 4000113, 4000114, 4000115, 4000116, 4000117, 4000118)
PLAIN_YOG = 4000182
SOURDOUGH, WHOLEMEAL, GF_BREAD, PITA, WRAPS = 4000103, 4000119, 4000120, 4000121, 4000122
BANANA, AVOCADO, APPLE, LEMON, BLUEB, STRAWB = 4000104, 4000106, 4000123, 4000124, 4000125, 4000181
TOMATO, CHERRY, CUCUMBER, ONION, GARLIC, POTATO, SWEETPOT = 4000126, 4000127, 4000128, 4000129, 4000130, 4000131, 4000132
SPINACH, BROCCOLI, CARROT, PEPPER, ZUCCHINI, MUSHROOM, LETTUCE, KALE, EGGPLANT = (
    4000133, 4000134, 4000135, 4000136, 4000137, 4000138, 4000139, 4000184, 4000187)
CORIANDER, PARSLEY, GINGER = 4000140, 4000141, 4000142
CHICKEN, THIGH, BEEF, LAMB, SALMON, SHRIMP, TUNA, TOFU = 4000143, 4000144, 4000146, 4000147, 4000148, 4000149, 4000150, 4000183
RICE, BROWN_RICE, OATS, QUINOA, SPAGHETTI, PENNE, GF_PASTA, NOODLES = (
    4000152, 4000153, 4000154, 4000155, 4000156, 4000157, 4000158, 4000159)
OLIVE_OIL, SUN_OIL, CHOPPED, CHICKPEAS, LENTILS, COCONUT, PB, ALMONDS, TAHINI, HONEY, SOY, PASSATA = (
    4000160, 4000161, 4000162, 4000163, 4000164, 4000165, 4000166, 4000167, 4000168, 4000169, 4000170, 4000171)
SALT, BLACK_PEPPER, CUMIN, PAPRIKA, FLOUR, FROZEN_VEG, PEAS, ALMOND_MILK = (
    4000172, 4000173, 4000174, 4000175, 4000176, 4000177, 4000178, 4000179)
CORN, OLIVES = 4000185, 4000186

RECIPES: tuple[Recipe, ...] = (
    # ------------------------------------------------------------ breakfasts
    Recipe("overnight-oats", "Blueberry overnight oats", "breakfast", 5, (), "Breakfast",
           "Oats soaked in yogurt and milk, topped with blueberries, honey and almonds.", (
               I(OATS, 50, "Rolled oats", "oats"), I(YOG, 100, "Greek yogurt", "greek yogurt"),
               I(MILK, 100, "Milk", "milk", alt=ALMOND_MILK), I(BLUEB, 50, "Blueberries", "blueberries"),
               I(HONEY, 10, "Honey", "honey"), I(ALMONDS, 15, "Almonds", "almonds")), (
               S("Stir the oats, yogurt and milk together in a jar or bowl."),
               S("Cover and refrigerate overnight, or at least 4 hours."),
               S("In the morning, top with blueberries, chopped almonds and a drizzle of honey.")),
           T("fiber", "fresh", "family")),
    Recipe("avocado-toast", "Avocado toast with soft eggs", "breakfast", 10, ("stovetop", ("toaster", "oven")), "Breakfast",
           "Toasted sourdough, smashed avocado and soft-boiled eggs.", (
               I(SOURDOUGH, 100, "Sourdough", "sourdough"), I(EGG, 2, "Eggs", "eggs"),
               I(AVOCADO, 1, "Avocado", "avocado", alt=LABNEH), I(LEMON, 10, "Lemon", "lemon")), (
               S("Lower the eggs into boiling water and cook.", 6),
               S("Toast the sourdough slices until golden."),
               S("Mash the avocado (or spread the labneh) with a squeeze of lemon and a pinch of salt."),
               S("Spread on the toast, halve the eggs and set them on top.")),
           T("fresh", "anti_inflammatory")),
    Recipe("mug-omelette", "Microwave spinach mushroom omelette", "breakfast", 5, ("microwave",), "Breakfast",
           "A two-minute omelette in a mug with spinach, mushrooms and cheddar.", (
               I(EGG, 2, "Eggs", "eggs"), I(SPINACH, 20, "Baby spinach", "spinach"),
               I(MUSHROOM, 40, "Mushrooms", "mushrooms"), I(CHEDDAR, 20, "Cheddar", "cheddar"), I(MILK, 20, "Milk", "milk")), (
               S("Whisk the eggs and milk in a large microwave-safe mug."),
               S("Stir in chopped spinach, sliced mushrooms and grated cheddar."),
               S("Microwave on high, stirring once halfway.", 2),
               S("Rest for a minute before eating; it keeps cooking.")),
           T("one_pan", "family")),
    Recipe("pb-smoothie", "Peanut butter banana smoothie", "breakfast", 5, ("blender",), "Breakfast",
           "Banana, peanut butter and oats blended with almond milk.", (
               I(BANANA, 120, "Banana", "banana"), I(PB, 20, "Peanut butter", "peanut butter"),
               I(OATS, 30, "Rolled oats", "oats"), I(ALMOND_MILK, 200, "Almond milk", "almond milk")), (
               S("Add the almond milk, oats, banana and peanut butter to the blender."),
               S("Blend until completely smooth.", 1),
               S("Pour and drink straight away, or chill for later.")),
           T("fiber", "family")),
    Recipe("pb-banana-toast", "Peanut butter banana toast", "breakfast", 5, (("toaster", "oven"),), "Breakfast",
           "Wholemeal toast with peanut butter, sliced banana and honey.", (
               I(WHOLEMEAL, 70, "Wholemeal bread", "wholemeal bread"), I(PB, 20, "Peanut butter", "peanut butter"),
               I(BANANA, 100, "Banana", "banana"), I(HONEY, 5, "Honey", "honey")), (
               S("Toast the bread."),
               S("Spread with peanut butter while it's warm."),
               S("Top with sliced banana and a little honey.")),
           T("family", "fiber")),
    Recipe("tofu-scramble", "Cumin tofu scramble with kale", "breakfast", 15, ("stovetop",), "Breakfast",
           "Crumbled tofu fried with cumin, onion and kale.", (
               I(TOFU, 150, "Firm tofu", "tofu"), I(KALE, 40, "Kale", "kale"), I(ONION, 40, "Red onion", "onion"),
               I(CUMIN, 2, "Cumin", "cumin"), I(OLIVE_OIL, 10, "Olive oil", "olive oil"),
               I(WHOLEMEAL, 70, "Wholemeal bread", "wholemeal bread")), (
               S("Soften the chopped onion in olive oil.", 4),
               S("Crumble in the tofu with cumin, salt and pepper; fry until lightly golden.", 5),
               S("Stir in the kale until it wilts.", 2),
               S("Serve with toast.")),
           T("one_pan", "fiber", "anti_inflammatory")),
    # ------------------------------------------------------------ mains
    Recipe("shakshuka", "Shakshuka with feta and pita", "main", 25, ("stovetop",), "Levantine",
           "Eggs poached in a spiced tomato and pepper sauce.", (
               I(EGG, 2, "Eggs", "eggs"), I(CHOPPED, 200, "Chopped tomatoes", "chopped tomatoes"),
               I(ONION, 50, "Red onion", "onion"), I(PEPPER, 0.5, "Bell pepper", "bell pepper"),
               I(GARLIC, 5, "Garlic", "garlic"), I(CUMIN, 2, "Cumin", "cumin"), I(PAPRIKA, 2, "Paprika", "paprika"),
               I(OLIVE_OIL, 10, "Olive oil", "olive oil"), I(FETA, 30, "Feta", "feta"), I(PITA, 1, "Pita bread", "pita")), (
               S("Soften the onion and pepper in olive oil in a wide pan.", 6),
               S("Add garlic, cumin and paprika; stir for a minute."),
               S("Pour in the chopped tomatoes and simmer until thick.", 8),
               S("Make wells, crack in the eggs, cover and cook until the whites set.", 6),
               S("Crumble over the feta and serve with warm pita.")),
           T("one_pan", "comfort", "mediterranean")),
    Recipe("chicken-rice-bowl", "Garlic soy chicken rice bowl", "main", 30, ("stovetop",), "Asian",
           "Seared chicken breast, basmati and broccoli with a soy-garlic glaze.", (
               I(CHICKEN, 150, "Chicken breast", "chicken breast"), I(RICE, 75, "Basmati rice", "basmati rice"),
               I(BROCCOLI, 100, "Broccoli", "broccoli"), I(GARLIC, 5, "Garlic", "garlic"),
               I(SOY, 15, "Soy sauce", "soy sauce"), I(OLIVE_OIL, 10, "Olive oil", "olive oil")), (
               S("Rinse the rice and simmer it covered.", 15),
               S("Slice the chicken and sear in oil until cooked through.", 7),
               S("Add the broccoli and a splash of water; cover to steam.", 3),
               S("Stir in garlic and soy sauce until glossy, then serve over the rice.")),
           T("takeout", "family")),
    Recipe("airfryer-thighs", "Air-fried paprika chicken with sweet potato", "main", 35, ("air_fryer",), "Modern",
           "Crispy chicken thighs, sweet potato wedges and a lemony spinach salad.", (
               I(THIGH, 180, "Chicken thighs", "chicken thigh"), I(SWEETPOT, 200, "Sweet potato", "sweet potato"),
               I(SPINACH, 40, "Baby spinach", "spinach"), I(LEMON, 25, "Lemon", "lemon"),
               I(OLIVE_OIL, 10, "Olive oil", "olive oil"), I(PAPRIKA, 2, "Paprika", "paprika")), (
               S("Cut the sweet potato into wedges and toss with half the oil and a pinch of salt."),
               S("Rub the chicken with paprika, salt and the rest of the oil."),
               S("Air-fry the wedges and chicken together at 200°C, shaking halfway.", 22),
               S("Toss the spinach with lemon juice and serve alongside.")),
           T("family", "comfort")),
    Recipe("bolognese", "Spaghetti bolognese", "main", 40, ("stovetop",), "Italian",
           "Slow-simmered beef and tomato sauce over spaghetti.", (
               I(BEEF, 125, "Beef mince", "beef mince"), I(SPAGHETTI, 100, "Spaghetti", "spaghetti"),
               I(PASSATA, 150, "Tomato passata", "passata"), I(ONION, 50, "Red onion", "onion"),
               I(GARLIC, 5, "Garlic", "garlic"), I(CARROT, 50, "Carrot", "carrot"),
               I(PARM, 10, "Parmesan", "parmesan"), I(OLIVE_OIL, 10, "Olive oil", "olive oil")), (
               S("Soften the finely chopped onion, carrot and garlic in olive oil.", 6),
               S("Brown the beef mince, breaking it up.", 6),
               S("Add the passata and simmer gently.", 20),
               S("Cook the spaghetti in salted water.", 10),
               S("Toss the pasta with the sauce and finish with parmesan.")),
           T("family", "comfort")),
    Recipe("lentil-dal", "Coconut red lentil dal", "main", 30, (("stovetop", "slow_cooker"),), "Indian",
           "Creamy red lentils with ginger and cumin, served with basmati.", (
               I(LENTILS, 80, "Red lentils", "red lentils"), I(COCONUT, 100, "Coconut milk", "coconut milk"),
               I(CHOPPED, 100, "Chopped tomatoes", "chopped tomatoes"), I(ONION, 50, "Red onion", "onion"),
               I(GARLIC, 5, "Garlic", "garlic"), I(GINGER, 5, "Ginger", "ginger"), I(CUMIN, 3, "Cumin", "cumin"),
               I(RICE, 60, "Basmati rice", "basmati rice")), (
               S("Fry the onion, garlic, ginger and cumin until fragrant.", 5),
               S("Add the rinsed lentils, tomatoes, coconut milk and 300 ml water per 2 servings."),
               S("Simmer until the lentils collapse (or 4 hours on low in a slow cooker).", 20),
               S("Cook the rice while the dal simmers.", 15),
               S("Season with salt and serve the dal over rice.")),
           T("fiber", "anti_inflammatory", "comfort")),
    Recipe("chickpea-curry", "Chickpea and spinach curry", "main", 25, ("stovetop",), "Indian",
           "Chickpeas and spinach in a spiced coconut tomato sauce with brown rice.", (
               I(CHICKPEAS, 200, "Chickpeas", "chickpeas"), I(SPINACH, 50, "Baby spinach", "spinach"),
               I(COCONUT, 100, "Coconut milk", "coconut milk"), I(CHOPPED, 100, "Chopped tomatoes", "chopped tomatoes"),
               I(ONION, 50, "Red onion", "onion"), I(GINGER, 5, "Ginger", "ginger"), I(CUMIN, 3, "Cumin", "cumin"),
               I(BROWN_RICE, 60, "Brown rice", "brown rice")), (
               S("Start the brown rice simmering.", 25),
               S("Fry the onion, ginger and cumin until soft.", 5),
               S("Add the chickpeas, tomatoes and coconut milk; simmer.", 10),
               S("Stir in the spinach until wilted and serve with the rice.")),
           T("one_pan", "fiber", "anti_inflammatory", "takeout")),
    Recipe("halloumi-traybake", "Halloumi and vegetable traybake", "main", 35, ("oven",), "Mediterranean",
           "Roasted halloumi, peppers, zucchini and cherry tomatoes over quinoa.", (
               I(HALLOUMI, 100, "Halloumi", "halloumi"), I(ZUCCHINI, 150, "Zucchini", "zucchini"),
               I(PEPPER, 1, "Bell pepper", "bell pepper"), I(ONION, 50, "Red onion", "onion"),
               I(CHERRY, 100, "Cherry tomatoes", "cherry tomatoes"), I(OLIVE_OIL, 15, "Olive oil", "olive oil"),
               I(QUINOA, 60, "Quinoa", "quinoa")), (
               S("Heat the oven to 220°C."),
               S("Toss the chopped vegetables with olive oil and salt on a tray; roast.", 15),
               S("Add the sliced halloumi and roast until golden.", 12),
               S("Meanwhile simmer the quinoa.", 15),
               S("Serve the tray over the quinoa.")),
           T("one_pan", "fresh", "mediterranean")),
    Recipe("tuna-pasta", "Lemony tuna pasta salad", "main", 20, ("stovetop",), "Mediterranean",
           "Penne with tuna, cherry tomatoes, cucumber and a yogurt-lemon dressing.", (
               I(PENNE, 90, "Penne", "penne"), I(TUNA, 80, "Tuna", "tuna"), I(CHERRY, 80, "Cherry tomatoes", "cherry tomatoes"),
               I(CUCUMBER, 80, "Cucumber", "cucumber"), I(YOG, 30, "Greek yogurt", "greek yogurt"), I(LEMON, 15, "Lemon", "lemon")), (
               S("Cook the penne in salted water, then rinse under cold water.", 10),
               S("Mix the yogurt with lemon juice, salt and pepper."),
               S("Toss the pasta with tuna, halved tomatoes, diced cucumber and the dressing.")),
           T("fresh", "mediterranean")),
    Recipe("salmon-traybake", "Roast salmon with potatoes and broccoli", "main", 35, ("oven",), "Modern",
           "Salmon fillet roasted with baby potatoes and broccoli.", (
               I(SALMON, 130, "Salmon fillet", "salmon", alt=CHICKEN), I(POTATO, 200, "Potatoes", "potatoes"),
               I(BROCCOLI, 100, "Broccoli", "broccoli"), I(LEMON, 20, "Lemon", "lemon"),
               I(OLIVE_OIL, 10, "Olive oil", "olive oil")), (
               S("Heat the oven to 200°C. Halve the potatoes, toss with oil and roast.", 15),
               S("Add the broccoli and the fish (or chicken) to the tray with lemon slices."),
               S("Roast until the fish flakes, or the chicken is cooked through.", 15),
               S("Squeeze over the roasted lemon and serve.")),
           T("one_pan", "anti_inflammatory", "fresh")),
    Recipe("shrimp-noodles", "Ginger shrimp rice noodles", "main", 20, ("stovetop",), "Asian",
           "Quick stir-fried shrimp with rice noodles, peppers and carrot.", (
               I(SHRIMP, 120, "Shrimp", "shrimp"), I(NOODLES, 80, "Rice noodles", "rice noodles"),
               I(PEPPER, 0.5, "Bell pepper", "bell pepper"), I(CARROT, 50, "Carrot", "carrot"),
               I(SOY, 15, "Soy sauce", "soy sauce"), I(GINGER, 5, "Ginger", "ginger"), I(SUN_OIL, 10, "Sunflower oil", "sunflower oil")), (
               S("Soak the rice noodles in hot water until soft, then drain.", 8),
               S("Stir-fry the shrimp with ginger in hot oil until pink.", 3),
               S("Add sliced pepper and carrot; toss for a couple of minutes.", 2),
               S("Add the noodles and soy sauce and toss until hot.")),
           T("takeout", "one_pan")),
    Recipe("beef-wraps", "Smoky beef and pepper wraps", "main", 20, ("stovetop",), "Mexican",
           "Paprika beef, peppers and cheddar rolled in whole wheat wraps.", (
               I(BEEF, 100, "Beef mince", "beef mince"), I(WRAPS, 2, "Tortilla wraps", "tortilla wraps"),
               I(PEPPER, 0.5, "Bell pepper", "bell pepper"), I(ONION, 40, "Red onion", "onion"),
               I(LETTUCE, 0.25, "Romaine lettuce", "lettuce"), I(CHEDDAR, 30, "Cheddar", "cheddar"),
               I(PAPRIKA, 2, "Paprika", "paprika")), (
               S("Brown the beef with the onion and pepper.", 8),
               S("Season with paprika and salt."),
               S("Warm the wraps in a dry pan.", 1),
               S("Fill with beef, shredded lettuce and grated cheddar, then roll.")),
           T("mexican", "family", "takeout")),
    Recipe("burrito-bowl", "Chicken burrito bowl", "main", 25, ("stovetop",), "Mexican",
           "Paprika chicken, rice, sweet corn, tomatoes and coriander.", (
               I(CHICKEN, 140, "Chicken breast", "chicken breast"), I(RICE, 70, "Basmati rice", "basmati rice"),
               I(CORN, 60, "Sweet corn", "sweet corn"), I(TOMATO, 80, "Tomatoes", "tomatoes"),
               I(CORIANDER, 5, "Coriander", "coriander"), I(LEMON, 10, "Lemon", "lemon"),
               I(PAPRIKA, 2, "Paprika", "paprika"), I(OLIVE_OIL, 10, "Olive oil", "olive oil")), (
               S("Simmer the rice.", 15),
               S("Season the chicken with paprika and salt; sear and slice.", 8),
               S("Dice the tomatoes and mix with coriander and lemon juice."),
               S("Build bowls of rice, chicken, corn and the tomato salsa.")),
           T("mexican", "takeout", "family")),
    Recipe("veggie-quesadilla", "Corn and pepper quesadillas", "main", 15, ("stovetop",), "Mexican",
           "Crisp wraps filled with cheddar, sweet corn and peppers.", (
               I(WRAPS, 2, "Tortilla wraps", "tortilla wraps"), I(CHEDDAR, 50, "Cheddar", "cheddar"),
               I(CORN, 50, "Sweet corn", "sweet corn"), I(PEPPER, 0.5, "Bell pepper", "bell pepper"),
               I(CHERRY, 60, "Cherry tomatoes", "cherry tomatoes")), (
               S("Scatter cheddar, corn and diced pepper over half of each wrap; fold."),
               S("Toast in a dry pan until crisp on both sides and the cheese melts.", 4),
               S("Cut into wedges and serve with halved cherry tomatoes.")),
           T("mexican", "family", "comfort")),
    Recipe("lamb-stew", "Lamb, chickpea and potato stew", "main", 60, (("stovetop", "slow_cooker"),), "Levantine",
           "Cumin-spiced lamb stew with chickpeas, carrots and potatoes.", (
               I(LAMB, 125, "Lamb cubes", "lamb"), I(CHICKPEAS, 100, "Chickpeas", "chickpeas"),
               I(CHOPPED, 150, "Chopped tomatoes", "chopped tomatoes"), I(ONION, 60, "Red onion", "onion"),
               I(CARROT, 60, "Carrot", "carrot"), I(CUMIN, 3, "Cumin", "cumin"), I(POTATO, 150, "Potatoes", "potatoes")), (
               S("Brown the lamb in batches and set aside.", 8),
               S("Soften the onion and carrot with cumin.", 5),
               S("Add the lamb, potatoes, chickpeas, tomatoes and water to cover."),
               S("Simmer covered until tender (or 6 hours on low in a slow cooker).", 45),
               S("Season and serve.")),
           T("comfort", "family", "fiber")),
    Recipe("slowcooker-chicken-curry", "Slow cooker chicken and chickpea curry", "main", 20, ("slow_cooker",), "Indian",
           "Tender chicken thighs, chickpeas and coconut, left to cook all day.", (
               I(THIGH, 150, "Chicken thighs", "chicken thigh"), I(CHICKPEAS, 100, "Chickpeas", "chickpeas"),
               I(COCONUT, 100, "Coconut milk", "coconut milk"), I(CHOPPED, 100, "Chopped tomatoes", "chopped tomatoes"),
               I(ONION, 50, "Red onion", "onion"), I(GINGER, 5, "Ginger", "ginger"), I(CUMIN, 3, "Cumin", "cumin"),
               I(RICE, 60, "Basmati rice", "basmati rice")), (
               S("Put everything except the rice into the slow cooker and stir."),
               S("Cook on low until the chicken pulls apart.", 360),
               S("Cook the rice shortly before serving.", 15),
               S("Shred the chicken into the sauce and serve over rice.")),
           T("comfort", "takeout", "family")),
    Recipe("gf-mushroom-pasta", "Creamy mushroom and spinach fusilli", "main", 20, ("stovetop",), "Italian",
           "Gluten-free fusilli in a garlic cream sauce with mushrooms and spinach.", (
               I(GF_PASTA, 90, "Gluten-free fusilli", "gluten free pasta"), I(MUSHROOM, 100, "Mushrooms", "mushrooms"),
               I(SPINACH, 40, "Baby spinach", "spinach"), I(CREAM, 60, "Cooking cream", "cooking cream"),
               I(GARLIC, 5, "Garlic", "garlic"), I(PARM, 10, "Parmesan", "parmesan")), (
               S("Cook the fusilli in salted water.", 10),
               S("Fry the sliced mushrooms until golden, then add garlic.", 6),
               S("Pour in the cream, add the spinach and let it wilt.", 2),
               S("Toss with the pasta and parmesan.")),
           T("comfort", "family")),
    Recipe("quinoa-chicken-salad", "Quinoa chicken salad with feta", "main", 25, ("stovetop",), "Mediterranean",
           "Warm quinoa, grilled chicken, cucumber, tomatoes, feta and parsley.", (
               I(QUINOA, 60, "Quinoa", "quinoa"), I(CHICKEN, 120, "Chicken breast", "chicken breast"),
               I(CUCUMBER, 80, "Cucumber", "cucumber"), I(CHERRY, 80, "Cherry tomatoes", "cherry tomatoes"),
               I(FETA, 30, "Feta", "feta"), I(LEMON, 15, "Lemon", "lemon"), I(OLIVE_OIL, 10, "Olive oil", "olive oil"),
               I(PARSLEY, 10, "Parsley", "parsley")), (
               S("Simmer the quinoa until the grains open.", 15),
               S("Season and pan-grill the chicken, then slice.", 8),
               S("Chop the cucumber, tomatoes and parsley; whisk lemon with olive oil."),
               S("Toss everything together and crumble over the feta.")),
           T("fresh", "mediterranean", "anti_inflammatory")),
    Recipe("tuna-potatoes", "Microwave jacket potato with tuna", "main", 15, ("microwave",), "Modern",
           "Fluffy jacket potatoes with tuna, yogurt and cheddar.", (
               I(POTATO, 300, "Potatoes", "potatoes"), I(TUNA, 80, "Tuna", "tuna"),
               I(YOG, 50, "Greek yogurt", "greek yogurt"), I(CHEDDAR, 20, "Cheddar", "cheddar")), (
               S("Prick the potatoes and microwave on high, turning halfway, until soft.", 10),
               S("Mix the tuna with the yogurt, salt and pepper."),
               S("Split the potatoes, fill with the tuna and top with cheddar.")),
           T("family", "comfort")),
    Recipe("veg-fried-rice", "Vegetable egg fried rice", "main", 20, ("stovetop",), "Asian",
           "Basmati fried with eggs, peas, mixed vegetables and soy.", (
               I(RICE, 80, "Basmati rice", "basmati rice"), I(EGG, 1, "Eggs", "eggs"),
               I(FROZEN_VEG, 100, "Frozen mixed vegetables", "frozen vegetables"), I(PEAS, 40, "Peas", "peas"),
               I(SOY, 15, "Soy sauce", "soy sauce"), I(SUN_OIL, 10, "Sunflower oil", "sunflower oil")), (
               S("Cook the rice and spread it out to cool (day-old rice is best).", 15),
               S("Scramble the eggs in hot oil and set aside.", 2),
               S("Fry the vegetables and peas, then add the rice.", 5),
               S("Stir in soy sauce and the eggs.")),
           T("takeout", "one_pan", "family")),
    Recipe("tofu-stir-fry", "Crispy tofu and broccoli stir-fry", "main", 25, ("stovetop",), "Asian",
           "Golden tofu, broccoli and peppers in a ginger soy glaze over rice.", (
               I(TOFU, 150, "Firm tofu", "tofu"), I(BROCCOLI, 100, "Broccoli", "broccoli"),
               I(PEPPER, 0.5, "Bell pepper", "bell pepper"), I(GINGER, 5, "Ginger", "ginger"),
               I(SOY, 15, "Soy sauce", "soy sauce"), I(SUN_OIL, 15, "Sunflower oil", "sunflower oil"),
               I(BROWN_RICE, 60, "Brown rice", "brown rice")), (
               S("Simmer the brown rice.", 25),
               S("Cube the tofu and fry in hot oil until crisp on all sides.", 8),
               S("Add the broccoli, pepper and ginger; stir-fry.", 4),
               S("Add the soy sauce, toss to glaze and serve over rice.")),
           T("takeout", "fiber", "anti_inflammatory")),
    Recipe("eggplant-tahini", "Roast eggplant with tahini and chickpeas", "main", 40, ("oven",), "Levantine",
           "Silky roast eggplant, crisp chickpeas and lemon tahini with pita.", (
               I(EGGPLANT, 250, "Eggplant", "eggplant"), I(CHICKPEAS, 120, "Chickpeas", "chickpeas"),
               I(TAHINI, 20, "Tahini", "tahini"), I(LEMON, 15, "Lemon", "lemon"),
               I(OLIVE_OIL, 15, "Olive oil", "olive oil"), I(PARSLEY, 10, "Parsley", "parsley"),
               I(PITA, 1, "Pita bread", "pita")), (
               S("Heat the oven to 220°C. Halve the eggplants, score, brush with oil and roast.", 30),
               S("Roast the drained chickpeas on the same tray for the last 15 minutes."),
               S("Whisk tahini with lemon juice, salt and water until pourable."),
               S("Top the eggplant with chickpeas, tahini and parsley; serve with pita.")),
           T("mediterranean", "anti_inflammatory", "fiber")),
    # ------------------------------------------------------------ snacks
    Recipe("hummus-sticks", "Hummus with veggie sticks", "snack", 10, ("blender",), "Snack",
           "Smooth homemade hummus with carrot and cucumber sticks.", (
               I(CHICKPEAS, 80, "Chickpeas", "chickpeas"), I(TAHINI, 10, "Tahini", "tahini"),
               I(LEMON, 10, "Lemon", "lemon"), I(GARLIC, 2, "Garlic", "garlic"), I(OLIVE_OIL, 5, "Olive oil", "olive oil"),
               I(CARROT, 60, "Carrot", "carrot"), I(CUCUMBER, 60, "Cucumber", "cucumber")), (
               S("Blend the chickpeas, tahini, lemon, garlic and a splash of water until smooth.", 2),
               S("Drizzle with olive oil."),
               S("Cut the carrot and cucumber into sticks for dipping.")),
           T("fiber", "fresh", "mediterranean")),
    Recipe("berry-yogurt-pot", "Strawberry yogurt pot", "snack", 5, (), "Snack",
           "Plain yogurt with strawberries, oats and a little honey.", (
               I(PLAIN_YOG, 125, "Plain yogurt", "plain yogurt"), I(STRAWB, 60, "Strawberries", "strawberries"),
               I(OATS, 15, "Rolled oats", "oats"), I(HONEY, 5, "Honey", "honey")), (
               S("Spoon the yogurt into a glass."),
               S("Top with sliced strawberries, oats and honey.")),
           T("fresh", "family")),
    Recipe("crispy-chickpeas", "Crispy spiced chickpeas", "snack", 20, (("air_fryer", "oven"),), "Snack",
           "Crunchy paprika chickpeas for snacking.", (
               I(CHICKPEAS, 80, "Chickpeas", "chickpeas"), I(OLIVE_OIL, 5, "Olive oil", "olive oil"),
               I(PAPRIKA, 1, "Paprika", "paprika")), (
               S("Drain and dry the chickpeas well."),
               S("Toss with oil, paprika and salt."),
               S("Air-fry at 200°C (or roast at 220°C), shaking once, until crunchy.", 15)),
           T("fiber")),
    Recipe("apple-pb", "Apple slices with peanut butter", "snack", 3, (), "Snack",
           "Crisp apple wedges with a spoon of peanut butter.", (
               I(APPLE, 150, "Apple", "apples"), I(PB, 20, "Peanut butter", "peanut butter")), (
               S("Core and slice the apple."),
               S("Serve with peanut butter for dipping.")),
           T("family", "fiber")),
    Recipe("olive-feta-plate", "Olives, feta and cucumber plate", "snack", 5, (), "Snack",
           "A Mediterranean nibble plate with pita.", (
               I(OLIVES, 40, "Green olives", "olives"), I(FETA, 30, "Feta", "feta"),
               I(CUCUMBER, 60, "Cucumber", "cucumber"), I(PITA, 0.5, "Pita bread", "pita")), (
               S("Slice the cucumber and cube the feta."),
               S("Arrange with the olives and warm pita.")),
           T("mediterranean", "fresh")),
)

BY_ID = {r.id: r for r in RECIPES}
ALL_PRODUCT_IDS = sorted({i.product_id for r in RECIPES for i in r.ingredients} | {i.alt for r in RECIPES for i in r.ingredients if i.alt})
