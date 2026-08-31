import { useState, useEffect, useRef } from 'react'
import { animate, stagger } from 'animejs'
import { animated, useSpring } from '@react-spring/web'
import { ChevronDown, ChevronRight, Clock, CheckCircle, XCircle } from 'lucide-react'

import { DashboardShell } from '../components/dashboard/DashboardShell'
import { ComparisonPanel } from '../components/dashboard/ComparisonPanel'
import type { ComparisonRun } from '../types/app'
import { API_BASE } from '../config'

type SessionComparison = {
  session_id: string
  status: string
  created_at: string
  eval_score: number | null
  baseline_result: Record<string, unknown> | null
  agent_result: Record<string, unknown> | null
}

function previewText(value: unknown, fallback: string): string {
  if (!value) return fallback
  if (typeof value === 'string') return value
  // Handle error objects from baseline/agent
  if (typeof value === 'object' && value !== null && 'message' in value) {
    return String((value as { message: string }).message)
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return fallback
  }
}

function transformSession(session: SessionComparison): ComparisonRun {
  const agent = (session.agent_result ?? {}) as Record<string, unknown>
  const baseline = (session.baseline_result ?? {}) as Record<string, unknown>
  
  // Extract meaningful text from baseline
  const baselineErr = baseline.error as { message?: string } | undefined
  const baselineText = (baseline.response as string)
    ?? (baseline.error ? `Error: ${baselineErr?.message ?? JSON.stringify(baseline.error)}` : null)
    ?? (Array.isArray(baseline.notes) ? (baseline.notes as string[]).join('\n') : null)
    ?? 'Baseline has not run yet.'
  
  // Extract meaningful text from agent
  const agentText = (agent.final_response as string)
    ?? (agent.reason ? `Rerouted: ${agent.reason}` : null)
    ?? (agent.close_skew != null ? `Close 25d skew: ${Number(agent.close_skew).toFixed(4)}` : null)
    ?? 'Agent has not run yet.'
  
  return {
    id: session.session_id,
    timestamp: session.created_at,
    baseline: {
      preview: previewText(baselineText, 'Baseline has not run yet.'),
      skew: typeof baseline.close_skew === 'number' ? baseline.close_skew : undefined,
      model: typeof baseline.model === 'string' ? baseline.model : undefined,
    },
    agent: {
      preview: previewText(agentText, 'Agent has not run yet.'),
      skew: typeof agent.close_skew === 'number' ? agent.close_skew : undefined,
      model: typeof agent.model === 'string' ? agent.model : 'calc-layer',
    },
  }
}

function ComparisonRow({ run }: { run: ComparisonRun }) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  const expandAnimation = useSpring({
    height: isExpanded ? 'auto' : 0,
    opacity: isExpanded ? 1 : 0,
    overflow: 'hidden',
    config: { tension: 200, friction: 20 },
  })

  const timestamp = new Date(run.timestamp).toLocaleString()
  const isPass = run.agent.preview !== 'Agent has not run yet.'

  return (
    <div className="rounded border border-[#444748] bg-[#1c1b1b] overflow-hidden">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 text-left hover:bg-[#20201f] transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {isExpanded ? (
              <ChevronDown className="h-5 w-5 text-[#8e9192]" />
            ) : (
              <ChevronRight className="h-5 w-5 text-[#8e9192]" />
            )}
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-[#8e9192]" />
              <span className="text-sm text-[#e5e2e1]">{timestamp}</span>
            </div>
            <span className="text-xs text-[#8e9192]">Session: {run.id.slice(0, 8)}…</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-[#8e9192]">Model: {run.agent.model ?? 'calc-layer'}</span>
            {isPass ? (
              <span className="flex items-center gap-1 rounded bg-emerald-500 px-2 py-1 text-[10px] font-bold uppercase text-[#0a0a0a]">
                <CheckCircle className="h-3 w-3" />
                PASS
              </span>
            ) : (
              <span className="flex items-center gap-1 rounded bg-red-500 px-2 py-1 text-[10px] font-bold uppercase text-[#0a0a0a]">
                <XCircle className="h-3 w-3" />
                FAIL
              </span>
            )}
          </div>
        </div>
      </button>

      <animated.div style={expandAnimation}>
        <div className="border-t border-[#444748] p-4">
          <ComparisonPanel
            baselinePreview={run.baseline.preview}
            agentPreview={run.agent.preview}
            model={run.agent.model}
          />
        </div>
      </animated.div>
    </div>
  )
}

export function ComparisonPage() {
  const [runs, setRuns] = useState<ComparisonRun[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchComparisons() {
      try {
        setIsLoading(true)
        // First fetch session list
        const listResponse = await fetch(`${API_BASE}/api/sessions/user/demo-user?days=30`)
        if (!listResponse.ok) {
          throw new Error(`Failed to fetch comparisons: ${listResponse.statusText}`)
        }
        const sessionList: Array<{ session_id: string }> = await listResponse.json()
        
        // Then fetch full details for each session (to get baseline/agent results)
        const detailedSessions = await Promise.all(
          sessionList.map(async (s) => {
            try {
              const detailResponse = await fetch(`${API_BASE}/api/sessions/${s.session_id}`)
              if (!detailResponse.ok) return null
              return await detailResponse.json() as SessionComparison
            } catch {
              return null
            }
          })
        )
        
        const comparisonRuns = detailedSessions
          .filter((s): s is SessionComparison => s !== null)
          .map(transformSession)
          .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        
        setRuns(comparisonRuns)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load comparisons')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchComparisons()
  }, [])

  const hasAnimated = useRef(false)

  useEffect(() => {
    if (!isLoading && runs.length > 0 && !hasAnimated.current) {
      hasAnimated.current = true
      const rows = document.querySelectorAll('[data-animate="comp-row"]')
      if (rows.length) {
        animate(rows, {
          opacity: [0, 1],
          translateY: [20, 0],
          duration: 450,
          delay: stagger(70, { start: 100 }),
          ease: 'outQuad',
        })
      }
    }
  }, [isLoading, runs.length])

  return (
    <DashboardShell>
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-[#e5e2e1]">Comparison Runs</h1>
            <p className="text-sm text-[#8e9192]">Baseline vs. tool-using agent, side by side, across every session run.</p>
          </div>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center p-12 text-[#8e9192]">
            Loading comparisons…
          </div>
        )}

        {error && (
          <div className="rounded border border-red-500/50 bg-red-950/40 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {!isLoading && !error && runs.length === 0 && (
          <div className="rounded border border-[#444748] bg-[#1c1b1b] p-12 text-center text-[#8e9192]">
            No comparison runs yet. Run an analysis from the Dashboard to see results here.
          </div>
        )}

        <div className="space-y-4">
          {runs.map((run) => (
            <div key={run.id} data-animate="comp-row" style={{ opacity: 0 }}>
              <ComparisonRow run={run} />
            </div>
          ))}
        </div>
      </div>
    </DashboardShell>
  )
}
