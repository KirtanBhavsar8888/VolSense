import { useCallback, useEffect, useState } from 'react'

import type { DashboardSessionData, EvaluationRow, SkewPoint, TrajectoryStep } from '../types/app'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type SessionPayload = {
  session_id: string
  status: string
  model?: string
  updated_at?: string
  eval_score?: number | null
  error_message?: string | null
  baseline_result?: Record<string, unknown> | null
  agent_result?: Record<string, unknown> | null
  skew_snapshots?: Array<{
    strike: number
    skew_value: number
    date?: string | null
    iv?: number | null
  }>
  evaluation_results?: Array<{
    case_id: string
    difficulty: string
    expected_skew: number
    actual_skew: number
    passed: boolean
    error_margin?: number | null
  }>
}

function previewText(value: unknown, fallback: string): string {
  if (!value) {
    return fallback
  }
  if (typeof value === 'string') {
    return value
  }
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

function transformSession(session: SessionPayload): DashboardSessionData {
  const snapshots = [...(session.skew_snapshots ?? [])].sort((left, right) => {
    return String(left.date ?? '').localeCompare(String(right.date ?? ''))
  })

  const skewSeries: SkewPoint[] = snapshots.map((point, index) => {
    const dateLabel = point.date ? new Date(point.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : `t${index + 1}`
    return {
      strike: point.date ? new Date(point.date).getTime() : index,
      label: dateLabel,
      skew: point.skew_value,
    }
  })

  const evaluationRows: EvaluationRow[] =
    session.evaluation_results?.map((row) => ({
      id: row.case_id,
      difficulty: row.difficulty,
      metrics: `Exp: ${row.expected_skew.toFixed(2)} | Act: ${row.actual_skew.toFixed(4)}`,
      result: row.passed ? 'Pass' : 'Fail',
      tone: row.passed ? ('pass' as const) : ('fail' as const),
    })) ?? []

  const byDifficulty = { easy: { pass: 0, total: 0 }, medium: { pass: 0, total: 0 }, hard: { pass: 0, total: 0 } }
  for (const row of session.evaluation_results ?? []) {
    const key = row.difficulty.toLowerCase() as keyof typeof byDifficulty
    if (!byDifficulty[key]) {
      continue
    }
    byDifficulty[key].total += 1
    if (row.passed) {
      byDifficulty[key].pass += 1
    }
  }

  const capabilityBars = (['easy', 'medium', 'hard'] as const).map((label) => {
    const bucket = byDifficulty[label]
    const value = bucket.total ? Math.round((bucket.pass / bucket.total) * 100) : 0
    return { label: label[0].toUpperCase() + label.slice(1), value }
  })

  const toolTrace = (session.agent_result?.tool_trace as Array<{ tool?: string; output?: { result?: { error?: string; rows?: number } } }>) ?? []
  const trajectory: TrajectoryStep[] = toolTrace.length
    ? toolTrace.map((step, index) => {
        const payload = (step.output?.result ?? step.output) as { error?: string; rows?: number } | undefined
        const error = payload?.error
        const rows = payload?.rows
        return {
          step: `${step.tool ?? 'tool'}()`,
          detail: error ? String(error) : rows != null ? `Rows: ${rows}` : 'Completed',
          state: error ? 'warning' : 'success',
          time: `${(index + 1) * 0.4}s`,
        }
      })
    : [{ step: 'Waiting for pipeline', detail: 'Click Run analysis to start.', state: 'warning', time: '\u2014' }]

  const closeSkew = skewSeries.length ? skewSeries[skewSeries.length - 1].skew : null
  const agent = session.agent_result ?? {}
  const baseline = session.baseline_result ?? {}

  // Extract meaningful text from baseline
  const baselineText = baseline.response 
    ?? (baseline.error ? `Error: ${(baseline.error as Record<string, unknown>).message ?? JSON.stringify(baseline.error)}` : null)
    ?? (baseline.notes ? (baseline.notes as string[]).join('\n') : null)
    ?? 'Baseline has not run yet.'
  
  // Extract meaningful text from agent
  const agentText = agent.final_response 
    ?? (agent.reason ? `Rerouted: ${agent.reason}` : null)
    ?? (agent.close_skew != null ? `Close 25d skew: ${Number(agent.close_skew).toFixed(4)}` : null)
    ?? 'Agent has not run yet.'

  return {
    summary: {
      title: 'Nifty Options Skew Analysis',
      marketStatus: session.status === 'completed' ? 'PASS' : session.status.toUpperCase(),
      generatedAt: session.updated_at ?? new Date().toISOString(),
      model: String(agent.model ?? session.model ?? 'calc-layer'),
    },
    metrics: [
      {
        label: 'Session close skew',
        value: closeSkew != null ? closeSkew.toFixed(4) : 'Pending',
        delta: 'PE IV \u2212 CE IV at last bar',
        tone: closeSkew != null && closeSkew > 0 ? 'positive' : 'neutral',
      },
      {
        label: 'Evaluation score',
        value: session.eval_score != null ? `${session.eval_score.toFixed(1)}%` : 'Pending',
        delta: 'eval/cases.json checks',
        tone: 'neutral',
      },
      { label: 'Agent status', value: session.status, delta: String(agent.agent ?? 'pipeline'), tone: 'neutral' },
      {
        label: 'Skew samples',
        value: String(skewSeries.length),
        delta: 'intraday 25\u0394 points',
        tone: 'neutral',
      },
    ],
    skewSeries,
    trajectory,
    capabilityBars,
    evaluationRows,
    baselinePreview: previewText(baselineText, 'Baseline has not run yet.'),
    agentPreview: previewText(agentText, 'Agent has not run yet.'),
    sessionId: session.session_id,
    errorMessage: session.error_message,
  }
}

export function useAnalysisSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('idle')
  const [data, setData] = useState<DashboardSessionData | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadSession = useCallback(async (id: string) => {
    const response = await fetch(`${API_BASE}/api/sessions/${id}`)
    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`)
    }
    const session = (await response.json()) as SessionPayload
    setStatus(session.status)
    setData(transformSession(session))
    return session.status
  }, [])

  const runAnalysis = useCallback(async () => {
    setError(null)
    setIsRunning(true)
    setStatus('running')
    try {
      const response = await fetch(`${API_BASE}/api/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'demo-user' }),
      })
      if (!response.ok) {
        throw new Error(`Failed to trigger analysis: ${response.statusText}`)
      }
      const result = (await response.json()) as { session_id: string }
      setSessionId(result.session_id)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start analysis'
      setError(message)
      setIsRunning(false)
      setStatus('failed')
    }
  }, [])

  useEffect(() => {
    if (!sessionId) {
      return
    }

    let cancelled = false
    let timer: number | undefined

    async function poll() {
      try {
        const nextStatus = await loadSession(sessionId!)
        if (cancelled) {
          return
        }
        if (nextStatus === 'completed' || nextStatus === 'failed') {
          setIsRunning(false)
          return
        }
        timer = window.setTimeout(() => {
          void poll()
        }, 1500)
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to fetch session'
          setError(message)
          setIsRunning(false)
        }
      }
    }

    void poll()
    return () => {
      cancelled = true
      if (timer) {
        window.clearTimeout(timer)
      }
    }
  }, [loadSession, sessionId])

  return { sessionId, status, data, error, isRunning, runAnalysis }
}

export async function getSessionStatus(sessionId: string) {
  const response = await fetch(`${API_BASE}/api/status/${sessionId}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch status: ${response.statusText}`)
  }
  return response.json()
}
