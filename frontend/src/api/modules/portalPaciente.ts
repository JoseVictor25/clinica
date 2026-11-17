import type { Paginated } from '@/types/api'
import { api } from '../client'
import type { SexoPaciente } from './pacientes'

export interface PacientePropio { id: number; ci: string; nombre: string; apellido: string; sexo: SexoPaciente; fecha_nacimiento: string; telefono: string; email: string; estado: boolean }
export interface EnfermedadPropia { id: number; nombre: string; tipo: string; severidad: string; fecha_deteccion: string }
export interface AlergiaPropia { id: number; nombre: string; tipo: string; severidad: string; descripcion: string }
export interface HistoriaPropia { id: number; fecha_apertura: string; grupo_sanguineo: string; observaciones_generales: string; estado: boolean; enfermedades: EnfermedadPropia[]; alergias: AlergiaPropia[] }
export interface MedicoPortal { id: number; nombre: string; especialidad: string }
export interface CitaPropia { id: number; fecha: string; hora: string; estado: string; motivo: string; medico: MedicoPortal }
export interface RecetaResumenPropia { id: number; fecha: string; indicaciones: string; cantidad_medicamentos: number }
export interface ConsultaPropia { id: number; fecha: string; motivo: string; observacion: string; diagnostico: string; medico: MedicoPortal; cita: { id: number; fecha: string; hora: string; estado: string } | null; recetas: RecetaResumenPropia[] }
export interface RecetaPropia { id: number; fecha: string; indicaciones: string; consulta: { id: number; fecha: string; motivo: string; diagnostico: string }; medico: MedicoPortal; medicamentos: { id: number; nombre_medicamento: string; dosis: string; frecuencia: string; duracion: string }[] }
export interface FiltrosPortal { fecha_desde?: string; fecha_hasta?: string; ordering?: 'fecha' | '-fecha'; page?: number; page_size?: number }
export interface FiltrosCitasPortal extends FiltrosPortal { estado?: string }

export const portalPacienteApi = {
  async miInformacion() { return (await api.get<PacientePropio>('/portal-paciente/mi-informacion/')).data },
  async miHistoria() { return (await api.get<HistoriaPropia>('/portal-paciente/mi-historia/')).data },
  async misCitas(params: FiltrosCitasPortal = {}) { return (await api.get<Paginated<CitaPropia>>('/portal-paciente/mis-citas/', { params })).data },
  async misConsultas(params: FiltrosPortal = {}) { return (await api.get<Paginated<ConsultaPropia>>('/portal-paciente/mis-consultas/', { params })).data },
  async miReceta(id: number) { return (await api.get<RecetaPropia>(`/portal-paciente/mis-recetas/${id}/`)).data },
}
