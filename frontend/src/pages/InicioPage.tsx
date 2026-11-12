import { useAuth } from '@/hooks/useAuth'

export function InicioPage() {
  const { usuario } = useAuth()
  if (!usuario) return null

  return (
    <section>
      <h1 className="text-2xl font-semibold text-slate-900">Bienvenido, {usuario.username}</h1>
      <p className="mt-2 text-slate-600">
        {usuario.esAdminSistema
          ? 'Administras clínicas, planes y suscripciones de la plataforma.'
          : usuario.roles.length > 0
            ? `Roles: ${usuario.roles.join(', ')}.`
            : 'Tu usuario no tiene roles asignados.'}
      </p>
    </section>
  )
}