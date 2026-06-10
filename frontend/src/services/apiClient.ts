import { useAuthStore } from '@/store/authStore'

import axios, {
  type AxiosInstance,
  type InternalAxiosRequestConfig,
  type AxiosError,
} from 'axios'
import { ENV } from '@/lib/env'

export const apiClient: AxiosInstance = axios.create({
  baseURL: ENV.API_BASE_URL,             // "/api/v1" — proxied to FastAPI in dev
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
})

// ── Request interceptor ────────────────────────────────────────────────
// Placeholder for JWT (M3): read token from authStore and set
// config.headers.Authorization = `Bearer ${token}`.
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error),
)


// ── Response interceptor ───────────────────────────────────────────────
// Placeholder for 401 handling (M3): logout + redirect to /login.
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // M3 groundwork: drop the invalid session so a stale token can't linger.
      // Token-refresh + redirect-to-/login get wired in a later step.
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  },
)

