type MetricCardProps = {
  label: string
  value: string
  delta: string
  tone?: 'positive' | 'negative' | 'neutral'
}

const toneClassMap = {
  positive: 'text-emerald-400',
  negative: 'text-rose-400',
  neutral: 'text-slate-300',
}

export function MetricCard({ label, value, delta, tone = 'neutral' }: MetricCardProps) {
  return (
    <div data-animate="card" className="rounded border border-[#444748] bg-[#1c1b1b] p-4 opacity-0">
      <div className="text-[10px] uppercase tracking-[0.18em] text-[#8e9192]">{label}</div>
      <div className="mt-3 text-[28px] font-light tracking-[-0.04em] text-[#e5e2e1]">{value}</div>
      <div className={`mt-2 text-[11px] ${toneClassMap[tone]}`}>{delta}</div>
    </div>
  )
}
