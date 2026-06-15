import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { ROUTES } from '@/routes/constants'

export default function RootLayout() {
  const navigate = useNavigate()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const logout = useAuthStore((s) => s.logout)

  const handleLogout = () => {
    logout()
    navigate(ROUTES.LOGIN, { replace: true })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {isAuthenticated && (
        <nav className="border-b bg-white">
          <div className="mx-auto flex max-w-4xl items-center gap-4 p-4">
            <Link to={ROUTES.DASHBOARD} className="font-semibold text-gray-900">
              Support Desk
            </Link>
            <Link to={ROUTES.TICKETS} className="text-sm text-gray-600 hover:text-gray-900">
              Tickets
            </Link>
            <Link to={ROUTES.TICKET_NEW} className="text-sm text-gray-600 hover:text-gray-900">
              New Ticket
            </Link>
            <button
              onClick={handleLogout}
              className="ml-auto text-sm text-gray-600 hover:text-gray-900"
            >
              Logout
            </button>
          </div>
        </nav>
      )}
      <Outlet />
    </div>
  )
}
