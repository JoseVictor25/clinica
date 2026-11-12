import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { medicosApi, todasLasPaginas, type Medico } from '@/api/modules/gestion'
import { personalApi } from '@/api/modules/personal'
import { especialidadesApi } from '@/api/modules/especialidades'
import { GestionRecurso, type ConfiguracionRecurso } from '@/components/gestion/GestionRecurso'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { esAdminClinica } from '@/lib/roles'
import { mensajeDeError } from '@/lib/errorMessages'

export function MedicosPage() {
  const { usuario } = useAuth()
  const admin = Boolean(usuario && esAdminClinica(usuario))
  const referencias = useQuery({
    queryKey: ['medicos', 'referencias', usuario?.clinicaId],
    queryFn: async () => {
      const [personal, especialidades, medicos] = await Promise.all([
        personalApi.listarTodos(), todasLasPaginas(especialidadesApi.listar), todasLasPaginas(medicosApi.listar),
      ])
      return { personal, especialidades, medicos }
    },
    enabled: admin,
  })
  const bloqueo = !admin ? null : referencias.isError ? mensajeDeError(referencias.error)
    : referencias.isPending ? 'Cargando personal y especialidades…' : null
  const config: ConfiguracionRecurso<Medico> = {
    clave: 'medicos', titulo: admin ? 'Médicos' : 'Mi registro de médico', nuevo: 'Registrar médico',
    descripcion: admin ? 'Relaciona un registro de personal con su especialidad y colegiatura. El rol Médico se asigna desde Usuarios.'
      : 'Consulta tu registro profesional y accede a tus horarios. Si no aparece, solicita que vinculen tu cuenta a Personal y creen su registro de médico.',
    gestionar: admin, bloqueoFormulario: bloqueo,
    listar: medicosApi.listar, obtener: medicosApi.obtener, buscar: true,
    campos: (registro) => [
      { nombre: 'personal', etiqueta: 'Personal', tipo: 'select', obligatorio: true,
        opciones: referencias.data?.personal.filter((persona) => persona.id === registro?.personal ||
          !referencias.data.medicos.some((medico) => medico.personal === persona.id)).map((persona) => ({
            valor: String(persona.id), etiqueta: `${persona.apellido}, ${persona.nombre} — ${persona.ci}${persona.estado ? '' : ' (inactivo)'}`,
          })) ?? (registro ? [{ valor: String(registro.personal), etiqueta: registro.personal_nombre }] : []) },
      { nombre: 'especialidad', etiqueta: 'Especialidad', tipo: 'select', obligatorio: true,
        opciones: referencias.data?.especialidades.map((especialidad) => ({ valor: String(especialidad.id), etiqueta: `${especialidad.nombre}${especialidad.estado ? '' : ' (inactiva)'}` }))
          ?? (registro ? [{ valor: String(registro.especialidad), etiqueta: registro.especialidad_nombre }] : []) },
      { nombre: 'numero_colegiatura', etiqueta: 'Número de colegiatura', obligatorio: true, maxLength: 30 },
      { nombre: 'estado', etiqueta: 'Médico activo', tipo: 'checkbox' },
    ],
    iniciales: (registro) => ({ personal: registro ? String(registro.personal) : '', especialidad: registro ? String(registro.especialidad) : '',
      numero_colegiatura: registro?.numero_colegiatura ?? '', estado: registro?.estado ?? true }),
    validar: (valores) => {
      const errores: Record<string, string> = {}
      if (!String(valores.numero_colegiatura).trim()) errores.numero_colegiatura = 'La colegiatura es obligatoria.'
      return errores
    },
    guardar: (valores, registro) => {
      const datos = { personal: Number(valores.personal), especialidad: Number(valores.especialidad),
        numero_colegiatura: String(valores.numero_colegiatura).trim(), estado: valores.estado === true }
      return registro ? medicosApi.actualizar(registro.id, datos) : medicosApi.crear(datos)
    },
    eliminar: medicosApi.eliminar,
    mensajeEliminar: (registro) => `¿Eliminar el registro médico de "${registro.personal_nombre}"? Sus horarios se eliminarán. Si tiene relaciones protegidas, no se podrá eliminar. El registro de personal se conserva.`,
    invalidar: ['horarios', 'personal'],
    filtros: admin ? [{ nombre: 'especialidad', etiqueta: 'Especialidad', opciones: referencias.data?.especialidades.map((especialidad) => ({ valor: String(especialidad.id), etiqueta: especialidad.nombre })) ?? [] }] : [],
    columnas: [
      { encabezado: 'Médico', celda: (registro) => registro.personal_nombre },
      { encabezado: 'Especialidad', celda: (registro) => registro.especialidad_nombre },
      { encabezado: 'Colegiatura', celda: (registro) => registro.numero_colegiatura },
      { encabezado: 'Estado', celda: (registro) => registro.estado ? 'Activo' : 'Inactivo' },
    ],
    acciones: (registro) => <Link className="rounded-md border border-slate-300 px-3 py-2 text-sm text-blue-700" to={`/horarios?medico=${registro.id}`}>Horarios</Link>,
  }
  return <>
    {admin && referencias.isError && <Button variante="secundario" onClick={() => void referencias.refetch()}>Reintentar carga de personal y especialidades</Button>}
    <GestionRecurso config={config} />
  </>
}