import type { NeedRow } from './api'

export interface ShopLine { packs: number; skip: boolean }

export function lineFor(n: NeedRow, lines: Record<number, ShopLine>): ShopLine {
  return lines[n.product.id] ?? { packs: n.packs, skip: n.match.status === 'not_found' || !n.product.available }
}

/** The app scrolls inside the phone screen, not the window. */
export function scrollScreenTop(smooth = false) {
  const el = document.getElementById('phone-screen')
  if (el) el.scrollTo({ top: 0, behavior: smooth ? 'smooth' : 'auto' })
  else window.scrollTo({ top: 0 })
}

/** A rect relative to the phone body, which fixed layers (like the fly-to-cart chips) are positioned against. */
export function screenRect(r: DOMRect): DOMRect {
  const s = document.getElementById('phone-inner')?.getBoundingClientRect()
  return s ? new DOMRect(r.left - s.left, r.top - s.top, r.width, r.height) : r
}

export const ALLERGEN_LABELS: Record<string, string> = {
  gluten: 'Gluten', dairy: 'Dairy', egg: 'Eggs', peanuts: 'Peanuts', tree_nuts: 'Tree nuts',
  soy: 'Soy', fish: 'Fish', shellfish: 'Shellfish', sesame: 'Sesame',
}
