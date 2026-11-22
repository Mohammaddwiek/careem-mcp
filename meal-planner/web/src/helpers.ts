import type { NeedRow } from './api'

export interface ShopLine { packs: number; skip: boolean }

export function lineFor(n: NeedRow, lines: Record<number, ShopLine>): ShopLine {
  return lines[n.product.id] ?? { packs: n.packs, skip: n.match.status === 'not_found' || !n.product.available }
}

export const ALLERGEN_LABELS: Record<string, string> = {
  gluten: 'Gluten', dairy: 'Dairy', egg: 'Eggs', peanuts: 'Peanuts', tree_nuts: 'Tree nuts',
  soy: 'Soy', fish: 'Fish', shellfish: 'Shellfish', sesame: 'Sesame',
}
