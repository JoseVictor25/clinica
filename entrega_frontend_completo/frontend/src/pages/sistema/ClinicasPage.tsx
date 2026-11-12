import { clinicasGestionApi, type Clinica } from '@/api/modules/gestion'
import { GestionRecurso, type ConfiguracionRecurso, type CampoFormulario } from '@/components/gestion/GestionRecurso'

const campos: CampoFormulario[] = [
  { nombre: 'nombre', etiqueta: 'Nombre', obligatorio: true, maxLength: 150 },
  { nombre: 'direccion', etiqueta: 'Dirección', obligatorio: true, maxLength: 255 },
  { nombre: 'telefono', etiqueta: 'Teléfono', tipo: 'tel', obligatorio: true, maxLength: 30 },
  { nombre: 'email', etiqueta: 'Correo de la clínica', tipo: 'email', obligatorio: true, maxLength: 254 },
  { nombre: 'nit', etiqueta: 'NIT', obligatorio: true, maxLength: 20 },
]
const config: ConfiguracionRecurso<Clinica> = {
  clave: 'clinicas', titulo: 'Clínicas', nuevo: 'Registrar clínica',
  descripcion: 'El registro crea los roles base, las especialidades iniciales y el primer administrador de la clínica.',
  listar: clinicasGestionApi.listar, obtener: clinicasGestionApi.obtener,
  campos: (registro) => registro ? [...campos, { nombre: 'estado', etiqueta: 'Clínica activa', tipo: 'checkbox' }] : [
    ...campos,
    { nombre: 'admin.username', etiqueta: 'Usuario del primer administrador', obligatorio: true, maxLength: 150 },
    { nombre: 'admin.email', etiqueta: 'Correo del primer administrador', tipo: 'email', obligatorio: true, maxLength: 254 },
    { nombre: 'admin.password', etiqueta: 'Contraseña del primer administrador', tipo: 'password', obligatorio: true },
    { nombre: 'confirmacion', etiqueta: 'Confirmar contraseña', tipo: 'password', obligatorio: true },
  ],
  iniciales: (registro) => ({
    nombre: registro?.nombre ?? '', direccion: registro?.direccion ?? '',
    telefono: registro?.telefono ?? '', email: registro?.email ?? '', nit: registro?.nit ?? '',
    estado: registro?.estado ?? true,
    'admin.username': '', 'admin.email': '', 'admin.password': '', confirmacion: '',
  }),
  validar: (valores, registro) => {
    const errores: Record<string, string> = {}
    if (!registro && valores['admin.password'] !== valores.confirmacion) errores.confirmacion = 'Las contraseñas no coinciden.'
    for (const campo of ['nombre', 'direccion', 'telefono', 'email', 'nit']) {
      if (!String(valores[campo]).trim()) errores[campo] = 'Este campo es obligatorio.'
    }
    return errores
  },
  guardar: (valores, registro) => {
    const datos = {
      nombre: String(valores.nombre).trim(), direccion: String(valores.direccion).trim(),
      telefono: String(valores.telefono).trim(), email: String(valores.email).trim(), nit: String(valores.nit).trim(),
    }
    if (registro) return clinicasGestionApi.actualizar(registro.id, { ...datos, estado: valores.estado === true })
    return clinicasGestionApi.crear({ ...datos, admin: {
      username: String(valores['admin.username']).trim(), email: String(valores['admin.email']).trim(),
      password: String(valores['admin.password']),
    } })
  },
  eliminar: clinicasGestionApi.eliminar,
  textoEliminar: 'Desactivar', puedeEliminar: (registro) => registro.estado,
  mensajeEliminar: (registro) => `¿Desactivar la clínica "${registro.nombre}"? Sus usuarios perderán el acceso. Puedes reactivarla desde Editar.`,
  invalidar: ['suscripciones'],
  columnas: [
    { encabezado: 'Nombre', celda: (registro) => registro.nombre },
    { encabezado: 'NIT', celda: (registro) => registro.nit },
    { encabezado: 'Correo', celda: (registro) => registro.email },
    { encabezado: 'Teléfono', celda: (registro) => registro.telefono },
    { encabezado: 'Estado', celda: (registro) => registro.estado ? 'Activa' : 'Inactiva' },
  ],
}
export function ClinicasPage() { return <GestionRecurso config={config} /> }
