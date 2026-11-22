import { Blend, CookingPot, Dumbbell, Flame, Microwave, PiggyBank, Scale, Search, Timer, Wind, X, Zap, type LucideIcon } from 'lucide-react'
import { useEffect, useId, useMemo, useState } from 'react'
import { api, aed, type Address, type Bootstrap, type Diet, type Goal, type Meals, type Prefs, type Product } from '../api'
import { ALLERGEN_LABELS } from '../helpers'
import { CategoryIcon, QtyStepper, Segmented, ToggleChip } from '../ui'

const APPLIANCES: Record<string, { label: string; icon: LucideIcon }> = {
  stove: { label: 'Stove', icon: CookingPot },
  oven: { label: 'Oven', icon: Flame },
  air_fryer: { label: 'Air fryer', icon: Wind },
  microwave: { label: 'Microwave', icon: Microwave },
  blender: { label: 'Blender', icon: Blend },
}
const STAPLES = [4000160, 4000172, 4000173, 4000130, 4000129, 4000152]

interface Props {
  boot: Bootstrap
  address: Address
  prefs: Prefs
  setPrefs: (p: Prefs) => void
  pantryNames: Map<number, Product>
  rememberProduct: (p: Product) => void
  onSubmit: () => void
  busy: boolean
}

export function Setup({ boot, address, prefs, setPrefs, pantryNames, rememberProduct, onSubmit, busy }: Props) {
  const set = <K extends keyof Prefs>(k: K, v: Prefs[K]) => setPrefs({ ...prefs, [k]: v })
  const toggle = (k: 'pantry' | 'appliances' | 'allergens', v: never) =>
    set(k, (prefs[k] as unknown[]).includes(v) ? (prefs[k] as unknown[]).filter((x) => x !== v) as never : [...prefs[k], v] as never)
  const addPantry = (p: Product) => {
    rememberProduct(p)
    if (!prefs.pantry.includes(p.id)) set('pantry', [...prefs.pantry, p.id])
  }
  const byId = useMemo(() => new Map(boot.products.map((p) => [p.id, p])), [boot.products])
  const staples = STAPLES.map((id) => byId.get(id)).filter((p): p is Product => !!p && !prefs.pantry.includes(p.id))
  const usuals = boot.usuals.filter((p) => !prefs.pantry.includes(p.id))

  return (
    <form className="setup" onSubmit={(e) => { e.preventDefault(); onSubmit() }}>
      <header className="screen-head">
        <h1>Hi {boot.user.name}, what's in your kitchen?</h1>
        <p className="lede">Tell us what you have and what you need. We'll plan the meals and only shop for what's missing.</p>
      </header>

      <div className="setup-grid">
        <section className="card pantry-card" aria-labelledby="pantry-h">
          <h2 id="pantry-h">Pantry and fridge</h2>
          <PantrySearch address={address} onPick={addPantry} />
          {prefs.pantry.length > 0 ? (
            <ul className="chip-row" aria-label="In your pantry">
              {prefs.pantry.map((id) => {
                const p = pantryNames.get(id) ?? byId.get(id)
                return (
                  <li key={id}>
                    <span className="chip chip-have">
                      <CategoryIcon category={p?.category} size={16} />
                      {p?.name ?? `Item ${id}`}
                      <button type="button" className="chip-x" aria-label={`Remove ${p?.name ?? 'item'} from pantry`}
                        onClick={() => toggle('pantry', id as never)}>
                        <X size={14} aria-hidden="true" />
                      </button>
                    </span>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="hint">Nothing added yet. Search above, or tap what you usually keep at home.</p>
          )}
          {usuals.length > 0 && (
            <div className="quick-add">
              <h3>You usually buy</h3>
              <div className="chip-row">
                {usuals.map((p) => (
                  <button key={p.id} type="button" className="chip chip-add" onClick={() => addPantry(p)}>
                    <PlusIcon /> {p.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          {staples.length > 0 && (
            <div className="quick-add">
              <h3>Kitchen staples</h3>
              <div className="chip-row">
                {staples.map((p) => (
                  <button key={p.id} type="button" className="chip chip-add" onClick={() => addPantry(p)}>
                    <PlusIcon /> {p.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>

        <div className="setup-side">
          <section className="card" aria-labelledby="kitchen-h">
            <h2 id="kitchen-h">Your kitchen</h2>
            <div className="appliances">
              {Object.entries(APPLIANCES).map(([key, a]) => {
                const on = prefs.appliances.includes(key)
                return (
                  <button key={key} type="button" aria-pressed={on} className={on ? 'tile on' : 'tile'}
                    onClick={() => toggle('appliances', key as never)}>
                    <a.icon size={22} aria-hidden="true" />
                    <span>{a.label}</span>
                  </button>
                )
              })}
            </div>
          </section>

          <section className="card" aria-labelledby="needs-h">
            <h2 id="needs-h">Diet and allergies</h2>
            <Segmented<Diet> label="Diet" value={prefs.diet} onChange={(v) => set('diet', v)} options={[
              { value: 'any', label: 'Anything' }, { value: 'vegetarian', label: 'Vegetarian' },
              { value: 'vegan', label: 'Vegan' }, { value: 'gluten_free', label: 'Gluten-free' },
            ]} />
            <h3 className="sub">Leave out anything with</h3>
            <div className="chip-row">
              {boot.allergens.map((a) => (
                <ToggleChip key={a} tone="danger" on={prefs.allergens.includes(a)} onClick={() => toggle('allergens', a as never)}>
                  {ALLERGEN_LABELS[a] ?? a}
                </ToggleChip>
              ))}
            </div>
          </section>

          <section className="card" aria-labelledby="plan-h">
            <h2 id="plan-h">The plan</h2>
            <div className="field-row">
              <span className="field-label" id="people-l">People</span>
              <QtyStepper label="people" value={prefs.people} min={1} max={8} onChange={(n) => set('people', n)} />
            </div>
            <div className="field-row">
              <span className="field-label">Days</span>
              <QtyStepper label="days" value={prefs.days} min={1} max={7} onChange={(n) => set('days', n)} />
            </div>
            <div className="field-col">
              <span className="field-label">Meals each day</span>
              <Segmented<Meals> label="Meals each day" value={prefs.meals} onChange={(v) => set('meals', v)} options={[
                { value: 'dinner', label: 'Dinner' }, { value: 'lunch_dinner', label: 'Lunch and dinner' }, { value: 'all', label: 'All three' },
              ]} />
            </div>
            <BudgetSlider value={prefs.budget} onChange={(n) => set('budget', n)} />
            <div className="field-col">
              <span className="field-label">Plan for</span>
              <Segmented<Goal> label="Plan for" value={prefs.goal} onChange={(v) => set('goal', v)} options={[
                { value: 'balanced', label: 'Balance', icon: Scale }, { value: 'save', label: 'Saving money', icon: PiggyBank },
                { value: 'protein', label: 'Protein', icon: Dumbbell }, { value: 'quick', label: 'Speed', icon: Zap },
              ]} />
            </div>
            <label className="switch-row">
              <input type="checkbox" className="switch" checked={prefs.batch_cook} onChange={(e) => set('batch_cook', e.target.checked)} />
              <span>
                <span className="switch-title">Cook once, eat twice</span>
                <span className="hint">Each recipe covers two meals, so the list stays shorter.</span>
              </span>
            </label>
          </section>
        </div>
      </div>

      <div className="action-bar glass">
        <p className="action-summary">
          <Timer size={16} aria-hidden="true" /> {prefs.days} {prefs.days === 1 ? 'day' : 'days'} for {prefs.people}{' '}
          {prefs.people === 1 ? 'person' : 'people'}, up to <span className="num">{aed(prefs.budget)}</span>
        </p>
        <button type="submit" className="btn btn-primary btn-lg" disabled={busy}>
          {busy ? 'Building your plan…' : 'Build my plan'}
        </button>
      </div>
    </form>
  )
}

function PlusIcon() {
  return <span aria-hidden="true" className="plus">+</span>
}

function BudgetSlider({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  const id = useId()
  return (
    <div className="field-col">
      <label className="field-label budget-label" htmlFor={id}>
        Weekly grocery budget <span className="num budget-value">{aed(value)}</span>
      </label>
      <input id={id} type="range" min={50} max={800} step={10} value={value} className="range"
        style={{ ['--fill' as string]: `${((value - 50) / 750) * 100}%` }}
        onChange={(e) => onChange(Number(e.target.value))} />
    </div>
  )
}

function PantrySearch({ address, onPick }: { address: Address; onPick: (p: Product) => void }) {
  const [q, setQ] = useState('')
  // results are stored with the term they answer, so stale or short-term results simply don't show
  const [result, setResult] = useState<{ term: string; items: Product[]; failed: boolean }>({ term: '', items: [], failed: false })
  const listId = useId()
  const term = q.trim()

  useEffect(() => {
    if (term.length < 2) return
    const t = setTimeout(() => {
      api.search(term, address)
        .then((r) => setResult({ term, items: r.items, failed: false }))
        .catch(() => setResult({ term, items: [], failed: true }))
    }, 250)
    return () => clearTimeout(t)
  }, [term, address])

  const current = term.length >= 2 && result.term === term
  const items = current ? result.items : []
  const state = term.length < 2 ? 'idle' : !current ? 'loading' : result.failed ? 'error' : items.length ? 'idle' : 'empty'
  const pick = (p: Product) => { onPick(p); setQ('') }
  return (
    <div className="search">
      <label htmlFor={`${listId}-input`} className="visually-hidden">Search Careem Quik for something you have</label>
      <div className="search-box">
        <Search size={18} aria-hidden="true" />
        <input id={`${listId}-input`} type="search" value={q} onChange={(e) => setQ(e.target.value)} autoComplete="off"
          placeholder="Add what you have: eggs, rice, olive oil…" aria-controls={listId} aria-expanded={items.length > 0} />
      </div>
      <div aria-live="polite" className="search-status">
        {state === 'loading' && <span className="hint">Searching Careem Quik…</span>}
        {state === 'empty' && <span className="hint">No match on Careem Quik. Try a simpler word, like "rice".</span>}
        {state === 'error' && <span className="hint error-text">Search isn't available right now.</span>}
      </div>
      {items.length > 0 && (
        <ul id={listId} className="search-results" aria-label="Search results">
          {items.map((p) => (
            <li key={p.id}>
              <button type="button" className="result" onClick={() => pick(p)}>
                <span className="result-name">{p.name}</span>
                <span className="hint">{p.unit}</span>
                <span className="result-add">Add</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
