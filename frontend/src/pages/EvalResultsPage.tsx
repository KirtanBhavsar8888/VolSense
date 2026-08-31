import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ChevronRight, CheckCircle, XCircle } from 'lucide-react'
import { animate, stagger } from 'animejs'

import { DashboardShell } from '../components/dashboard/DashboardShell'
import type { EvalCaseResult, EvalCheckResult } from '../types/app'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type SessionEvaluation = {
  session_id: string
  evaluation_results: Array<{
    case_id: string
    difficulty: string
    expected_skew: number
    actual_skew: number
    passed: boolean
    error_margin: number | null
  }>
  eval_score: number | null
}

type DifficultyFilter = 'all' | 'easy' | 'medium' | 'hard'

function transformEvaluation(session: SessionEvaluation): EvalCaseResult[] {
  return session.evaluation_results.map((result) => ({
    case_id: result.case_id,
    difficulty: result.difficulty.toLowerCase() as 'easy' | 'medium' | 'hard',
    checks: {
      skew: {
        expected: result.expected_skew,
        actual: result.actual_skew,
        passed: result.passed,
      },
      ...(result.error_margin !== null ? {
        error_margin: {
          expected: '< 0.1',
          actual: result.error_margin,
          passed: result.error_margin < 0.1,
        },
      } : {}),
    },
    passed: result.passed ? 1 : 0,
    failed: result.passed ? 0 : 1,
  }))
}

