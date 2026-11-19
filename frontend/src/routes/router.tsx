import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { esAdminClinica, esAdminSistema, esMedico, esPaciente, puedeConsultarPacientes, puedeGestionarCitas } from '@/lib/roles'
import { LoginPage } from '@/pages/auth/LoginPage'
import { EspecialidadesPage } from '@/pages/clinica/especialidades/EspecialidadesPage'
import { PersonalPage } from '@/pages/clinica/Personal/PersonalPage'
import { RolesPage } from '@/pages/clinica/roles/RolesPage'
import { SuscripcionesPage } from '@/pages/clinica/suscripciones/SuscripcionesPage'
import { UsuariosPage } from '@/pages/clinica/usuarios/UsuariosPage'
import { MedicosPage } from '@/pages/clinica/medicos/MedicosPage'
import { HorariosPage } from '@/pages/clinica/horarios/HorariosPage'
import { MiClinicaPage } from '@/pages/clinica/MiClinicaPage'
import { PacientesPage } from '@/pages/clinica/pacientes/PacientesPage'
import { CitasPage } from '@/pages/clinica/citas/CitasPage'
import { MiAgendaPage } from '@/pages/medico/MiAgendaPage'
import { HistorialConsultasPage } from '@/pages/medico/HistorialConsultasPage'
import { CuentaPage } from '@/pages/cuenta/CuentaPage'
import { ClinicasPage } from '@/pages/sistema/ClinicasPage'
import { PlanesPage } from '@/pages/sistema/PlanesPage'
import { ClinicaInactivaPage } from '@/pages/errors/ClinicaInactivaPage'
import { NotFoundPage } from '@/pages/errors/NotFoundPage'
import { SinPermisoPage } from '@/pages/errors/SinPermisoPage'
import { InicioPage } from '@/pages/InicioPage'
import { PortalPacientePage } from '@/pages/paciente/PortalPacientePage'
import { SalaVirtualPage } from '@/pages/telemedicina/SalaVirtualPage'
import { VisorEstudioPage } from '@/pages/estudios/VisorEstudioPage'
import { ProtectedRoute } from './ProtectedRoute'
import { Raiz } from './Raiz'
import { RoleRoute } from './RoleRoute'

const adminOMedico = (usuario: Parameters<typeof esAdminClinica>[0]) => esAdminClinica(usuario) || esMedico(usuario)
const medicoOPaciente = (usuario: Parameters<typeof esMedico>[0]) => esMedico(usuario) || esPaciente(usuario)
const puedeVerEstudios = (usuario: Parameters<typeof esAdminClinica>[0]) =>
  esAdminClinica(usuario) || esMedico(usuario) || esPaciente(usuario)

export const router = createBrowserRouter([
  {
    element: <Raiz />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/clinica-inactiva', element: <ClinicaInactivaPage /> },
      {
        element: <ProtectedRoute />,
        children: [
          {
            element: <RoleRoute permitir={medicoOPaciente} />,
            children: [{ path: '/sala-virtual/:citaId', element: <SalaVirtualPage /> }],
          },
          {
            element: <RoleRoute permitir={puedeVerEstudios} />,
            children: [{ path: '/estudios/:estudioId/visor', element: <VisorEstudioPage /> }],
          },
          {
            element: <AppLayout />,
          children: [
            { index: true, element: <InicioPage /> },
            { path: 'cuenta', element: <CuentaPage /> },
            { path: 'sin-permiso', element: <SinPermisoPage /> },
            {
              element: <RoleRoute permitir={esAdminSistema} />,
              children: [
                { path: 'sistema/clinicas', element: <ClinicasPage /> },
                { path: 'sistema/planes', element: <PlanesPage /> },
                { path: 'sistema/suscripciones', element: <SuscripcionesPage /> },
              ],
            },
            {
              element: <RoleRoute permitir={esAdminClinica} />,
              children: [
                { path: 'suscripciones', element: <SuscripcionesPage /> },
                { path: 'planes', element: <PlanesPage /> },
                { path: 'mi-clinica', element: <MiClinicaPage /> },
                { path: 'usuarios', element: <UsuariosPage /> },
                { path: 'roles', element: <RolesPage /> },
                { path: 'personal', element: <PersonalPage /> },
              ],
            },
            {
              element: <RoleRoute permitir={adminOMedico} />,
              children: [
                { path: 'especialidades', element: <EspecialidadesPage /> },
                { path: 'medicos', element: <MedicosPage /> },
                { path: 'horarios', element: <HorariosPage /> },
              ],
            },
            {
              element: <RoleRoute permitir={puedeConsultarPacientes} />,
              children: [{ path: 'pacientes', element: <PacientesPage /> }],
            },
            {
              element: <RoleRoute permitir={puedeGestionarCitas} />,
              children: [{ path: 'citas', element: <CitasPage /> }],
            },
            {
              element: <RoleRoute permitir={esMedico} />,
              children: [
                { path: 'mi-agenda', element: <MiAgendaPage /> },
                { path: 'pacientes/:pacienteId/historial', element: <HistorialConsultasPage /> },
              ],
            },
            {
              element: <RoleRoute permitir={esPaciente} />,
              children: [{ path: 'mi-informacion', element: <PortalPacientePage /> }],
            },
            { path: '*', element: <NotFoundPage /> },
          ],
        },
        ],
      },
    ],
  },
])
