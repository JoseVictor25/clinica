import type { ListParams, Paginated } from '@/types/api'
import { api } from '../client'

export type SexoPaciente = 'M' | 'F' | 'OTRO'
export interface Paciente { id: number; clinica: number; ci: string; nombre: string; apellido: string; sexo: SexoPaciente; fecha_nacimiento: string; telefono: string; email: string; estado: boolean; tiene_usuario_vinculado: boolean }
export type PacienteInput = Omit<Paciente, 'id' | 'clinica' | 'tiene_usuario_vinculado'>
export const SEXOS = [{ valor: 'M', etiqueta: 'Masculino' }, { valor: 'F', etiqueta: 'Femenino' }, { valor: 'OTRO', etiqueta: 'Otro' }] as const

export const pacientesApi = {
  async listar(params: ListParams = {}) { return (await api.get<Paginated<Paciente>>('/pacientes/', { params })).data },
  async obtener(id: number) { return (await api.get<Paciente>(`/pacientes/${id}/`)).data },
  async crear(datos: PacienteInput) { return (await api.post<Paciente>('/pacientes/', datos)).data },
  async actualizar(id: number, datos: Partial<PacienteInput>) { return (await api.patch<Paciente>(`/pacientes/${id}/`, datos)).data },
  async desactivar(id: number) { await api.delete(`/pacientes/${id}/`) },
  async vincularUsuario(id: number, usuarioId: number) { return (await api.post<{ codigo: string; mensaje: string; paciente_id: number; usuario_id: number }>(`/pacientes/${id}/vincular-usuario/`, { usuario_id: usuarioId })).data },
}