function PassRateBar({ label, passed, total, animateIn }: { label: string; passed: number; total: number; animateIn?: boolean }) {
  const percentage = total > 0 ? Math.round((passed / total) * 100) : 0
  const barRef = useRef<HTMLDivElement>(null)
  const hasAnimated = useRef(false)

  useEffect(() => {
    if (!animateIn || !barRef.current || hasAnimated.current) return
    hasAnimated.current = true
    const el = barRef.current
    const target = el.dataset.barWidth ?? '0%'
    el.style.width = '0%'
    const ctrl = animate(el, {
      width: [0, target],
      duration: 2400,
      ease: 'outQuad',
    })
    return () => { try { ctrl.revert() } catch { /* noop */ } }
  }, [animateIn, percentage])

  return (
    <div className="flex items-center gap-3 text-xs text-[#e5e2e1]">
      <span className="w-16 text-right uppercase text-[#8e9192]">{label}</span>
      <div className="h-4 flex-1 overflow-hidden rounded border border-[#444748] bg-[#0e0e0e]">
        <div
          ref={barRef}
          data-bar-width={`${percentage}%`}
          className={`h-full ${percentage >= 70 ? 'bg-emerald-500' : percentage >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
          style={animateIn ? { width: '0%' } : { width: `${percentage}%` }}
        />
      </div>
      <span className="w-20 text-right text-[#8e9192]">
        {percentage}% ({passed}/{total})
      </span>
    </div>
  )
}

function CheckBreakdown({ checks }: { checks: Record<string, EvalCheckResult> }) {
  return (
    <div className="space-y-2">
      {Object.entries(checks).map(([key, check]) => (
        <div key={key} className="flex items-center justify-between rounded border border-[#444748] bg-[#0e0e0e] p-3">
          <div className="flex items-center gap-3">
            {check.passed ? (
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            ) : (
              <XCircle className="h-4 w-4 text-red-400" />
            )}
            <span className="text-sm text-[#e5e2e1]">{key}</span>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="text-[#8e9192]">
              Expected: <span className="text-[#e5e2e1]">{String(check.expected)}</span>
            </div>
            <div className="text-[#8e9192]">
              Actual: <span className={check.passed ? 'text-emerald-400' : 'text-red-400'}>{String(check.actual)}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function EvalCaseRow({ caseResult, index }: { caseResult: EvalCaseResult; index: number }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const rowRef = useRef<HTMLDivElement>(null)
  const animated = useRef(false)

  useEffect(() => {
    if (!rowRef.current || animated.current) return
    animated.current = true
    const el = rowRef.current
    el.style.opacity = '0'
    el.style.transform = 'translateY(12px)'
    const ctrl = animate(el, {
      opacity: [0, 1],
      translateY: [40, 0],
      duration: 1200,
      delay: index * 200 + 500,
      ease: 'outQuad',
    })
    return () => { try { ctrl.revert() } catch { /* noop */ } }
  }, [index])
  const totalChecks = caseResult.passed + caseResult.failed
  const isPass = caseResult.failed === 0

  return (
    <div className="border-b border-[#444748] last:border-b-0">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 text-left hover:bg-[#20201f] transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-[#8e9192]" />
            ) : (
              <ChevronRight className="h-4 w-4 text-[#8e9192]" />
            )}
            <span className="font-medium text-[#e5e2e1]">{caseResult.case_id}</span>
          </div>
          <div className="flex items-center gap-4">
            <span className={`rounded px-2 py-1 text-[10px] font-bold uppercase ${
              caseResult.difficulty === 'easy' 
                ? 'bg-emerald-500/20 text-emerald-400' 
                : caseResult.difficulty === 'medium'
                ? 'bg-yellow-500/20 text-yellow-400'
                : 'bg-red-500/20 text-red-400'
            }`}>
              {caseResult.difficulty}
            </span>
            <span className="text-xs text-[#8e9192]">
              {caseResult.passed}/{totalChecks} passed
            </span>
            {isPass ? (
              <span className="rounded bg-emerald-500 px-2 py-1 text-[10px] font-bold uppercase text-[#0a0a0a]">
                PASS
              </span>
            ) : (
              <span className="rounded bg-red-500 px-2 py-1 text-[10px] font-bold uppercase text-[#0a0a0a]">
                FAIL
              </span>
            )}
          </div>
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-[#444748] p-4 bg-[#0e0e0e]">
          <CheckBreakdown checks={caseResult.checks} />
        </div>
      )}
    </div>
  )
}

export function EvalResultsPage() {
  const [cases, setCases] = useState<EvalCaseResult[]>([])
  const [filter, setFilter] = useState<DifficultyFilter>('all')
  const [evalScore, setEvalScore] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchEvaluation() {
      try {
        setIsLoading(true)
        
        // Get most recent session
        const sessionsResponse = await fetch(`${API_BASE}/api/sessions/user/demo-user?days=1`)
        if (!sessionsResponse.ok) {
          throw new Error('Failed to fetch sessions')
        }
        const sessions = await sessionsResponse.json() as Array<{ session_id: string }>
        
        if (sessions.length === 0) {
          setIsLoading(false)
          return
        }

        const sessionResponse = await fetch(`${API_BASE}/api/sessions/${sessions[0].session_id}`)
        if (!sessionResponse.ok) {
          throw new Error('Failed to fetch session details')
        }
        
        const sessionData: SessionEvaluation = await sessionResponse.json()
        setCases(transformEvaluation(sessionData))
        setEvalScore(sessionData.eval_score)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load evaluation results')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchEvaluation()
  }, [])

  const filteredCases = filter === 'all' 
    ? cases 
    : cases.filter(c => c.difficulty === filter)

  const stats = {
    easy: { passed: 0, total: 0 },
    medium: { passed: 0, total: 0 },
    hard: { passed: 0, total: 0 },
  }
  
  for (const c of cases) {
    stats[c.difficulty].total++
    if (c.failed === 0) {
      stats[c.difficulty].passed++
    }
  }

  const filters: Array<{ key: DifficultyFilter; label: string }> = [
    { key: 'all', label: 'All' },
    { key: 'easy', label: 'Easy' },
    { key: 'medium', label: 'Medium' },
    { key: 'hard', label: 'Hard' },
  ]

  return (
    <DashboardShell>
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-[#e5e2e1]">Evaluation Results</h1>
            <p className="text-sm text-[#8e9192]">Automated test suite results across all cases, broken down by difficulty.</p>
            <p className="text-sm text-[#8e9192]">
              {evalScore !== null 
                ? `Overall pass rate: ${evalScore.toFixed(1)}%`
                : 'No evaluation data yet. Run an analysis to see results.'}
            </p>
          </div>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center p-12 text-[#8e9192]">
            Loading evaluation results…
          </div>
        )}

        {error && (
          <div className="rounded border border-red-500/50 bg-red-950/40 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {!isLoading && !error && cases.length === 0 && (
          <div className="rounded border border-[#444748] bg-[#1c1b1b] p-12 text-center text-[#8e9192]">
            No evaluation cases yet. Run an analysis from the Dashboard to see evaluation results here.
          </div>
        )}

        {cases.length > 0 && (
          <>
            <div className="rounded border border-[#444748] bg-[#1c1b1b] p-4">
              <div className="mb-4 text-[10px] uppercase tracking-[0.2em] text-[#8e9192]">
                Pass Rate by Difficulty
              </div>
              <div className="space-y-3">
                <PassRateBar label="Easy" passed={stats.easy.passed} total={stats.easy.total} animateIn />
                <PassRateBar label="Medium" passed={stats.medium.passed} total={stats.medium.total} animateIn />
                <PassRateBar label="Hard" passed={stats.hard.passed} total={stats.hard.total} animateIn />
              </div>
            </div>

            <div className="flex items-center gap-2">
              {filters.map(({ key, label }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFilter(key)}
                  className={`rounded-full px-4 py-2 text-xs font-medium transition-colors ${
                    filter === key
                      ? 'bg-cyan-400 text-[#0a0a0a]'
                      : 'border border-[#444748] bg-[#1c1b1b] text-[#8e9192] hover:bg-[#20201f] hover:text-[#e5e2e1]'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="rounded border border-[#444748] bg-[#1c1b1b] overflow-hidden">
              <div className="p-4 border-b border-[#444748]">
                <span className="text-[10px] uppercase tracking-[0.2em] text-[#8e9192]">
                  {filteredCases.length} cases
                </span>
              </div>
              {filteredCases.map((caseResult, index) => (
                <EvalCaseRow key={caseResult.case_id} caseResult={caseResult} index={index} />
              ))}
            </div>
          </>
        )}
      </div>
    </DashboardShell>
  )
}
