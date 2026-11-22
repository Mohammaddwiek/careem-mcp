import { Bike, Check, PackageCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { aed, api, type CartLine, type CheckoutResult, type Tracking } from '../api'
import { Banner } from '../ui'

export interface Order { result: CheckoutResult; lines: CartLine[]; total: number; payment: string; address: string }

const STEPS = ['Order placed', 'Packing at the store', 'On the way', 'Delivered']
const stepFor = (status: string) =>
  /DELIVER(ED)?$/i.test(status) && !/OUT_FOR/i.test(status) ? 3 : /WAY|OUT_FOR|PICKED/i.test(status) ? 2 : /PACK|PREPAR|ACCEPT/i.test(status) ? 1 : 0

export function Track({ order, onDone }: { order: Order; onDone: () => void }) {
  const [t, setT] = useState<Tracking | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let stop = false
    let timer: ReturnType<typeof setTimeout>
    const poll = () => api.track()
      .then((r) => {
        if (stop) return
        setT(r); setErr(r.error ?? null)
        timer = setTimeout(poll, Math.max(5, r.poll_after ?? 10) * 1000)
      })
      .catch((e: Error) => { if (!stop) { setErr(e.message); timer = setTimeout(poll, 15000) } })
    poll()
    return () => { stop = true; clearTimeout(timer) }
  }, [])

  const step = t ? stepFor(t.status) : 0
  const progress = t && t.initial_eta_minutes ? 1 - t.current_eta_minutes / t.initial_eta_minutes : 0.1
  const ref = order.result.checkout?.masterInvoiceReference

  return (
    <div className="track">
      <header className="screen-head">
        <h1>Order placed</h1>
        <p className="lede">{ref ? `Order ${ref}. ` : ''}{aed(order.total)} paid with {order.payment}, delivering to {order.address}.</p>
      </header>

      {order.result.deep_link && (
        <Banner tone="info" action={<a className="btn btn-quiet" href={order.result.deep_link} target="_blank" rel="noreferrer">Finish payment</a>}>
          Your card needs one more step in Careem Pay.
        </Banner>
      )}
      {err && <Banner tone="error">Live tracking isn't updating right now ({err}). Your order is still on its way.</Banner>}

      <div className="track-grid">
        <section className="card eta-card" aria-live="polite" aria-labelledby="eta-h">
          <div className="eta-ring" style={{ ['--p' as string]: `${Math.max(0.05, Math.min(1, progress)) * 360}deg` }}>
            <span className="eta-min num">{t ? t.current_eta_minutes : '…'}</span>
            <span className="eta-unit">min</span>
          </div>
          <div>
            <h2 id="eta-h">{t?.title ?? (step === 2 ? 'On the way' : 'Getting your order ready')}</h2>
            <p className="hint">
              {t?.merchant_name ?? 'Careem Quik'}{t?.captain_name ? `, ${t.captain_name} is bringing it` : ''}
            </p>
          </div>
          <ol className="steps" aria-label="Delivery progress">
            {STEPS.map((s, i) => (
              <li key={s} className={i < step ? 'done' : i === step ? 'now' : ''} aria-current={i === step ? 'step' : undefined}>
                <span className="dot" aria-hidden="true">{i < step ? <Check size={13} /> : i === 2 ? <Bike size={13} /> : null}</span>
                {s}
              </li>
            ))}
          </ol>
        </section>

        <section className="card" aria-labelledby="items-h">
          <h2 id="items-h"><PackageCheck size={20} aria-hidden="true" /> In this order</h2>
          <ul className="order-lines">
            {order.lines.map((l) => (
              <li key={l.item_uuid}><span className="num qty-tag">{l.count}×</span> {l.name}<span className="num">{aed(l.total)}</span></li>
            ))}
          </ul>
          <p className="order-total"><span>Total</span><span className="num">{aed(order.total)}</span></p>
        </section>
      </div>

      <div className="action-bar glass">
        <button type="button" className="btn btn-primary btn-lg" onClick={onDone}>Plan next week</button>
      </div>
    </div>
  )
}
