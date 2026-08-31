type ComparisonPanelProps = {
  baselinePreview: string
  agentPreview: string
  model?: string
}

export function ComparisonPanel({
  baselinePreview,
  agentPreview,
  model = 'calc-layer',
}: ComparisonPanelProps) {
  return (
    <div className="rounded border border-[#444748] bg-[#1c1b1b] p-4">
      <div className="mb-4 flex items-center justify-between border-b border-[#444748] pb-3">
        <span className="text-[10px] uppercase tracking-[0.2em] text-[#8e9192]">Model performance comparison</span>
        <span className="text-[10px] uppercase tracking-[0.18em] text-[#8e9192]">Model: {model}</span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded border border-[#ffb4ab]/60 bg-[#171717] p-3">
          <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-[#ffb4ab]">Baseline</div>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap text-xs leading-6 text-[#e5e2e1]">{baselinePreview}</pre>
        </div>

        <div className="rounded border border-[#44d8f1]/60 bg-[#171717] p-3">
          <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-[#44d8f1]">Agent</div>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap text-xs leading-6 text-[#e5e2e1]">{agentPreview}</pre>
        </div>
      </div>
    </div>
  )
}
