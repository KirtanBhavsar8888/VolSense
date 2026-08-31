import { useState, useEffect, useRef } from 'react'
import { DashboardShell } from '../components/dashboard/DashboardShell'
import { animate, stagger } from 'animejs'

import { API_BASE } from '../config'

type TradeLogEntry = {
  timestamp: string
  prices: Record<string, number>
  hold_minutes: number
}

type LegGreeks = {
  iv: number | null
  delta: number | null
}

type BacktestResult = {
  strategy: Record<string, unknown>
  entry_time: string
  entry_price: number
  exit_price: number
  exit_reason: string
  pnl_per_unit: number
  pnl_pct: number
  pnl: number | null
  greeks: { legs: LegGreeks[]; net_delta: number | null }
  legs: Array<{ option_type: string; strike: number; quantity: number; direction: string }>
  trade_log: TradeLogEntry[]
}

const STRATEGY_TYPES = [
  { value: 'atm_straddle', label: 'ATM Straddle' },
  { value: 'otm_strangle', label: 'OTM Strangle' },
  { value: 'single_leg', label: 'Single Leg' },
  { value: 'custom', label: 'Custom Strategy' },
]

type CustomLeg = {
  option_type: string
  moneyness: string
  offset: number
  direction: string
  quantity: number
}

const DIRECTIONS = [
  { value: 'long', label: 'Long' },
  { value: 'short', label: 'Short' },
]

const OPTION_TYPES = [
  { value: 'CE', label: 'Call (CE)' },
  { value: 'PE', label: 'Put (PE)' },
]

const MONEYNESS = [
  { value: 'ATM', label: 'ATM' },
  { value: 'OTM', label: 'OTM' },
  { value: 'ITM', label: 'ITM' },
]

const PRESET_TIMES = [
  '2026-08-28 10:30:00',
  '2026-08-28 11:30:00',
  '2026-08-28 13:15:00',
  '2026-08-28 15:20:00',
]

