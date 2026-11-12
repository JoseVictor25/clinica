import { Link } from 'react-router-dom'

export function ClinicaInactivaPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="max-w-md rounded-xl bg-white p-6 text-center shadow">
        <h1 className="text-2xl font-semibold text-slate-900">Clínica desactivada</h1>
        <p className="mt-2 text-slate-600">
          El acceso de tu clínica está suspendido. Contacta al administrador de la plataforma para
          reactivarlo. Tu sesión fue cerrada.
        </p>
        <Link
          to="/login"
          className="mt-4 inline-block rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          Ir al inicio de sesión
        </Link>
      </div>
    </main>
  )
}