import { useRef, useCallback } from 'react'
import { BarChart3, Gauge, Layers3, LogIn, FlaskConical } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { animate } from 'animejs'

const navItems = [
  { label: 'Dashboard', icon: Gauge, to: '/dashboard', tooltip: 'Live session overview \u2014 current skew curve, evaluation score, and agent status at a glance.' },
  { label: 'Comparison', icon: BarChart3, to: '/comparison', tooltip: 'Baseline vs. tool-using agent, side by side, across every session run.' },
  { label: 'Tool Trace', icon: Layers3, to: '/tool-trace', tooltip: 'Full step-by-step record of every tool call the agent made \u2014 inputs, outputs, and timing.' },
  { label: 'Eval Results', icon: LogIn, to: '/eval-results', tooltip: 'Automated test suite results across all cases, broken down by difficulty.' },
  { label: 'Backtest', icon: FlaskConical, to: '/backtest', tooltip: 'Test option strategies against historical chain data \u2014 entry/exit pricing, P&L, and trade timeline.' },
]

function NavItem({ label, icon: Icon, to, tooltip }: { label: string; icon: typeof Gauge; to: string; tooltip: string }) {
  const iconRef = useRef<HTMLDivElement>(null)

  const handleMouseEnter = useCallback(() => {
    if (iconRef.current) {
      animate(iconRef.current, {
        scale: [1, 1.2, 1],
        duration: 300,
        ease: 'outQuad',
      })
    }
  }, [])

  return (
    <NavLink
      to={to}
      onMouseEnter={handleMouseEnter}
      className={({ isActive }) =>
        [
          'group flex h-12 w-full items-center justify-center border-l-[3px] transition-colors duration-100',
          isActive
            ? 'border-[#44d8f1] bg-[#1c1b1b] text-[#44d8f1]'
            : 'border-transparent text-[#8e9192] hover:bg-[#20201f] hover:text-[#e5e2e1]',
        ].join(' ')
      }
      aria-label={label}
      title={tooltip}
    >
      <div ref={iconRef} className="flex items-center justify-center">
        <Icon className="h-5 w-5" />
      </div>
    </NavLink>
  )
}

export function NavRail() {
  return (
    <aside className="fixed left-0 top-0 z-50 flex h-screen w-16 flex-col items-center border-r border-[#444748] bg-[#0e0e0e] py-4">
      <div className="mb-8 mt-3 text-lg font-bold tracking-tight text-[#44d8f1]">VOL</div>

      <nav className="flex w-full flex-col items-center gap-2">
        {navItems.map((item) => (
          <NavItem key={item.label} {...item} />
        ))}
      </nav>
    </aside>
  )
}
