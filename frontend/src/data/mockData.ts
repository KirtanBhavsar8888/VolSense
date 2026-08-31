export type SkewPoint = {
  strike: number
  skew: number
}

export const skewSeries: SkewPoint[] = [
  { strike: 21000, skew: 0.06 },
  { strike: 21250, skew: 0.07 },
  { strike: 21500, skew: 0.09 },
  { strike: 21750, skew: 0.11 },
  { strike: 22000, skew: 0.12 },
  { strike: 22250, skew: 0.15 },
  { strike: 22500, skew: 0.17 },
  { strike: 22750, skew: 0.18 },
  { strike: 23000, skew: 0.16 },
]

export const metricCards = [
  { label: 'Session close skew', value: '0.12', delta: '+0.01 vs prior', tone: 'positive' as const },
  { label: 'Intraday mean', value: '0.11', delta: 'stable', tone: 'neutral' as const },
  { label: 'Skew delta', value: '+0.01', delta: 'vs previous session', tone: 'positive' as const },
  { label: 'Rows processed', value: '142,400', delta: '7.8% higher', tone: 'neutral' as const },
]

export const trajectory = [
  {
    step: 'synthesize_future()',
    detail: 'Rows: 142K | filter cleared',
    state: 'success',
    time: '0.4s',
  },
  {
    step: 'validate_iv_delta()',
    detail: 'Delta anomaly detected; fallback interpolation enabled',
    state: 'warning',
    time: '0.8s',
  },
  {
    step: 'interpolate_25delta_skew()',
    detail: 'Nearest-neighbor smoothing applied within valid window',
    state: 'success',
    time: '1.2s',
  },
]

export const evalRows = [
  { id: 'NIF-01', difficulty: 'Hard', metrics: 'Exp: 0.12 | Act: 0.15', result: 'Fail', tone: 'fail' as const },
  { id: 'NIF-02', difficulty: 'Medium', metrics: 'Exp: 0.11 | Act: 0.12', result: 'Pass', tone: 'pass' as const },
  { id: 'NIF-03', difficulty: 'Easy', metrics: 'Exp: 0.09 | Act: 0.09', result: 'Pass', tone: 'pass' as const },
  { id: 'NIF-04', difficulty: 'Hard', metrics: 'Exp: 0.18 | Act: 0.17', result: 'Pass', tone: 'pass' as const },
]

export const capabilityBars = [
  { label: 'Easy', value: 98 },
  { label: 'Medium', value: 85 },
  { label: 'Hard', value: 62 },
]
