/**
 * Centralised API base URL.
 *
 * In production (Vercel) this MUST be set via the VITE_API_URL environment
 * variable pointing at the Railway backend, e.g.
 *   https://volsense-production.up.railway.app
 *
 * Locally it falls back to the default uvicorn port.
 */
export const API_BASE: string =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
