export interface Usuario {
  id: number
  username: string
  email: string
  clinicaId: number | null
  clinicaNombre: string | null
  /** Superusuario sin clínica. */
  esAdminSistema: boolean
  /** Nombres de los roles activos asignados al usuario. */
  roles: string[]
  suscripcionVigente: boolean
  /** Fecha YYYY-MM-DD o null cuando no hay suscripción vigente. */
  suscripcionFin: string | null
  accesoRestringido: boolean
}