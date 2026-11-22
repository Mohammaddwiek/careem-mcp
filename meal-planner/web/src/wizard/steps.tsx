import {
  Check, Cookie, Dumbbell, Fish, Flame, Globe, HeartPulse, LeafyGreen, Minus, Moon, Package, Plus, Salad, Search, Soup,
  Sprout, Sun, Sunrise, Users, UtensilsCrossed, Vegan, Wheat, X, Zap, CookingPot, Sandwich, Beef, type LucideIcon,
} from 'lucide-react'
import { useEffect, useId, useMemo, useState, type ReactNode } from 'react'
import { aed, api, type Address, type Product } from '../api'
import { ApplianceArt } from './ApplianceArt'
import {
  ALLERGY_OPTIONS, APPLIANCE_OPTIONS, DAY_LETTERS, DAY_NAMES, DIET_OPTIONS, DISLIKE_OPTIONS, MEAL_OPTIONS, PANTRY_TILES,
  VIBE_OPTIONS, fmtPortions, planBody, plural, portions, type Answers, type PantryCategory,
} from './answers'

export interface StepProps {
  a: Answers
  set: (patch: Partial<Answers>) => void
  address: Address
  aiAvailable: boolean
  products: Map<number, Product>
  remember: (p: Product) => void
}

const toggle = (list: string[], key: string) => (list.includes(key) ? list.filter((k) => k !== key) : [...list, key])
/** Toggle in a list where `exclusive` clears everything else, and anything else clears `exclusive`. */
const toggleExclusive = (list: string[], key: string, exclusive = 'none') =>
  key === exclusive ? (list.includes(key) ? [] : [key]) : toggle(list.filter((k) => k !== exclusive), key)

export function StepHead({ title, sub }: { title: string; sub?: ReactNode }) {
  return (
    <header className="step-head">
      <h1 tabIndex={-1} data-step-title>{title}</h1>
      {sub && <p className="lede">{sub}</p>}
    </header>
  )
}

function Stepper({ label, sub, value, min, onChange }: { label: string; sub: string; value: number; min: number; onChange: (n: number) => void }) {
  const id = useId()
  return (
    <div className="count-row">
      <div>
        <span className="count-label" id={id}>{label}</span>
        <span className="hint">{sub}</span>
      </div>
      <div className="count-ctl" role="group" aria-labelledby={id}>
        <button type="button" className="round-btn" aria-label={`Fewer ${label.toLowerCase()}`} disabled={value <= min}
          onClick={() => onChange(value - 1)}><Minus size={20} aria-hidden="true" /></button>
        <output className="count-value num" aria-live="polite">{value}</output>
        <button type="button" className="round-btn" aria-label={`More ${label.toLowerCase()}`} disabled={value >= 10}
          onClick={() => onChange(value + 1)}><Plus size={20} aria-hidden="true" /></button>
      </div>
    </div>
  )
}

// 1 ------------------------------------------------------------------
export function StepWho({ a, set }: StepProps) {
  const p = portions(a)
  return (
    <>
      <StepHead title="Who's eating?" sub="We scale every recipe and the grocery list to this." />
      <div className="card stack">
        <Stepper label="Adults" sub="Full portions" value={a.adults} min={0} onChange={(adults) => set({ adults })} />
        <Stepper label="Kids" sub="Half portions" value={a.kids} min={0} onChange={(kids) => set({ kids })} />
      </div>
      <p className="summary-bar" aria-live="polite">
        <Users size={18} aria-hidden="true" />
        {p === 0 ? 'Add at least one person.' : (
          <>{plural(a.adults, 'adult')}{a.kids ? ` + ${plural(a.kids, 'kid')}` : ''} = <strong className="num">{fmtPortions(p)}</strong>{' '}
            {p === 1 ? 'portion' : 'portions'}/meal</>
        )}
      </p>
    </>
  )
}

