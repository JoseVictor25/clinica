import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { citasApi, ESTADOS_CITA, type Cita, type EstadoCita } from '@/api/modules/citas'
import { DataTable, type Columna } from '@/components/data/DataTable'
import { Pagination } from '@/components/data/Pagination'
import { EstudiosCitaModal } from '@/components/estudios/EstudiosCitaModal'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { inputClass } from '@/components/ui/styles'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'
import { esAdminClinica } from '@/lib/roles'
import { CitaDetalleModal } from './CitaDetalleModal'
import { CitaFormModal } from './CitaFormModal'
import { ReprogramarCitaModal } from './ReprogramarCitaModal'

type AccionEstado = {
  tipo: 'confirmar' | 'cancelar'
  cita: Cita
}

export function CitasPage() {
  const { usuario } = useAuth()
  const admin = Boolean(usuario && esAdminClinica(usuario))
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [fecha, setFecha] = useState('')
  const [estado, setEstado] = useState<EstadoCita | ''>('')
  const [formulario, setFormulario] = useState(false)
  const [detalle, setDetalle] = useState<Cita | null>(null)
  const [reprogramando, setReprogramando] = useState<Cita | null>(null)
  const [citaEstudios, setCitaEstudios] = useState<Cita | null>(null)
  const [accion, setAccion] = useState<AccionEstado | null>(null)

  const query = useQuery({
    queryKey: ['citas', { page, fecha, estado }],
    queryFn: () => citasApi.listar({ page, fecha: fecha || undefined, estado: estado || undefined }),
  })

  const cambiarEstado = useMutation({
    mutationFn: ({ tipo, cita }: AccionEstado) => (
      tipo === 'confirmar' ? citasApi.confirmar(cita.id) : citasApi.cancelar(cita.id)
    ),
    onSuccess: (_, datos) => {
      toast.success(datos.tipo === 'confirmar' ? 'Cita confirmada.' : 'Cita cancelada.')
      setAccion(null)
      void queryClient.invalidateQueries({ queryKey: ['citas'] })
    },
    onError: (error) => toast.error(mensajeDeError(error)),
  })

  const columnas: Columna<Cita>[] = [
    { encabezado: 'Paciente', celda: (c) => c.paciente_nombre },
    { encabezado: 'Médico', celda: (c) => c.medico_nombre },
    { encabezado: 'Especialidad', celda: (c) => c.especialidad_nombre },
    { encabezado: 'Fecha', celda: (c) => c.fecha },
    { encabezado: 'Hora', celda: (c) => c.hora.slice(0, 5) },
    { encabezado: 'Modalidad', celda: (c) => c.modalidad_display },
    { encabezado: 'Estado', celda: (c) => c.estado_display },
    { encabezado: 'Motivo', celda: (c) => c.motivo },
    {
      encabezado: 'Acciones',
      className: 'text-right',
      celda: (cita) => (
        <div className="flex flex-wrap justify-end gap-2">
          <Button variante="secundario" onClick={() => setDetalle(cita)}>Ver</Button>
          {admin && (
            <Button variante="secundario" onClick={() => setCitaEstudios(cita)}>Estudios</Button>
          )}
          {cita.estado === 'PROGRAMADA' && (
            <Button variante="secundario" onClick={() => setAccion({ tipo: 'confirmar', cita })}>
              Confirmar
            </Button>
          )}
          {(cita.estado === 'PROGRAMADA' || cita.estado === 'CONFIRMADA') && (
            <>
              <Button variante="secundario" onClick={() => setReprogramando(cita)}>
                Reprogramar
              </Button>
              <Button variante="peligro" onClick={() => setAccion({ tipo: 'cancelar', cita })}>
                Cancelar
              </Button>
            </>
          )}
        </div>
      ),
    },
  ]

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Citas</h1>
          <p className="mt-1 text-sm text-slate-600">Programa y consulta las citas de tu clínica.</p>
        </div>
        <Button onClick={() => setFormulario(true)}>Nueva cita</Button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <input aria-label="Filtrar por fecha" type="date" value={fecha} className={inputClass} onChange={(e) => { setFecha(e.target.value); setPage(1) }} />
        <select aria-label="Filtrar por estado" value={estado} className={inputClass} onChange={(e) => { setEstado(e.target.value as EstadoCita | ''); setPage(1) }}>
          <option value="">Todos los estados</option>
          {ESTADOS_CITA.map((item) => <option key={item.valor} value={item.valor}>{item.etiqueta}</option>)}
        </select>
      </div>
      <DataTable filas={query.data?.results} columnas={columnas} claveFila={(c) => c.id} cargando={query.isLoading} error={query.isError ? mensajeDeError(query.error) : null} textoVacio="Todavía no hay citas registradas." />
      {query.isError && <Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button>}
      <Pagination pagina={page} total={query.data?.count ?? 0} onCambiar={setPage} />

      {formulario && <CitaFormModal onClose={() => setFormulario(false)} />}
      {detalle && <CitaDetalleModal cita={detalle} onClose={() => setDetalle(null)} />}
      {reprogramando && <ReprogramarCitaModal cita={reprogramando} onClose={() => setReprogramando(null)} />}
      {citaEstudios && <EstudiosCitaModal cita={citaEstudios} onClose={() => setCitaEstudios(null)} />}
      {accion && (
        <ConfirmDialog
          titulo={accion.tipo === 'confirmar' ? 'Confirmar cita' : 'Cancelar cita'}
          mensaje={accion.tipo === 'confirmar'
            ? `¿Quieres confirmar la cita de ${accion.cita.paciente_nombre} para el ${accion.cita.fecha} a las ${accion.cita.hora.slice(0, 5)}?`
            : `¿Quieres cancelar la cita de ${accion.cita.paciente_nombre}? El horario quedará disponible.`}
          textoConfirmar={accion.tipo === 'confirmar' ? 'Confirmar' : 'Cancelar cita'}
          cargando={cambiarEstado.isPending}
          onConfirmar={() => cambiarEstado.mutate(accion)}
          onCancelar={() => setAccion(null)}
        />
      )}
    </section>
  )
}
