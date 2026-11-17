import { crearCrud } from '../crud'

export interface Especialidad {
  id: number
  nombre: string
  descripcion: string
  estado: boolean
}

export interface EspecialidadInput {
  nombre: string
  descripcion: string
  estado: boolean
}

export const especialidadesApi = crearCrud<Especialidad, EspecialidadInput>('/especialidades/')