import type { Usuario } from '@/types/auth'
import { api } from '../client'
import { ENDPOINTS } from '../endpoints'
import { tokenStorage } from '../tokenStorage'

interface LoginResponse {
  access: string
  refresh: string
  usuario: unknown
  acceso_restringido: boolean
}

/**
 * Convierte el perfil definido por PerfilSerializer del backend
 * al formato utilizado por el frontend.
 */
function aUsuario(crudo: unknown): Usuario {
  if (!crudo || typeof crudo !== 'object' || Array.isArray(crudo)) {
    throw new Error('El servidor devolvió un perfil de usuario inválido.')
  }

  const perfil = crudo as Record<string, unknown>

  if (
    typeof perfil.id !== 'number' ||
    !Number.isInteger(perfil.id) ||
    typeof perfil.username !== 'string' ||
    typeof perfil.email !== 'string' ||
    !(
      perfil.clinica === null ||
      (typeof perfil.clinica === 'number' &&
        Number.isInteger(perfil.clinica))
    ) ||
    !(
      perfil.clinica_nombre === null ||
      typeof perfil.clinica_nombre === 'string'
    ) ||
    typeof perfil.is_superuser !== 'boolean' ||
    !Array.isArray(perfil.roles) ||
    !perfil.roles.every((rol) => typeof rol === 'string') ||
    typeof perfil.suscripcion_vigente !== 'boolean' ||
    !(
      perfil.suscripcion_fin === null ||
      typeof perfil.suscripcion_fin === 'string'
    ) ||
    typeof perfil.acceso_restringido !== 'boolean'
  ) {
    throw new Error(
      'La respuesta del perfil de usuario no tiene el formato esperado.',
    )
  }

  return {
    id: perfil.id,
    username: perfil.username,
    email: perfil.email,
    clinicaId: perfil.clinica,
    clinicaNombre: perfil.clinica_nombre,
    esAdminSistema:
      perfil.is_superuser && perfil.clinica === null,
    roles: perfil.roles as string[],
    suscripcionVigente: perfil.suscripcion_vigente,
    suscripcionFin: perfil.suscripcion_fin,
    accesoRestringido: perfil.acceso_restringido,
  }
}

export async function obtenerPerfil(): Promise<Usuario> {
  const { data } = await api.get<unknown>(ENDPOINTS.me)
  return aUsuario(data)
}

export async function login(
  username: string,
  password: string,
): Promise<Usuario> {
  const { data } = await api.post<LoginResponse>(
    ENDPOINTS.login,
    { username, password },
    { skipAuth: true },
  )

  if (
    typeof data.access !== 'string' ||
    !data.access ||
    typeof data.refresh !== 'string' ||
    !data.refresh
  ) {
    throw new Error(
      'El servidor no devolvió los tokens de sesión esperados.',
    )
  }

  try {
    const usuario = aUsuario(data.usuario)
    tokenStorage.set(data.access, data.refresh)
    return usuario
  } catch (error) {
    tokenStorage.clear()
    throw error
  }
}

export async function logout(): Promise<void> {
  const refresh = tokenStorage.getRefresh()

  try {
    if (refresh) {
      await api.post(ENDPOINTS.logout, { refresh })
    }
  } catch {
    // Permite cerrar la sesión local aunque el servidor no responda.
  } finally {
    tokenStorage.clear()
  }
}