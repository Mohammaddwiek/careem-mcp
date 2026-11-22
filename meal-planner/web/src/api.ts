// Typed calls to the meal-planner backend (/api, proxied by Vite to FastAPI).

export interface Product {
  id: number
  name: string
  unit: string
  price: number
  original_price: number | null
  deal_pct: number
  available: boolean
  allergens: string[]
  diet: string[]
  category?: string
}

export interface Address {
  id: string
  title: string
  subTitle: string
  latitude: number
  longitude: number
  test?: boolean
}

export interface Bootstrap {
  user: { name: string; currency: string }
  addresses: Address[]
  serviceable: boolean
  service_error?: string | null
  usuals: Product[]
  deals: Product[]
  products: Product[]
  appliances: string[]
  allergens: string[]
  ai_available: boolean
}

export interface Swap { ingredient: string; from: string; to: string; reason: string }

export interface Recipe {
  id: string
  name: string
  slot: 'breakfast' | 'main' | 'snack'
  minutes: number
  cuisine: string
  blurb: string
  appliances: string[]
  servings: number
  per_serving: { kcal: number; protein: number; carbs: number; fat: number; cost: number }
  deals: string[]
  swaps: Swap[]
  ingredients: { name: string; product_id: number; product: string; amount: number; unit: string }[]
  steps: { text: string; minutes: number | null }[]
  tags: string[]
  why?: string | null
}

export interface HaveRow {
  product: Product
  term: string
  amount: number
  amount_unit: string
  for: string[]
}

export interface NeedRow extends HaveRow {
  packs: number
  line_total: number
  saving: number
  match: { status: 'matched' | 'alternative' | 'not_found'; price?: number; suggested?: Product }
}

export interface Plan {
  portions: number
  days: { day: number; name: string }[]
  meals: string[]
  schedule: { day: number; day_name: string; meal: string; recipe: string; leftovers: boolean }[]
  recipes: Recipe[]
  have: HaveRow[]
  need: NeedRow[]
  estimate: number
  saving: number
  budget: number
  over_budget: boolean
  excluded: { recipe: string; reason: string }[]
  ai?: { used: boolean; summary: string | null }
  prioritized_deals?: boolean
  missing?: string[]
  error?: string
}

export interface CartLine { item_uuid: string; catalog_item_id: string; name: string; count: number; total: number; original: number }

export interface Cart {
  basket: { id: number; count: number; lines: CartLine[] } | null
  breakdown?: { label: string; amount: number; kind: string; note?: string | null }[]
  total?: number
  saving?: number
  promo?: string | null
  payment_method?: { type: string; id?: number } | null
  merchant?: { name?: string; eta?: number }
  failed_items?: { keyword: string; requested_quantity: number; error_code: string; error_message: string; added_quantity?: number }[]
  payment_type?: string
  error?: string | null
}

export interface CheckoutResult {
  checkout?: { masterInvoiceReference: string }
  deep_link?: string
  amount?: number
  payment_type?: string
  error?: string
  message?: string
}

export interface Tracking {
  status: string
  title?: string
  service_specific_status?: string
  current_eta_minutes: number
  initial_eta_minutes: number
  merchant_name?: string
  poll_after?: number
  captain_name?: string
  error?: string
}

export class ApiError extends Error {}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init })
  } catch {
    throw new ApiError("Can't reach the planner service. Check that it's running, then try again.")
  }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : 'Something went wrong. Try again.'
    throw new ApiError(res.status === 502 ? `Careem Quik didn't answer: ${detail}` : detail)
  }
  return body as T
}

const post = <T>(path: string, body: unknown) => call<T>(path, { method: 'POST', body: JSON.stringify(body) })
const at = (a: Address) => ({ lat: a.latitude, lng: a.longitude })
const qs = (a: Address) => `lat=${a.latitude}&lng=${a.longitude}`

export const api = {
  bootstrap: (a?: Address) => call<Bootstrap>(`/api/bootstrap${a ? `?${qs(a)}` : ''}`),
  search: (q: string, a: Address) => call<{ items: Product[]; error?: string | null }>(`/api/search?q=${encodeURIComponent(q)}&${qs(a)}`),
  plan: (body: Record<string, unknown>, a: Address) => post<Plan>('/api/plan', { ...body, ...at(a) }),
  estimate: (body: Record<string, unknown>, a: Address) => post<{ estimate: number }>('/api/estimate', { ...body, ...at(a) }),
  cart: (a: Address) => call<Cart>(`/api/cart?${qs(a)}`),
  fillCart: (a: Address, mode: 'replace' | 'keep', lines: { catalog_item_id: string; keyword: string; quantity: number }[]) =>
    post<Cart>('/api/cart', { ...at(a), mode, lines }),
  updateLine: (a: Address, line: CartLine, count: number) =>
    call<Cart>('/api/cart/line', { method: 'PATCH', body: JSON.stringify({ ...at(a), item_uuid: line.item_uuid, catalog_item_id: line.catalog_item_id, count }) }),
  deleteLine: (a: Address, line: CartLine) => post<Cart>('/api/cart/line/delete', { ...at(a), item_uuid: line.item_uuid }),
  checkout: (a: Address, total: number, payment_type: string, payment_id?: number) =>
    post<CheckoutResult>('/api/checkout', { ...at(a), total_price: total, payment_type, payment_id, confirmed: true }),
  track: () => call<Tracking>('/api/track'),
}

export const aed = (n: number | undefined | null) => `AED ${(n ?? 0).toFixed(2)}`
