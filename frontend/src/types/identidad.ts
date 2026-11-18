export interface IdentidadCompartida {
  encontrado: boolean
  ci: string
  nombre: string
  apellido: string
  telefono: string
  email: string
  origen: 'PERSONAL' | 'PACIENTE' | null
}
