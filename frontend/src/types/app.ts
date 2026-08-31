export type SessionUser = {
  id: string
  email: string
  name: string
  role: 'analyst' | 'admin'
}

export type AuthMode = 'demo' | 'supabase'

export type AppSession = {
  user: SessionUser
  authenticatedAt: string
  authMode: AuthMode
}

export type SkewPoint = {
  strike: number
  skew: number
  label?: string
}

export type MetricCardData = {
  label: string
  value: string
  delta: string
  tone: 'positive' | 'negative' | 'neutral'
}

export type TrajectoryStep = {
  step: string
  detail: string
  state: 'success' | 'warning'
  time: string
}

export type CapabilityBar = {
  label: string
  value: number
}

export type EvaluationRow = {
  id: string
  difficulty: string
  metrics: string
  result: string
  tone: 'pass' | 'fail'
}

export type DashboardSessionData = {
  summary: {
    title: string
    marketStatus: string
    generatedAt: string
    model: string
  }
  metrics: MetricCardData[]
  skewSeries: SkewPoint[]
  trajectory: TrajectoryStep[]
  capabilityBars: CapabilityBar[]
  evaluationRows: EvaluationRow[]
  baselinePreview: string
  agentPreview: string
  sessionId?: string
  errorMessage?: string | null
}

export type ComparisonRun = {
  id: string
  timestamp: string
  baseline: {
    preview: string
    skew?: number
    model?: string
  }
  agent: {
    preview: string
    skew?: number
    model?: string
  }
}

export type ToolCallStep = {
  tool: string
  input: Record<string, unknown>
  output: Record<string, unknown>
}

export type EvalCheckResult = {
  expected: unknown
  actual: unknown
  passed: boolean
}

export type EvalCaseResult = {
  case_id: string
  difficulty: 'easy' | 'medium' | 'hard'
  checks: Record<string, EvalCheckResult>
  passed: number
  failed: number
}
