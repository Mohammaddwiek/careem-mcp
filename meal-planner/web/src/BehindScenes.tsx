import { useEffect, useRef, useState } from 'react'

interface McpEvent {
  seq: number
  at: number
  stage: string
  tool: string
  what: string
  mutating: boolean
  ms: number
  args: Record<string, unknown>
  ok: boolean
  result: string
}

const GUIDE: [string, string][] = [
  ['user_info', 'Who is the customer, plus saved addresses'],
  ['search_groceries_items', 'Match every ingredient to a real Quik product'],
  ['create_grocery_cart_with_quantities', 'Put the whole list into the Quik basket'],
  ['cart_get_basket_price', 'Fees, discounts and the final total'],
  ['cart_grocery_checkout', 'Place the order'],
]

/** Short, readable version of a call's arguments (drops coordinates, which every call carries). */
function argText(args: Record<string, unknown>) {
  const parts = Object.entries(args)
    .filter(([k]) => k !== 'latitude' && k !== 'longitude')
    .map(([k, v]) => {
      if (Array.isArray(v)) return `${k}: ${v.length} ${v.length === 1 ? 'item' : 'items'}`
      const s = typeof v === 'string' ? v : JSON.stringify(v)
      return `${k}: ${s.length > 28 ? `${s.slice(0, 28)}…` : s}`
    })
  return parts.join(' · ')
}

/** "Behind the scenes": every Careem MCP call the app makes, live, beside the phone. */
export function BehindScenes({ hidden }: { hidden: boolean }) {
  const [events, setEvents] = useState<McpEvent[]>([])
  const [info, setInfo] = useState<{ ai: boolean; model: string | null; mcp_url: string } | null>(null)
  const [online, setOnline] = useState(true)
  const cursor = useRef(0)

  useEffect(() => {
    let stop = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const r = await fetch(`/api/mcp-log?after=${cursor.current}`)
        const body = await r.json()
        if (stop) return
        setOnline(r.ok)
        setInfo({ ai: body.ai, model: body.model, mcp_url: body.mcp_url })
        if (body.events?.length) {
          cursor.current = body.events[body.events.length - 1].seq
          setEvents((prev) => [...prev, ...body.events].slice(-150))
        }
      } catch {
        if (!stop) setOnline(false)
      }
      if (!stop) timer = setTimeout(poll, 800)
    }
    // start from now: calls made before the panel opened aren't replayed
    fetch('/api/mcp-log').then((r) => r.json()).then((b) => {
      cursor.current = Math.max(0, ...((b.events ?? []) as McpEvent[]).map((e) => e.seq))
    }).catch(() => undefined).finally(poll)
    return () => { stop = true; clearTimeout(timer) }
  }, [])

  const shown = [...events].reverse()
  return (
    // stays mounted while hidden, so the history is still there when it comes back
    <aside className="scenes" aria-labelledby="scenes-h" hidden={hidden}>
      <div className="scenes-head">
        <div>
          <p className="scenes-eyebrow">Behind the scenes</p>
          <h2 id="scenes-h">Live Careem MCP calls</h2>
        </div>
        <button type="button" className="scenes-clear" onClick={() => setEvents([])} disabled={!events.length}>Clear</button>
      </div>

      <div className="scenes-chips">
        <div className="scenes-chip">
          <span className="chip-title"><span className={online ? 'dot on' : 'dot off'} aria-hidden="true" />Careem MCP</span>
          <span className="chip-sub">{online ? info?.mcp_url ?? 'connecting…' : 'not reachable'}</span>
        </div>
        <div className="scenes-chip">
          <span className="chip-title"><span className={info?.ai ? 'dot on' : 'dot idle'} aria-hidden="true" />AI planner: {info?.ai ? 'Claude' : 'rules'}</span>
          <span className="chip-sub">{info?.ai ? info.model : 'No Claude key set'}</span>
        </div>
      </div>

      <div className="scenes-body" aria-live="polite" aria-relevant="additions">
        {shown.length === 0 ? (
          <div className="scenes-empty">
            <p>Use the app. Every Careem tool call appears here in real time.</p>
            <ul>{GUIDE.map(([t, d]) => <li key={t}><code>{t}</code>: {d}</li>)}</ul>
          </div>
        ) : (
          <ol className="scenes-list">
            {shown.map((e) => (
              <li key={e.seq} className={`call${e.ok ? '' : ' failed'}`}>
                <div className="call-top">
                  <span className="call-stage">{e.stage}</span>
                  <span className="call-time">{new Date(e.at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })} · {e.ms} ms</span>
                </div>
                <code className="call-tool">{e.tool}</code>
                {e.mutating && <span className="call-flag">Changes the customer's cart or order</span>}
                <p className="call-what">{e.what}</p>
                {argText(e.args) && <p className="call-args">{argText(e.args)}</p>}
                <p className="call-result">{e.ok ? '→ ' : '✕ '}{e.result}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </aside>
  )
}
