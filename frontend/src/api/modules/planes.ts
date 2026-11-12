import type { Paginated } from '@/types/api'
import { api } from '../client'

export interface PlanSuscripcion {
  id: number
  nombre: string
  /** El backend devuelve los importes decimales como texto. */
  precio: string
  max_usuarios: number
  descripcion: string
  activo: boolean
}

export interface PlanesParams {
  page?: number
  page_size?: number
  activo?: boolean
}

export const planesApi = {
  async listar(
    params: PlanesParams = {},
  ): Promise<Paginated<PlanSuscripcion>> {
    const { data } = await api.get<Paginated<PlanSuscripcion>>(
      '/planes/',
      { params },
    )

    return data
  },

  async obtener(id: number): Promise<PlanSuscripcion> {
    const { data } = await api.get<PlanSuscripcion>(
      `/planes/${id}/`,
    )

    return data
  },

  /**
   * Obtiene todos los planes activos para el selector del formulario.
   * Recorre la paginación para no limitarse a la primera página.
   */
  async listarActivos(): Promise<PlanSuscripcion[]> {
    const planes: PlanSuscripcion[] = []
    let page = 1

    while (true) {
      const { data } = await api.get<Paginated<PlanSuscripcion>>(
        '/planes/',
        {
          params: {
            activo: true,
            page,
            page_size: 100,
          },
        },
      )

      planes.push(...data.results)

      if (!data.next) {
        return planes
      }

      page += 1
    }
  },
}
