import { ChevronLeft } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import type { Address, Product } from '../api'
import { scrollScreenTop } from '../helpers'
import type { Answers } from './answers'
import { STEPS, blocker } from './registry'

interface Props {
  answers: Answers
  setAnswers: (a: Answers) => void
  step: number
  setStep: (n: number) => void
  address: Address
  aiAvailable: boolean
  products: Map<number, Product>
  remember: (p: Product) => void
  busy: boolean
  error: string | null
  onDone: () => void
}

const LABELS = ['Next', 'Next', 'Next', 'Next', 'Next', 'Next', 'Next', 'Next', 'Continue', 'Confirm & continue']

/** The 10-step onboarding: progress bar, back button, sliding steps and a sticky CTA. */
export function Wizard({ answers, setAnswers, step, setStep, address, aiAvailable, products, remember, busy, error, onDone }: Props) {
  const [dir, setDir] = useState(1)
  const [tried, setTried] = useState(false)
  const body = useRef<HTMLDivElement>(null)
  const Step = STEPS[step]
  const block = blocker(step, answers)
  const last = step === STEPS.length - 1

  useEffect(() => {
    // move focus to the new step's heading so screen readers announce it
    const t = setTimeout(() => body.current?.querySelector<HTMLElement>('[data-step-title]')?.focus({ preventScroll: true }), 50)
    scrollScreenTop()
    return () => clearTimeout(t)
  }, [step])

  const go = (n: number) => { setDir(n > step ? 1 : -1); setTried(false); setStep(n) }
  const next = () => {
    if (block) { setTried(true); return }
    if (last) onDone()
    else go(step + 1)
  }

  return (
    <div className="wizard">
      <div className="wizard-top">
        <button type="button" className="icon-btn" onClick={() => go(step - 1)} disabled={step === 0} aria-label="Back to the previous question">
          <ChevronLeft size={22} aria-hidden="true" />
        </button>
        <div className="progress" role="progressbar" aria-label="Onboarding progress" aria-valuemin={1} aria-valuemax={STEPS.length}
          aria-valuenow={step + 1} aria-valuetext={`Question ${step + 1} of ${STEPS.length}`}>
          <motion.span className="progress-fill" initial={false} animate={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
            transition={{ type: 'spring', stiffness: 260, damping: 30 }} />
        </div>
        <span className="progress-count num" aria-hidden="true">{step + 1}/{STEPS.length}</span>
      </div>

      <div className="wizard-body" ref={body}>
        <AnimatePresence mode="wait" custom={dir} initial={false}>
          <motion.section key={step} className="wizard-step" custom={dir}
            variants={{
              enter: (d: number) => ({ x: d * 48, opacity: 0 }),
              center: { x: 0, opacity: 1 },
              exit: (d: number) => ({ x: d * -48, opacity: 0 }),
            }}
            initial="enter" animate="center" exit="exit" transition={{ type: 'spring', stiffness: 420, damping: 38, opacity: { duration: 0.15 } }}>
            <Step a={answers} set={(patch) => setAnswers({ ...answers, ...patch })} address={address} aiAvailable={aiAvailable}
              products={products} remember={remember} />
          </motion.section>
        </AnimatePresence>
      </div>

      <div className="wizard-cta">
        {(tried && block) && <p className="field-error" role="alert">{block}</p>}
        {error && <p className="field-error" role="alert">{error}</p>}
        <button type="button" className="btn btn-primary btn-cta" onClick={next} disabled={busy} aria-disabled={!!block || undefined}>
          {busy ? (aiAvailable ? 'Claude is planning your week…' : 'Building your plan…') : LABELS[step]}
        </button>
      </div>
    </div>
  )
}
