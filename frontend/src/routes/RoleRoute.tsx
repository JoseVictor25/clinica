import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import type { Usuario } from '@/types/auth'

export function RoleRoute({ permitir }: { permitir: (usuario: Usuario) => boolean }) {
  const { usuario } = useAuth()
  if (!usuario || !permitir(usuario)) return <Navigate to="/sin-permiso" replace />
  return <Outlet />
}