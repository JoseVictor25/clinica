import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section className="py-16 text-center">
      <h1 className="text-4xl font-semibold text-slate-900">404</h1>
      <p className="mt-2 text-slate-600">La página que buscas no existe.</p>
      <Link to="/" className="mt-4 inline-block text-blue-700 underline">
        Volver al inicio
      </Link>
    </section>
  )
}