// 2 ------------------------------------------------------------------
const MEAL_ICONS: Record<string, LucideIcon> = { breakfast: Sunrise, lunch: Sun, dinner: Moon, snacks: Cookie }
export function StepMeals({ a, set }: StepProps) {
  return (
    <>
      <StepHead title="Which meals?" sub="Pick every meal you want planned." />
      <div className="list-cards">
        {MEAL_OPTIONS.map((m) => {
          const on = a.meals.includes(m.key), Icon = MEAL_ICONS[m.key]
          return (
            <button key={m.key} type="button" role="checkbox" aria-checked={on} aria-label={`${m.label}, ${m.sub}`} className={on ? 'list-card on' : 'list-card'}
              onClick={() => set({ meals: toggle(a.meals, m.key) })}>
              <span className={`icon-badge tone-${m.tone}`}><Icon size={22} aria-hidden="true" /></span>
              <span className="list-text"><span className="opt-title">{m.label}</span><span className="hint">{m.sub}</span></span>
              <span className="check" aria-hidden="true">{on && <Check size={16} strokeWidth={3} />}</span>
            </button>
          )
        })}
      </div>
    </>
  )
}

// 3 ------------------------------------------------------------------
export function StepDays({ a, set }: StepProps) {
  return (
    <>
      <StepHead title="Which days are you cooking?" sub={`${a.days.length} ${a.days.length === 1 ? 'day' : 'days'} selected.`} />
      <div className="day-pills" role="group" aria-label="Cooking days">
        {DAY_LETTERS.map((letter, i) => {
          const on = a.days.includes(i)
          return (
            <button key={i} type="button" role="checkbox" aria-checked={on} aria-label={DAY_NAMES[i]}
              className={on ? 'day-pill on' : 'day-pill'}
              onClick={() => set({ days: on ? a.days.filter((d) => d !== i) : [...a.days, i].sort() })}>
              <span className="day-letter">{letter}</span>
              <span className="day-dot" aria-hidden="true">{on && <Check size={12} strokeWidth={3} />}</span>
            </button>
          )
        })}
      </div>
      <div className="quick-row">
        <button type="button" className="btn btn-quiet" onClick={() => set({ days: [0, 1, 2, 3, 4] })}>Weekdays</button>
        <button type="button" className="btn btn-quiet" onClick={() => set({ days: [0, 1, 2, 3, 4, 5, 6] })}>Every day</button>
      </div>
    </>
  )
}

