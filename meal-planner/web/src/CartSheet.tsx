import { ArrowLeft, Banknote, CreditCard, Lock, MapPin, Trash2, Wallet, X } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { aed, type Address, type Cart, type CartLine } from './api'
import { Banner, QtyStepper } from './ui'

export interface Payment { type: 'wallet' | 'card' | 'cash'; id?: number; label: string }

interface Props {
  open: boolean
  cart: Cart | null
  address: Address
  budget: number | null
  dev: boolean
  busyLine: string | null
  placing: boolean
  error: string | null
  onClose: () => void
  onUpdate: (line: CartLine, count: number) => void
  onDelete: (line: CartLine) => void
  onPlace: (payment: Payment) => void
}

export function CartSheet({ open, cart, address, budget, dev, busyLine, placing, error, onClose, onUpdate, onDelete, onPlace }: Props) {
  const reduce = useReducedMotion()
  const [stage, setStage] = useState<'review' | 'confirm'>('review')
  const [payType, setPayType] = useState<string>('wallet')
  const sheet = useRef<HTMLDivElement>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const payments: Payment[] = [
    { type: 'wallet', label: 'Careem Pay wallet' },
    { type: 'card', id: 4242, label: 'Visa ending 4242' },
    { type: 'cash', label: 'Cash on delivery' },
    ...(dev ? [{ type: 'card' as const, id: 4000002, label: 'Test card that declines' }] : []),
  ]
  const payment = payments.find((p) => `${p.type}${p.id ?? ''}` === payType) ?? payments[0]

  // Adjust state when props change (during render, as React recommends, not in effects)
  const [seen, setSeen] = useState({ open, error, payment: cart?.payment_type })
  if (seen.open !== open || seen.error !== error || seen.payment !== cart?.payment_type) {
    if (open && !seen.open) setStage('review')
    if (error && error !== seen.error) setStage('review')
    const pt = cart?.payment_type
    if (pt && pt !== seen.payment && ['wallet', 'card', 'cash'].includes(pt)) setPayType(pt === 'card' ? 'card4242' : pt)
    setSeen({ open, error, payment: pt })
  }
  useEffect(() => {
    if (!open) return
    const opener = document.activeElement as HTMLElement | null
    requestAnimationFrame(() => heading.current?.focus())
    // give focus back to whatever opened the sheet (the cart button, usually)
    return () => { if (opener?.isConnected) opener.focus({ preventScroll: true }) }
  }, [open])
  // Escape closes the sheet even when focus has left it (e.g. a re-rendered button)
  useEffect(() => {
    if (!open) return
    const onKey = (e: globalThis.KeyboardEvent) => { if (e.key === 'Escape' && !placing) onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, placing, onClose])

  const trap = (e: KeyboardEvent) => {
    if (e.key !== 'Tab' || !sheet.current) return
    const items = [...sheet.current.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input, [tabindex="0"], h2[tabindex]')]
    if (!items.length) return
    const first = items[0], last = items[items.length - 1]
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
  }

  const lines = cart?.basket?.lines ?? []
  const total = cart?.total ?? 0
  const overBy = budget ? total - budget : 0

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="overlay" key="overlay" onClick={() => !placing && onClose()}
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} />
          <motion.div ref={sheet} key="sheet" className="sheet glass" role="dialog" aria-modal="true" aria-labelledby="sheet-h"
            onKeyDown={trap}
            initial={reduce ? { opacity: 0 } : { y: '100%' }} animate={reduce ? { opacity: 1 } : { y: 0 }}
            exit={reduce ? { opacity: 0 } : { y: '100%' }}
            transition={reduce ? { duration: 0.15 } : { type: 'spring', stiffness: 320, damping: 34 }}>
            <div className="sheet-grip" aria-hidden="true" />
            <div className="sheet-head">
              {stage === 'confirm' && (
                <button type="button" className="icon-btn" onClick={() => setStage('review')} aria-label="Back to cart" disabled={placing}>
                  <ArrowLeft size={20} aria-hidden="true" />
                </button>
              )}
              <h2 id="sheet-h" ref={heading} tabIndex={-1}>{stage === 'review' ? 'Your Careem Quik cart' : 'Confirm your order'}</h2>
              <button type="button" className="icon-btn" onClick={onClose} aria-label="Close cart" disabled={placing}>
                <X size={20} aria-hidden="true" />
              </button>
            </div>

            <div className="sheet-body">
              {error && <Banner tone="error">{error}</Banner>}
              {cart?.failed_items && cart.failed_items.length > 0 && stage === 'review' && (
                <Banner tone="info">
                  {cart.failed_items.map((f) => (
                    <span key={f.keyword} className="block">
                      {f.added_quantity ? `Only ${f.added_quantity} of ${f.requested_quantity} ${f.keyword} were in stock.` : `${f.keyword}: ${f.error_message.toLowerCase()}, so it wasn't added.`}
                    </span>
                  ))}
                </Banner>
              )}
              {!cart?.basket ? (
                <p className="empty">Your cart is empty. Build a plan and add what you need.</p>
              ) : stage === 'review' ? (
                <>
                  <p className="hint merchant-line">{cart.merchant?.name}, delivery in about {cart.merchant?.eta ?? 15} minutes</p>
                  <ul className="cart-lines" aria-live="polite">
                    {lines.map((l) => (
                      <li key={l.item_uuid} className="cart-line">
                        <span className="cart-name">{l.name}</span>
                        <span className="cart-price">
                          <span className="num">{aed(l.total)}</span>
                          {l.original > l.total && <s className="num was">{aed(l.original)}</s>}
                        </span>
                        <QtyStepper label={l.name} value={l.count} min={1} max={50} busy={busyLine === l.item_uuid}
                          onChange={(n) => onUpdate(l, n)} />
                        <button type="button" className="icon-btn" aria-label={`Remove ${l.name}`} disabled={busyLine === l.item_uuid}
                          onClick={() => onDelete(l)}>
                          <Trash2 size={18} aria-hidden="true" />
                        </button>
                      </li>
                    ))}
                  </ul>
                  <Breakdown cart={cart} />
                  {budget != null && (
                    <p className={overBy > 0 ? 'budget-note over' : 'budget-note'}>
                      {overBy > 0 ? `${aed(overBy)} over your ${aed(budget)} budget.` : `${aed(-overBy)} under your ${aed(budget)} budget.`}
                    </p>
                  )}
                  <fieldset className="payments">
                    <legend>Pay with</legend>
                    {payments.map((p) => {
                      const key = `${p.type}${p.id ?? ''}`
                      const Icon = p.type === 'wallet' ? Wallet : p.type === 'cash' ? Banknote : CreditCard
                      return (
                        <label key={key} className={payType === key ? 'pay on' : 'pay'}>
                          <input type="radio" name="pay" value={key} checked={payType === key} onChange={() => setPayType(key)} />
                          <Icon size={18} aria-hidden="true" /> {p.label}
                        </label>
                      )
                    })}
                  </fieldset>
                </>
              ) : (
                <div className="confirm">
                  <p className="confirm-total"><span className="num">{aed(total)}</span></p>
                  <dl className="confirm-facts">
                    <div><dt>Items</dt><dd>{cart.basket.count} from {cart.merchant?.name}</dd></div>
                    <div><dt>Deliver to</dt><dd><MapPin size={15} aria-hidden="true" /> {address.title}, {address.subTitle}</dd></div>
                    <div><dt>Pay with</dt><dd>{payment.label}</dd></div>
                  </dl>
                  <p className="hint">Placing the order charges this exact total. You can't undo it from here.</p>
                </div>
              )}
            </div>

            {cart?.basket && (
              <div className="sheet-foot">
                {stage === 'review' ? (
                  <button type="button" className="btn btn-primary btn-lg btn-block" onClick={() => setStage('confirm')}>
                    Review order, {aed(total)}
                  </button>
                ) : (
                  <button type="button" className="btn btn-primary btn-lg btn-block" disabled={placing} onClick={() => onPlace(payment)}>
                    <Lock size={17} aria-hidden="true" /> {placing ? 'Placing your order…' : `Place order, ${aed(total)}`}
                  </button>
                )}
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

function Breakdown({ cart }: { cart: Cart }) {
  return (
    <dl className="breakdown">
      {(cart.breakdown ?? []).map((r) => (
        <div key={r.label} className={r.label === 'Total' ? 'row total' : r.kind === 'success' ? 'row promo' : 'row'}>
          <dt>{r.label}{r.note && <span className="hint"> {r.note}</span>}</dt>
          <dd className="num">{aed(r.amount)}</dd>
        </div>
      ))}
      {(cart.saving ?? 0) > 0 && (
        <div className="row promo"><dt>You save on deals</dt><dd className="num">{aed(cart.saving)}</dd></div>
      )}
    </dl>
  )
}
