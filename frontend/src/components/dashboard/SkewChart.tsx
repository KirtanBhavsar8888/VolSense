import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { SkewPoint } from '../../types/app'

type SkewChartProps = {
  data: SkewPoint[]
}

export function SkewChart({ data }: SkewChartProps) {
  if (!data.length) {
    return (
      <div className="flex h-[360px] items-center justify-center border border-[#444748] bg-[#0e0e0e] text-sm text-slate-400">
        No skew samples yet. Run analysis to populate this chart.
      </div>
    )
  }

  const useLabels = data.some((point) => point.label)

  return (
    <div className="chart-grid relative h-[420px] w-full overflow-hidden border border-[#444748] bg-[#0e0e0e] p-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(68,216,241,0.12),_transparent_45%)]" />
      <ResponsiveContainer width="100%" height="100%" className="relative z-10">
        <AreaChart data={data} margin={{ top: 16, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="skewArea" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.55} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.08} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#334155" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey={useLabels ? 'label' : 'strike'}
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            domain={['auto', 'auto']}
            tickFormatter={(value) => Number(value).toFixed(3)}
          />
          <Tooltip
            formatter={(value) => {
              const numericValue = Number(value ?? 0)
              return [`${numericValue.toFixed(4)}`, 'Skew']
            }}
            labelFormatter={(value) => String(value)}
            contentStyle={{
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              borderRadius: 0,
              color: '#e2e8f0',
            }}
          />
          <Area type="monotone" dataKey="skew" stroke="#22d3ee" strokeWidth={2} fill="url(#skewArea)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
