import {
  especialidadesApi,
  type Especialidad,
} from '@/api/modules/especialidades'
import {
  GestionRecurso,
  type ConfiguracionRecurso,
} from '@/components/gestion/GestionRecurso'
import { useAuth } from '@/hooks/useAuth'
import { esAdminClinica } from '@/lib/roles'

export function EspecialidadesPage() {
  const { usuario } = useAuth()
  const admin = Boolean(usuario && esAdminClinica(usuario))

  const config: ConfiguracionRecurso<Especialidad> = {
    clave: 'especialidades',
    titulo: 'Especialidades',
    nuevo: 'Nueva especialidad',
    gestionar: admin,
    buscar: true,

    listar: especialidadesApi.listar,
    obtener: especialidadesApi.obtener,

    campos: () => [
      {
        nombre: 'nombre',
        etiqueta: 'Nombre',
        obligatorio: true,
        maxLength: 100,
      },
      {
        nombre: 'descripcion',
        etiqueta: 'Descripción',
        tipo: 'textarea',
      },
      {
        nombre: 'estado',
        etiqueta: 'Especialidad activa',
        tipo: 'checkbox',
      },
    ],

    iniciales: (registro) => ({
      nombre: registro?.nombre ?? '',
      descripcion: registro?.descripcion ?? '',
      estado: registro?.estado ?? true,
    }),

    validar: (valores) => {
      const errores: Record<string, string> = {}

      if (!String(valores.nombre).trim()) {
        errores.nombre = 'El nombre es obligatorio.'
      }

      return errores
    },

    guardar: (valores, registro) => {
      const datos = {
        nombre: String(valores.nombre).trim(),
        descripcion: String(valores.descripcion),
        estado: valores.estado === true,
      }

      return registro
        ? especialidadesApi.actualizar(registro.id, datos)
        : especialidadesApi.crear(datos)
    },

    eliminar: especialidadesApi.eliminar,

    mensajeEliminar: (registro) =>
      `¿Eliminar "${registro.nombre}"? No se podrá eliminar si algún médico la utiliza.`,

    invalidar: ['medicos'],

    columnas: [
      {
        encabezado: 'Nombre',
        celda: (registro) => registro.nombre,
      },
      {
        encabezado: 'Descripción',
        celda: (registro) => registro.descripcion || '—',
      },
      {
        encabezado: 'Estado',
        celda: (registro) => registro.estado ? 'Activa' : 'Inactiva',
      },
    ],
  }

  return <GestionRecurso config={config} />
}