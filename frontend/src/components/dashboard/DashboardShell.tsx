import type { ReactNode } from 'react'
import { NavRail } from '../layout/NavRail'
import { TopBar } from '../layout/TopBar'

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#131313] text-[#e5e2e1]">
      <NavRail />
      <TopBar />
      <main className="ml-16 mt-12 h-[calc(100vh-48px)] overflow-y-auto p-4">{children}</main>
    </div>
  )
}
