import { useMutation } from '@tanstack/react-query'
import { authService } from '@/services/authService'
import { useAuthStore } from '@/store/authStore'
import type { LoginRequest, RegisterRequest, AuthResponse } from '@/types/auth'

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth)

  return useMutation({
    mutationFn: (payload: LoginRequest) => authService.login(payload),
    onSuccess: (res: AuthResponse) => {
      setAuth({
        accessToken: res.access_token,    // snake_case → camelCase
        refreshToken: res.refresh_token,
        user: res.user,
      })
    },
  })
}

export function useRegister() {
  const setAuth = useAuthStore((s) => s.setAuth)

  return useMutation({
    mutationFn: (payload: RegisterRequest) => authService.register(payload),
    onSuccess: (res: AuthResponse) => {
      setAuth({
        accessToken: res.access_token,
        refreshToken: res.refresh_token,
        user: res.user,
      })
    },
  })
}
