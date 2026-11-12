import type { ListParams, Paginated } from '@/types/api'
import { api } from '../client'

export interface Rol {
  id: number
  clinica: number
  clinica_nombre: string
  nombre: string
  descripcion: string
  estado: boolean
  es_base: boolean
}

export interface RolInput {
  nombre: string
  descripcion: string
  estado: boolean
}

export const rolesApi = {
  async listar(
    params: ListParams = {},
  ): Promise<Paginated<Rol>> {
    const { data } = await api.get<Paginated<Rol>>(
      '/roles/',
      { params },
    )

    return data
  },

  async obtener(id: number): Promise<Rol> {
    const { data } = await api.get<Rol>(`/roles/${id}/`)
    return data
  },

  async crear(datos: RolInput): Promise<Rol> {
    const { data } = await api.post<Rol>('/roles/', datos)
    return data
  },

  async actualizar(
    id: number,
    datos: Partial<RolInput>,
  ): Promise<Rol> {
    const { data } = await api.patch<Rol>(
      `/roles/${id}/`,
      datos,
    )

    return data
  },

  async eliminar(id: number): Promise<void> {
    await api.delete(`/roles/${id}/`)
  },

  /**
   * Recorre todas las páginas para los selectores de roles.
   * Si activo se omite, incluye roles activos e inactivos.
   */
  async listarTodos(activo?: boolean): Promise<Rol[]> {
    const roles: Rol[] = []
    let page = 1

    while (true) {
      const { data } = await api.get<Paginated<Rol>>(
        '/roles/',
        {
          params: {
            page,
            page_size: 100,
            estado: activo,
          },
        },
      )

      roles.push(...data.results)

      if (!data.next) {
        return roles
      }

      page += 1
    }
  },
}