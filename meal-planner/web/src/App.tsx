import { ChefHat, ChevronLeft, MapPin, Moon, ShoppingCart, Sun } from 'lucide-react'
import { MotionConfig, motion, useReducedMotion } from 'motion/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { aed, api, type Address, type Bootstrap, type Cart, type CartLine, type Plan, type Product, type Recipe } from './api'
import { CartSheet, type Payment } from './CartSheet'
import { FlyLayer, type Flyer } from './FlyLayer'
import { lineFor, screenRect, scrollScreenTop, type ShopLine } from './helpers'
import { BehindScenes } from './BehindScenes'
import { ErrorBoundary } from './ErrorBoundary'
import { PhoneFrame } from './PhoneFrame'
import { CareemHome } from './screens/CareemHome'
import { PlanLoader } from './screens/PlanLoader'
import { RecipeDrawer } from './RecipeDrawer'
import { PlanError, PlanView } from './screens/PlanView'
import { Shop } from './screens/Shop'
import { Track, type Order } from './screens/Track'
import { Banner } from './ui'
import { DEFAULT_ANSWERS, planBody, type Answers } from './wizard/answers'
import { Wizard } from './wizard/Wizard'

type View = 'home' | 'wizard' | 'loading' | 'plan' | 'track'

export default function App() {
  const dev = useMemo(() => new URLSearchParams(location.search).has('dev'), [])
  const reduce = useReducedMotion()
  const [theme, setTheme] = useState<'dark' | 'light'>(() => (localStorage.getItem('theme') as 'dark' | 'light') ?? 'dark')
  const [boot, setBoot] = useState<Bootstrap | null>(null)
  const [bootError, setBootError] = useState<string | null>(null)
  const [address, setAddress] = useState<Address | null>(null)
  const [products, setProducts] = useState<Map<number, Product>>(new Map())
  const [view, setView] = useState<View>('home')
  const [pending, setPending] = useState<Plan | null>(null)
  const [wizardStep, setWizardStep] = useState(0)
  const [answers, setAnswers] = useState<Answers>(DEFAULT_ANSWERS)
  const [tab, setTab] = useState<'plan' | 'shop'>('plan')
  const [plan, setPlan] = useState<Plan | null>(null)
  const [planBusy, setPlanBusy] = useState(false)
  const [planError, setPlanError] = useState<string | null>(null)
  const [exclude, setExclude] = useState<string[]>([])
  const [swapBusy, setSwapBusy] = useState(false)
  const [openRecipe, setOpenRecipe] = useState<string | null>(null)
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
  const [scenes, setScenes] = useState(() => localStorage.getItem('scenes') !== 'hidden')
  useEffect(() => { localStorage.setItem('scenes', scenes ? 'shown' : 'hidden') }, [scenes])
  const cartBtn = useRef<HTMLButtonElement>(null)

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
  useEffect(() => { if (address) api.cart(address).then(setCart).catch(() => undefined) }, [address])

  const closeRecipe = useCallback(() => setOpenRecipe(null), [])
  const top = () => scrollScreenTop(!reduce)

  const buildPlan = async (extra: Record<string, unknown> = {}) => {
    if (!address) return null
    setPlanError(null)
    try {
      const p = await api.plan(planBody(answers, extra), address)
      if (p.error) { setPlanError(p.error); return null }
      return p
    } catch (e) {
      setPlanError((e as Error).message)
      return null
    }
  }

  // the loader shows the checks while the real plan is built; it hands over once both are done
  const finishWizard = async () => {
    setPlanBusy(true)
    setExclude([])
    setPending(null)
    setView('loading')
    scrollScreenTop()
    const p = await buildPlan()
    setPlanBusy(false)
    if (p) setPending(p)
  }
  const showPlan = useCallback(() => {
    setPlan(pending); setLines({}); setTab('plan'); setView('plan'); scrollScreenTop()
  }, [pending])

  const swap = async (id: string) => {
    if (!plan) return
    setSwapBusy(true)
    const keep = plan.recipes.map((r) => r.id).filter((r) => r !== id)
    const ex = [...new Set([...exclude, id])]
    setExclude(ex)
    const next = await buildPlan({ keep, exclude: ex })
    setSwapBusy(false)
    if (!next) return
    // a swap is planned by rules; keep Claude's summary and notes for the meals that stayed
    const why = new Map(plan.recipes.map((r) => [r.id, r.why]))
    setPlan(plan.ai?.used ? { ...next, ai: plan.ai, recipes: next.recipes.map((r) => ({ ...r, why: r.why ?? why.get(r.id) ?? null })) } : next)
    setLines({})
    setOpenRecipe(null)
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
      // chips launch only from rows the user can see; with none in view, from the button they pressed
      const box = document.getElementById('phone-screen')?.getBoundingClientRect()
      const inView = (el: Element) => { const r = el.getBoundingClientRect(); return !box || (r.bottom > box.top + 40 && r.top < box.bottom - 40) }
      let rows = [...document.querySelectorAll<HTMLElement>('[data-fly]')].filter((el) => !el.classList.contains('skipped') && inView(el))
      if (!rows.length) {
        const btn = document.querySelector<HTMLElement>('.shop-actions .btn-primary')
        if (btn) { btn.dataset.fly = 'cta'; rows = [btn] }
      }
      if (!reduce && target && rows.length) {
        setFlyers(rows.slice(0, 14).map((el, i) => ({
          id: `${el.dataset.fly}-${Date.now()}-${i}`, label: el.querySelector('.need-name')?.textContent ?? `${shopLines().length} items`,
          from: screenRect(el.getBoundingClientRect()), to: screenRect(target), delay: i * 0.045,
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
      setView('track')
      top()
    } catch (e) {
      // A transport failure here might still have placed the order, so never retry automatically.
      setSheetError(`${(e as Error).message} Check your Careem orders before trying again.`)
    } finally {
      setPlacing(false)
    }
  }

  const count = cart?.basket?.count ?? 0
  const recipe: Recipe | null = (plan && openRecipe && plan.recipes.find((r) => r.id === openRecipe)) || null

  return (
    <MotionConfig reducedMotion="user">
      <PhoneFrame tone={view === 'home' ? 'careem' : 'app'}
        aside={<BehindScenes hidden={!scenes} />}
        below={
          <button type="button" className="scenes-toggle" aria-pressed={scenes} onClick={() => setScenes(!scenes)}>
            {scenes ? 'Hide behind the scenes' : 'Show behind the scenes'}
          </button>
        }>
      <ErrorBoundary onReset={() => { setSheetOpen(false); setOpenRecipe(null); setView('home') }}>
      {view === 'home' ? (
        <CareemHome name={boot?.user.name ?? 'there'} onMealPrep={() => { setView(plan ? 'plan' : 'wizard'); scrollScreenTop() }} />
      ) : (<>
      <a href="#main" className="skip-link">Skip to content</a>
      <header className="topbar glass">
        <button type="button" className="icon-btn back-home" aria-label="Back to Careem home" disabled={view === 'loading'}
          onClick={() => { setView('home'); scrollScreenTop() }}>
          <ChevronLeft size={22} aria-hidden="true" />
        </button>
        <div className="brand">
          <span className="brand-mark" aria-hidden="true"><ChefHat size={20} /></span>
          <span className="brand-name">Prep</span>
          <span className="brand-sub">with Careem Quik</span>
        </div>
        {boot && address && (
          <label className="address">
            <MapPin size={16} aria-hidden="true" />
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
            <motion.span key={count} className="cart-count" initial={reduce ? false : { scale: 1.6 }} animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 18 }}>{count}</motion.span>
          </button>
        </div>
      </header>

      <main id="main" tabIndex={-1} className={view === 'wizard' ? 'main main-wizard' : 'main'}>
        {bootError && <Banner tone="error" action={<button type="button" className="btn btn-quiet" onClick={() => load(address ?? undefined)}>Try again</button>}>{bootError}</Banner>}
        {boot && !boot.serviceable && (
          <Banner tone="error">Careem Quik doesn't deliver to {address?.title ?? 'this address'}. You can still plan; pick another address to order.</Banner>
        )}
        {!boot && !bootError && <div className="loading" role="status">Loading your Careem profile…</div>}

        {boot && address && view === 'wizard' && (
          <Wizard answers={answers} setAnswers={setAnswers} step={wizardStep} setStep={setWizardStep} address={address}
            aiAvailable={boot.ai_available} products={products} remember={(p) => remember([p])} busy={planBusy}
            error={planError} onDone={finishWizard} />
        )}
        {view === 'loading' && (
          <PlanLoader answers={answers} ai={!!boot?.ai_available} ready={!!pending} error={planError} onFinished={showPlan}
            onBack={() => { setPlanError(null); setView('wizard') }} />
        )}
        {view === 'plan' && planError && <PlanError message={planError} onBack={() => setView('wizard')} />}
        {view === 'plan' && plan && boot && (
          <PlanView plan={plan} deals={boot.deals} tab={tab} setTab={(t) => { setTab(t); top() }} onOpen={(r) => setOpenRecipe(r.id)}
            onEdit={() => { setWizardStep(0); setView('wizard') }}
            shop={<Shop plan={plan} lines={lines} setLine={(id, l) => setLines({ ...lines, [id]: l })} serviceable={boot.serviceable}
              busy={cartBusy} onBack={() => { setTab('plan'); top() }} onAddToCart={startAddToCart} />} />
        )}
        {view === 'track' && order && <Track order={order} onDone={() => { setOrder(null); setPlan(null); setWizardStep(0); setView('wizard') }} />}
      </main>

      {plan && <RecipeDrawer recipe={recipe} plan={plan} swapBusy={swapBusy} onClose={closeRecipe} onSwap={swap} />}

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
      </>)}
      </ErrorBoundary>
      </PhoneFrame>
    </MotionConfig>
  )
}
