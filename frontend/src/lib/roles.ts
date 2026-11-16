import type { Usuario } from '@/types/auth'

// Nombres de los roles base cargados por la semilla del backend.
export const ROL_ADMIN_CLINICA = 'Administrador de clínica'
export const ROL_RECEPCIONISTA = 'Recepcionista'
export const ROL_MEDICO = 'Médico'
export const ROL_PACIENTE = 'Paciente'

export const esAdminSistema = (u: Usuario) => u.esAdminSistema
export const esAdminClinica = (u: Usuario) => !u.esAdminSistema && u.roles.includes(ROL_ADMIN_CLINICA)
export const esMedico = (u: Usuario) => !u.esAdminSistema && u.roles.includes(ROL_MEDICO)
export const esRecepcionista = (u: Usuario) => !u.esAdminSistema && u.roles.includes(ROL_RECEPCIONISTA)
export const esPaciente = (u: Usuario) => !u.esAdminSistema && u.roles.includes(ROL_PACIENTE)
export const puedeConsultarPacientes = (u: Usuario) => esAdminClinica(u) || esRecepcionista(u) || esMedico(u)
export const puedeGestionarPacientes = (u: Usuario) => esAdminClinica(u) || esRecepcionista(u)
export const puedeConsultarEnfermedades = (u: Usuario) => esAdminClinica(u) || esMedico(u)
export const puedeGestionarEnfermedades = (u: Usuario) => esMedico(u)
export const puedeConsultarAlergias = (u: Usuario) => esAdminClinica(u) || esMedico(u)
export const puedeGestionarAlergias = (u: Usuario) => esMedico(u)
export const puedeGestionarCitas = (u: Usuario) => esAdminClinica(u) || esRecepcionista(u)
