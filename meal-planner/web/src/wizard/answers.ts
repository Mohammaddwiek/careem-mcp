// The onboarding answers and the option lists the 10 steps offer.

export interface Answers {
  adults: number
  kids: number
  meals: string[]
  days: number[]
  appliances: string[]
  diets: string[] // 'none' is exclusive
  vibes: string[]
  allergens: string[] // 'none' is exclusive
  dislikes: string[]
  pantryTiles: string[]
  pantryExtra: number[] // product ids added through search
  budget: number
  notes: string
}

export const DEFAULT_ANSWERS: Answers = {
  adults: 1, kids: 0, meals: ['dinner'], days: [0, 1, 2, 3, 4], appliances: ['stovetop', 'oven'],
  diets: ['none'], vibes: [], allergens: [], dislikes: [], pantryTiles: [], pantryExtra: [], budget: 250, notes: '',
}

export const portions = (a: Pick<Answers, 'adults' | 'kids'>) => a.adults + 0.5 * a.kids
export const fmtPortions = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1))
export const plural = (n: number, one: string, many = `${one}s`) => `${fmtPortions(n)} ${n === 1 ? one : many}`

export const MEAL_OPTIONS = [
  { key: 'breakfast', label: 'Breakfast', sub: 'Quick and repeatable', tone: 'deal' },
  { key: 'lunch', label: 'Lunch', sub: 'Leftovers-friendly', tone: 'brand' },
  { key: 'dinner', label: 'Dinner', sub: 'The main event', tone: 'ai' },
  { key: 'snacks', label: 'Snacks', sub: 'Optional extras', tone: 'warm' },
] as const

export const DAY_LETTERS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
export const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export const APPLIANCE_OPTIONS = [
  { key: 'stovetop', label: 'Stovetop' },
  { key: 'oven', label: 'Oven' },
  { key: 'microwave', label: 'Microwave' },
  { key: 'air_fryer', label: 'Air fryer' },
  { key: 'toaster', label: 'Toaster' },
  { key: 'blender', label: 'Blender' },
  { key: 'slow_cooker', label: 'Slow cooker' },
] as const

export const DIET_OPTIONS = [
  { key: 'none', label: 'No restrictions', sub: 'I eat everything' },
  { key: 'vegetarian', label: 'Vegetarian', sub: 'No meat or fish' },
  { key: 'vegan', label: 'Vegan', sub: 'Plants only' },
  { key: 'pescatarian', label: 'Pescatarian', sub: 'Fish, no meat' },
  { key: 'keto', label: 'Keto', sub: 'Under 20 g carbs a serving' },
  { key: 'high_protein', label: 'High-protein', sub: 'Protein first' },
  { key: 'glp1', label: 'GLP-1 friendly', sub: 'Protein, fiber, smaller portions' },
  { key: 'anti_inflammatory', label: 'Anti-inflammatory', sub: 'Fish, greens, legumes' },
  { key: 'mediterranean', label: 'Mediterranean', sub: 'Olive oil, veg, grains' },
  { key: 'mexican', label: 'Mexican', sub: 'Bowls, wraps, salsa' },
] as const
export const STRICT_DIETS = ['vegetarian', 'vegan', 'pescatarian', 'keto']

export const VIBE_OPTIONS = [
  { key: 'quick', label: 'Quick and easy', sub: 'About 20 minutes' },
  { key: 'one_pan', label: 'One pan', sub: 'Minimal cleanup' },
  { key: 'batch', label: 'Batch cook', sub: 'Cook once, eat twice' },
  { key: 'family', label: 'Family favorites', sub: 'Everyone eats it' },
  { key: 'comfort', label: 'Comfort classics', sub: 'Warm and filling' },
  { key: 'fresh', label: 'Fresh and light', sub: 'Salads and bright flavors' },
  { key: 'fiber', label: 'Fiber-forward', sub: 'Beans, grains, veg' },
  { key: 'takeout', label: 'Takeout at home', sub: 'Bowls, curries, stir-fries' },
] as const

export const ALLERGY_OPTIONS = [
  { key: 'none', label: 'No allergies', emoji: '✅' },
  { key: 'peanuts', label: 'Peanuts', emoji: '🥜' },
  { key: 'tree_nuts', label: 'Tree nuts', emoji: '🌰' },
  { key: 'dairy', label: 'Dairy', emoji: '🥛' },
  { key: 'egg', label: 'Eggs', emoji: '🥚' },
  { key: 'gluten', label: 'Gluten (wheat)', emoji: '🌾' },
  { key: 'soy', label: 'Soy', emoji: '🫘' },
  { key: 'shellfish', label: 'Shellfish', emoji: '🦐' },
  { key: 'fish', label: 'Fish', emoji: '🐟' },
  { key: 'sesame', label: 'Sesame', emoji: '🫓' },
] as const

