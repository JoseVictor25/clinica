import type { ListParams, Paginated } from '@/types/api'
import { api } from '../client'

export interface UsuarioClinica {
  id: number
  username: string
  email: string
  clinica: number
  clinica_nombre: string
  estado: boolean
  is_staff: boolean
  is_superuser: boolean
  fecha_creacion: string
  /** Nombres de los roles activos. */
  roles: string[]
}

export interface CrearUsuarioInput {
  username: string
  email: string
  password: string
  estado?: boolean
  /** Identificadores de los roles, no sus nombres. */
  roles?: number[]
}

export interface ActualizarUsuarioInput {
  email?: string
  estado?: boolean
  /** Omitir cuando no se quiera cambiar la contraseña. */
  password?: string
}

export const usuariosApi = {
  async listar(
    params: ListParams = {},
  ): Promise<Paginated<UsuarioClinica>> {
    const { data } = await api.get<Paginated<UsuarioClinica>>(
      '/usuarios/',
      { params },
    )

    return data
  },

  async obtener(id: number): Promise<UsuarioClinica> {
    const { data } = await api.get<UsuarioClinica>(
      `/usuarios/${id}/`,
    )

    return data
  },

  async crear(datos: CrearUsuarioInput): Promise<UsuarioClinica> {
    const { data } = await api.post<UsuarioClinica>(
      '/usuarios/',
      datos,
    )

    return data
  },

  async actualizar(
    id: number,
    datos: ActualizarUsuarioInput,
  ): Promise<UsuarioClinica> {
    const { data } = await api.patch<UsuarioClinica>(
      `/usuarios/${id}/`,
      datos,
    )

    return data
  },

  /** DELETE desactiva al usuario; no elimina su registro. */
  async desactivar(id: number): Promise<void> {
    await api.delete(`/usuarios/${id}/`)
  },

  async reactivar(id: number): Promise<UsuarioClinica> {
    const { data } = await api.patch<UsuarioClinica>(
      `/usuarios/${id}/`,
      { estado: true },
    )

    return data
  },
}