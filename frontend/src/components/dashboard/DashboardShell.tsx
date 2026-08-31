import { type ReactNode, useEffect, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { NavRail } from '../layout/NavRail'
import { TopBar } from '../layout/TopBar'
import { API_BASE } from '../../config'

export function DashboardShell({ children }: { children: ReactNode }) {
  const [backendOk, setBackendOk] = useState<boolean | null>(null)

  useEffect(() => {
    let mounted = true
    async function check() {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) })
        if (mounted) setBackendOk(res.ok)
      } catch {
        if (mounted) setBackendOk(false)
      }
    }
    void check()
    const id = window.setInterval(check, 30_000)
    return () => { mounted = false; window.clearInterval(id) }
  }, [])

  return (
    <div className="min-h-screen bg-[#131313] text-[#e5e2e1]">
      <NavRail />
      <TopBar />
      {backendOk === false && (
        <div className="ml-16 mt-12 flex items-center gap-3 border-b border-amber-500/30 bg-amber-950/50 px-6 py-3 text-sm text-amber-200">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            Backend unreachable at <code className="rounded bg-amber-900/40 px-1 py-0.5 text-amber-100">{API_BASE}</code> —
            {' '}check that the Railway service is running and VITE_API_URL is set correctly.
          </span>
        </div>
      )}
      <main className="ml-16 mt-12 h-[calc(100vh-48px)] overflow-y-auto p-4">{children}</main>
    </div>
  )
}
