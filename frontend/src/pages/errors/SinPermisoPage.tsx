import { Link } from 'react-router-dom'

export function SinPermisoPage() {
  return (
    <section className="py-16 text-center">
      <h1 className="text-2xl font-semibold text-slate-900">Sin permiso</h1>
      <p className="mt-2 text-slate-600">No tienes permiso para acceder a esta sección.</p>
      <Link to="/" className="mt-4 inline-block text-blue-700 underline">
        Volver al inicio
      </Link>
    </section>
  )
}