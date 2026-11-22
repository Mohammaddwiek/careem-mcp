import { Check, Clock, Minus, Pause, Play, Plus, RefreshCw, RotateCcw, ShoppingBasket, Sparkles, Tag, TriangleAlert, X } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { aed, type Plan, type Recipe } from './api'
import { fmtPortions } from './wizard/answers'

const APPLIANCE_LABELS: Record<string, string> = {
  stovetop: 'Stovetop', oven: 'Oven', microwave: 'Microwave', air_fryer: 'Air fryer', toaster: 'Toaster', blender: 'Blender', slow_cooker: 'Slow cooker',
}

function fmtAmount(amount: number, unit: string, name: string) {
  if (unit === 'pcs') {
    const n = Math.round(amount * 4) / 4
    const whole = Math.floor(n), frac = n - whole
    const f = frac === 0.25 ? '¼' : frac === 0.5 ? '½' : frac === 0.75 ? '¾' : ''
    return `${whole || !f ? whole : ''}${f}`.trim() + ` × ${name}`
  }
  const big = amount >= 1000
  const v = big ? amount / 1000 : amount
  const u = unit === 'g' ? (big ? 'kg' : 'g') : big ? 'L' : 'ml'
  return `${big ? v.toFixed(v < 10 ? 1 : 0) : Math.round(v)} ${u} ${name}`
}

interface Props {
  recipe: Recipe | null
  plan: Plan
  swapBusy: boolean
  onClose: () => void
  onSwap: (id: string) => void
}

