import { createBrowserRouter } from 'react-router-dom'
import RootLayout from '@/components/layout/RootLayout'
import ProtectedRoute from '@/components/layout/ProtectedRoute'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import TicketsPage from '@/pages/tickets/TicketsPage'
import NotFoundPage from '@/pages/NotFoundPage'
import { ROUTES } from '@/routes/constants'
import TicketDetailPage from '@/pages/tickets/TicketDetailPage'
import CreateTicketPage from '@/pages/tickets/CreateTicketPage'
import EditTicketPage from '@/pages/tickets/EditTicketPage'



export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { path: ROUTES.LOGIN, element: <LoginPage /> },
      { path: ROUTES.REGISTER, element: <RegisterPage /> },
      {
        element: <ProtectedRoute />,
        children: [
          { path: ROUTES.DASHBOARD, element: <DashboardPage /> },
          { path: ROUTES.TICKETS, element: <TicketsPage /> },
          { path: ROUTES.TICKET_NEW, element: <CreateTicketPage /> },
          { path: '/tickets/:id', element: <TicketDetailPage /> },
          { path: '/tickets/:id/edit', element: <EditTicketPage /> },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
