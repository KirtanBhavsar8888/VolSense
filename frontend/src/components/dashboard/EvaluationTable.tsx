import type { EvaluationRow } from '../../types/app'

export function EvaluationTable({ rows }: { rows: EvaluationRow[] }) {
  if (!rows.length) {
    return <div className="p-4 text-sm text-slate-400">No evaluation rows yet.</div>
  }

  return (
    <div className="overflow-hidden rounded border border-slate-700">
      <table className="w-full text-left text-xs">
        <thead className="bg-[#111827] text-slate-400">
          <tr>
            <th className="p-3">Case ID</th>
            <th className="p-3">Difficulty</th>
            <th className="p-3">Metrics</th>
            <th className="p-3">Result</th>
          </tr>
        </thead>
        <tbody className="text-slate-200">
          {rows.map((row) => (
            <tr key={row.id} className="border-t border-slate-700">
              <td className="p-3">{row.id}</td>
              <td className="p-3 text-slate-300">{row.difficulty}</td>
              <td className="p-3 text-slate-400">{row.metrics}</td>
              <td className="p-3">
                <span
                  className={[
                    'rounded px-2 py-1 text-[10px] font-bold uppercase text-[#111827]',
                    row.tone === 'pass' ? 'bg-emerald-500' : 'bg-red-500',
                  ].join(' ')}
                >
                  {row.result}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
