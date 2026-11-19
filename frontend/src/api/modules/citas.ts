import type { ListParams, Paginated } from '@/types/api'
import { api } from '../client'

export type EstadoCita =
  | 'PROGRAMADA'
  | 'CONFIRMADA'
  | 'ATENDIDA'
  | 'CANCELADA'
  | 'NO_ASISTIO'

export const ESTADOS_CITA: { valor: EstadoCita; etiqueta: string }[] = [
  { valor: 'PROGRAMADA', etiqueta: 'Programada' },
  { valor: 'CONFIRMADA', etiqueta: 'Confirmada' },
  { valor: 'ATENDIDA', etiqueta: 'Atendida' },
  { valor: 'CANCELADA', etiqueta: 'Cancelada' },
  { valor: 'NO_ASISTIO', etiqueta: 'No asistió' },
]

export type ModalidadCita = 'PRESENCIAL' | 'VIRTUAL'

export const MODALIDADES_CITA: { valor: ModalidadCita; etiqueta: string }[] = [
  { valor: 'PRESENCIAL', etiqueta: 'Presencial' },
  { valor: 'VIRTUAL', etiqueta: 'Virtual' },
]

export interface Cita {
  id: number
  paciente_id: number
  paciente_nombre: string
  medico_id: number
  medico_nombre: string
  especialidad_id: number
  especialidad_nombre: string
  fecha: string
  hora: string
  estado: EstadoCita
  estado_display: string
  modalidad: ModalidadCita
  modalidad_display: string
  link_videollamada: string | null
  motivo: string
  consulta_id: number | null
  tiene_consulta: boolean
}

export interface CitaCrearInput {
  paciente_id: number
  medico_id: number
  fecha: string
  hora: string
  modalidad?: ModalidadCita
  motivo: string
}

export interface CitaReprogramarInput {
  fecha: string
  hora: string
}

export interface DisponibilidadCita {
  paciente_id: number
  medico_id: number
  fecha: string
  duracion_minutos: number
  horarios: string[]
}

export interface FiltrosCita extends ListParams {
  fecha?: string
  paciente_id?: number
  medico_id?: number
  estado?: EstadoCita
}

export interface FiltrosMiAgenda extends ListParams {
  fecha?: string
  estado?: EstadoCita
}

export const citasApi = {
  async listar(params: FiltrosCita = {}): Promise<Paginated<Cita>> {
    return (await api.get<Paginated<Cita>>('/citas/', { params })).data
  },
  async obtenerMiAgenda(params: FiltrosMiAgenda = {}): Promise<Paginated<Cita>> {
    return (await api.get<Paginated<Cita>>('/citas/mi-agenda/', { params })).data
  },
  async obtener(id: number): Promise<Cita> {
    return (await api.get<Cita>(`/citas/${id}/`)).data
  },
  async obtenerSalaVirtual(id: number): Promise<Cita> {
    return (await api.get<Cita>(`/citas/${id}/sala-virtual/`)).data
  },
  async crear(datos: CitaCrearInput): Promise<Cita> {
    return (await api.post<Cita>('/citas/', datos)).data
  },
  async confirmar(id: number): Promise<Cita> {
    return (await api.post<Cita>(`/citas/${id}/confirmar/`, {})).data
  },
  async cancelar(id: number): Promise<Cita> {
    return (await api.post<Cita>(`/citas/${id}/cancelar/`, {})).data
  },
  async reprogramar(id: number, datos: CitaReprogramarInput): Promise<Cita> {
    return (await api.post<Cita>(`/citas/${id}/reprogramar/`, datos)).data
  },
  async disponibilidad(
    pacienteId: number,
    medicoId: number,
    fecha: string,
    citaId?: number,
  ): Promise<DisponibilidadCita> {
    return (
      await api.get<DisponibilidadCita>('/citas/disponibilidad/', {
        params: {
          paciente_id: pacienteId,
          medico_id: medicoId,
          fecha,
          cita_id: citaId,
        },
      })
    ).data
  },
}
