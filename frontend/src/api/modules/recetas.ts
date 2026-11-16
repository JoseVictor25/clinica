import { api } from '../client'

export interface MedicamentoRecetado {
  id: number
  nombre_medicamento: string
  dosis: string
  frecuencia: string
  duracion: string
}

export interface MedicamentoRecetadoInput {
  nombre_medicamento: string
  dosis: string
  frecuencia: string
  duracion: string
}

export interface AdvertenciaAlergia {
  alergia_id: number
  nombre_alergia: string
  severidad: string
  medicamento: string
  mensaje: string
}

export interface RecetaResumen {
  id: number
  fecha: string
  indicaciones: string
  cantidad_medicamentos: number
}

export interface Receta extends RecetaResumen {
  consulta_id: number
  paciente_id: number
  paciente_nombre: string
  medico_id: number
  medico_nombre: string
  medicamentos: MedicamentoRecetado[]
  advertencias_alergia: AdvertenciaAlergia[]
}

export interface RecetaCrearInput {
  indicaciones: string
  medicamentos: MedicamentoRecetadoInput[]
}

export const recetasApi = {
  async crearReceta(consultaId: number, datos: RecetaCrearInput): Promise<Receta> {
    return (await api.post<Receta>(`/consultas/${consultaId}/recetas/`, datos)).data
  },
  async obtenerReceta(id: number): Promise<Receta> {
    return (await api.get<Receta>(`/recetas/${id}/`)).data
  },
}
