import { ChevronRight, Clock, Flame, PiggyBank, Repeat, Sparkles, Tag } from 'lucide-react'
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from 'motion/react'
import type { PointerEvent, ReactNode } from 'react'
import { aed, type Plan, type Product, type Recipe } from '../api'
import { fmtPortions } from '../wizard/answers'
import { Banner, DealBadge } from '../ui'

const MEAL_LABEL: Record<string, string> = { breakfast: 'Breakfast', lunch: 'Lunch', dinner: 'Dinner', snacks: 'Snack' }
const POOL_LABEL: Record<string, string> = { breakfast: 'breakfasts', main: 'lunches or dinners', snack: 'snacks' }

interface Props {
  plan: Plan
  deals: Product[]
  tab: 'plan' | 'shop'
  setTab: (t: 'plan' | 'shop') => void
  onOpen: (r: Recipe) => void
  shop: ReactNode
  onEdit: () => void
}

export function PlanView({ plan, deals, tab, setTab, onOpen, shop, onEdit }: Props) {
  const byId = new Map(plan.recipes.map((r) => [r.id, r]))
  const dealMeals = plan.recipes.filter((r) => r.deals.length).length
  return (
    <div className="plan">
      <header className="screen-head">
        <h1>Your week</h1>
        <p className="lede">
          {plan.days.length} {plan.days.length === 1 ? 'day' : 'days'}, {plan.meals.length} {plan.meals.length === 1 ? 'meal' : 'meals'} a day,{' '}
          {fmtPortions(plan.portions)} {plan.portions === 1 ? 'portion' : 'portions'} a meal. Tap any meal for the recipe.
        </p>
      </header>

      {plan.ai?.used && plan.ai.summary && (
        <section className="ai-summary" aria-label="Why this plan">
          <span className="ai-badge"><Sparkles size={15} aria-hidden="true" /> Planned with Claude</span>
          <p>{plan.ai.summary}</p>
        </section>
      )}
      {plan.prioritized_deals && (
        <Banner tone="info"><PiggyBank size={16} aria-hidden="true" className="inline-icon" /> Your budget is tight, so this week leans on cheaper recipes and today's Careem Quik deals.</Banner>
      )}
      {(plan.missing ?? []).map((m) => (
        <Banner key={m} tone="info">No {POOL_LABEL[m] ?? m} fit your answers, so we left them out. Adding an appliance or removing a dislike usually helps.</Banner>
      ))}

      <div className="tabs" role="tablist" aria-label="Plan views">
        <button type="button" role="tab" id="tab-plan" aria-selected={tab === 'plan'} aria-controls="panel-plan"
          className={tab === 'plan' ? 'tab on' : 'tab'} onClick={() => setTab('plan')}>Meal plan</button>
        <button type="button" role="tab" id="tab-shop" aria-selected={tab === 'shop'} aria-controls="panel-shop"
          className={tab === 'shop' ? 'tab on' : 'tab'} onClick={() => setTab('shop')}>
          Shopping list <span className="tab-count num">{plan.need.length}</span>
        </button>
      </div>

      {tab === 'plan' ? (
        <div id="panel-plan" role="tabpanel" aria-labelledby="tab-plan" className="plan-layout">
          <div className="days">
            {plan.days.map((d) => (
              <section key={d.day} className="day" aria-labelledby={`day-${d.day}`}>
                <h2 id={`day-${d.day}`} className="day-name">{d.name}</h2>
                <div className="day-meals">
                  {plan.schedule.filter((s) => s.day === d.day).map((s) => {
                    const r = byId.get(s.recipe)
                    return r ? <MealCard key={s.meal} recipe={r} meal={MEAL_LABEL[s.meal] ?? s.meal} leftovers={s.leftovers} onOpen={() => onOpen(r)} /> : null
                  })}
                </div>
              </section>
            ))}
          </div>
          <aside className="card deals-rail" aria-labelledby="deals-h">
            <h2 id="deals-h"><Tag size={18} aria-hidden="true" /> Today's Careem Quik deals</h2>
            <p className="hint">{dealMeals ? `${dealMeals} of your meals use a deal.` : 'None of these fit your meals this week.'}</p>
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
          <div className="action-bar glass">
            <button type="button" className="btn btn-ghost" onClick={onEdit}>Edit answers</button>
            <button type="button" className="btn btn-primary btn-lg" onClick={() => setTab('shop')}>See shopping list</button>
          </div>
        </div>
      ) : (
        <div id="panel-shop" role="tabpanel" aria-labelledby="tab-shop">{shop}</div>
      )}

      {plan.excluded.length > 0 && tab === 'plan' && (
        <details className="excluded">
          <summary>{plan.excluded.length} recipes left out for your answers</summary>
          <ul>{plan.excluded.map((e) => <li key={e.recipe}><strong>{e.recipe}</strong>: {e.reason}</li>)}</ul>
        </details>
      )}
    </div>
  )
}

function MealCard({ recipe: r, meal, leftovers, onOpen }: { recipe: Recipe; meal: string; leftovers: boolean; onOpen: () => void }) {
  return (
    <Tilt>
      <button type="button" className="meal-card" onClick={onOpen} aria-label={`${meal}: ${r.name}. Open recipe`}>
        <span className="meal-top">
          <span className="meal-slot">{meal}</span>
          {leftovers && <span className="leftover"><Repeat size={13} aria-hidden="true" /> Leftovers</span>}
        </span>
        <span className="meal-name">{r.name}</span>
        <span className="meal-facts">
          <span><Clock size={14} aria-hidden="true" /> {r.minutes} min</span>
          <span><Flame size={14} aria-hidden="true" /> <span className="num">{r.per_serving.kcal}</span> kcal</span>
          <span><span className="num">{r.per_serving.protein}</span> g protein</span>
        </span>
        {r.deals.length > 0 && <span className="badge badge-deal meal-deal"><Tag size={12} aria-hidden="true" /> Deal-powered</span>}
        {r.why && <span className="meal-why-short"><Sparkles size={13} aria-hidden="true" /> {r.why}</span>}
        <span className="open-hint" aria-hidden="true">Recipe <ChevronRight size={14} /></span>
      </button>
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
  return (
    <motion.div className="tilt" style={reduce ? undefined : { rotateX: rx, rotateY: ry, transformPerspective: 900 }}
      onPointerMove={move} onPointerLeave={() => { x.set(0); y.set(0) }}>
      {children}
    </motion.div>
  )
}

export function PlanError({ message, onBack }: { message: string; onBack: () => void }) {
  return (
    <Banner tone="error" action={<button type="button" className="btn btn-quiet" onClick={onBack}>Edit answers</button>}>
      {message}
    </Banner>
  )
}
