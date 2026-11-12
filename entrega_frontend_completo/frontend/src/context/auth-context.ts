import { createContext } from 'react'
import type { Usuario } from '@/types/auth'

export interface AuthContextValue {
  usuario: Usuario | null
  cargando: boolean
  /** Indica que la clínica tiene acceso restringido por suscripción. */
  suscripcionVencida: boolean
  iniciarSesion: (
    username: string,
    password: string,
  ) => Promise<Usuario>
  cerrarSesion: () => Promise<void>
  /** Consulta nuevamente el perfil y actualiza el estado de suscripción. */
  actualizarPerfil: () => Promise<Usuario>
}

export const AuthContext = createContext<AuthContextValue | null>(null)