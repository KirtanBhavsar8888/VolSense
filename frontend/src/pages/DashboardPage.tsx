import { Suspense, lazy, useEffect } from 'react'
import { animate, stagger } from 'animejs'

import { DashboardShell } from '../components/dashboard/DashboardShell'
import { ComparisonPanel } from '../components/dashboard/ComparisonPanel'
import { EvaluationTable } from '../components/dashboard/EvaluationTable'
import { MetricCard } from '../components/dashboard/MetricCard'
import { useAnalysisSession } from '../hooks/useApi'

const SkewChart = lazy(() =>
  import('../components/dashboard/SkewChart').then((module) => ({ default: module.SkewChart })),
)

export function DashboardPage() {
  const { data, status, error, isRunning, runAnalysis, sessionId } = useAnalysisSession()
  const metrics = data?.metrics ?? []
  const skewSeries = data?.skewSeries ?? []
  const trajectory = data?.trajectory ?? []
  const capabilityBars = data?.capabilityBars ?? []
  const evaluationRows = data?.evaluationRows ?? []

  // ── Anime.js stagger reveals ──
  useEffect(() => {
    const sections = document.querySelectorAll('[data-animate="section"]')
    if (sections.length) {
      animate(sections, {
        opacity: [0, 1],
        translateY: [40, 0],
        duration: 1500,
        delay: stagger(240, { start: 200 }),
        ease: 'outQuad',
      })
    }
    const cards = document.querySelectorAll('[data-animate="card"]')
    if (cards.length) {
      animate(cards, {
        opacity: [0, 1],
        translateY: [40, 0],
        duration: 1500,
        delay: stagger(180, { start: 800 }),
        ease: 'outQuad',
      })
    }
    const bars = document.querySelectorAll('[data-animate="bar"]')
    if (bars.length) {
      animate(bars, {
        width: ['0%', (el: HTMLElement) => el.dataset.barWidth ?? '0%'],
        duration: 2400,
        delay: stagger(300, { start: 1500 }),
        ease: 'outQuad',
      })
    }
  }, [metrics.length, skewSeries.length, capabilityBars.length])

  return (
    <DashboardShell>
      <div className="space-y-6 p-6">
        <div data-animate="section" className="opacity-0">
          <h1 className="text-xl font-semibold text-[#e5e2e1]">Dashboard</h1>
          <p className="text-sm text-[#8e9192]">Live session overview — current skew curve, evaluation score, and agent status at a glance.</p>
        </div>
        <section data-animate="section" className="flex flex-wrap items-center justify-between gap-4 rounded border border-slate-700 bg-[#1b1b1b] p-4 opacity-0">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Live pipeline</div>
            <div className="mt-1 text-lg text-slate-100">
              {sessionId ? `Session ${sessionId.slice(0, 8)}… · ${status}` : 'No session yet'}
            </div>
            {error ? <div className="mt-2 text-sm text-rose-300">{error}</div> : null}
            {data?.errorMessage ? <div className="mt-2 text-sm text-rose-300">{data.errorMessage}</div> : null}
          </div>
          <button
            type="button"
            onClick={() => void runAnalysis()}
            disabled={isRunning}
            className="rounded bg-cyan-400 px-4 py-2 text-sm font-semibold text-[#111827] transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRunning ? 'Running analysis…' : 'Run analysis'}
          </button>
        </section>

        <section data-animate="section" className="grid gap-6 xl:grid-cols-[2fr_1fr] opacity-0">
          <div className="rounded border border-slate-700 bg-[#1b1b1b] p-4">
            <div className="mb-4 flex items-center justify-between">
              <span className="text-xs uppercase tracking-[0.2em] text-slate-400">Session skew</span>
              <span className="text-xs text-cyan-400">25Δ over time</span>
            </div>
            <Suspense fallback={<div className="h-[360px] rounded border border-slate-700 bg-[#111827] p-4 text-slate-300">Loading chart…</div>}>
              <SkewChart data={skewSeries} />
            </Suspense>
          </div>

          <div className="space-y-4">
            {metrics.length
              ? metrics.map((card) => <MetricCard key={card.label} {...card} />)
              : ['Session close skew', 'Evaluation score', 'Agent status', 'Skew samples'].map((label) => (
                  <MetricCard key={label} label={label} value="—" delta="Run analysis to populate" tone="neutral" />
                ))}
          </div>
        </section>

        <section data-animate="section" className="grid gap-6 xl:grid-cols-[2fr_1fr] opacity-0">
          <ComparisonPanel
            baselinePreview={data?.baselinePreview ?? 'Click Run analysis to compare the baseline prompt with the calc/agent path.'}
            agentPreview={data?.agentPreview ?? 'Agent output will appear here after the pipeline finishes.'}
            model={data?.summary.model}
          />

          <div className="rounded border border-slate-700 bg-[#1b1b1b] p-4">
            <div className="mb-4 border-b border-slate-700 pb-3 text-[10px] uppercase tracking-[0.2em] text-slate-400">Agent trajectory</div>
            <div className="space-y-5">
              {trajectory.length ? (
                trajectory.map(({ step, detail, time }, idx) => (
                  <div key={`${step}-${idx}`} className="flex gap-3">
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-400 text-[10px] font-bold text-[#111827]">
                      {idx + 1}
                    </div>
                    <div className="flex-1 rounded border border-slate-700 bg-[#111827] p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-cyan-300">{step}</span>
                        <span className="text-[10px] uppercase tracking-[0.18em] text-slate-400">{time}</span>
                      </div>
                      <div className="mt-2 text-[11px] text-slate-400">{detail}</div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-400">Tool steps will show after a run.</div>
              )}
            </div>
          </div>
        </section>

        <section data-animate="section" className="rounded border border-slate-700 bg-[#1b1b1b] p-4 opacity-0">
          <div className="mb-4 border-b border-slate-700 pb-3 text-[10px] uppercase tracking-[0.2em] text-slate-400">Evaluation results</div>
          <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
            <div className="space-y-4">
              {capabilityBars.map(({ label, value }) => (
                <div key={label} className="flex items-center gap-3 text-xs text-slate-300">
                  <span className="w-12 text-right uppercase">{label}</span>
                  <div className="h-3 flex-1 overflow-hidden rounded border border-slate-700 bg-[#111827]">
                    <div data-animate="bar" data-bar-width={`${value}%`} className="h-full bg-cyan-400" style={{ width: '0%' }} />
                  </div>
                  <span className="w-10 text-right">{value}%</span>
                </div>
              ))}
            </div>

            <EvaluationTable rows={evaluationRows} />
          </div>
        </section>
      </div>
    </DashboardShell>
  )
}
