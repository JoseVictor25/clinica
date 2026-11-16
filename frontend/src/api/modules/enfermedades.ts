import type { ListParams, Paginated } from '@/types/api'
import { api } from '../client'

export type TipoEnfermedad = 'CRONICA' | 'AGUDA' | 'HEREDITARIA' | 'INFECCIOSA' | 'OTRA'
export type SeveridadEnfermedad = 'LEVE' | 'MODERADA' | 'GRAVE'

export interface Enfermedad {
  id: number
  nombre: string
  tipo: TipoEnfermedad
  severidad: SeveridadEnfermedad
  fecha_deteccion: string
}

export interface EnfermedadInput {
  nombre: string
  tipo: TipoEnfermedad
  severidad: SeveridadEnfermedad
  fecha_deteccion: string
}

export interface EnfermedadesParams extends ListParams {
  tipo?: TipoEnfermedad
  severidad?: SeveridadEnfermedad
}

export const TIPOS_ENFERMEDAD = [
  { valor: 'CRONICA', etiqueta: 'Crónica' },
  { valor: 'AGUDA', etiqueta: 'Aguda' },
  { valor: 'HEREDITARIA', etiqueta: 'Hereditaria' },
  { valor: 'INFECCIOSA', etiqueta: 'Infecciosa' },
  { valor: 'OTRA', etiqueta: 'Otra' },
] as const

export const SEVERIDADES_ENFERMEDAD = [
  { valor: 'LEVE', etiqueta: 'Leve' },
  { valor: 'MODERADA', etiqueta: 'Moderada' },
  { valor: 'GRAVE', etiqueta: 'Grave' },
] as const

const base = (pacienteId: number) => `/pacientes/${pacienteId}/enfermedades/`

export const enfermedadesApi = {
  async listar(pacienteId: number, params: EnfermedadesParams = {}) {
    return (await api.get<Paginated<Enfermedad>>(base(pacienteId), { params })).data
  },
  async obtener(pacienteId: number, enfermedadId: number) {
    return (await api.get<Enfermedad>(`${base(pacienteId)}${enfermedadId}/`)).data
  },
  async crear(pacienteId: number, datos: EnfermedadInput) {
    return (await api.post<Enfermedad>(base(pacienteId), datos)).data
  },
  async actualizar(pacienteId: number, enfermedadId: number, datos: Partial<EnfermedadInput>) {
    return (await api.patch<Enfermedad>(`${base(pacienteId)}${enfermedadId}/`, datos)).data
  },
}