export function BacktestPage() {
  const [strategyType, setStrategyType] = useState('atm_straddle')
  const [direction, setDirection] = useState('long')
  const [quantity, setQuantity] = useState(1)
  const [targetDelta, setTargetDelta] = useState(0.25)
  const [optionType, setOptionType] = useState('CE')
  const [moneyness, setMoneyness] = useState('ATM')
  const [offset, setOffset] = useState(0)
  const [lotSize, setLotSize] = useState<number | ''>('')
  const [numLots, setNumLots] = useState<number>(1)
  const [customLegs, setCustomLegs] = useState<CustomLeg[]>([
    { option_type: 'CE', moneyness: 'ATM', offset: 0, direction: 'long', quantity: 1 },
  ])
  const [entryTime, setEntryTime] = useState('2026-08-28 10:30:00')
  const [stopLoss, setStopLoss] = useState(5.0)
  const [takeProfit, setTakeProfit] = useState(10.0)
  const [maxHold, setMaxHold] = useState(375)

  const [result, setResult] = useState<BacktestResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const resultsRef = useRef<HTMLDivElement>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    setLoading(true)

    const strategy: Record<string, unknown> = {
      type: strategyType,
      direction,
      quantity,
    }

    if (strategyType === 'otm_strangle') {
      strategy.target_delta = targetDelta
    } else if (strategyType === 'single_leg') {
      strategy.option_type = optionType
      strategy.moneyness = moneyness
      strategy.offset = offset
    } else if (strategyType === 'custom') {
      strategy.legs = customLegs
    }

    const body: Record<string, unknown> = {
      strategy,
      entry_time: entryTime,
      exit_rule: { stop_loss_pct: stopLoss, take_profit_pct: takeProfit, max_hold_minutes: maxHold },
    }
    if (lotSize !== '' && lotSize > 0) {
      body.lot_size = lotSize
      body.num_lots = numLots
    }

    try {
      const res = await fetch(`${API_BASE}/api/backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(data.detail || 'Backtest failed')
      }
      setResult(await res.json())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  // Stagger-animate results cards + trade timeline rows when new result arrives
  useEffect(() => {
    if (!result || !resultsRef.current) return
    const cards = resultsRef.current.querySelectorAll('[data-animate="bt-card"]')
    const rows = resultsRef.current.querySelectorAll('[data-animate="bt-row"]')
    const controls: ReturnType<typeof animate>[] = []
    if (cards.length) {
      controls.push(animate(cards, {
        opacity: [0, 1],
        translateY: [40, 0],
        duration: 1500,
        delay: stagger(210, { start: 100 }),
        ease: 'outQuad',
      }))
    }
    if (rows.length) {
      controls.push(animate(rows, {
        opacity: [0, 1],
        translateX: [30, 0],
        duration: 1200,
        delay: stagger(150, { start: 1000 }),
        ease: 'outQuad',
      }))
    }
    return () => { controls.forEach(c => { try { c.revert() } catch { /* noop */ } }) }
  }, [result])

  const pnlDisplay = result?.pnl ?? result?.pnl_per_unit ?? 0
  const isPnlPositive = pnlDisplay >= 0
  const netDelta = result?.greeks?.net_delta ?? null
  const isNeutral = netDelta !== null && Math.abs(netDelta) < 0.15

  return (
    <DashboardShell>
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-xl font-semibold text-[#e5e2e1]">Strategy Backtest</h1>
          <p className="text-sm text-[#8e9192]">Test option strategies against historical NIFTY chain data — entry/exit pricing, P&L, and trade timeline.</p>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          {/* ── Form ── */}
          <form onSubmit={handleSubmit} className="space-y-4 rounded border border-[#444748] bg-[#1c1b1b] p-5">
            <h2 className="text-sm font-medium uppercase tracking-[0.16em] text-[#8e9192]">Strategy</h2>

            {/* Strategy Type */}
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Type</span>
              <select value={strategyType} onChange={(e) => setStrategyType(e.target.value)} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]">
                {STRATEGY_TYPES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </label>

            {/* Direction + Quantity */}
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Direction</span>
                <select value={direction} onChange={(e) => setDirection(e.target.value)} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]">
                  {DIRECTIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Quantity</span>
                <input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]" />
              </label>
            </div>

            {/* OTM Strangle: target delta */}
            {strategyType === 'otm_strangle' && (
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Target Delta</span>
                <input type="number" step={0.01} min={0.05} max={0.50} value={targetDelta} onChange={(e) => setTargetDelta(Number(e.target.value))} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]" />
              </label>
            )}

            {/* Single Leg: option type, moneyness, offset */}
            {strategyType === 'single_leg' && (
              <div className="grid grid-cols-3 gap-3">
                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Option</span>
                  <select value={optionType} onChange={(e) => setOptionType(e.target.value)} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]">
                    {OPTION_TYPES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Moneyness</span>
                  <select value={moneyness} onChange={(e) => setMoneyness(e.target.value)} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]">
                    {MONEYNESS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Offset</span>
                  <input type="number" value={offset} onChange={(e) => setOffset(Number(e.target.value))} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]" />
                </label>
              </div>
            )}

            {/* Custom Strategy: multi-leg builder */}
            {strategyType === 'custom' && (
              <div className="space-y-3">
                <hr className="border-[#444748]" />
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-medium uppercase tracking-[0.16em] text-[#8e9192]">Strategy Legs</h2>
                  <button
                    type="button"
                    onClick={() => setCustomLegs([...customLegs, { option_type: 'PE', moneyness: 'OTM', offset: 1, direction: 'long', quantity: 1 }])}
                    className="rounded border border-[#44d8f1]/40 bg-[#44d8f1]/10 px-3 py-1 text-xs font-medium text-[#44d8f1] transition hover:bg-[#44d8f1]/20"
                  >
                    + Add Leg
                  </button>
                </div>

                {customLegs.map((leg, idx) => (
                  <div key={idx} className="rounded border border-[#444748] bg-[#111827] p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8e9192]">Leg {idx + 1}</span>
                      {customLegs.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setCustomLegs(customLegs.filter((_, i) => i !== idx))}
                          className="rounded border border-rose-500/40 bg-rose-500/10 px-2 py-0.5 text-[10px] font-medium text-rose-400 transition hover:bg-rose-500/20"
                        >
                          Remove
                        </button>
                      )}
                    </div>

                    <div className="grid grid-cols-5 gap-2">
                      <label className="block">
                        <span className="mb-0.5 block text-[9px] uppercase tracking-[0.12em] text-[#8e9192]">Type</span>
                        <select
                          value={leg.option_type}
                          onChange={(e) => {
                            const updated = [...customLegs]
                            updated[idx] = { ...updated[idx], option_type: e.target.value }
                            setCustomLegs(updated)
                          }}
                          className="w-full rounded border border-[#444748] bg-[#1c1b1b] p-1.5 text-xs text-[#e5e2e1] outline-none focus:border-[#44d8f1]"
                        >
                          {OPTION_TYPES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </label>

                      <label className="block">
                        <span className="mb-0.5 block text-[9px] uppercase tracking-[0.12em] text-[#8e9192]">Moneyness</span>
                        <select
                          value={leg.moneyness}
                          onChange={(e) => {
                            const updated = [...customLegs]
                            updated[idx] = { ...updated[idx], moneyness: e.target.value }
                            setCustomLegs(updated)
                          }}
                          className="w-full rounded border border-[#444748] bg-[#1c1b1b] p-1.5 text-xs text-[#e5e2e1] outline-none focus:border-[#44d8f1]"
                        >
                          {MONEYNESS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                        </select>
                      </label>

                      <label className="block">
                        <span className="mb-0.5 block text-[9px] uppercase tracking-[0.12em] text-[#8e9192]">Offset</span>
                        <input
                          type="number"
                          value={leg.offset}
                          onChange={(e) => {
                            const updated = [...customLegs]
                            updated[idx] = { ...updated[idx], offset: Number(e.target.value) }
                            setCustomLegs(updated)
                          }}
                          className="w-full rounded border border-[#444748] bg-[#1c1b1b] p-1.5 text-xs text-[#e5e2e1] outline-none focus:border-[#44d8f1]"
                        />
                      </label>

                      <label className="block">
                        <span className="mb-0.5 block text-[9px] uppercase tracking-[0.12em] text-[#8e9192]">Direction</span>
                        <select
                          value={leg.direction}
                          onChange={(e) => {
                            const updated = [...customLegs]
                            updated[idx] = { ...updated[idx], direction: e.target.value }
                            setCustomLegs(updated)
                          }}
                          className="w-full rounded border border-[#444748] bg-[#1c1b1b] p-1.5 text-xs text-[#e5e2e1] outline-none focus:border-[#44d8f1]"
                        >
                          {DIRECTIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
                        </select>
                      </label>

                      <label className="block">
                        <span className="mb-0.5 block text-[9px] uppercase tracking-[0.12em] text-[#8e9192]">Qty</span>
                        <input
                          type="number"
                          min={1}
                          value={leg.quantity}
                          onChange={(e) => {
                            const updated = [...customLegs]
                            updated[idx] = { ...updated[idx], quantity: Number(e.target.value) }
                            setCustomLegs(updated)
                          }}
                          className="w-full rounded border border-[#444748] bg-[#1c1b1b] p-1.5 text-xs text-[#e5e2e1] outline-none focus:border-[#44d8f1]"
                        />
                      </label>
                    </div>
                  </div>
                ))}

                <p className="text-[10px] text-[#8e9192]">
                  Add legs to build any strategy — Butterfly, Iron Condor, Calendar Spread, etc. Each leg resolves to a real strike from the chain data.
                </p>
              </div>
            )}

            <hr className="border-[#444748]" />
            <h2 className="text-sm font-medium uppercase tracking-[0.16em] text-[#8e9192]">Position Sizing</h2>

            {/* Lot Size + Num Lots */}
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Lot Size</span>
                <input
                  type="number"
                  min={1}
                  value={lotSize}
                  onChange={(e) => setLotSize(e.target.value === '' ? '' : Number(e.target.value))}
                  placeholder="e.g. 25"
                  className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1] placeholder:text-[#555]"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Number of Lots</span>
                <input type="number" min={1} value={numLots} onChange={(e) => setNumLots(Number(e.target.value))} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]" />
              </label>
            </div>

            <hr className="border-[#444748]" />
            <h2 className="text-sm font-medium uppercase tracking-[0.16em] text-[#8e9192]">Entry & Exit</h2>

            {/* Entry Time */}
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Entry Time</span>
              <select value={entryTime} onChange={(e) => setEntryTime(e.target.value)} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]">
                {PRESET_TIMES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>

            {/* SL / TP / Hold */}
            <div className="grid grid-cols-3 gap-3">
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Stop Loss %</span>
                <input type="number" step={0.5} value={stopLoss} onChange={(e) => setStopLoss(Number(e.target.value))} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]" />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Take Profit %</span>
                <input type="number" step={0.5} value={takeProfit} onChange={(e) => setTakeProfit(Number(e.target.value))} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]" />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.14em] text-[#8e9192]">Max Hold (min)</span>
                <input type="number" value={maxHold} onChange={(e) => setMaxHold(Number(e.target.value))} className="w-full rounded border border-[#444748] bg-[#111827] p-2.5 text-sm text-[#e5e2e1] outline-none focus:border-[#44d8f1]" />
              </label>
            </div>

            <button type="submit" disabled={loading} className="mt-2 w-full rounded bg-[#44d8f1] px-4 py-3 font-semibold text-[#0a0a0a] transition hover:bg-[#33c4dd] disabled:cursor-not-allowed disabled:opacity-60">
              {loading ? 'Running…' : 'Run Backtest'}
            </button>
          </form>

          {/* ── Results ── */}
          <div className="space-y-4">
            {error && (
              <div className="rounded border border-rose-500/50 bg-rose-950/40 p-4 text-sm text-rose-200">
                {error}
              </div>
            )}

            {!result && !error && !loading && (
              <div className="flex h-64 items-center justify-center rounded border border-[#444748] bg-[#1c1b1b] text-sm text-[#8e9192]">
                Configure a strategy and click Run Backtest
              </div>
            )}

            {result && (
              <div ref={resultsRef}>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 gap-4">
                  <div data-animate="bt-card" className="rounded border border-[#444748] bg-[#1c1b1b] p-4 opacity-0">
                    <div className="text-xs uppercase tracking-[0.16em] text-[#8e9192]">Entry Price</div>
                    <div className="mt-1 text-lg font-mono text-[#e5e2e1]">₹{result.entry_price.toFixed(2)}</div>
                  </div>
                  <div data-animate="bt-card" className="rounded border border-[#444748] bg-[#1c1b1b] p-4 opacity-0">
                    <div className="text-xs uppercase tracking-[0.16em] text-[#8e9192]">Exit Price</div>
                    <div className="mt-1 text-lg font-mono text-[#e5e2e1]">₹{result.exit_price.toFixed(2)}</div>
                  </div>
                  <div data-animate="bt-card" className="rounded border border-[#444748] bg-[#1c1b1b] p-4 opacity-0">
                    <div className="text-xs uppercase tracking-[0.16em] text-[#8e9192]">P&L</div>
                    {result.pnl !== null ? (
                      <>
                        <div className={`mt-1 text-lg font-mono font-bold ${isPnlPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {isPnlPositive ? '+' : ''}₹{result.pnl.toFixed(2)} ({isPnlPositive ? '+' : ''}{result.pnl_pct.toFixed(2)}%)
                        </div>
                        <div className="mt-0.5 text-xs font-mono text-[#8e9192]">
                          ₹{result.pnl_per_unit.toFixed(2)} per unit
                        </div>
                      </>
                    ) : (
                      <div className={`mt-1 text-lg font-mono font-bold ${isPnlPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isPnlPositive ? '+' : ''}₹{result.pnl_per_unit.toFixed(2)} ({isPnlPositive ? '+' : ''}{result.pnl_pct.toFixed(2)}%)
                      </div>
                    )}
                  </div>
                  <div data-animate="bt-card" className="rounded border border-[#444748] bg-[#1c1b1b] p-4 opacity-0">
                    <div className="text-xs uppercase tracking-[0.16em] text-[#8e9192]">Exit Reason</div>
                    <div className="mt-1 text-lg font-mono text-[#e5e2e1] capitalize">{result.exit_reason.replace('_', ' ')}</div>
                  </div>
                </div>

                {/* Entry Greeks */}
                {result.greeks && (
                  <div data-animate="bt-card" className="rounded border border-[#444748] bg-[#1c1b1b] p-4 opacity-0">
                    <div className="mb-3 flex items-center gap-3">
                      <span className="text-xs uppercase tracking-[0.16em] text-[#8e9192]">Entry Greeks</span>
                      {netDelta !== null && (
                        <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${isNeutral ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                          Δ {netDelta >= 0 ? '+' : ''}{netDelta.toFixed(4)} {isNeutral ? '≈ neutral' : ''}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="mb-1 text-[10px] uppercase tracking-[0.14em] text-[#8e9192]">Net Delta</div>
                        <div className={`text-2xl font-mono font-bold ${isNeutral ? 'text-emerald-400' : 'text-amber-400'}`}>
                          {netDelta !== null ? (netDelta >= 0 ? '+' : '') + netDelta.toFixed(4) : '—'}
                        </div>
                        <div className="mt-1 text-[10px] text-[#8e9192]">
                          {isNeutral ? 'Position is delta-neutral' : 'Position has directional exposure'}
                        </div>
                      </div>
                      <div className="space-y-1">
                        {result.greeks.legs.map((lg, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs">
                            <span className="font-mono text-[#e5e2e1]">{result.legs[i]?.option_type} K={result.legs[i]?.strike}</span>
                            <span className="text-[#8e9192]">IV={lg.iv !== null ? (lg.iv * 100).toFixed(1) + '%' : '—'}</span>
                            <span className="text-[#8e9192]">Δ={lg.delta !== null ? lg.delta.toFixed(4) : '—'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Legs */}
                <div data-animate="bt-card" className="rounded border border-[#444748] bg-[#1c1b1b] p-4 opacity-0">
                  <div className="mb-3 text-xs uppercase tracking-[0.16em] text-[#8e9192]">Legs</div>
                  <div className="space-y-2">
                    {result.legs.map((leg, i) => {
                      const greeks = result.greeks?.legs?.[i]
                      return (
                        <div key={i} className="flex items-center gap-3 text-sm">
                          <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${leg.direction === 'long' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                            {leg.direction}
                          </span>
                          <span className="text-[#e5e2e1]">{leg.quantity}x {leg.option_type}</span>
                          <span className="font-mono text-[#8e9192]">K={leg.strike}</span>
                          {greeks && greeks.iv !== null && (
                            <span className="text-xs text-[#8e9192]">IV={(greeks.iv * 100).toFixed(1)}%</span>
                          )}
                          {greeks && greeks.delta !== null && (
                            <span className="text-xs text-[#8e9192]">Δ={greeks.delta.toFixed(4)}</span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Trade Timeline */}
                {result.trade_log.length > 0 && (
                  <div data-animate="bt-card" className="rounded border border-[#444748] bg-[#1c1b1b] p-4 opacity-0">
                    <div className="mb-3 text-xs uppercase tracking-[0.16em] text-[#8e9192]">Trade Timeline ({result.trade_log.length} bars)</div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-[#444748] text-left text-[#8e9192]">
                            <th className="pb-2 pr-4">Time</th>
                            <th className="pb-2 pr-4">Hold (min)</th>
                            {result.legs.map((leg, i) => (
                              <th key={i} className="pb-2 pr-4">{leg.option_type} K={leg.strike}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {result.trade_log.map((row, i) => {
                            const isEntry = i === 0
                            const isExit = i === result.trade_log.length - 1
                            return (
                              <tr key={i} data-animate="bt-row" className={`border-b border-[#444748]/50 opacity-0 ${isEntry ? 'bg-emerald-500/10' : isExit ? 'bg-rose-500/10' : ''}`}>
                                <td className="py-1.5 pr-4 font-mono text-[#e5e2e1]">
                                  {isEntry && '▶ '}{isExit && '⏹ '}
                                  {new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </td>
                                <td className="py-1.5 pr-4 font-mono text-[#8e9192]">{row.hold_minutes}</td>
                                {result.legs.map((leg, j) => {
                                  const key = `${leg.option_type}_K${leg.strike}`
                                  return (
                                    <td key={j} className="py-1.5 pr-4 font-mono text-[#e5e2e1]">
                                      ₹{(row.prices[key] ?? 0).toFixed(2)}
                                    </td>
                                  )
                                })}
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardShell>
  )
}
