import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { esAdminClinica, esAdminSistema, esMedico } from '@/lib/roles'
import { LoginPage } from '@/pages/auth/LoginPage'
import { EspecialidadesPage } from '@/pages/clinica/especialidades/EspecialidadesPage'
import { PersonalPage } from '@/pages/clinica/Personal/PersonalPage'
import { RolesPage } from '@/pages/clinica/roles/RolesPage'
import { SuscripcionesPage } from '@/pages/clinica/suscripciones/SuscripcionesPage'
import { UsuariosPage } from '@/pages/clinica/usuarios/UsuariosPage'
import { MedicosPage } from '@/pages/clinica/medicos/MedicosPage'
import { HorariosPage } from '@/pages/clinica/horarios/HorariosPage'
import { MiClinicaPage } from '@/pages/clinica/MiClinicaPage'
import { CuentaPage } from '@/pages/cuenta/CuentaPage'
import { ClinicasPage } from '@/pages/sistema/ClinicasPage'
import { PlanesPage } from '@/pages/sistema/PlanesPage'
import { ClinicaInactivaPage } from '@/pages/errors/ClinicaInactivaPage'
import { NotFoundPage } from '@/pages/errors/NotFoundPage'
import { SinPermisoPage } from '@/pages/errors/SinPermisoPage'
import { InicioPage } from '@/pages/InicioPage'
import { ProtectedRoute } from './ProtectedRoute'
import { Raiz } from './Raiz'
import { RoleRoute } from './RoleRoute'

const adminOMedico = (usuario: Parameters<typeof esAdminClinica>[0]) => esAdminClinica(usuario) || esMedico(usuario)

export const router = createBrowserRouter([
  {
    element: <Raiz />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/clinica-inactiva', element: <ClinicaInactivaPage /> },
      {
        element: <ProtectedRoute />,
        children: [{
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
            { path: '*', element: <NotFoundPage /> },
          ],
        }],
      },
    ],
  },
])