export const DISLIKE_OPTIONS: { label: string; emoji: string }[] = [
  { label: 'Beef', emoji: '🥩' }, { label: 'Bell peppers', emoji: '🫑' }, { label: 'Mushroom', emoji: '🍄' },
  { label: 'Pork', emoji: '🥓' }, { label: 'Tomatoes', emoji: '🍅' }, { label: 'Eggplant', emoji: '🍆' },
  { label: 'Avocado', emoji: '🥑' }, { label: 'Broccoli', emoji: '🥦' }, { label: 'Lamb', emoji: '🍖' },
  { label: 'Shellfish', emoji: '🦀' }, { label: 'Chicken', emoji: '🍗' }, { label: 'Cilantro', emoji: '🌿' },
  { label: 'Turkey', emoji: '🦃' }, { label: 'Salmon', emoji: '🍣' }, { label: 'Shrimp', emoji: '🦐' },
  { label: 'Pickles', emoji: '🥒' }, { label: 'Fish', emoji: '🐟' }, { label: 'Honey', emoji: '🍯' },
  { label: 'Olives', emoji: '🫒' }, { label: 'Tuna', emoji: '🐠' }, { label: 'Corn', emoji: '🌽' },
  { label: 'Tofu', emoji: '🧈' }, { label: 'Kale', emoji: '🥬' },
]

export type PantryCategory = 'Fresh' | 'Meat' | 'Fridge' | 'Pantry'
export const PANTRY_TILES: { key: string; label: string; emoji: string; cat: PantryCategory; ids: number[] }[] = [
  { key: 'eggs', label: 'Eggs', emoji: '🥚', cat: 'Fridge', ids: [4000102] },
  { key: 'milk', label: 'Milk', emoji: '🥛', cat: 'Fridge', ids: [4000101, 4000110] },
  { key: 'bananas', label: 'Bananas', emoji: '🍌', cat: 'Fresh', ids: [4000104] },
  { key: 'bread', label: 'Bread', emoji: '🍞', cat: 'Pantry', ids: [4000103, 4000119] },
  { key: 'chicken', label: 'Chicken breast', emoji: '🍗', cat: 'Meat', ids: [4000143] },
  { key: 'apples', label: 'Apples', emoji: '🍎', cat: 'Fresh', ids: [4000123] },
  { key: 'cheddar', label: 'Cheddar', emoji: '🧀', cat: 'Fridge', ids: [4000112] },
  { key: 'potatoes', label: 'Potatoes', emoji: '🥔', cat: 'Fresh', ids: [4000131] },
  { key: 'onions', label: 'Onions', emoji: '🧅', cat: 'Fresh', ids: [4000129] },
  { key: 'tomatoes', label: 'Tomatoes', emoji: '🍅', cat: 'Fresh', ids: [4000126] },
  { key: 'yogurt', label: 'Plain yogurt', emoji: '🥣', cat: 'Fridge', ids: [4000182] },
  { key: 'rice', label: 'Rice', emoji: '🍚', cat: 'Pantry', ids: [4000152, 4000153] },
  { key: 'pasta', label: 'Pasta', emoji: '🍝', cat: 'Pantry', ids: [4000156, 4000157] },
  { key: 'beef', label: 'Ground beef', emoji: '🥩', cat: 'Meat', ids: [4000146] },
  { key: 'butter', label: 'Butter', emoji: '🧈', cat: 'Fridge', ids: [4000117] },
  { key: 'strawberries', label: 'Strawberries', emoji: '🍓', cat: 'Fresh', ids: [4000181] },
]

export function pantryIds(a: Answers): number[] {
  const tiles = PANTRY_TILES.filter((t) => a.pantryTiles.includes(t.key)).flatMap((t) => t.ids)
  return [...new Set([...tiles, ...a.pantryExtra])]
}

/** The body the backend's /api/plan and /api/estimate take. */
export function planBody(a: Answers, extra: Record<string, unknown> = {}) {
  return {
    adults: a.adults, kids: a.kids, meals: a.meals, days: a.days, appliances: a.appliances,
    diets: a.diets.filter((d) => d !== 'none'), vibes: a.vibes, allergens: a.allergens.filter((x) => x !== 'none'),
    dislikes: a.dislikes, pantry: pantryIds(a), budget: a.budget, notes: a.notes, ...extra,
  }
}
