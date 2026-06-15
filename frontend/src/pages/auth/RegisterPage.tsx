import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useRegister } from '@/hooks/useAuth'
import { ROUTES } from '@/routes/constants'

export default function RegisterPage() {
  const navigate = useNavigate()
  const register = useRegister()

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [mismatch, setMismatch] = useState(false)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (password !== confirmPassword) {
      setMismatch(true)
      return
    }
    setMismatch(false)
    register.mutate(
      { username, email, password, confirm_password: confirmPassword },
      { onSuccess: () => navigate(ROUTES.DASHBOARD, { replace: true }) },
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg bg-white p-8 shadow"
      >
        <h1 className="text-2xl font-bold text-gray-900">Create account</h1>

        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username"
          minLength={3}
          maxLength={50}
          required
          className="w-full rounded border px-3 py-2"
        />
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          required
          className="w-full rounded border px-3 py-2"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password (8+ chars, upper, lower, digit)"
          minLength={8}
          required
          className="w-full rounded border px-3 py-2"
        />
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="Confirm password"
          required
          className="w-full rounded border px-3 py-2"
        />

        {mismatch && <p className="text-sm text-red-600">Passwords do not match.</p>}
        {register.isError && (
          <p className="text-sm text-red-600">
            Registration failed. Check your details (email may already be in use).
          </p>
        )}

        <button
          type="submit"
          disabled={register.isPending}
          className="w-full rounded bg-blue-600 py-2 font-medium text-white disabled:opacity-50"
        >
          {register.isPending ? 'Creating account…' : 'Create account'}
        </button>

        <p className="text-center text-sm text-gray-500">
          Already have an account?{' '}
          <Link to={ROUTES.LOGIN} className="text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  )
}
