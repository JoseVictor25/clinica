import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { PantallaCarga } from '@/components/ui/PantallaCarga'
import { useAuth } from '@/hooks/useAuth'
import { esAdminClinica } from '@/lib/roles'

export function ProtectedRoute() {
  const { usuario, cargando, suscripcionVencida } = useAuth()
  const location = useLocation()
  if (cargando) return <PantallaCarga />
  if (!usuario) return <Navigate to="/login" replace state={{ from: location }} />
  if (suscripcionVencida) {
    const administrador = esAdminClinica(usuario)
    // Perfil y contraseña están disponibles con sesión; planes y suscripción
    // también están permitidos al administrador con acceso restringido.
    const permitidas = administrador ? ['/suscripciones', '/planes', '/cuenta', '/sin-permiso'] : ['/cuenta', '/sin-permiso']
    if (!permitidas.includes(location.pathname)) {
      return <Navigate to={administrador ? '/suscripciones' : '/sin-permiso'} replace />
    }
  }
  return <Outlet />
}
