import { planesGestionApi, type Plan } from '@/api/modules/gestion'
import { GestionRecurso, type ConfiguracionRecurso } from '@/components/gestion/GestionRecurso'
import { useAuth } from '@/hooks/useAuth'
import { esAdminSistema } from '@/lib/roles'

const config: ConfiguracionRecurso<Plan> = {
  clave: 'planes', titulo: 'Planes de suscripción', nuevo: 'Crear plan',
  listar: planesGestionApi.listar, obtener: planesGestionApi.obtener,
  campos: () => [
    { nombre: 'nombre', etiqueta: 'Nombre', obligatorio: true, maxLength: 80 },
    { nombre: 'precio', etiqueta: 'Precio', tipo: 'number', obligatorio: true, min: 0, max: 99999999.99, step: '0.01' },
    { nombre: 'max_usuarios', etiqueta: 'Máximo de usuarios activos', tipo: 'number', obligatorio: true, min: 1, step: '1' },
    { nombre: 'descripcion', etiqueta: 'Descripción', tipo: 'textarea' },
    { nombre: 'activo', etiqueta: 'Plan activo', tipo: 'checkbox' },
  ],
  iniciales: (registro) => ({
    nombre: registro?.nombre ?? '', precio: registro?.precio ?? '0.00',
    max_usuarios: String(registro?.max_usuarios ?? 1), descripcion: registro?.descripcion ?? '', activo: registro?.activo ?? true,
  }),
  validar: (valores) => {
    const errores: Record<string, string> = {}
    if (!String(valores.nombre).trim()) errores.nombre = 'El nombre es obligatorio.'
    if (!Number.isInteger(Number(valores.max_usuarios)) || Number(valores.max_usuarios) < 1) errores.max_usuarios = 'Introduce un entero mayor a cero.'
    if (!/^\d{1,8}(\.\d{1,2})?$/.test(String(valores.precio))) errores.precio = 'Introduce un precio no negativo con hasta dos decimales.'
    return errores
  },
  guardar: (valores, registro) => {
    const datos = { nombre: String(valores.nombre).trim(), precio: String(valores.precio),
      max_usuarios: Number(valores.max_usuarios), descripcion: String(valores.descripcion), activo: valores.activo === true }
    return registro ? planesGestionApi.actualizar(registro.id, datos) : planesGestionApi.crear(datos)
  },
  eliminar: planesGestionApi.eliminar, textoEliminar: 'Desactivar', puedeEliminar: (registro) => registro.activo,
  mensajeEliminar: (registro) => `¿Desactivar el plan "${registro.nombre}"? No podrá contratarse mientras esté inactivo. Las suscripciones existentes se conservan.`,
  filtros: [{ nombre: 'activo', etiqueta: 'Estado', opciones: [{ valor: 'true', etiqueta: 'Activo' }, { valor: 'false', etiqueta: 'Inactivo' }] }],
  columnas: [
    { encabezado: 'Plan', celda: (registro) => registro.nombre },
    { encabezado: 'Precio', celda: (registro) => registro.precio },
    { encabezado: 'Usuarios', celda: (registro) => registro.max_usuarios },
    { encabezado: 'Estado', celda: (registro) => registro.activo ? 'Activo' : 'Inactivo' },
  ],
}
export function PlanesPage() {
  const { usuario } = useAuth()
  const admin = Boolean(usuario && esAdminSistema(usuario))
  return <GestionRecurso config={{ ...config, gestionar: admin,
    descripcion: admin ? 'Administra los planes ofrecidos por la plataforma.'
      : 'Consulta los planes y sus límites. La contratación se realiza desde Mi suscripción.' }} />
}
