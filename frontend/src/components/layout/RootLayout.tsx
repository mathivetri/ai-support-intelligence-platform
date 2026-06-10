import { Outlet } from 'react-router-dom'

export default function RootLayout() {
  // The full AppShell (sidebar/topbar) will replace this wrapper in a later step.
  return <Outlet />
}
