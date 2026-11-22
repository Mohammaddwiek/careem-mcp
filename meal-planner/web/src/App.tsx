import { ChefHat, MapPin, Moon, ShoppingCart, Sun } from 'lucide-react'
import { MotionConfig, motion, useReducedMotion } from 'motion/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { aed, api, type Address, type Bootstrap, type Cart, type CartLine, type Plan, type Prefs, type Product } from './api'
import { CartSheet, type Payment } from './CartSheet'
import { FlyLayer, type Flyer } from './FlyLayer'
import { PlanError, PlanView } from './screens/PlanView'
import { Setup } from './screens/Setup'
import { lineFor, type ShopLine } from './helpers'
import { Shop } from './screens/Shop'
import { Track, type Order } from './screens/Track'
import { Banner } from './ui'

type Step = 'setup' | 'plan' | 'shop' | 'track'
const STEPS: { key: Step; label: string }[] = [
  { key: 'setup', label: 'Your kitchen' }, { key: 'plan', label: 'Meal plan' },
  { key: 'shop', label: 'Shopping list' }, { key: 'track', label: 'Delivery' },
]
const DEFAULT_PREFS: Prefs = {
  pantry: [], appliances: ['stove', 'oven'], allergens: [], diet: 'any', people: 2, days: 5, meals: 'dinner',
  budget: 250, goal: 'balanced', batch_cook: true, keep: [], exclude: [], notes: '',
}

