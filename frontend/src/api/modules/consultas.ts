import { api } from '../client'
import type { RecetaResumen } from './recetas'

export interface Consulta {
  id: number
  cita_id: number
  fecha: string
  paciente_id: number
  paciente_nombre: string
  medico_id: number
  medico_nombre: string
  motivo: string
  observacion: string
  diagnostico: string
  estado_cita: 'ATENDIDA'
  recetas: RecetaResumen[]
}

export interface ConsultaCrearInput {
  cita_id: number
  motivo: string
  observacion: string
  diagnostico: string
}

export const consultasApi = {
  async crear(datos: ConsultaCrearInput): Promise<Consulta> {
    return (await api.post<Consulta>('/consultas/', datos)).data
  },
  async obtener(id: number): Promise<Consulta> {
    return (await api.get<Consulta>(`/consultas/${id}/`)).data
  },
}
