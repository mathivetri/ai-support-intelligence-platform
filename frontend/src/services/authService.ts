import { apiClient } from '@/services/apiClient'
import type { LoginRequest, RegisterRequest, AuthResponse } from '@/types/auth'

async function login(payload: LoginRequest): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/login', payload)
  return data
}

async function register(payload: RegisterRequest): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/register', payload)
  return data
}

export const authService = { login, register }
