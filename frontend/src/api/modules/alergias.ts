import type { ListParams, Paginated } from '@/types/api'
import { api } from '../client'

export type TipoAlergia = 'MEDICAMENTO' | 'ALIMENTO' | 'AMBIENTAL' | 'OTRA'
export type SeveridadAlergia = 'LEVE' | 'MODERADA' | 'GRAVE'

export interface Alergia {
  id: number
  nombre: string
  tipo: TipoAlergia
  severidad: SeveridadAlergia
  descripcion: string
}

export interface AlergiaInput {
  nombre: string
  tipo: TipoAlergia
  severidad: SeveridadAlergia
  descripcion: string
}

export interface AlergiasParams extends ListParams {
  tipo?: TipoAlergia
  severidad?: SeveridadAlergia
}

export const TIPOS_ALERGIA = [
  { valor: 'MEDICAMENTO', etiqueta: 'Medicamento' },
  { valor: 'ALIMENTO', etiqueta: 'Alimento' },
  { valor: 'AMBIENTAL', etiqueta: 'Ambiental' },
  { valor: 'OTRA', etiqueta: 'Otra' },
] as const

export const SEVERIDADES_ALERGIA = [
  { valor: 'LEVE', etiqueta: 'Leve' },
  { valor: 'MODERADA', etiqueta: 'Moderada' },
  { valor: 'GRAVE', etiqueta: 'Grave' },
] as const

const base = (pacienteId: number) => `/pacientes/${pacienteId}/alergias/`

export const alergiasApi = {
  async listar(pacienteId: number, params: AlergiasParams = {}) {
    return (await api.get<Paginated<Alergia>>(base(pacienteId), { params })).data
  },
  async obtener(pacienteId: number, alergiaId: number) {
    return (await api.get<Alergia>(`${base(pacienteId)}${alergiaId}/`)).data
  },
  async crear(pacienteId: number, datos: AlergiaInput) {
    return (await api.post<Alergia>(base(pacienteId), datos)).data
  },
  async actualizar(pacienteId: number, alergiaId: number, datos: Partial<AlergiaInput>) {
    return (await api.patch<Alergia>(`${base(pacienteId)}${alergiaId}/`, datos)).data
  },
}
