import { Suspense, lazy, useState, useRef, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { animate, stagger } from 'animejs'

import { AppSessionProvider, useAppSession } from './contexts/AppSessionContext'

const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })),
)
const ComparisonPage = lazy(() =>
  import('./pages/ComparisonPage').then((module) => ({ default: module.ComparisonPage })),
)
const ToolTracePage = lazy(() =>
  import('./pages/ToolTracePage').then((module) => ({ default: module.ToolTracePage })),
)
const EvalResultsPage = lazy(() =>
  import('./pages/EvalResultsPage').then((module) => ({ default: module.EvalResultsPage })),
)
const BacktestPage = lazy(() =>
  import('./pages/BacktestPage').then((module) => ({ default: module.BacktestPage })),
)

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAppSession()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#131313] text-slate-300">
        Loading session…
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function LoginPage() {
  const navigate = useNavigate()
  const { signIn, signUp, signInWithGoogle, isAuthenticated } = useAppSession()

  // ── Form state ──
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const loginCardRef = useRef<HTMLDivElement>(null)

  // Stagger-animate login card on mount
  useEffect(() => {
    if (!loginCardRef.current) return
    const items = loginCardRef.current.querySelectorAll('[data-login-animate]')
    if (!items.length) return
    const ctrl = animate(items, {
      opacity: [0, 1],
      translateY: [40, 0],
      duration: 1200,
      delay: stagger(180, { start: 200 }),
      ease: 'outQuad',
    })
    return () => { try { ctrl.revert() } catch { /* noop */ } }
  }, [])

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  // ── Main form submit ──
  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSuccess('')
    setIsSubmitting(true)

    try {
      if (mode === 'signup') {
        if (password !== confirmPassword) {
          throw new Error('Passwords do not match')
        }
        await signUp(email, password)
        setSuccess('Account created! Check your email for a confirmation link, then sign in.')
        setMode('signin')
      } else {
        await signIn(email, password)
        navigate('/dashboard', { replace: true })
      }
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : 'Unable to continue.'
      setError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  // ── Google Sign-In ──
  async function handleGoogleSignIn() {
    setError('')
    setIsSubmitting(true)
    try {
      await signInWithGoogle()
      // For demo mode, this just creates a session
      // For Supabase, this redirects to Google
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Google sign-in failed'
      setError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const isSignUp = mode === 'signup'

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#131313] text-slate-100">
      <div ref={loginCardRef} className="w-full max-w-md rounded border border-slate-700 bg-[#1b1b1b] p-8 shadow-lg shadow-cyan-950/10">
        <div data-login-animate className="mb-6 text-center opacity-0">
          <div className="mb-2 text-2xl font-semibold text-cyan-400">VOL</div>
          <h1 className="text-xl font-medium">{isSignUp ? 'Create account' : 'Sign in'}</h1>
        </div>

        {/* Google Sign-In Button */}
        <button
          data-login-animate
          type="button"
          onClick={handleGoogleSignIn}
          disabled={isSubmitting}
          className="mb-4 flex w-full items-center justify-center gap-3 rounded border border-slate-600 bg-white px-4 py-3 text-sm font-medium text-slate-800 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60 opacity-0"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          {isSignUp ? 'Sign up with Google' : 'Sign in with Google'}
        </button>

        {/* Divider */}
        <div data-login-animate className="relative mb-4 opacity-0">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-700" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-[#1b1b1b] px-2 text-slate-500">or continue with email</span>
          </div>
        </div>

        <form data-login-animate className="space-y-4 opacity-0" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-2 block text-xs uppercase tracking-[0.18em] text-slate-400">Email</span>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              required
              className="w-full rounded border border-slate-700 bg-[#111827] p-3 text-sm text-slate-200 outline-none transition focus:border-cyan-400"
              placeholder="you@example.com"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-xs uppercase tracking-[0.18em] text-slate-400">Password</span>
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              required
              minLength={6}
              className="w-full rounded border border-slate-700 bg-[#111827] p-3 text-sm text-slate-200 outline-none transition focus:border-cyan-400"
              placeholder="At least 6 characters"
            />
          </label>

          {isSignUp ? (
            <label className="block">
              <span className="mb-2 block text-xs uppercase tracking-[0.18em] text-slate-400">Confirm Password</span>
              <input
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                type="password"
                required
                minLength={6}
                className={`w-full rounded border bg-[#111827] p-3 text-sm text-slate-200 outline-none transition focus:border-cyan-400 ${
                  confirmPassword && password !== confirmPassword
                    ? 'border-rose-500'
                    : 'border-slate-700'
                }`}
                placeholder="Re-enter password"
              />
              {confirmPassword && password !== confirmPassword ? (
                <p className="mt-1 text-xs text-rose-400">Passwords do not match</p>
              ) : null}
            </label>
          ) : null}

          {error ? <div className="rounded border border-rose-500/50 bg-rose-950/40 p-3 text-sm text-rose-200">{error}</div> : null}
          {success ? <div className="rounded border border-emerald-500/50 bg-emerald-950/40 p-3 text-sm text-emerald-200">{success}</div> : null}

          <button
            type="submit"
            disabled={isSubmitting || (isSignUp && password !== confirmPassword)}
            className="w-full rounded bg-cyan-400 px-4 py-3 font-semibold text-[#111827] transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? (isSignUp ? 'Creating account…' : 'Signing in…') : 'Continue'}
          </button>
        </form>

        <div data-login-animate className="mt-6 text-center text-sm text-slate-400 opacity-0">
          {isSignUp ? (
            <>Already have an account?{' '}<button type="button" onClick={() => { setMode('signin'); setError(''); setSuccess(''); setConfirmPassword(''); }} className="text-cyan-400 hover:text-cyan-300 transition">Sign in</button></>
          ) : (
            <>Don't have an account?{' '}<button type="button" onClick={() => { setMode('signup'); setError(''); setSuccess(''); setConfirmPassword(''); }} className="text-cyan-400 hover:text-cyan-300 transition">Create one</button></>
          )}
        </div>
      </div>
    </div>
  )
}

function AppShell() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-[#131313] text-slate-300">Loading dashboard…</div>}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/comparison"
            element={
              <ProtectedRoute>
                <ComparisonPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tool-trace"
            element={
              <ProtectedRoute>
                <ToolTracePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/eval-results"
            element={
              <ProtectedRoute>
                <EvalResultsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/backtest"
            element={
              <ProtectedRoute>
                <BacktestPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

function App() {
  return (
    <AppSessionProvider>
      <AppShell />
    </AppSessionProvider>
  )
}

export default App
