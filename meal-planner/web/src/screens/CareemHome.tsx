import { ChevronRight, House, ReceiptText, Search, ShoppingCart, User } from 'lucide-react'

// The Careem super-app home, recreated for the demo. Only "Meal prep" works; every other tile,
// card and tab is for show, so they're plain elements, not buttons, and can't take focus.
const SERVICES = [
  { label: 'Rides', art: '🚗' },
  { label: 'Food', art: '🍔' },
  { label: 'Groceries', art: '🧺' },
  { label: 'Shops', art: '🛍️' },
  { label: 'Taxi', art: '🚕' },
  { label: 'Box', art: '🛵', badge: 'Send' },
  { label: 'DineOut', art: '🍽️' },
  { label: 'Pay', art: '🪙' },
]

export function CareemHome({ name, onMealPrep }: { name: string; onMealPrep: () => void }) {
  return (
    <div className="careem-home">
      <header className="ch-header">
        <div className="ch-search" aria-hidden="true">
          <span>Discover food</span>
          <Search size={24} strokeWidth={2} />
        </div>
      </header>

      <main className="ch-sheet" aria-label="Careem home">
        <h1 className="visually-hidden">Careem, welcome {name}</h1>
        <div className="ch-tiles">
          {SERVICES.map((s) => (
            <div key={s.label} className="ch-tile" aria-disabled="true">
              {s.badge && <span className="ch-badge">{s.badge}</span>}
              <span className="ch-art" aria-hidden="true">{s.art}</span>
              <span className="ch-label">{s.label}</span>
            </div>
          ))}
        </div>

        <button type="button" className="ch-mealprep" onClick={onMealPrep}>
          <span className="ch-mp-art" aria-hidden="true">🥗</span>
          <span className="ch-mp-text">
            <span className="ch-mp-title">Meal prep <span className="ch-new">New</span></span>
            <span className="ch-mp-sub">Plan your week, order the groceries on Careem Quik</span>
          </span>
          <ChevronRight size={22} aria-hidden="true" className="ch-mp-go" />
        </button>

        <div className="ch-cards" aria-hidden="true">
          <div className="ch-card"><span><span className="ch-card-k">Balance</span><span className="ch-card-v">AED 0.05</span></span><span className="ch-card-art">👛</span></div>
          <div className="ch-card"><span><span className="ch-card-k">Ride to</span><span className="ch-card-v">Home</span></span><span className="ch-card-art">🚘</span></div>
          <div className="ch-card"><span><span className="ch-card-k">Add card</span><span className="ch-card-v">Set up payment</span></span></div>
        </div>

        <section className="ch-promo" aria-hidden="true">
          <span className="ch-gift">🎁</span>
          <span className="ch-promo-tag">3 months <small>for AED 15</small></span>
          <p className="ch-promo-title">Limited time offer!</p>
          <p className="ch-promo-sub">Careem Plus offer just for you</p>
          <span className="ch-promo-btn">Subscribe for 3 months at AED 15</span>
        </section>
      </main>

      <nav className="ch-tabbar" aria-hidden="true">
        <span className="ch-tab on"><House size={24} /> Home</span>
        <span className="ch-tab"><ReceiptText size={24} /> Activities</span>
        <span className="ch-tab"><ShoppingCart size={24} /> Carts</span>
        <span className="ch-tab"><User size={24} /> Profile</span>
      </nav>
    </div>
  )
}
