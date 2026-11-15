import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { horariosApi, medicosApi, todasLasPaginas, type Horario } from '@/api/modules/gestion'
import { GestionRecurso, type ConfiguracionRecurso, type CampoFormulario } from '@/components/gestion/GestionRecurso'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { esAdminClinica } from '@/lib/roles'
import { mensajeDeError } from '@/lib/errorMessages'

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
export function HorariosPage() {
  const { usuario } = useAuth()
  const admin = Boolean(usuario && esAdminClinica(usuario))
  const [params] = useSearchParams()
  const medicoParametro = params.get('medico') ?? ''
  const medicos = useQuery({
    queryKey: ['medicos', 'selector', usuario?.clinicaId, usuario?.id],
    queryFn: () => todasLasPaginas(medicosApi.listar),
  })
  const sinMedico = !admin && medicos.isSuccess && medicos.data.length === 0
  const bloqueo = medicos.isError ? mensajeDeError(medicos.error) : medicos.isPending ? 'Cargando médicos…'
    : sinMedico ? 'Tu cuenta no tiene un médico vinculado. Solicita al administrador que complete la vinculación.'
      : admin && medicos.data?.length === 0 ? 'Registra un médico antes de crear horarios.' : null
  const opciones = medicos.data?.map((medico) => ({ valor: String(medico.id), etiqueta: medico.personal_nombre })) ?? []
  const config: ConfiguracionRecurso<Horario> = {
    clave: 'horarios', titulo: admin ? 'Horarios de atención' : 'Mis horarios', nuevo: 'Crear horario',
    descripcion: 'El horario final debe ser posterior al inicial. El servidor impide superponer horarios del mismo médico.',
    bloqueoFormulario: bloqueo,
    listar: (filtros = {}) => horariosApi.listar({ ...(admin && medicoParametro ? { medico: medicoParametro } : {}), ...filtros }),
    obtener: horariosApi.obtener,
    campos: (registro) => {
      const campos: CampoFormulario[] = []
      if (admin) campos.push({ nombre: 'medico', etiqueta: 'Médico', tipo: 'select', obligatorio: true,
        soloLectura: Boolean(registro), opciones,
        ayuda: registro ? 'Para asignar este intervalo a otro médico, elimina el horario y crea uno nuevo.' : undefined })
      else if (registro) campos.push({ nombre: 'medico_nombre', etiqueta: 'Médico', soloLectura: true })
      campos.push(
        { nombre: 'dia_semana', etiqueta: 'Día', tipo: 'select', obligatorio: true, opciones: DIAS.map((dia, indice) => ({ valor: String(indice), etiqueta: dia })) },
        { nombre: 'hora_inicio', etiqueta: 'Hora de inicio', tipo: 'time', obligatorio: true, step: '1' },
        { nombre: 'hora_fin', etiqueta: 'Hora de fin', tipo: 'time', obligatorio: true, step: '1' },
      )
      return campos
    },
    iniciales: (registro) => ({ medico: registro ? String(registro.medico)
      : opciones.some((opcion) => opcion.valor === medicoParametro) ? medicoParametro : '',
      medico_nombre: registro?.medico_nombre ?? '', dia_semana: String(registro?.dia_semana ?? 0),
      hora_inicio: registro?.hora_inicio ?? '08:00:00', hora_fin: registro?.hora_fin ?? '09:00:00' }),
    validar: (valores) => {
      const errores: Record<string, string> = {}
      const segundos = (hora: string) => { const [h = 0, m = 0, s = 0] = hora.split(':').map(Number); return h * 3600 + m * 60 + s }
      if (segundos(String(valores.hora_inicio)) >= segundos(String(valores.hora_fin))) errores.hora_fin = 'La hora final debe ser posterior al inicio.'
      return errores
    },
    guardar: (valores, registro) => {
      const datos = { dia_semana: Number(valores.dia_semana), hora_inicio: String(valores.hora_inicio), hora_fin: String(valores.hora_fin) }
      if (registro) return horariosApi.actualizar(registro.id, datos)
      return horariosApi.crear({ ...datos, ...(admin ? { medico: Number(valores.medico) } : {}) })
    },
    eliminar: horariosApi.eliminar,
    filtros: [
      ...(admin ? [{ nombre: 'medico', etiqueta: 'Médico', opciones }] : []),
      ...(admin ? [{ nombre: 'dia_semana', etiqueta: 'Día', opciones: DIAS.map((dia, indice) => ({ valor: String(indice), etiqueta: dia })) }] : []),
    ],
    columnas: [
      { encabezado: 'Médico', celda: (registro) => registro.medico_nombre },
      { encabezado: 'Día', celda: (registro) => DIAS[registro.dia_semana] ?? String(registro.dia_semana) },
      { encabezado: 'Inicio', celda: (registro) => registro.hora_inicio },
      { encabezado: 'Fin', celda: (registro) => registro.hora_fin },
    ],
  }
  return <>
    {medicoParametro && admin && <p className="mb-3 text-sm">Lista inicial del médico seleccionado. <a className="text-blue-700 underline" href="/horarios">Ver todos los médicos</a></p>}
    {medicos.isError && <Button variante="secundario" onClick={() => void medicos.refetch()}>Reintentar carga de médicos</Button>}
    <GestionRecurso key={medicoParametro || 'todos'} config={config} />
  </>
}
