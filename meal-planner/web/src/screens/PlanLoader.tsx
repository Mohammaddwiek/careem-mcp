import { Check, Sparkles, TriangleAlert } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { useEffect, useMemo, useState } from 'react'
import { aed } from '../api'
import { ALLERGY_OPTIONS, APPLIANCE_OPTIONS, fmtPortions, plural, portions, type Answers } from '../wizard/answers'

const STEP_MS = 650

/** Every step names something the planner really checks; the last one finishes only when the plan has arrived. */
function stepsFor(a: Answers, ai: boolean): { title: string; detail: string }[] {
  const allergies = a.allergens.filter((x) => x !== 'none')
    .map((k) => ALLERGY_OPTIONS.find((o) => o.key === k)?.label ?? k)
  const appliances = APPLIANCE_OPTIONS.filter((o) => a.appliances.includes(o.key)).map((o) => o.label.toLowerCase())
  const p = portions(a)
  return [
    { title: 'Counting portions', detail: `${plural(a.adults, 'adult')}${a.kids ? ` + ${plural(a.kids, 'kid')}` : ''} = ${fmtPortions(p)} ${p === 1 ? 'portion' : 'portions'} a meal` },
    { title: 'Checking allergies', detail: allergies.length ? `Leaving out ${allergies.join(', ').toLowerCase()}` : 'No allergies to avoid' },
    ...(a.dislikes.length ? [{ title: 'Skipping dislikes', detail: a.dislikes.join(', ') }] : []),
    { title: 'Matching your kitchen', detail: appliances.length ? `Recipes for your ${appliances.join(', ')}` : 'No-cook recipes only' },
    { title: "Pulling today's Careem Quik deals", detail: 'Live prices and offers near you' },
    { title: 'Fitting your budget', detail: `Keeping the week near ${aed(a.budget)}` },
    { title: ai ? 'Claude is choosing your meals' : 'Choosing your meals', detail: `${a.days.length} ${a.days.length === 1 ? 'day' : 'days'}, ${a.meals.length} ${a.meals.length === 1 ? 'meal' : 'meals'} a day` },
  ]
}

interface Props {
  answers: Answers
  ai: boolean
  ready: boolean // the plan request finished successfully
  error: string | null
  onFinished: () => void
  onBack: () => void
}

export function PlanLoader({ answers, ai, ready, error, onFinished, onBack }: Props) {
  const reduce = useReducedMotion()
  const steps = useMemo(() => stepsFor(answers, ai), [answers, ai])
  const [tick, setTick] = useState(0) // how many steps the animation has completed
  const last = steps.length - 1
  const done = Math.min(tick, ready ? steps.length : last) // the final step waits for the real plan

  useEffect(() => {
    if (error || tick >= last) return
    const t = setTimeout(() => setTick((n) => n + 1), reduce ? STEP_MS / 2 : STEP_MS)
    return () => clearTimeout(t)
  }, [tick, last, error, reduce])

  useEffect(() => {
    if (!ready || tick < last) return
    const t = setTimeout(onFinished, 700)
    return () => clearTimeout(t)
  }, [ready, tick, last, onFinished])

  const pct = Math.round(((ready && tick >= last ? steps.length : done + 0.5) / steps.length) * 100)

  return (
    <section className="loader" aria-labelledby="loader-h">
      <div className="loader-orb" aria-hidden="true">
        <span className="orb-ring" />
        <span className="orb-core"><Sparkles size={30} /></span>
      </div>
      <h1 id="loader-h">{error ? "We couldn't build your plan" : ready && tick >= last ? 'Your week is ready' : 'Building your week'}</h1>
      <div className="loader-bar" role="progressbar" aria-label="Plan progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
        <motion.span initial={false} animate={{ width: `${pct}%` }} transition={{ type: 'spring', stiffness: 120, damping: 24 }} />
      </div>
      <ol className="loader-steps" aria-live="polite">
        {steps.map((s, i) => {
          const state = i < done || (ready && tick >= last) ? 'done' : i === done && !error ? 'active' : 'waiting'
          return (
            <motion.li key={s.title} className={`lstep ${state}`}
              initial={reduce ? false : { opacity: 0, y: 8 }} animate={{ opacity: state === 'waiting' ? 0.55 : 1, y: 0 }}
              transition={{ delay: reduce ? 0 : i * 0.05, duration: 0.25 }}>
              <span className="lstep-icon" aria-hidden="true">
                {state === 'done' ? (
                  <motion.span className="lcheck" initial={reduce ? false : { scale: 0.4 }} animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 18 }}><Check size={15} strokeWidth={3} /></motion.span>
                ) : state === 'active' ? <span className="lspin" /> : <span className="ldot" />}
              </span>
              <span className="lstep-text">
                <span className="lstep-title">{s.title}{state === 'done' && <span className="visually-hidden">, done</span>}</span>
                <span className="lstep-detail">{s.detail}</span>
              </span>
            </motion.li>
          )
        })}
      </ol>
      {error && (
        <div className="loader-error" role="alert">
          <TriangleAlert size={18} aria-hidden="true" /> <span>{error}</span>
          <button type="button" className="btn btn-quiet" onClick={onBack}>Change answers</button>
        </div>
      )}
    </section>
  )
}
