import {
  Briefcase, Building2, CalendarCheck, Clock, CreditCard,
  HeartPulse, LayoutDashboard, ShieldCheck, Stethoscope, Users, UserRound,
  type LucideIcon,
} from 'lucide-react'
import type { Usuario } from '@/types/auth'
import { esAdminClinica, esAdminSistema, esMedico, esPaciente, puedeConsultarPacientes, puedeGestionarCitas } from './roles'

export interface ItemNav {
  etiqueta: string
  ruta: string
  guiaId: string
  icono: LucideIcon
  visible: (usuario: Usuario) => boolean
}
const completo = (usuario: Usuario) => usuario.esAdminSistema || (!usuario.accesoRestringido && usuario.suscripcionVigente)
const admin = (usuario: Usuario) => esAdminClinica(usuario) && completo(usuario)
const clinico = (usuario: Usuario) => (esAdminClinica(usuario) || esMedico(usuario)) && completo(usuario)
const pacientes = (usuario: Usuario) => puedeConsultarPacientes(usuario) && completo(usuario)
const citas = (usuario: Usuario) => puedeGestionarCitas(usuario) && completo(usuario)
const miAgenda = (usuario: Usuario) => esMedico(usuario) && completo(usuario)
const portalPaciente = (usuario: Usuario) => esPaciente(usuario) && completo(usuario)

export const ITEMS_NAV: ItemNav[] = [
  { etiqueta: 'Inicio', ruta: '/', guiaId: 'nav-inicio', icono: LayoutDashboard, visible: completo },
  { etiqueta: 'Mi cuenta', ruta: '/cuenta', guiaId: 'nav-cuenta', icono: UserRound, visible: () => true },
  { etiqueta: 'Mi información', ruta: '/mi-informacion', guiaId: 'nav-mi-informacion', icono: UserRound, visible: portalPaciente },
  { etiqueta: 'Clínicas', ruta: '/sistema/clinicas', guiaId: 'nav-sistema-clinicas', icono: Building2, visible: esAdminSistema },
  { etiqueta: 'Planes', ruta: '/sistema/planes', guiaId: 'nav-sistema-planes', icono: CreditCard, visible: esAdminSistema },
  { etiqueta: 'Suscripciones', ruta: '/sistema/suscripciones', guiaId: 'nav-sistema-suscripciones', icono: CalendarCheck, visible: esAdminSistema },
  { etiqueta: 'Mi clínica', ruta: '/mi-clinica', guiaId: 'nav-mi-clinica', icono: Building2, visible: admin },
  { etiqueta: 'Mi suscripción', ruta: '/suscripciones', guiaId: 'nav-suscripciones', icono: CalendarCheck, visible: esAdminClinica },
  { etiqueta: 'Planes disponibles', ruta: '/planes', guiaId: 'nav-planes', icono: CreditCard, visible: esAdminClinica },
  { etiqueta: 'Usuarios', ruta: '/usuarios', guiaId: 'nav-usuarios', icono: Users, visible: admin },
  { etiqueta: 'Roles', ruta: '/roles', guiaId: 'nav-roles', icono: ShieldCheck, visible: admin },
  { etiqueta: 'Personal', ruta: '/personal', guiaId: 'nav-personal', icono: Briefcase, visible: admin },
  { etiqueta: 'Pacientes', ruta: '/pacientes', guiaId: 'nav-pacientes', icono: Users, visible: pacientes },
  { etiqueta: 'Citas', ruta: '/citas', guiaId: 'nav-citas', icono: CalendarCheck, visible: citas },
  { etiqueta: 'Mi agenda', ruta: '/mi-agenda', guiaId: 'nav-mi-agenda', icono: CalendarCheck, visible: miAgenda },
  { etiqueta: 'Especialidades', ruta: '/especialidades', guiaId: 'nav-especialidades', icono: Stethoscope, visible: clinico },
  { etiqueta: 'Médicos', ruta: '/medicos', guiaId: 'nav-medicos', icono: HeartPulse, visible: clinico },
  { etiqueta: 'Horarios', ruta: '/horarios', guiaId: 'nav-horarios', icono: Clock, visible: clinico },
]
