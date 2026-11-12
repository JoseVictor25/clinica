import { api } from '../client'
import type { ListParams, Paginated } from '@/types/api'

export interface Clinica {
  id: number
  nombre: string
  direccion: string
  telefono: string
  email: string
  nit: string
  estado: boolean
}
export interface ClinicaInput {
  nombre: string
  direccion: string
  telefono: string
  email: string
  nit: string
  estado?: boolean
}
export interface ClinicaCreateInput extends Omit<ClinicaInput, 'estado'> {
  admin: { username: string; email: string; password: string }
}
export interface Plan {
  id: number
  nombre: string
  precio: string
  max_usuarios: number
  descripcion: string
  activo: boolean
}
export type PlanInput = Omit<Plan, 'id'>
export interface Medico {
  id: number
  clinica: number
  clinica_nombre: string
  personal: number
  personal_nombre: string
  especialidad: number
  especialidad_nombre: string
  numero_colegiatura: string
  estado: boolean
}
export interface MedicoInput {
  personal: number
  especialidad: number
  numero_colegiatura: string
  estado: boolean
}
export interface Horario {
  id: number
  medico: number
  medico_nombre: string
  dia_semana: number
  hora_inicio: string
  hora_fin: string
}
export interface HorarioInput {
  medico?: number
  dia_semana: number
  hora_inicio: string
  hora_fin: string
}
export interface RecursoApi<T, C, U = Partial<C>> {
  listar: (params?: ListParams) => Promise<Paginated<T>>
  obtener: (id: number) => Promise<T>
  crear: (datos: C) => Promise<T>
  actualizar: (id: number, datos: U) => Promise<T>
  eliminar: (id: number) => Promise<void>
}
function recurso<T, C, U = Partial<C>>(ruta: string): RecursoApi<T, C, U> {
  return {
    listar: async (params = {}) => (await api.get<Paginated<T>>(ruta, { params })).data,
    obtener: async (id) => (await api.get<T>(`${ruta}${id}/`)).data,
    crear: async (datos) => (await api.post<T>(ruta, datos)).data,
    actualizar: async (id, datos) => (await api.patch<T>(`${ruta}${id}/`, datos)).data,
    eliminar: async (id) => { await api.delete(`${ruta}${id}/`) },
  }
}
export const clinicasGestionApi = recurso<Clinica, ClinicaCreateInput, Partial<ClinicaInput>>('/clinicas/')
export const planesGestionApi = recurso<Plan, PlanInput>('/planes/')
export const medicosApi = recurso<Medico, MedicoInput>('/medicos/')
export const horariosApi = recurso<Horario, HorarioInput>('/horarios/')

export async function todasLasPaginas<T>(
  listar: (params?: ListParams) => Promise<Paginated<T>>,
  filtros: ListParams = {},
): Promise<T[]> {
  const filas: T[] = []
  let page = 1
  while (true) {
    const resultado = await listar({ ...filtros, page, page_size: 100 })
    filas.push(...resultado.results)
    if (!resultado.next) return filas
    page += 1
  }
}

export async function cambiarPassword(datos: {
  password_actual: string
  password_nueva: string
}): Promise<{ codigo: string; mensaje: string }> {
  return (await api.post<{ codigo: string; mensaje: string }>('/auth/cambiar-password/', datos)).data
}
