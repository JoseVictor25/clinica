import type { Paginated } from '@/types/api'
import { api } from '../client'

export type TipoEstudio = 'RADIOGRAFIA' | 'ECOGRAFIA' | 'TOMOGRAFIA' | 'LABORATORIO'
export type FormatoEstudio = 'DICOM' | 'IMAGEN' | 'PDF'
export type EstadoEstudio = 'PENDIENTE_REVISION' | 'REVISADO'

export const TIPOS_ESTUDIO: { valor: TipoEstudio; etiqueta: string }[] = [
  { valor: 'RADIOGRAFIA', etiqueta: 'Radiografía' },
  { valor: 'ECOGRAFIA', etiqueta: 'Ecografía' },
  { valor: 'TOMOGRAFIA', etiqueta: 'Tomografía' },
  { valor: 'LABORATORIO', etiqueta: 'Laboratorio' },
]

export interface EstudioMedico {
  id: number
  paciente_id: number
  paciente_nombre: string
  historia_clinica_id: number | null
  cita_id: number | null
  consulta_id: number | null
  medico_id: number | null
  medico_nombre: string | null
  tipo_estudio: TipoEstudio
  tipo_estudio_display: string
  formato: FormatoEstudio
  formato_display: string
  nombre_archivo: string
  url_archivo: string
  ruta_storage: string | null
  estado: EstadoEstudio
  estado_display: string
  observacion_lectura: string | null
  fecha_estudio: string
  puede_modificar: boolean
}

export interface FiltrosEstudio {
  cita_id?: number
  paciente_id?: number
  consulta_id?: number
  estado?: EstadoEstudio
  formato?: FormatoEstudio
  page?: number
  page_size?: number
}

export interface EstudioSubirInput {
  tipo_estudio: TipoEstudio
  cita_id?: number
  paciente_id?: number
  archivo: File
}

export interface EstudioRevisarInput {
  observacion_lectura: string
  consulta_id?: number | null
}

export const estudiosMedicosApi = {
  async listar(params: FiltrosEstudio = {}): Promise<Paginated<EstudioMedico>> {
    return (await api.get<Paginated<EstudioMedico>>('/estudios-medicos/', { params })).data
  },

  async obtener(id: number): Promise<EstudioMedico> {
    return (await api.get<EstudioMedico>(`/estudios-medicos/${id}/`)).data
  },

  async subir(datos: EstudioSubirInput): Promise<EstudioMedico> {
    const formData = new FormData()
    formData.append('tipo_estudio', datos.tipo_estudio)
    formData.append('archivo', datos.archivo)
    if (datos.cita_id !== undefined) {
      formData.append('cita_id', String(datos.cita_id))
    }
    if (datos.paciente_id !== undefined) {
      formData.append('paciente_id', String(datos.paciente_id))
    }
    return (
      await api.post<EstudioMedico>('/estudios-medicos/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    ).data
  },

  async actualizar(
    id: number,
    datos: { tipo_estudio?: TipoEstudio; archivo?: File },
  ): Promise<EstudioMedico> {
    const formData = new FormData()
    if (datos.tipo_estudio) formData.append('tipo_estudio', datos.tipo_estudio)
    if (datos.archivo) formData.append('archivo', datos.archivo)
    return (
      await api.patch<EstudioMedico>(`/estudios-medicos/${id}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    ).data
  },

  async eliminar(id: number): Promise<void> {
    await api.delete(`/estudios-medicos/${id}/`)
  },

  async revisar(id: number, datos: EstudioRevisarInput): Promise<EstudioMedico> {
    return (await api.patch<EstudioMedico>(`/estudios-medicos/${id}/revisar/`, datos)).data
  },

  async descargarArchivoBlob(id: number): Promise<Blob> {
    return (
      await api.get<Blob>(`/estudios-medicos/${id}/archivo/`, {
        responseType: 'blob',
      })
    ).data
  },
}
