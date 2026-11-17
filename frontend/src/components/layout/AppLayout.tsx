import { LogOut, Menu } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { ITEMS_NAV } from '@/lib/navigation'

export function AppLayout() {
  const { usuario, cerrarSesion, suscripcionVencida } = useAuth()
  const [menuAbierto, setMenuAbierto] = useState(false)

  if (!usuario) return null
  const items = ITEMS_NAV.filter((item) => item.visible(usuario))

  return (
    <div className="min-h-screen md:flex">
      <aside
        className={`${menuAbierto ? 'block' : 'hidden'} w-full shrink-0 border-r border-slate-200 bg-white md:block md:w-64`}
        aria-label="Navegación principal"
      >
        <div className="px-4 py-5 text-lg font-semibold text-blue-700">Clínicas SaaS</div>
        <nav className="space-y-1 px-2 pb-4">
          {items.map(({ etiqueta, ruta, icono: Icono }) => (
            <NavLink
              key={ruta}
              to={ruta}
              end={ruta === '/'}
              onClick={() => setMenuAbierto(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm ${isActive ? 'bg-blue-50 font-medium text-blue-700' : 'text-slate-700 hover:bg-slate-100'
                }`
              }
            >
              <Icono size={18} aria-hidden="true" />
              {etiqueta}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
          <button
            type="button"
            className="rounded-md p-2 text-slate-700 hover:bg-slate-100 md:hidden"
            onClick={() => setMenuAbierto((v) => !v)}
            aria-label="Abrir o cerrar menú"
            aria-expanded={menuAbierto}
          >
            <Menu size={20} />
          </button>
          <div className="ml-auto flex items-center gap-4">
            <span className="text-sm text-slate-600">
              {usuario.username}
              {usuario.esAdminSistema && ' · Administrador del sistema'}
            </span>
            <button
              type="button"
              onClick={() => void cerrarSesion()}
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
            >
              <LogOut size={16} aria-hidden="true" />
              Salir
            </button>
          </div>
        </header>

        <main className="flex-1 p-6">
          {suscripcionVencida && (
            <p role="alert" className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
              La suscripción de tu clínica no está vigente. Algunas secciones están bloqueadas hasta
              que se renueve o se contrate un plan.
            </p>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  )
}