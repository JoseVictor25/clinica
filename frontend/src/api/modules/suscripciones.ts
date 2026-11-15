import type { Paginated } from '@/types/api'
import { api } from '../client'

export type EstadoSuscripcion =
  | 'ACTIVA'
  | 'VENCIDA'
  | 'CANCELADA'
  | 'SUSPENDIDA'

export interface Suscripcion {
  id: number
  clinica: number
  clinica_nombre: string
  plan: number
  plan_nombre: string
  /** Fecha en formato YYYY-MM-DD. */
  fecha_inicio: string
  /** Fecha en formato YYYY-MM-DD. */
  fecha_fin: string
  estado: EstadoSuscripcion
  /**
   * Actualmente el backend indica si la clínica tiene alguna
   * suscripción vigente. No identifica la vigencia de esta fila.
   */
  vigente: boolean
}

export interface SuscripcionesParams {
  page?: number
  page_size?: number
  estado?: EstadoSuscripcion
}

export interface ContratarSuscripcionInput {
  plan_id: number
  /** Si se omite, el backend utiliza la fecha actual. */
  fecha_inicio?: string
  fecha_fin: string
}

export interface RenovarSuscripcionInput {
  nueva_fecha_fin: string
}

export interface CambiarPlanInput {
  plan_id: number
  /** Si se omite, el backend utiliza la fecha actual. */
  fecha_inicio?: string
  fecha_fin: string
}

export const suscripcionesApi = {
  async listar(
    params: SuscripcionesParams = {},
  ): Promise<Paginated<Suscripcion>> {
    const { data } = await api.get<Paginated<Suscripcion>>(
      '/suscripciones/',
      { params },
    )

    return data
  },

  async obtener(id: number): Promise<Suscripcion> {
    const { data } = await api.get<Suscripcion>(
      `/suscripciones/${id}/`,
    )

    return data
  },

  async contratar(
    datos: ContratarSuscripcionInput,
  ): Promise<Suscripcion> {
    const { data } = await api.post<Suscripcion>(
      '/suscripciones/',
      datos,
    )

    return data
  },

  async renovar(
    id: number,
    datos: RenovarSuscripcionInput,
  ): Promise<Suscripcion> {
    const { data } = await api.post<Suscripcion>(
      `/suscripciones/${id}/renovar/`,
      datos,
    )

    return data
  },

  async cambiarPlan(
    id: number,
    datos: CambiarPlanInput,
  ): Promise<Suscripcion> {
    const { data } = await api.post<Suscripcion>(
      `/suscripciones/${id}/cambiar-plan/`,
      datos,
    )

    return data
  },

  async cancelar(id: number): Promise<Suscripcion> {
    const { data } = await api.post<Suscripcion>(
      `/suscripciones/${id}/cancelar/`,
    )

    return data
  },
}