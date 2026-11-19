import { api } from '../client'
import type { SexoPaciente } from './pacientes'

export interface PacienteHistorial {
  id: number
  ci: string
  nombre: string
  apellido: string
  sexo: SexoPaciente
  fecha_nacimiento: string
  estado: boolean
}

export interface MedicoHistorial {
  id: number
  nombre: string
  especialidad: string
}

export interface CitaHistorial {
  id: number
  fecha: string
  hora: string
  estado: string
}

export interface MedicamentoHistorial {
  id: number
  nombre_medicamento: string
  dosis: string
  frecuencia: string
  duracion: string
}

export interface RecetaHistorial {
  id: number
  fecha: string
  indicaciones: string
  puede_ver_detalle: boolean
  medicamentos: MedicamentoHistorial[]
}

export interface EstudioHistorial {
  id: number
  tipo_estudio: string
  tipo_estudio_display: string
  formato: string
  formato_display: string
  nombre_archivo: string
  estado: string
  estado_display: string
  observacion_lectura: string | null
  fecha_estudio: string
}

export interface ConsultaHistorial {
  id: number
  fecha: string
  motivo: string
  observacion: string
  diagnostico: string
  medico: MedicoHistorial
  cita: CitaHistorial | null
  recetas: RecetaHistorial[]
  estudios_medicos: EstudioHistorial[]
}

export interface HistorialConsultasPaciente {
  paciente: PacienteHistorial
  count: number
  next: string | null
  previous: string | null
  results: ConsultaHistorial[]
}

export interface HistorialConsultasParametros {
  fecha_desde?: string
  fecha_hasta?: string
  medico_id?: number
  ordering?: 'fecha' | '-fecha'
  page?: number
  page_size?: number
}

export const historialConsultasApi = {
  async obtenerHistorialConsultas(
    pacienteId: number,
    parametros: HistorialConsultasParametros = {},
  ): Promise<HistorialConsultasPaciente> {
    return (await api.get<HistorialConsultasPaciente>(
      `/pacientes/${pacienteId}/historial-consultas/`,
      { params: parametros },
    )).data
  },
}
