import { createClient } from '@supabase/supabase-js'

import type { AppSession, SessionUser } from '../types/app'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL ?? ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY ?? ''

export const hasSupabaseConfig = Boolean(supabaseUrl && supabaseAnonKey)

export const supabase = hasSupabaseConfig
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
      },
    })
  : null

export function createDemoSession(email = 'analyst@local.dev'): AppSession {
  const safeEmail = email.trim() || 'analyst@local.dev'
  const name = safeEmail.split('@')[0] || 'analyst'

  const user: SessionUser = {
    id: 'demo-user',
    email: safeEmail,
    name,
    role: 'analyst',
  }

  return {
    user,
    authenticatedAt: new Date().toISOString(),
    authMode: 'demo',
  }
}

export async function signInWithCredentials(email: string, password: string): Promise<AppSession> {
  if (!supabase) {
    return createDemoSession(email)
  }

  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })

  if (error) {
    throw new Error(error.message)
  }

  const user = data.user
  const sessionUser: SessionUser = {
    id: user.id,
    email: user.email ?? email,
    name: user.user_metadata?.full_name ?? user.email?.split('@')[0] ?? 'analyst',
    role: 'analyst',
  }

  return {
    user: sessionUser,
    authenticatedAt: new Date().toISOString(),
    authMode: 'supabase',
  }
}

export async function signUpWithCredentials(email: string, password: string): Promise<AppSession> {
  if (!supabase) {
    return createDemoSession(email)
  }

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
  })

  if (error) {
    throw new Error(error.message)
  }

  // If email confirmation is required, data.session will be null
  if (!data.session || !data.user) {
    throw new Error('Check your email for a confirmation link!')
  }

  const user = data.user
  const sessionUser: SessionUser = {
    id: user.id,
    email: user.email ?? email,
    name: user.user_metadata?.full_name ?? user.email?.split('@')[0] ?? 'analyst',
    role: 'analyst',
  }

  return {
    user: sessionUser,
    authenticatedAt: new Date().toISOString(),
    authMode: 'supabase',
  }
}

export async function getCurrentSupabaseSession(): Promise<AppSession | null> {
  if (!supabase) {
    return null
  }

  const {
    data: { session },
    error,
  } = await supabase.auth.getSession()

  if (error || !session) {
    return null
  }

  const user = session.user

  return {
    user: {
      id: user.id,
      email: user.email ?? 'unknown@local.dev',
      name: user.user_metadata?.full_name ?? user.email?.split('@')[0] ?? 'analyst',
      role: 'analyst',
    },
    authenticatedAt: new Date().toISOString(),
    authMode: 'supabase',
  }
}

// ── Google OAuth helpers ──

/** Sign in with Google OAuth — redirects to Google consent screen */
export async function signInWithGoogle(): Promise<void> {
  if (!supabase) throw new Error('Supabase is not configured')
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${window.location.origin}/dashboard`,
      queryParams: {
        access_type: 'offline',
        prompt: 'consent',
      },
    },
  })
  if (error) throw new Error(error.message)
}

/** Sign up with Google OAuth — same as sign in (Google creates the account) */
export async function signUpWithGoogle(): Promise<void> {
  return signInWithGoogle()
}

// ── MFA (Google Authenticator / TOTP) helpers ──

export type MFAEnrollment = {
  qrCode: string
  secret: string
  factorId: string
}

/** Check if the user already has a TOTP factor enrolled */
export async function getMFAFactors(): Promise<Array<{ id: string; type: string; friendly_name?: string }>> {
  if (!supabase) return []
  const { data, error } = await supabase.auth.mfa.listFactors()
  if (error) throw new Error(error.message)
  return (data?.totp ?? []).map((f) => ({
    id: f.id,
    type: f.factor_type,
    friendly_name: f.friendly_name ?? undefined,
  }))
}

/** Start TOTP enrollment — returns a QR code URL and secret for the authenticator app */
export async function enrollMFA(): Promise<MFAEnrollment> {
  if (!supabase) throw new Error('Supabase is not configured')
  const { data, error } = await supabase.auth.mfa.enroll({
    factorType: 'totp',
    friendlyName: 'Google Authenticator',
  })
  if (error) throw new Error(error.message)
  // Narrow the union type — we enrolled TOTP so `.totp` exists
  const totpData = data as { totp: { qr_code: string; secret: string }; id: string }
  return {
    qrCode: totpData.totp.qr_code,
    secret: totpData.totp.secret,
    factorId: totpData.id,
  }
}

/** Verify a TOTP code to complete enrollment */
export async function verifyMFAEnrollment(factorId: string, code: string): Promise<void> {
  if (!supabase) throw new Error('Supabase is not configured')
  const { error } = await supabase.auth.mfa.verify({ factorId, code, challengeId: '' })
  // Supabase may require a challenge first; try the enroll-then-verify flow
  if (error) {
    // Create a challenge then verify
    const { data: challengeData, error: challengeError } = await supabase.auth.mfa.challenge({ factorId })
    if (challengeError) throw new Error(challengeError.message)
    const { error: verifyError } = await supabase.auth.mfa.verify({
      factorId,
      code,
      challengeId: challengeData.id,
    })
    if (verifyError) throw new Error(verifyError.message)
  }
}

/** Create a challenge for an existing TOTP factor (for login-time verification) */
export async function challengeMFA(factorId: string): Promise<string> {
  if (!supabase) throw new Error('Supabase is not configured')
  const { data, error } = await supabase.auth.mfa.challenge({ factorId })
  if (error) throw new Error(error.message)
  return data.id
}

/** Verify a TOTP code against a challenge (for login-time verification) */
export async function verifyMFAChallenge(factorId: string, challengeId: string, code: string): Promise<void> {
  if (!supabase) throw new Error('Supabase is not configured')
  const { error } = await supabase.auth.mfa.verify({ factorId, challengeId, code })
  if (error) throw new Error(error.message)
}

/** Unenroll (remove) a TOTP factor */
export async function unenrollMFA(factorId: string): Promise<void> {
  if (!supabase) throw new Error('Supabase is not configured')
  const { error } = await supabase.auth.mfa.unenroll({ factorId })
  if (error) throw new Error(error.message)
}
