import { useState, useEffect, useRef } from 'react'
import { animate, stagger } from 'animejs'
import { Database, FileText, Calculator, CheckCircle, AlertCircle, Wrench } from 'lucide-react'

import { DashboardShell } from '../components/dashboard/DashboardShell'
import type { ToolCallStep } from '../types/app'
import { API_BASE } from '../config'

type SessionData = {
  session_id: string
  agent_result: {
    tool_trace?: Array<{
      tool?: string
      input?: Record<string, unknown>
      output?: Record<string, unknown>
    }>
  } | null
}

const toolIcons: Record<string, typeof Wrench> = {
  flag_bad_chain: AlertCircle,
  compute_synthetic_future: Calculator,
  compute_iv_delta: Calculator,
  compute_skew: FileText,
  query_memory: Database,
  run_sanity_check: CheckCircle,
}

function syntaxHighlight(json: string): string {
  return json
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g, (match) => {
      let cls = 'text-yellow-400' // number
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = 'text-cyan-400' // key
        } else {
          cls = 'text-emerald-400' // string
        }
      } else if (/true|false/.test(match)) {
        cls = 'text-purple-400' // boolean
      } else if (/null/.test(match)) {
        cls = 'text-red-400' // null
      }
      return `<span class="${cls}">${match}</span>`
    })
}

function HighlightedJson({ data }: { data: Record<string, unknown> }) {
  const jsonString = JSON.stringify(data, null, 2)
  const highlighted = syntaxHighlight(jsonString)
  
  return (
    <pre 
      className="overflow-x-auto text-xs leading-5"
      dangerouslySetInnerHTML={{ __html: highlighted }}
    />
  )
}

function ToolCallStepCard({ step, index }: { step: ToolCallStep; index: number }) {
  const Icon = toolIcons[step.tool] ?? Wrench
  const hasError = step.output && 'error' in step.output
  
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <div className={`flex h-10 w-10 items-center justify-center rounded-full ${hasError ? 'bg-red-500' : 'bg-cyan-400'} text-sm font-bold text-[#0a0a0a]`}>
          {index + 1}
        </div>
        <div className="w-px flex-1 bg-[#444748]" />
      </div>
      
      <div className="flex-1 pb-8">
        <div className="rounded border border-[#444748] bg-[#1c1b1b] p-4">
          <div className="mb-3 flex items-center gap-3">
            <Icon className={`h-5 w-5 ${hasError ? 'text-red-400' : 'text-cyan-400'}`} />
            <span className="font-medium text-[#e5e2e1]">{step.tool}()</span>
            {hasError && (
              <span className="rounded bg-red-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-red-400">
                Error
              </span>
            )}
          </div>
          
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-[#8e9192]">Input</div>
              <div className="rounded border border-[#444748] bg-[#0e0e0e] p-3">
                <HighlightedJson data={step.input} />
              </div>
            </div>
            
            <div>
              <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-[#8e9192]">Output</div>
              <div className={`rounded border ${hasError ? 'border-red-500/50' : 'border-[#444748]'} bg-[#0e0e0e] p-3`}>
                <HighlightedJson data={step.output} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function ToolTracePage() {
  const [steps, setSteps] = useState<ToolCallStep[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchToolTrace() {
      try {
        setIsLoading(true)
        
        // First, get the most recent session
        const sessionsResponse = await fetch(`${API_BASE}/api/sessions/user/demo-user?days=1`)
        if (!sessionsResponse.ok) {
          throw new Error('Failed to fetch sessions')
        }
        const sessions = await sessionsResponse.json() as Array<{ session_id: string; status: string }>
        
        if (sessions.length === 0) {
          setIsLoading(false)
          return
        }

        const latestSession = sessions[0]
        setSessionId(latestSession.session_id)

        // Fetch full session details to get tool trace
        const sessionResponse = await fetch(`${API_BASE}/api/sessions/${latestSession.session_id}`)
        if (!sessionResponse.ok) {
          throw new Error('Failed to fetch session details')
        }
        
        const sessionData: SessionData = await sessionResponse.json()
        const toolTrace = sessionData.agent_result?.tool_trace ?? []
        
        const toolSteps: ToolCallStep[] = toolTrace.map((trace) => ({
          tool: trace.tool ?? 'unknown',
          input: trace.input ?? {},
          output: trace.output ?? {},
        }))
        
        setSteps(toolSteps)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load tool trace')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchToolTrace()
  }, [])

  const hasAnimated = useRef(false)

  useEffect(() => {
    if (!isLoading && steps.length > 0 && !hasAnimated.current) {
      hasAnimated.current = true
      const els = document.querySelectorAll('[data-animate="trace-step"]')
      if (els.length) {
        animate(els, {
          opacity: [0, 1],
          translateX: [30, 0],
          duration: 400,
          delay: stagger(100, { start: 80 }),
          ease: 'outQuad',
        })
      }
    }
  }, [isLoading, steps.length])

  return (
    <DashboardShell>
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-[#e5e2e1]">Tool Trace</h1>
            <p className="text-sm text-[#8e9192]">Full step-by-step record of every tool call the agent made — inputs, outputs, and timing.</p>
            <p className="text-sm text-[#8e9192]">
              {sessionId 
                ? `Session ${sessionId.slice(0, 8)}… — Full tool call timeline`
                : 'No active session. Run an analysis to see tool traces.'}
            </p>
          </div>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center p-12 text-[#8e9192]">
            Loading tool trace…
          </div>
        )}

        {error && (
          <div className="rounded border border-red-500/50 bg-red-950/40 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {!isLoading && !error && steps.length === 0 && (
          <div className="rounded border border-[#444748] bg-[#1c1b1b] p-12 text-center text-[#8e9192]">
            No tool calls recorded yet. Run an analysis from the Dashboard to see the full tool trace here.
          </div>
        )}

        <div className="space-y-2">
          {steps.map((step, index) => (
            <div key={`${step.tool}-${index}`} data-animate="trace-step" style={{ opacity: 0 }}>
              <ToolCallStepCard step={step} index={index} />
            </div>
          ))}
        </div>
      </div>
    </DashboardShell>
  )
}
