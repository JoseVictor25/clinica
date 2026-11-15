import type { ListParams, Paginated } from '@/types/api'
import { api } from './client'

function limpiar(params: ListParams): ListParams {
  return Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== ''),
  ) as ListParams
}

/** Operaciones estándar sobre un recurso REST: base debe terminar en "/" (p. ej. "/especialidades/"). */
export function crearCrud<T, I = Partial<T>>(base: string) {
  return {
    listar: async (params: ListParams = {}) =>
      (await api.get<Paginated<T>>(base, { params: limpiar(params) })).data,
    obtener: async (id: number) => (await api.get<T>(`${base}${id}/`)).data,
    crear: async (datos: I) => (await api.post<T>(base, datos)).data,
    actualizar: async (id: number, datos: Partial<I>) => (await api.patch<T>(`${base}${id}/`, datos)).data,
    eliminar: async (id: number) => {
      await api.delete(`${base}${id}/`)
    },
  }
}