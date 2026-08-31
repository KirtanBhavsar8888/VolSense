import { LogOut, Shield } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { animate } from 'animejs'

import { useAppSession } from '../../contexts/AppSessionContext'

const tickers = [
  { label: 'NIFTY', value: '22,456.20', delta: '+0.45%' },
  { label: 'BANKNIFTY', value: '48,120.55', delta: '-0.12%' },
  { label: 'RELIANCE', value: '2,984.10', delta: '+1.20%' },
]

function MFAContent({
  mfaPhase,
  mfaLoading,
  mfaError,
  mfaQRCode,
  mfaSecret,
  mfaCode,
  setMfaCode,
  startMFASetup,
  verifyMFASetup,
  closeMFA,
}: {
  mfaPhase: 'idle' | 'enroll' | 'verify'
  mfaLoading: boolean
  mfaError: string
  mfaQRCode: string
  mfaSecret: string
  mfaCode: string
  setMfaCode: (v: string) => void
  startMFASetup: () => void
  verifyMFASetup: (e: React.FormEvent) => void
  closeMFA: () => void
}) {
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!contentRef.current) return
    const el = contentRef.current
    const ctrl = animate(el, {
      opacity: [0, 1],
      scale: [0.85, 1],
      duration: 900,
      ease: 'outBack(1.4)',
    })
    return () => { try { ctrl.revert() } catch { /* noop */ } }
  }, [])

  return (
    <div ref={contentRef} className="w-full max-w-md rounded border border-slate-700 bg-[#1b1b1b] p-6 shadow-xl opacity-0">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-medium text-[#e5e2e1]">🔐 Set up Google Authenticator</h2>
        <button type="button" onClick={closeMFA} className="text-slate-500 hover:text-slate-300">✕</button>
      </div>

      {mfaPhase === 'idle' ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-400">Add an extra layer of security to your account with two-factor authentication.</p>
          <button
            type="button"
            onClick={startMFASetup}
            disabled={mfaLoading}
            className="w-full rounded bg-cyan-400 px-4 py-3 font-semibold text-[#111827] transition hover:bg-cyan-300 disabled:opacity-60"
          >
            {mfaLoading ? 'Setting up\u2026' : 'Enable Authenticator'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-slate-400">Scan this QR code with Google Authenticator:</p>
          <div className="flex flex-col items-center gap-3">
            <img src={mfaQRCode} alt="MFA QR Code" className="rounded border border-slate-600 bg-white p-2" width={180} height={180} />
            <div className="text-center">
              <p className="mb-1 text-xs text-slate-500">Or enter manually:</p>
              <code className="rounded bg-[#111827] px-2 py-1 text-xs text-cyan-400 tracking-wider select-all">{mfaSecret}</code>
            </div>
          </div>
          <form onSubmit={verifyMFASetup} className="space-y-3">
            <input
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
              type="text"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              className="w-full rounded border border-slate-700 bg-[#111827] p-3 text-center text-lg tracking-[0.3em] text-slate-200 outline-none focus:border-cyan-400"
              placeholder="000000"
            />
            {mfaError ? <p className="text-sm text-rose-400">{mfaError}</p> : null}
            <button
              type="submit"
              disabled={mfaLoading || mfaCode.length !== 6}
              className="w-full rounded bg-cyan-400 px-4 py-3 font-semibold text-[#111827] transition hover:bg-cyan-300 disabled:opacity-60"
            >
              {mfaLoading ? 'Verifying\u2026' : 'Verify & Enable'}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

export function TopBar() {
  const navigate = useNavigate()
  const { session, signOut } = useAppSession()
  const [showMFA, setShowMFA] = useState(false)
  const [mfaPhase, setMfaPhase] = useState<'idle' | 'enroll' | 'verify'>('idle')
  const [mfaQRCode, setMfaQRCode] = useState('')
  const [mfaSecret, setMfaSecret] = useState('')
  const [mfaFactorId, setMfaFactorId] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [mfaError, setMfaError] = useState('')
  const [mfaLoading, setMfaLoading] = useState(false)
  const overlayRef = useRef<HTMLDivElement>(null)

  function handleSignOut() {
    signOut()
    navigate('/login', { replace: true })
  }

  async function startMFASetup() {
    setMfaError('')
    setMfaLoading(true)
    try {
      const { enrollMFA } = await import('../../lib/supabase')
      const enrollment = await enrollMFA()
      setMfaQRCode(enrollment.qrCode)
      setMfaSecret(enrollment.secret)
      setMfaFactorId(enrollment.factorId)
      setMfaPhase('enroll')
    } catch (err) {
      setMfaError(err instanceof Error ? err.message : 'Failed to start MFA setup')
    } finally {
      setMfaLoading(false)
    }
  }

  async function verifyMFASetup(e: React.FormEvent) {
    e.preventDefault()
    setMfaError('')
    setMfaLoading(true)
    try {
      const { verifyMFAEnrollment } = await import('../../lib/supabase')
      await verifyMFAEnrollment(mfaFactorId, mfaCode)
      setShowMFA(false)
      setMfaPhase('idle')
      setMfaCode('')
    } catch (err) {
      setMfaError(err instanceof Error ? err.message : 'Invalid code')
    } finally {
      setMfaLoading(false)
    }
  }

  function closeMFA() {
    setShowMFA(false)
    setMfaPhase('idle')
    setMfaCode('')
    setMfaError('')
  }

  // Animate overlay fade-in
  useEffect(() => {
    if (!showMFA || !overlayRef.current) return
    const el = overlayRef.current
    const ctrl = animate(el, {
      opacity: [0, 1],
      duration: 600,
      ease: 'outQuad',
    })
    return () => { try { ctrl.revert() } catch { /* noop */ } }
  }, [showMFA])

  return (
    <>
      <header className="fixed left-16 right-0 top-0 z-40 flex h-12 items-center justify-between border-b border-[#444748] bg-[#131313] px-4">
        <div className="flex items-center gap-2 text-[16px] font-medium uppercase tracking-[0.04em] text-[#e5e2e1]">
          <span className="text-[#44d8f1]">●</span>
          <span>Nifty Options Skew Analysis</span>
        </div>

        <div className="flex items-center gap-6 border-x border-[#444748] bg-[#1c1b1b] px-4 py-1 h-full">
          {tickers.map(({ label, value, delta }) => (
            <div key={label} className="flex items-center gap-2 text-[10px]">
              <span className="uppercase tracking-[0.12em] text-[#8e9192]">{label}</span>
              <span className="font-mono text-[#e5e2e1]">{value}</span>
              <span className={delta.startsWith('+') ? 'text-[#4caf50]' : 'text-[#f44336]'}>{delta}</span>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3 text-[12px] text-[#8e9192]">
          <span className="font-mono">14:30:05</span>
          <span className="bg-[#4caf50] px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] text-[#0a0a0a]">PASS</span>
          <div className="flex items-center gap-2 border-l border-[#444748] pl-3 text-[10px] uppercase tracking-[0.16em] text-slate-300">
            <span>{session?.user.name ?? 'Analyst'}</span>
            <button type="button" onClick={() => setShowMFA(true)} aria-label="Set up MFA" className="rounded border border-slate-600 p-1 text-slate-200 transition hover:border-cyan-400 hover:text-cyan-300" title="Set up Google Authenticator">
              <Shield className="h-3.5 w-3.5" />
            </button>
            <button type="button" onClick={handleSignOut} aria-label="Sign out" className="rounded border border-slate-600 p-1 text-slate-200 transition hover:border-cyan-400 hover:text-cyan-300">
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </header>

      {/* MFA Setup Modal */}
      {showMFA && (
        <div ref={overlayRef} className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 opacity-0">
          <MFAContent
            mfaPhase={mfaPhase}
            mfaLoading={mfaLoading}
            mfaError={mfaError}
            mfaQRCode={mfaQRCode}
            mfaSecret={mfaSecret}
            mfaCode={mfaCode}
            setMfaCode={setMfaCode}
            startMFASetup={startMFASetup}
            verifyMFASetup={verifyMFASetup}
            closeMFA={closeMFA}
          />
        </div>
      )}
    </>
  )
}