export function RecipeDrawer({ recipe, plan, swapBusy, onClose, onSwap }: Props) {
  const reduce = useReducedMotion()
  const panel = useRef<HTMLDivElement>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const [servings, setServings] = useState(plan.portions)
  const [done, setDone] = useState<number[]>([])
  const [seen, setSeen] = useState<string | null>(null)
  // reset the scaler and check-offs when a different recipe opens (during render, not in an effect)
  if ((recipe?.id ?? null) !== seen) {
    setSeen(recipe?.id ?? null)
    setServings(plan.portions)
    setDone([])
  }

  // remember what opened the drawer and give focus back to it on close
  const openId = recipe?.id ?? null
  useEffect(() => {
    if (!openId) return
    const opener = document.activeElement as HTMLElement | null
    return () => { opener?.focus?.({ preventScroll: true }) }
  }, [openId])

  useEffect(() => {
    if (!recipe) return
    requestAnimationFrame(() => heading.current?.focus())
    const onKey = (e: globalThis.KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [recipe, onClose])

  const trap = (e: KeyboardEvent) => {
    if (e.key !== 'Tab' || !panel.current) return
    const items = [...panel.current.querySelectorAll<HTMLElement>('button:not([disabled]), input, [tabindex="0"]')]
    if (!items.length) return
    const first = items[0], lastEl = items[items.length - 1]
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); lastEl.focus() }
    else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); first.focus() }
  }

  const have = new Set(plan.have.map((h) => h.product.id))
  const need = new Map(plan.need.map((n) => [n.product.id, n]))

  return (
    <AnimatePresence>
      {recipe && (
        <>
          <motion.div key="ov" className="overlay" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.div key="panel" ref={panel} className="drawer glass" role="dialog" aria-modal="true" aria-labelledby="recipe-h" onKeyDown={trap}
            initial={reduce ? { opacity: 0 } : { x: '100%' }} animate={reduce ? { opacity: 1 } : { x: 0 }} exit={reduce ? { opacity: 0 } : { x: '100%' }}
            transition={reduce ? { duration: 0.15 } : { type: 'spring', stiffness: 320, damping: 36 }}>
            <div className="drawer-head">
              <div className="drawer-title">
                <span className="meal-cuisine">{recipe.cuisine}</span>
                <h2 id="recipe-h" ref={heading} tabIndex={-1}>{recipe.name}</h2>
              </div>
              <button type="button" className="icon-btn" onClick={onClose} aria-label="Close recipe"><X size={20} aria-hidden="true" /></button>
            </div>

            <div className="drawer-body">
              <div className="badge-row">
                <span className="chip-static"><Clock size={15} aria-hidden="true" /> {recipe.minutes} min</span>
                {recipe.appliances.map((ap) => <span key={ap} className="chip-static">{APPLIANCE_LABELS[ap] ?? ap}</span>)}
                {recipe.deals.length > 0 && <span className="badge badge-deal"><Tag size={13} aria-hidden="true" /> Deal on {recipe.deals.length === 1 ? recipe.deals[0] : `${recipe.deals.length} items`}</span>}
              </div>
              <p className="meal-blurb">{recipe.blurb}</p>
              {recipe.why && <p className="meal-why"><Sparkles size={14} aria-hidden="true" /> {recipe.why}</p>}
              {recipe.swaps.map((s) => (
                <p key={s.ingredient} className="swap-note"><Sparkles size={15} aria-hidden="true" /> {s.reason}, so this uses {s.to}.</p>
              ))}

              <dl className="macros" aria-label="Per serving">
                <div><dt>kcal</dt><dd className="num">{recipe.per_serving.kcal}</dd></div>
                <div><dt>Protein</dt><dd className="num">{recipe.per_serving.protein} g</dd></div>
                <div><dt>Carbs</dt><dd className="num">{recipe.per_serving.carbs} g</dd></div>
                <div><dt>Fat</dt><dd className="num">{recipe.per_serving.fat} g</dd></div>
              </dl>
              <p className="hint per-serving-note">Per serving. About {aed(recipe.per_serving.cost)} a serving on Careem Quik.</p>

              <section aria-labelledby="ing-h" className="drawer-section">
                <div className="section-row">
                  <h3 id="ing-h">Ingredients</h3>
                  <div className="scaler" role="group" aria-label="Servings">
                    <button type="button" className="round-btn sm" aria-label="Fewer servings" disabled={servings <= 1}
                      onClick={() => setServings(Math.max(1, servings - 1))}><Minus size={16} aria-hidden="true" /></button>
                    <output className="scaler-value" aria-live="polite"><span className="num">{fmtPortions(servings)}</span> {servings === 1 ? 'serving' : 'servings'}</output>
                    <button type="button" className="round-btn sm" aria-label="More servings" disabled={servings >= 20}
                      onClick={() => setServings(servings + 1)}><Plus size={16} aria-hidden="true" /></button>
                  </div>
                </div>
                <ul className="ingredients">
                  {recipe.ingredients.map((ing) => {
                    const n = need.get(ing.product_id)
                    const inPantry = have.has(ing.product_id)
                    const unavailable = n && (n.match.status === 'not_found' || !n.product.available)
                    return (
                      <li key={ing.product_id + ing.name}>
                        <span className="ing-amount">{fmtAmount(ing.amount * servings, ing.unit, ing.name.toLowerCase())}</span>
                        {inPantry ? (
                          <span className="ing-tag have"><Check size={14} aria-hidden="true" /> In pantry</span>
                        ) : unavailable ? (
                          <span className="ing-tag bad"><TriangleAlert size={14} aria-hidden="true" /> Not on Careem Quik right now</span>
                        ) : n ? (
                          <span className="ing-tag buy"><ShoppingBasket size={14} aria-hidden="true" />
                            <span>Buy on Careem Quik: {n.product.name}, <span className="num">{aed(n.product.price)}</span></span></span>
                        ) : null}
                      </li>
                    )
                  })}
                </ul>
              </section>

              <section aria-labelledby="steps-h" className="drawer-section">
                <div className="section-row">
                  <h3 id="steps-h">Steps</h3>
                  <span className="hint" aria-live="polite">{done.length} of {recipe.steps.length} done</span>
                </div>
                <ol className="steps-list">
                  {recipe.steps.map((s, i) => {
                    const on = done.includes(i)
                    return (
                      <li key={i} className={on ? 'step-item done' : 'step-item'}>
                        <label className="step-check">
                          <input type="checkbox" checked={on} onChange={() => setDone(on ? done.filter((x) => x !== i) : [...done, i])} />
                          <span className="step-num num" aria-hidden="true">{on ? <Check size={14} strokeWidth={3} /> : i + 1}</span>
                          <span className="step-text"><span className="visually-hidden">Step {i + 1}: </span>{s.text}</span>
                        </label>
                        {s.minutes && s.minutes <= 120 && <StepTimer minutes={s.minutes} label={`step ${i + 1}`} />}
                        {s.minutes && s.minutes > 120 && <span className="hint timer-long">About {Math.round(s.minutes / 60)} hours</span>}
                      </li>
                    )
                  })}
                </ol>
              </section>
            </div>

            <div className="drawer-foot">
              <button type="button" className="btn btn-ghost" onClick={() => onSwap(recipe.id)} disabled={swapBusy}>
                <RefreshCw size={16} aria-hidden="true" className={swapBusy ? 'spin' : undefined} /> {swapBusy ? 'Finding another…' : 'Swap this meal'}
              </button>
              <button type="button" className="btn btn-primary" onClick={onClose}>Done</button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

/** A countdown for one cooking step. */
function StepTimer({ minutes, label }: { minutes: number; label: string }) {
  const total = minutes * 60
  const [left, setLeft] = useState(total)
  const [running, setRunning] = useState(false)
  useEffect(() => {
    if (!running) return
    const t = setInterval(() => setLeft((l) => {
      if (l <= 1) { setRunning(false); return 0 }
      return l - 1
    }), 1000)
    return () => clearInterval(t)
  }, [running])
  const mm = String(Math.floor(left / 60)).padStart(2, '0'), ss = String(left % 60).padStart(2, '0')
  return (
    <div className={left === 0 ? 'timer finished' : 'timer'}>
      <span className="num" role="timer" aria-live={left === 0 ? 'assertive' : 'off'}>{left === 0 ? 'Done' : `${mm}:${ss}`}</span>
      <button type="button" className="round-btn sm" onClick={() => setRunning(!running)} disabled={left === 0}
        aria-label={`${running ? 'Pause' : 'Start'} timer for ${label}`}>
        {running ? <Pause size={14} aria-hidden="true" /> : <Play size={14} aria-hidden="true" />}
      </button>
      <button type="button" className="round-btn sm" onClick={() => { setRunning(false); setLeft(total) }} aria-label={`Reset timer for ${label}`}>
        <RotateCcw size={14} aria-hidden="true" />
      </button>
    </div>
  )
}
