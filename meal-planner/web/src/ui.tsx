import {
  Apple, Coffee, Croissant, CupSoda, Drumstick, Info, Milk, Minus, Package, Plus, Snowflake, Tag, TriangleAlert, Wheat,
  type LucideIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  'Dairy & Eggs': Milk,
  Bakery: Croissant,
  'Fruits & Vegetables': Apple,
  'Meat & Seafood': Drumstick,
  'Coffee & Tea': Coffee,
  Pantry: Wheat,
  Frozen: Snowflake,
  Beverages: CupSoda,
}

export function CategoryIcon({ category, size = 20 }: { category?: string; size?: number }) {
  const Icon = (category && CATEGORY_ICONS[category]) || Package
  return (
    <span className="cat-icon" aria-hidden="true">
      <Icon size={size} strokeWidth={1.8} />
    </span>
  )
}

export function DealBadge({ pct }: { pct: number }) {
  if (!pct) return null
  return (
    <span className="badge badge-deal">
      <Tag size={13} aria-hidden="true" /> {pct}% off
    </span>
  )
}

export function Banner({ tone = 'info', children, action }: { tone?: 'info' | 'error' | 'ai'; children: ReactNode; action?: ReactNode }) {
  const Icon = tone === 'error' ? TriangleAlert : Info
  return (
    <div className={`banner banner-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <Icon size={18} aria-hidden="true" className="banner-icon" />
      <div className="banner-body">{children}</div>
      {action}
    </div>
  )
}

export function QtyStepper({ value, min = 0, max = 50, onChange, label, busy }: {
  value: number; min?: number; max?: number; onChange: (n: number) => void; label: string; busy?: boolean
}) {
  return (
    <div className="qty" role="group" aria-label={label} aria-busy={busy || undefined}>
      {/* stays focusable while saving (disabling would drop keyboard focus); extra presses are ignored */}
      <button type="button" className="qty-btn" onClick={() => !busy && onChange(value - 1)} disabled={value <= min}
        aria-label={`Fewer ${label}`}>
        <Minus size={16} aria-hidden="true" />
      </button>
      <output className="qty-value num" aria-live="polite">{value}</output>
      <button type="button" className="qty-btn" onClick={() => !busy && onChange(value + 1)} disabled={value >= max}
        aria-label={`More ${label}`}>
        <Plus size={16} aria-hidden="true" />
      </button>
    </div>
  )
}

export function Segmented<T extends string>({ value, options, onChange, label }: {
  value: T; options: { value: T; label: string; icon?: LucideIcon }[]; onChange: (v: T) => void; label: string
}) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value}
          className={value === o.value ? 'seg on' : 'seg'} onClick={() => onChange(o.value)}>
          {o.icon && <o.icon size={16} aria-hidden="true" />}
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function ToggleChip({ on, onClick, children, tone = 'brand' }: {
  on: boolean; onClick: () => void; children: ReactNode; tone?: 'brand' | 'danger'
}) {
  return (
    <button type="button" aria-pressed={on} className={`chip chip-${tone}${on ? ' on' : ''}`} onClick={onClick}>
      {children}
    </button>
  )
}
