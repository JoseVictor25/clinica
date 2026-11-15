import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { normalizarError } from '@/api/errors'
import { PantallaCarga } from '@/components/ui/PantallaCarga'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'

export function LoginPage() {
  const { usuario, cargando, iniciarSesion } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const destino = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/'

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  if (cargando) return <PantallaCarga />
  if (usuario) return <Navigate to={destino} replace />

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await iniciarSesion(username.trim(), password)
      navigate(destino, { replace: true })
    } catch (err) {
      const apiError = normalizarError(err)
      setError(
        apiError.status === 401 && !apiError.code
          ? 'Usuario o contraseña incorrectos.'
          : mensajeDeError(apiError),
      )
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <form
        onSubmit={enviar}
        className="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow"
        noValidate
      >
        <h1 className="text-2xl font-semibold text-slate-900">Iniciar sesión</h1>

        {error && (
          <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="space-y-1">
          <label htmlFor="username" className="block text-sm font-medium text-slate-700">
            Usuario
          </label>
          <input
            id="username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="block text-sm font-medium text-slate-700">
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
        </div>

        <button
          type="submit"
          disabled={enviando || !username || !password}
          className="w-full rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
    </main>
  )
}