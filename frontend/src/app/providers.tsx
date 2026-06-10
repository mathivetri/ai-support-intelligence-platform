// app/providers.tsx — QueryClientProvider + BrowserRouter (+ Devtools). Phase 0 step 7.

// src/app/providers.tsx
import { type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

// One client per app. Tune defaults to your data-freshness needs.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,            // 1 min before refetch is considered
      retry: 1,                     // one retry on failure
      refetchOnWindowFocus: false,  // avoid surprise refetches in dev
    },
  },
})

export default function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
