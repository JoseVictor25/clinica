import type { Usuario } from '@/types/auth'

// Nombres de los roles base cargados por la semilla del backend.
export const ROL_ADMIN_CLINICA = 'Administrador de clínica'
export const ROL_RECEPCIONISTA = 'Recepcionista'
export const ROL_MEDICO = 'Médico'

export const esAdminSistema = (u: Usuario) => u.esAdminSistema
export const esAdminClinica = (u: Usuario) => !u.esAdminSistema && u.roles.includes(ROL_ADMIN_CLINICA)
export const esMedico = (u: Usuario) => !u.esAdminSistema && u.roles.includes(ROL_MEDICO)