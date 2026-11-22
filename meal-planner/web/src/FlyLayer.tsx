import { motion } from 'motion/react'

export interface Flyer { id: string; label: string; from: DOMRect; to: DOMRect; delay: number }

/** The signature moment: each needed item lifts off its row and lands in the cart button. */
export function FlyLayer({ flyers, onDone }: { flyers: Flyer[]; onDone: () => void }) {
  if (!flyers.length) return null
  const last = Math.max(...flyers.map((f) => f.delay))
  return (
    <div className="fly-layer" aria-hidden="true">
      {flyers.map((f) => (
        <motion.span key={f.id} className="flyer"
          initial={{ x: f.from.left + 16, y: f.from.top + f.from.height / 2 - 18, scale: 1, opacity: 0.95 }}
          animate={{
            x: [f.from.left + 16, (f.from.left + f.to.left) / 2, f.to.left + f.to.width / 2 - 18],
            y: [f.from.top + f.from.height / 2 - 18, Math.min(f.from.top, f.to.top) - 60, f.to.top + f.to.height / 2 - 18],
            scale: [1, 0.9, 0.35],
            opacity: [0.95, 1, 0],
          }}
          transition={{ duration: 0.75, delay: f.delay, ease: [0.22, 1, 0.36, 1], times: [0, 0.55, 1] }}
          onAnimationComplete={f.delay === last ? onDone : undefined}>
          {f.label}
        </motion.span>
      ))}
    </div>
  )
}
