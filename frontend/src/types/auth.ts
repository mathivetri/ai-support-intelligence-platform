import type { User } from '@/types/user'

// Request payloads — mirror the FastAPI auth schemas (snake_case on the wire).

// POST /api/v1/auth/login  (UserLogin) — email + password only.
export interface LoginRequest {
  email: string
  password: string
}

// POST /api/v1/auth/register (UserCreate) — confirm_password is validated server-side.
export interface RegisterRequest {
  username: string
  email: string
  password: string
  confirm_password: string
}

// Response from both /login and /register (TokenResponse).
export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}
