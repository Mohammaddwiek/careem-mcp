import { Clock, RefreshCw, Sparkles, Users } from 'lucide-react'
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from 'motion/react'
import type { PointerEvent, ReactNode } from 'react'
import { aed, type Plan, type Product, type Recipe } from '../api'
import { Banner, DealBadge } from '../ui'

const SLOT_LABEL: Record<string, string> = { breakfast: 'Breakfast', lunch: 'Lunch', dinner: 'Dinner' }

interface Props {
  plan: Plan
  deals: Product[]
  busySwap: string | null
  onSwap: (id: string) => void
  onBack: () => void
  onNext: () => void
}

export function PlanView({ plan, deals, busySwap, onSwap, onBack, onNext }: Props) {
  const days = [...new Set(plan.schedule.map((s) => s.day))]
  const byId = new Map(plan.recipes.map((r) => [r.id, r]))
  const whenFor = (id: string) =>
    plan.schedule.filter((s) => s.recipe === id).map((s) => `day ${s.day} ${SLOT_LABEL[s.slot]?.toLowerCase() ?? s.slot}`)

  return (
    <div className="plan">
      <header className="screen-head">
        <h1>Your {days.length}-day plan</h1>
        <p className="lede">
          {plan.recipes.length} recipes, chosen around today's Careem Quik deals and what you already have.
          Swap anything that doesn't sound good.
        </p>
      </header>

      <ol className="week" aria-label="Week at a glance">
        {days.map((d) => (
          <li key={d} className="week-day">
            <span className="week-label">Day {d}</span>
            {plan.schedule.filter((s) => s.day === d).map((s) => (
              <span key={s.slot} className="week-meal">
                <span className="hint">{SLOT_LABEL[s.slot]}</span>
                <span className="week-name">{byId.get(s.recipe)?.name}</span>
              </span>
            ))}
          </li>
        ))}
      </ol>

      <div className="plan-grid">
        <div className="meals">
          {plan.recipes.map((r) => (
            <MealCard key={r.id} recipe={r} when={whenFor(r.id)} busy={busySwap === r.id} onSwap={() => onSwap(r.id)} />
          ))}
          {plan.excluded.length > 0 && (
            <details className="excluded">
              <summary>{plan.excluded.length} recipes left out for your settings</summary>
              <ul>{plan.excluded.map((e) => <li key={e.recipe}><strong>{e.recipe}</strong>: {e.reason}</li>)}</ul>
            </details>
          )}
        </div>

        <aside className="card deals-rail" aria-labelledby="deals-h">
          <h2 id="deals-h">Live Careem Quik deals</h2>
          <p className="hint">Your plan leans on these where it can.</p>
          <ul className="deal-list">
            {deals.map((d) => (
              <li key={d.id} className="deal-row">
                <span className="deal-name">{d.name}</span>
                <span className="deal-prices">
                  <span className="num price">{aed(d.price)}</span>
                  {d.original_price && <s className="num was">{aed(d.original_price)}</s>}
                </span>
                <DealBadge pct={d.deal_pct} />
              </li>
            ))}
          </ul>
        </aside>
      </div>

      <div className="action-bar glass">
        <button type="button" className="btn btn-ghost" onClick={onBack}>Change settings</button>
        <button type="button" className="btn btn-primary btn-lg" onClick={onNext}>See what to buy</button>
      </div>
    </div>
  )
}

function MealCard({ recipe: r, when, busy, onSwap }: { recipe: Recipe; when: string[]; busy: boolean; onSwap: () => void }) {
  return (
    <Tilt>
      <article className="meal" aria-labelledby={`meal-${r.id}`}>
        <div className="meal-top">
          <span className="meal-cuisine">{r.cuisine}</span>
          <span className="meal-when">{when.join(', ')}</span>
        </div>
        <h3 id={`meal-${r.id}`} className="meal-name">{r.name}</h3>
        <p className="meal-blurb">{r.blurb}</p>
        <div className="meal-facts">
          <span><Clock size={15} aria-hidden="true" /> {r.minutes} min</span>
          <span><Users size={15} aria-hidden="true" /> {r.servings} servings</span>
          <span className="num">{aed(r.per_serving.cost)} a serving</span>
        </div>
        <dl className="macros" aria-label="Per serving">
          <div><dt>kcal</dt><dd className="num">{r.per_serving.kcal}</dd></div>
          <div><dt>Protein</dt><dd className="num">{r.per_serving.protein} g</dd></div>
          <div><dt>Carbs</dt><dd className="num">{r.per_serving.carbs} g</dd></div>
          <div><dt>Fat</dt><dd className="num">{r.per_serving.fat} g</dd></div>
        </dl>
        {r.deals.length > 0 && (
          <p className="meal-deals"><span className="badge badge-deal">On deal</span> {r.deals.join(', ')}</p>
        )}
        {r.swaps.map((s) => (
          <p key={s.ingredient} className="swap-note">
            <Sparkles size={15} aria-hidden="true" /> {s.reason}, so we used {s.to}.
          </p>
        ))}
        <button type="button" className="btn btn-quiet meal-swap" onClick={onSwap} disabled={busy}>
          <RefreshCw size={15} aria-hidden="true" className={busy ? 'spin' : undefined} />
          {busy ? 'Finding another meal…' : 'Swap this meal'}
        </button>
      </article>
    </Tilt>
  )
}

/** Gentle 3D tilt that follows the pointer. Off for touch and reduced motion. */
function Tilt({ children }: { children: ReactNode }) {
  const reduce = useReducedMotion()
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const rx = useSpring(useTransform(y, [-0.5, 0.5], [5, -5]), { stiffness: 220, damping: 22 })
  const ry = useSpring(useTransform(x, [-0.5, 0.5], [-6, 6]), { stiffness: 220, damping: 22 })
  const move = (e: PointerEvent<HTMLDivElement>) => {
    if (reduce || e.pointerType !== 'mouse') return
    const b = e.currentTarget.getBoundingClientRect()
    x.set((e.clientX - b.left) / b.width - 0.5)
    y.set((e.clientY - b.top) / b.height - 0.5)
  }
  const leave = () => { x.set(0); y.set(0) }
  return (
    <motion.div className="tilt" style={reduce ? undefined : { rotateX: rx, rotateY: ry, transformPerspective: 900 }}
      onPointerMove={move} onPointerLeave={leave}>
      {children}
    </motion.div>
  )
}

export function PlanError({ message, onBack }: { message: string; onBack: () => void }) {
  return (
    <Banner tone="error" action={<button type="button" className="btn btn-quiet" onClick={onBack}>Change settings</button>}>
      {message}
    </Banner>
  )
}
