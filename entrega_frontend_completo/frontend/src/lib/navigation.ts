import {
  Briefcase, Building2, CalendarCheck, Clock, CreditCard,
  HeartPulse, LayoutDashboard, ShieldCheck, Stethoscope, Users, UserRound,
  type LucideIcon,
} from 'lucide-react'
import type { Usuario } from '@/types/auth'
import { esAdminClinica, esAdminSistema, esMedico } from './roles'

export interface ItemNav {
  etiqueta: string
  ruta: string
  icono: LucideIcon
  visible: (usuario: Usuario) => boolean
}
const completo = (usuario: Usuario) => usuario.esAdminSistema || (!usuario.accesoRestringido && usuario.suscripcionVigente)
const admin = (usuario: Usuario) => esAdminClinica(usuario) && completo(usuario)
const clinico = (usuario: Usuario) => (esAdminClinica(usuario) || esMedico(usuario)) && completo(usuario)

export const ITEMS_NAV: ItemNav[] = [
  { etiqueta: 'Inicio', ruta: '/', icono: LayoutDashboard, visible: completo },
  { etiqueta: 'Mi cuenta', ruta: '/cuenta', icono: UserRound, visible: () => true },
  { etiqueta: 'Clínicas', ruta: '/sistema/clinicas', icono: Building2, visible: esAdminSistema },
  { etiqueta: 'Planes', ruta: '/sistema/planes', icono: CreditCard, visible: esAdminSistema },
  { etiqueta: 'Suscripciones', ruta: '/sistema/suscripciones', icono: CalendarCheck, visible: esAdminSistema },
  { etiqueta: 'Mi clínica', ruta: '/mi-clinica', icono: Building2, visible: admin },
  { etiqueta: 'Mi suscripción', ruta: '/suscripciones', icono: CalendarCheck, visible: esAdminClinica },
  { etiqueta: 'Planes disponibles', ruta: '/planes', icono: CreditCard, visible: esAdminClinica },
  { etiqueta: 'Usuarios', ruta: '/usuarios', icono: Users, visible: admin },
  { etiqueta: 'Roles', ruta: '/roles', icono: ShieldCheck, visible: admin },
  { etiqueta: 'Personal', ruta: '/personal', icono: Briefcase, visible: admin },
  { etiqueta: 'Especialidades', ruta: '/especialidades', icono: Stethoscope, visible: clinico },
  { etiqueta: 'Médicos', ruta: '/medicos', icono: HeartPulse, visible: clinico },
  { etiqueta: 'Horarios', ruta: '/horarios', icono: Clock, visible: clinico },
]