// 4 ------------------------------------------------------------------
export function StepKitchen({ a, set }: StepProps) {
  return (
    <>
      <StepHead title="What's in your kitchen?" sub="Tap everything you own. We only suggest recipes you can cook with them." />
      <div className="kitchen" role="group" aria-label="Kitchen appliances">
        <div className="kitchen-wall" aria-hidden="true" />
        <div className="kitchen-grid">
          {APPLIANCE_OPTIONS.map((ap) => {
            const on = a.appliances.includes(ap.key)
            return (
              <button key={ap.key} type="button" role="checkbox" aria-checked={on} aria-label={ap.label}
                className={`appliance appliance-${ap.key}${on ? ' on' : ''}`} onClick={() => set({ appliances: toggle(a.appliances, ap.key) })}>
                {on && <span className="float-pill" aria-hidden="true"><Check size={12} strokeWidth={3} /> {ap.label}</span>}
                <ApplianceArt kind={ap.key} />
                <span className="appliance-name">{ap.label}</span>
              </button>
            )
          })}
        </div>
        <div className="kitchen-counter" aria-hidden="true" />
      </div>
      {a.appliances.length === 0 && <p className="hint">With no appliances we'll stick to no-cook meals and snacks.</p>}
    </>
  )
}

// 5 + 6 + 7 -----------------------------------------------------------
const DIET_ICONS: Record<string, LucideIcon> = {
  none: UtensilsCrossed, vegetarian: Salad, vegan: Vegan, pescatarian: Fish, keto: Beef, high_protein: Dumbbell,
  glp1: HeartPulse, anti_inflammatory: LeafyGreen, mediterranean: Globe, mexican: Flame,
}
const VIBE_ICONS: Record<string, LucideIcon> = {
  quick: Zap, one_pan: CookingPot, batch: Package, family: Users, comfort: Soup, fresh: Sprout, fiber: Wheat, takeout: Sandwich,
}

function GridCard({ on, onClick, icon, emoji, title, sub }: {
  on: boolean; onClick: () => void; icon?: LucideIcon; emoji?: string; title: string; sub?: string
}) {
  const Icon = icon
  return (
    <button type="button" role="checkbox" aria-checked={on} aria-label={sub ? `${title}, ${sub}` : title}
      className={on ? 'grid-card on' : 'grid-card'} onClick={onClick}>
      <span className="corner-check" aria-hidden="true">{on && <Check size={14} strokeWidth={3} />}</span>
      {Icon && <Icon size={24} aria-hidden="true" className="grid-icon" />}
      {emoji && <span className="grid-emoji" aria-hidden="true">{emoji}</span>}
      <span className="opt-title">{title}</span>
      {sub && <span className="hint">{sub}</span>}
    </button>
  )
}

export function StepDiet({ a, set }: StepProps) {
  return (
    <>
      <StepHead title="How do you eat?" sub="Vegetarian, vegan, pescatarian and keto are strict. The rest shape what we suggest." />
      <div className="grid-2">
        {DIET_OPTIONS.map((d) => (
          <GridCard key={d.key} on={a.diets.includes(d.key)} icon={DIET_ICONS[d.key]} title={d.label} sub={d.sub}
            onClick={() => set({ diets: toggleExclusive(a.diets, d.key) })} />
        ))}
      </div>
    </>
  )
}

export function StepVibe({ a, set }: StepProps) {
  return (
    <>
      <StepHead title="What kind of vibe?" sub="Pick as many as you like." />
      <div className="grid-2">
        {VIBE_OPTIONS.map((v) => (
          <GridCard key={v.key} on={a.vibes.includes(v.key)} icon={VIBE_ICONS[v.key]} title={v.label} sub={v.sub}
            onClick={() => set({ vibes: toggle(a.vibes, v.key) })} />
        ))}
      </div>
    </>
  )
}

export function StepAllergies({ a, set }: StepProps) {
  return (
    <>
      <StepHead title="Any allergies?" sub="We leave these out of every recipe and every Careem Quik product we pick." />
      <div className="grid-2 grid-allergy">
        {ALLERGY_OPTIONS.map((o) => (
          <GridCard key={o.key} on={a.allergens.includes(o.key)} emoji={o.emoji} title={o.label}
            onClick={() => set({ allergens: toggleExclusive(a.allergens, o.key) })} />
        ))}
      </div>
    </>
  )
}

// 8 ------------------------------------------------------------------
export function StepDislikes({ a, set }: StepProps) {
  const [q, setQ] = useState('')
  const id = useId()
  const term = q.trim()
  const custom = a.dislikes.filter((d) => !DISLIKE_OPTIONS.some((o) => o.label === d))
  const shown = [...DISLIKE_OPTIONS, ...custom.map((label) => ({ label, emoji: '🚫' }))]
    .filter((o) => !term || o.label.toLowerCase().includes(term.toLowerCase()))
  const canAdd = term.length > 1 && !shown.some((o) => o.label.toLowerCase() === term.toLowerCase())
  const add = () => { if (canAdd) { set({ dislikes: [...a.dislikes, term] }); setQ('') } }
  return (
    <>
      <StepHead title="Any dislikes?" sub={a.dislikes.length ? `We'll skip ${a.dislikes.length} ${a.dislikes.length === 1 ? 'food' : 'foods'}.` : 'Tap anything you would rather not eat.'} />
      <div className="search-box">
        <Search size={18} aria-hidden="true" />
        <label htmlFor={id} className="visually-hidden">Search any food</label>
        <input id={id} type="search" value={q} placeholder="Search any food..." autoComplete="off"
          onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() } }} />
      </div>
      {canAdd && <button type="button" className="btn btn-quiet add-custom" onClick={add}><Plus size={16} aria-hidden="true" /> Add "{term}"</button>}
      <div className="pill-wrap" role="group" aria-label="Foods you dislike">
        {shown.map((o) => {
          const on = a.dislikes.includes(o.label)
          return (
            <button key={o.label} type="button" role="checkbox" aria-checked={on} aria-label={o.label} className={on ? 'food-pill on' : 'food-pill'}
              onClick={() => set({ dislikes: toggle(a.dislikes, o.label) })}>
              <span aria-hidden="true">{o.emoji}</span> {o.label}
              {on && <X size={14} aria-hidden="true" />}
            </button>
          )
        })}
        {shown.length === 0 && !canAdd && <p className="hint">No match.</p>}
      </div>
    </>
  )
}

