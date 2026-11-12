import type { ListParams, Paginated } from '@/types/api'
import { api } from '../client'

export interface UsuarioRol {
  /** Identificador de la asignación, distinto del identificador del rol. */
  id: number
  usuario: number
  usuario_username: string
  rol: number
  rol_nombre: string
  fecha_asignacion: string
}

export interface AsignarRolInput {
  usuario: number
  rol: number
}

export const usuarioRolesApi = {
  async listar(
    params: ListParams = {},
  ): Promise<Paginated<UsuarioRol>> {
    const { data } = await api.get<Paginated<UsuarioRol>>(
      '/usuario-roles/',
      { params },
    )

    return data
  },

  /**
   * El backend actual no implementa filtro por usuario en este endpoint.
   * Por eso recorremos las páginas y filtramos las asignaciones localmente.
   */
  async listarDelUsuario(usuarioId: number): Promise<UsuarioRol[]> {
    const asignaciones: UsuarioRol[] = []
    let page = 1

    while (true) {
      const { data } = await api.get<Paginated<UsuarioRol>>(
        '/usuario-roles/',
        {
          params: {
            page,
            page_size: 100,
          },
        },
      )

      asignaciones.push(
        ...data.results.filter(
          (asignacion) => asignacion.usuario === usuarioId,
        ),
      )

      if (!data.next) {
        return asignaciones
      }

      page += 1
    }
  },

  async asignar(datos: AsignarRolInput): Promise<UsuarioRol> {
    const { data } = await api.post<UsuarioRol>(
      '/usuario-roles/',
      datos,
    )

    return data
  },

  /** Recibe el identificador de la asignación que se quiere quitar. */
  async quitar(asignacionId: number): Promise<void> {
    await api.delete(`/usuario-roles/${asignacionId}/`)
  },
}