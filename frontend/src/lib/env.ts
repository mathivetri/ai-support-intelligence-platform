// lib/env.ts — typed access to import.meta.env. Phase 0 step 5.
// Typed access to Vite environment variables (see .env / .env.example).
interface Env {
  API_BASE_URL: string
}

export const ENV: Env = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
}