// 9 ------------------------------------------------------------------
const CATS: ('All' | PantryCategory)[] = ['All', 'Fresh', 'Meat', 'Fridge', 'Pantry']
export function StepPantry({ a, set, address, products, remember }: StepProps) {
  const [cat, setCat] = useState<(typeof CATS)[number]>('All')
  const [q, setQ] = useState('')
  const [result, setResult] = useState<{ term: string; items: Product[] }>({ term: '', items: [] })
  const id = useId()
  const term = q.trim()
  useEffect(() => {
    if (term.length < 2) return
    const t = setTimeout(() => {
      api.search(term, address).then((r) => setResult({ term, items: r.items })).catch(() => setResult({ term, items: [] }))
    }, 250)
    return () => clearTimeout(t)
  }, [term, address])
  const tiles = PANTRY_TILES.filter((t) => (cat === 'All' || t.cat === cat) && (!term || t.label.toLowerCase().includes(term.toLowerCase())))
  const found = term.length >= 2 && result.term === term ? result.items.filter((p) => !a.pantryExtra.includes(p.id)) : []
  const count = a.pantryTiles.length + a.pantryExtra.length
  return (
    <>
      <StepHead title="What do you already have?" sub={count ? `${count} ${count === 1 ? 'item' : 'items'} in your pantry. We won't buy these again.` : "Tap what's in your kitchen, so we don't buy it again."} />
      <div className="search-box">
        <Search size={18} aria-hidden="true" />
        <label htmlFor={id} className="visually-hidden">Search foods</label>
        <input id={id} type="search" value={q} placeholder="Search foods" autoComplete="off" onChange={(e) => setQ(e.target.value)} />
      </div>
      <div className="cat-pills" role="radiogroup" aria-label="Food category">
        {CATS.map((c) => (
          <button key={c} type="button" role="radio" aria-checked={cat === c} aria-label={c} className={cat === c ? 'cat-pill on' : 'cat-pill'}
            onClick={() => setCat(c)}>{c}</button>
        ))}
      </div>
      <div className="tile-grid">
        {tiles.map((t) => {
          const on = a.pantryTiles.includes(t.key)
          return (
            <button key={t.key} type="button" role="checkbox" aria-checked={on} aria-label={t.label} className={on ? 'food-tile on' : 'food-tile'}
              onClick={() => set({ pantryTiles: toggle(a.pantryTiles, t.key) })}>
              <span className="tile-emoji" aria-hidden="true">{t.emoji}</span>
              <span className="tile-label">{t.label}</span>
              {on && <span className="tile-check" aria-hidden="true"><Check size={12} strokeWidth={3} /></span>}
            </button>
          )
        })}
        {a.pantryExtra.map((pid) => (
          <button key={pid} type="button" role="checkbox" aria-checked="true" aria-label={products.get(pid)?.name ?? `Item ${pid}`} className="food-tile on"
            onClick={() => set({ pantryExtra: a.pantryExtra.filter((x) => x !== pid) })}>
            <span className="tile-emoji" aria-hidden="true">🛒</span>
            <span className="tile-label">{products.get(pid)?.name ?? `Item ${pid}`}</span>
            <span className="tile-check" aria-hidden="true"><Check size={12} strokeWidth={3} /></span>
          </button>
        ))}
      </div>
      {found.length > 0 && (
        <div className="found">
          <h2 className="sub">Add from Careem Quik</h2>
          <ul className="search-results">
            {found.slice(0, 6).map((p) => (
              <li key={p.id}>
                <button type="button" className="result" onClick={() => { remember(p); set({ pantryExtra: [...a.pantryExtra, p.id] }); setQ('') }}>
                  <span className="result-name">{p.name}</span><span className="hint">{p.unit}</span><span className="result-add">Add</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}

// 10 -----------------------------------------------------------------
export function StepBudget({ a, set, address, aiAvailable }: StepProps) {
  const [est, setEst] = useState<{ value: number | null; failed: boolean }>({ value: null, failed: false })
  const amountId = useId(), notesId = useId()
  const body = useMemo(() => planBody(a), [a])
  // the estimate ignores the budget, so pin it: dragging the slider must not refetch prices
  const key = JSON.stringify({ ...body, budget: 100, notes: '' })
  useEffect(() => {
    let live = true
    api.estimate(JSON.parse(key), address)
      .then((r) => live && setEst({ value: r.estimate, failed: false }))
      .catch(() => live && setEst({ value: null, failed: true }))
    return () => { live = false }
  }, [key, address])
  const p = portions(a)
  const meals = a.meals.length
  const summary = [plural(a.adults, 'adult'), a.kids ? plural(a.kids, 'kid') : null, `${meals} ${meals === 1 ? 'meal' : 'meals'}/day`,
    `${a.days.length} ${a.days.length === 1 ? 'day' : 'days'}`, `${fmtPortions(p)} ${p === 1 ? 'portion' : 'portions'}/meal`].filter(Boolean).join(' · ')
  const ratio = est.value ? a.budget / est.value : null
  const feedback = ratio == null ? null : ratio >= 1.1
    ? { tone: 'good', title: 'Room to spare', text: `Careem Quik should come to about ${aed(est.value)} this week.` }
    : ratio >= 0.95
      ? { tone: 'good', title: 'Right on target', text: `About ${aed(est.value)} on Careem Quik, close to your budget.` }
      : { tone: 'tight', title: 'Tight budget, prioritizing Careem Quik deals', text: `A typical week for you is about ${aed(est.value)}. We'll favor cheaper recipes and today's deals.` }
  return (
    <>
      <StepHead title="Your weekly budget" sub={summary} />
      <div className="card budget-card">
        <label htmlFor={amountId} className="visually-hidden">Weekly budget in AED</label>
        <div className="budget-amount-row">
          <span className="currency">AED</span>
          <input id={amountId} className="budget-input num" type="number" inputMode="numeric" min={50} max={2000} step={10}
            value={a.budget} onChange={(e) => set({ budget: Math.max(0, Math.min(2000, Number(e.target.value) || 0)) })} />
        </div>
        <input type="range" min={50} max={1000} step={10} value={Math.min(1000, Math.max(50, a.budget))} className="range"
          aria-label="Weekly budget" style={{ ['--fill' as string]: `${((Math.min(1000, Math.max(50, a.budget)) - 50) / 950) * 100}%` }}
          onChange={(e) => set({ budget: Number(e.target.value) })} />
        <div className="range-ends hint"><span>AED 50</span><span>AED 1,000</span></div>
      </div>
      <div className={`feedback ${feedback ? `fb-${feedback.tone}` : ''}`} aria-live="polite">
        {est.failed ? <p className="hint">Couldn't check Careem Quik prices right now. You can still continue.</p>
          : !feedback ? <p className="hint">Checking Careem Quik prices…</p>
            : <><p className="fb-title">{feedback.title}</p><p>{feedback.text}</p></>}
      </div>
      {aiAvailable && (
        <div className="field-col">
          <label className="field-label" htmlFor={notesId}>Anything else Claude should know?</label>
          <textarea id={notesId} className="notes" rows={2} maxLength={300} value={a.notes}
            placeholder="We love spicy food, Thursday needs to be quick…" onChange={(e) => set({ notes: e.target.value })} />
        </div>
      )}
    </>
  )
}
