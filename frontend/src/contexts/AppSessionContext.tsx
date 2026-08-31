import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { createDemoSession, getCurrentSupabaseSession, hasSupabaseConfig } from '../lib/supabase'
import type { AppSession } from '../types/app'

type AppSessionContextValue = {
  session: AppSession | null
  isLoading: boolean
  signIn: (email: string, password: string) => Promise<AppSession>
  signUp: (email: string, password: string) => Promise<AppSession>
  signInWithGoogle: () => Promise<void>
  signOut: () => void
  isAuthenticated: boolean
}

const AppSessionContext = createContext<AppSessionContextValue | undefined>(undefined)

export function AppSessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AppSession | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isMounted = true

    async function hydrateSession() {
      try {
        const current = await getCurrentSupabaseSession()
        if (isMounted) {
          if (current) {
            setSession(current)
          } else if (!hasSupabaseConfig) {
            // Only auto-create demo session when Supabase is not configured
            setSession(createDemoSession())
          }
          // If Supabase is configured but no session, leave session null → shows login
        }
      } catch {
        if (isMounted && !hasSupabaseConfig) {
          setSession(createDemoSession())
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    void hydrateSession()

    // Listen for auth state changes (important for OAuth redirects)
    let subscription: { unsubscribe: () => void } | null = null
    if (hasSupabaseConfig) {
      import('../lib/supabase').then(({ supabase }) => {
        if (supabase && isMounted) {
          const { data } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
            if (!isMounted) return
            if (newSession) {
              const user = newSession.user
              setSession({
                user: {
                  id: user.id,
                  email: user.email ?? 'unknown@local.dev',
                  name: user.user_metadata?.full_name ?? user.email?.split('@')[0] ?? 'analyst',
                  role: 'analyst',
                },
                authenticatedAt: new Date().toISOString(),
                authMode: 'supabase',
              })
            } else {
              setSession(null)
            }
          })
          subscription = data.subscription
        }
      })
    }

    return () => {
      isMounted = false
      subscription?.unsubscribe()
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    const nextSession = await (async () => {
      if (hasSupabaseConfig) {
        const { signInWithCredentials } = await import('../lib/supabase')
        return await signInWithCredentials(email, password)
      }
      return createDemoSession(email)
    })()

    setSession(nextSession)
    return nextSession
  }, [])

  const signUp = useCallback(async (email: string, password: string) => {
    const nextSession = await (async () => {
      if (hasSupabaseConfig) {
        const { signUpWithCredentials } = await import('../lib/supabase')
        return await signUpWithCredentials(email, password)
      }
      return createDemoSession(email)
    })()

    setSession(nextSession)
    return nextSession
  }, [])

  const signInWithGoogle = useCallback(async () => {
    if (hasSupabaseConfig) {
      const { signInWithGoogle: googleSignIn } = await import('../lib/supabase')
      await googleSignIn()
    } else {
      // In demo mode, just create a demo session
      setSession(createDemoSession('user@gmail.com'))
    }
  }, [])

  const signOut = useCallback(async () => {
    if (typeof window !== 'undefined') {
      try {
        const { supabase } = await import('../lib/supabase')
        if (supabase) {
          await supabase.auth.signOut()
        }
      } catch {
        // Ignore Supabase sign-out failures and keep the app in demo-safe mode.
      }
    }

    setSession(null)
  }, [])

  const value = useMemo<AppSessionContextValue>(
    () => ({
      session,
      isLoading,
      signIn,
      signUp,
      signInWithGoogle,
      signOut,
      isAuthenticated: Boolean(session),
    }),
    [isLoading, session, signIn, signUp, signInWithGoogle, signOut],
  )

  return <AppSessionContext.Provider value={value}>{children}</AppSessionContext.Provider>
}

export function useAppSession() {
  const context = useContext(AppSessionContext)

  if (!context) {
    throw new Error('useAppSession must be used within AppSessionProvider')
  }

  return context
}