export default function App() {
  const dev = useMemo(() => new URLSearchParams(location.search).has('dev'), [])
  const reduce = useReducedMotion()
  const [theme, setTheme] = useState<'dark' | 'light'>(() => (localStorage.getItem('theme') as 'dark' | 'light') ?? 'dark')
  const [boot, setBoot] = useState<Bootstrap | null>(null)
  const [bootError, setBootError] = useState<string | null>(null)
  const [address, setAddress] = useState<Address | null>(null)
  const [products, setProducts] = useState<Map<number, Product>>(new Map())
  const [step, setStep] = useState<Step>('setup')
  const [reached, setReached] = useState<Step[]>(['setup'])
  const [prefs, setPrefs] = useState<Prefs>(DEFAULT_PREFS)
  const [plan, setPlan] = useState<Plan | null>(null)
  const [planBusy, setPlanBusy] = useState(false)
  const [planError, setPlanError] = useState<string | null>(null)
  const [swapBusy, setSwapBusy] = useState<string | null>(null)
  const [lines, setLines] = useState<Record<number, ShopLine>>({})
  const [cart, setCart] = useState<Cart | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [cartBusy, setCartBusy] = useState(false)
  const [busyLine, setBusyLine] = useState<string | null>(null)
  const [placing, setPlacing] = useState(false)
  const [sheetError, setSheetError] = useState<string | null>(null)
  const [existing, setExisting] = useState<Cart | null>(null)
  const [flyers, setFlyers] = useState<Flyer[]>([])
  const [order, setOrder] = useState<Order | null>(null)
  const cartBtn = useRef<HTMLButtonElement>(null)
  const main = useRef<HTMLElement>(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('theme', theme)
  }, [theme])

  const remember = useCallback((list: Product[]) => setProducts((m) => {
    const next = new Map(m)
    list.forEach((p) => next.set(p.id, { ...next.get(p.id), ...p }))
    return next
  }), [])

  const load = useCallback((a?: Address) => {
    api.bootstrap(a).then((b) => {
      setBootError(null)
      setBoot((prev) => (prev && !b.serviceable ? { ...b, products: prev.products, usuals: prev.usuals, deals: prev.deals } : b))
      remember([...b.products, ...b.usuals])
      setAddress((cur) => a ?? cur ?? b.addresses[0])
    }).catch((e: Error) => setBootError(e.message))
  }, [remember])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (address) api.cart(address).then(setCart).catch(() => undefined)
  }, [address])

  const go = (s: Step) => {
    setStep(s)
    setReached((r) => (r.includes(s) ? r : [...r, s]))
    requestAnimationFrame(() => { main.current?.focus({ preventScroll: true }); window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' }) })
  }

  const buildPlan = async (extra?: Partial<Prefs>) => {
    if (!address) return
    setPlanError(null)
    try {
      const p = await api.plan({ ...prefs, ...extra }, address)
      setPlan(p)
      setLines({})
      if (p.error) setPlanError(p.error)
      return p
    } catch (e) {
      setPlanError((e as Error).message)
    }
  }

  const submitSetup = async () => {
    setPlanBusy(true)
    const p = await buildPlan({ keep: [], exclude: [] })
    setPlanBusy(false)
    if (p && !p.error) go('plan')
    else go('plan')
  }

  const swap = async (id: string) => {
    if (!plan) return
    setSwapBusy(id)
    const keep = plan.recipes.map((r) => r.id).filter((r) => r !== id)
    const exclude = [...new Set([...prefs.exclude, id])]
    setPrefs({ ...prefs, exclude })
    const before = plan
    const next = await buildPlan({ keep, exclude })
    // a swap is planned by rules; keep Claude's summary and notes for the meals that stayed
    if (next && !next.error && before.ai?.used) {
      const why = new Map(before.recipes.map((r) => [r.id, r.why]))
      setPlan({ ...next, ai: before.ai, recipes: next.recipes.map((r) => ({ ...r, why: r.why ?? why.get(r.id) ?? null })) })
    }
    setSwapBusy(null)
  }

  const shopLines = () => (plan?.need ?? []).filter((n) => !lineFor(n, lines).skip).map((n) => ({
    catalog_item_id: String(n.product.id), keyword: n.term, quantity: lineFor(n, lines).packs,
  }))

  const startAddToCart = async () => {
    if (!address) return
    const current = await api.cart(address).catch(() => null)
    if (current?.basket && current.basket.count > 0) { setExisting(current); return }
    await addToCart('replace')
  }

  const addToCart = async (mode: 'replace' | 'keep') => {
    if (!address || !plan) return
    setExisting(null)
    setCartBusy(true)
    setSheetError(null)
    try {
      const c = await api.fillCart(address, mode, shopLines())
      setCart(c)
      if (c.error) { setSheetError(c.error); setSheetOpen(true); return }
      const target = cartBtn.current?.getBoundingClientRect()
      const rows = [...document.querySelectorAll<HTMLElement>('[data-fly]')].filter((el) => !el.classList.contains('skipped'))
      if (!reduce && target && rows.length) {
        setFlyers(rows.slice(0, 14).map((el, i) => ({
          id: `${el.dataset.fly}-${Date.now()}`, label: el.querySelector('.need-name')?.textContent ?? '',
          from: el.getBoundingClientRect(), to: target, delay: i * 0.045,
        })))
      } else {
        setSheetOpen(true)
      }
    } catch (e) {
      setSheetError((e as Error).message)
      setSheetOpen(true)
    } finally {
      setCartBusy(false)
    }
  }

  const updateLine = async (line: CartLine, count: number) => {
    if (!address) return
    setBusyLine(line.item_uuid); setSheetError(null)
    try {
      const c = await api.updateLine(address, line, count)
      setCart((prev) => ({ ...c, failed_items: prev?.failed_items, payment_type: prev?.payment_type }))
      if (c.error) setSheetError(c.error)
    } catch (e) { setSheetError((e as Error).message) } finally { setBusyLine(null) }
  }

  const deleteLine = async (line: CartLine) => {
    if (!address) return
    setBusyLine(line.item_uuid); setSheetError(null)
    try { setCart(await api.deleteLine(address, line)) } catch (e) { setSheetError((e as Error).message) } finally { setBusyLine(null) }
  }

  const place = async (payment: Payment) => {
    if (!address || !cart?.basket || cart.total == null) return
    setPlacing(true); setSheetError(null)
    try {
      const r = await api.checkout(address, cart.total, payment.type, payment.id)
      if (r.error) {
        setSheetError(r.message ?? r.error)
        setCart(await api.cart(address))  // show the current total (it may have changed)
        return
      }
      setOrder({ result: r, lines: cart.basket.lines, total: r.amount ?? cart.total, payment: payment.label,
        address: `${address.title}, ${address.subTitle}` })
      setCart({ basket: null })
      setSheetOpen(false)
      go('track')
    } catch (e) {
      // A transport failure here might still have placed the order, so never retry automatically.
      setSheetError(`${(e as Error).message} Check your Careem orders before trying again.`)
    } finally {
      setPlacing(false)
    }
  }

  const restart = () => {
    setPlan(null); setOrder(null); setPrefs({ ...prefs, keep: [], exclude: [] }); setReached(['setup']); go('setup')
  }

  const count = cart?.basket?.count ?? 0
  const pantryNames = products

  return (
    <MotionConfig reducedMotion="user">
      <a href="#main" className="skip-link">Skip to content</a>
      <header className="topbar glass">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true"><ChefHat size={20} /></span>
          <span className="brand-name">Prep</span>
          <span className="brand-sub">with Careem Quik</span>
        </div>
        {boot && address && (
          <label className="address">
            <MapPin size={16} aria-hidden="true" />
            <span className="visually-hidden">Deliver to</span>
            <select aria-label="Deliver to" value={address.id} onChange={(e) => {
              const a = boot.addresses.find((x) => x.id === e.target.value)
              if (a) { setAddress(a); load(a) }
            }}>
              {boot.addresses.filter((a) => !a.test || dev).map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}
            </select>
          </label>
        )}
        <div className="topbar-actions">
          <button type="button" className="icon-btn" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
            {theme === 'dark' ? <Sun size={19} aria-hidden="true" /> : <Moon size={19} aria-hidden="true" />}
          </button>
          <button type="button" ref={cartBtn} className="cart-btn" onClick={() => { setSheetError(null); setSheetOpen(true) }}
            aria-label={`Open cart, ${count} ${count === 1 ? 'item' : 'items'}${cart?.total ? `, ${aed(cart.total)}` : ''}`}>
            <ShoppingCart size={19} aria-hidden="true" />
            <motion.span key={count} className="cart-count num" initial={reduce ? false : { scale: 1.6 }} animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 18 }}>{count}</motion.span>
          </button>
        </div>
      </header>

      <nav className="steps-nav" aria-label="Progress">
        <ol>
          {STEPS.map((s, i) => {
            const can = reached.includes(s.key) && !(s.key === 'track' && !order) && step !== 'track'
            return (
              <li key={s.key}>
                <button type="button" className={step === s.key ? 'stepper on' : 'stepper'} disabled={!can || step === s.key}
                  aria-current={step === s.key ? 'step' : undefined} onClick={() => go(s.key)}>
                  <span className="stepper-n num" aria-hidden="true">{i + 1}</span> {s.label}
                </button>
              </li>
            )
          })}
        </ol>
      </nav>

      <main id="main" ref={main} tabIndex={-1} className="main">
        {bootError && <Banner tone="error" action={<button type="button" className="btn btn-quiet" onClick={() => load(address ?? undefined)}>Try again</button>}>{bootError}</Banner>}
        {boot && !boot.serviceable && (
          <Banner tone="error">Careem Quik doesn't deliver to {address?.title ?? 'this address'}. You can still plan; pick another address to order.</Banner>
        )}
        {!boot && !bootError && <div className="loading" role="status">Loading your Careem profile…</div>}

        {boot && address && step === 'setup' && (
          <Setup boot={boot} address={address} prefs={prefs} setPrefs={setPrefs} pantryNames={pantryNames}
            rememberProduct={(p) => remember([p])} onSubmit={submitSetup} busy={planBusy} aiAvailable={boot.ai_available} />
        )}
        {step === 'plan' && planError && <PlanError message={planError} onBack={() => go('setup')} />}
        {step === 'plan' && plan && !plan.error && boot && (
          <PlanView plan={plan} deals={boot.deals} busySwap={swapBusy} onSwap={swap} onBack={() => go('setup')} onNext={() => go('shop')} />
        )}
        {step === 'shop' && plan && boot && (
          <Shop plan={plan} lines={lines} setLine={(id, l) => setLines({ ...lines, [id]: l })} serviceable={boot.serviceable}
            busy={cartBusy} onBack={() => go('plan')} onAddToCart={startAddToCart} />
        )}
        {step === 'track' && order && <Track order={order} onDone={restart} />}
      </main>

      {existing?.basket && (
        <div className="overlay center" role="presentation">
          <div className="dialog card" role="alertdialog" aria-modal="true" aria-labelledby="existing-h" aria-describedby="existing-d">
            <h2 id="existing-h">Your Careem Quik cart already has items</h2>
            <p id="existing-d" className="hint">
              {existing.basket.count} items ({aed(existing.total)}) are in your cart. Replace them with this plan's list, or keep them and add the new items.
            </p>
            <div className="dialog-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setExisting(null)}>Cancel</button>
              <button type="button" className="btn btn-ghost" onClick={() => addToCart('keep')}>Keep them and add</button>
              <button type="button" className="btn btn-primary" autoFocus onClick={() => addToCart('replace')}>Replace with this list</button>
            </div>
          </div>
        </div>
      )}

      <FlyLayer flyers={flyers} onDone={() => { setFlyers([]); setSheetOpen(true) }} />

      {address && (
        <CartSheet open={sheetOpen} cart={cart} address={address} budget={plan?.budget ?? null} dev={dev} busyLine={busyLine}
          placing={placing} error={sheetError} onClose={() => setSheetOpen(false)} onUpdate={updateLine} onDelete={deleteLine}
          onPlace={place} />
      )}
    </MotionConfig>
  )
}
