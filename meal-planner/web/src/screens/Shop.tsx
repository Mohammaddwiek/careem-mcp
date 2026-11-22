import { Check, CircleCheck, ShoppingBasket, Sparkles, TriangleAlert } from 'lucide-react'
import { aed, type Plan } from '../api'
import { lineFor, type ShopLine } from '../helpers'
import { Banner, CategoryIcon, DealBadge, QtyStepper } from '../ui'

interface Props {
  plan: Plan
  lines: Record<number, ShopLine>
  setLine: (id: number, l: ShopLine) => void
  serviceable: boolean
  busy: boolean
  onBack: () => void
  onAddToCart: () => void
}

function amountText(n: { amount: number; amount_unit: string }) {
  const u = n.amount_unit
  if (u === 'pcs') return `${n.amount} ${n.amount === 1 ? 'piece' : 'pieces'}`
  if (n.amount >= 1000) return `${(n.amount / 1000).toFixed(n.amount % 1000 ? 1 : 0)} ${u === 'g' ? 'kg' : 'L'}`
  return `${Math.round(n.amount)} ${u}`
}

export function Shop({ plan, lines, setLine, serviceable, busy, onBack, onAddToCart }: Props) {
  const chosen = plan.need.filter((n) => !lineFor(n, lines).skip)
  const items = chosen.reduce((s, n) => s + lineFor(n, lines).packs, 0)
  const estimate = chosen.reduce((s, n) => s + lineFor(n, lines).packs * n.product.price, 0)
  const saving = chosen.reduce((s, n) => s + lineFor(n, lines).packs * ((n.product.original_price ?? n.product.price) - n.product.price), 0)
  const pct = Math.min(100, (estimate / plan.budget) * 100)
  const over = estimate > plan.budget

  return (
    <div className="shop">
      <header className="screen-head">
        <h1>What to buy</h1>
        <p className="lede">
          {plan.have.length === 0 ? 'None of the ingredients are in your pantry yet. ' :
            `${plan.have.length} ${plan.have.length === 1 ? 'ingredient is' : 'ingredients are'} already in your pantry. `}
          {plan.need.length === 1 ? 'The other one is' : `The other ${plan.need.length} are`} matched to live Careem Quik stock and prices.
        </p>
      </header>

      <div className="shop-grid">
        <section className="card have" aria-labelledby="have-h">
          <h2 id="have-h"><CircleCheck size={20} aria-hidden="true" className="have-icon" /> You have</h2>
          {plan.have.length === 0 ? (
            <p className="hint">None of these ingredients were in your pantry list.</p>
          ) : (
            <ul className="have-list">
              {plan.have.map((h) => (
                <li key={h.product.id}>
                  <Check size={16} aria-hidden="true" className="have-check" />
                  <span>
                    <span className="have-name">{h.product.name}</span>
                    <span className="hint">{amountText(h)} for {h.for.length} {h.for.length === 1 ? 'recipe' : 'recipes'}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card need" aria-labelledby="need-h">
          <h2 id="need-h"><ShoppingBasket size={20} aria-hidden="true" /> You need</h2>
          <ul className="need-list">
            {plan.need.map((n) => {
              const l = lineFor(n, lines)
              const unavailable = n.match.status === 'not_found' || !n.product.available
              return (
                <li key={n.product.id} className={l.skip ? 'need-row skipped' : 'need-row'} data-fly={n.product.id}>
                  <CategoryIcon category={n.product.category} />
                  <div className="need-main">
                    <div className="need-title">
                      <span className="need-name">{n.product.name}</span>
                      <DealBadge pct={n.product.deal_pct} />
                    </div>
                    <span className="hint">{n.product.unit} pack. Need {amountText(n)} for {n.for.join(', ')}</span>
                    {n.match.status === 'matched' && (
                      <span className="match ok"><Check size={14} aria-hidden="true" /> In stock on Careem Quik</span>
                    )}
                    {n.match.status === 'alternative' && n.match.suggested && (
                      <span className="match ai"><Sparkles size={14} aria-hidden="true" /> Careem Quik suggests {n.match.suggested.name}</span>
                    )}
                    {unavailable && (
                      <span className="match bad"><TriangleAlert size={14} aria-hidden="true" /> Not available on Careem Quik right now</span>
                    )}
                  </div>
                  <div className="need-side">
                    <span className="num need-price">{aed(l.packs * n.product.price)}</span>
                    {!unavailable && (
                      <QtyStepper label={n.product.name} value={l.skip ? 0 : l.packs} min={0} max={20}
                        onChange={(v) => setLine(n.product.id, { packs: Math.max(v, 1), skip: v === 0 })} />
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      </div>

      {!serviceable && (
        <Banner tone="error">Careem Quik doesn't deliver to the selected address. Pick another address at the top to order.</Banner>
      )}

      <div className="action-bar glass shop-bar">
        <div className="budget" aria-live="polite">
          <div className="budget-text">
            <span className="num budget-amount">{aed(estimate)}</span>
            <span className="hint">of {aed(plan.budget)} budget, {items} {items === 1 ? 'item' : 'items'}
              {saving > 0 && <>, <span className="saving">{aed(saving)} saved on deals</span></>}
            </span>
          </div>
          <div className={over ? 'meter over' : 'meter'} role="meter" aria-valuemin={0} aria-valuemax={plan.budget}
            aria-valuenow={Math.round(estimate)} aria-label="Spend against budget">
            <span style={{ width: `${pct}%` }} />
          </div>
          {over && <span className="over-text">{aed(estimate - plan.budget)} over budget. Lower some quantities or swap a meal.</span>}
        </div>
        <div className="shop-actions">
          <button type="button" className="btn btn-ghost" onClick={onBack}>Back to plan</button>
          <button type="button" className="btn btn-primary btn-lg" onClick={onAddToCart} disabled={busy || items === 0 || !serviceable}>
            {busy ? 'Adding to cart…' : `Add ${items} ${items === 1 ? 'item' : 'items'} to Careem Quik cart`}
          </button>
        </div>
      </div>
    </div>
  )
}
