import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { citasApi, ESTADOS_CITA, type Cita, type EstadoCita } from '@/api/modules/citas'
import { DataTable, type Columna } from '@/components/data/DataTable'
import { Pagination } from '@/components/data/Pagination'
import { Button } from '@/components/ui/Button'
import { inputClass } from '@/components/ui/styles'
import { mensajeDeError } from '@/lib/errorMessages'
import { fechaLocalActual } from '@/pages/clinica/citas/fechaLocal'
import { AgendaDetalleModal } from './AgendaDetalleModal'
import { ConsultaDetalleModal } from './ConsultaDetalleModal'
import { ConsultaFormModal } from './ConsultaFormModal'

export function MiAgendaPage() {
  const [page, setPage] = useState(1)
  const [fecha, setFecha] = useState(fechaLocalActual)
  const [estado, setEstado] = useState<EstadoCita | ''>('')
  const [detalle, setDetalle] = useState<Cita | null>(null)
  const [citaAAtender, setCitaAAtender] = useState<Cita | null>(null)
  const [consultaDetalle, setConsultaDetalle] = useState<number | null>(null)

  const query = useQuery({
    queryKey: ['mi-agenda', { page, fecha, estado }],
    queryFn: () => citasApi.obtenerMiAgenda({
      page,
      fecha,
      estado: estado || undefined,
    }),
  })

  const columnas: Columna<Cita>[] = [
    { encabezado: 'Paciente', celda: (cita) => cita.paciente_nombre },
    { encabezado: 'Fecha', celda: (cita) => cita.fecha },
    { encabezado: 'Hora', celda: (cita) => cita.hora.slice(0, 5) },
    { encabezado: 'Modalidad', celda: (cita) => cita.modalidad_display },
    { encabezado: 'Estado', celda: (cita) => cita.estado_display },
    { encabezado: 'Motivo', celda: (cita) => cita.motivo },
    { encabezado: 'Especialidad', celda: (cita) => cita.especialidad_nombre },
    {
      encabezado: 'Acciones',
      className: 'text-right',
      celda: (cita) => (
        <div className="flex flex-wrap justify-end gap-2">
          <Button data-guia-id="btn-fila-agenda-ver" variante="secundario" onClick={() => setDetalle(cita)}>Ver</Button>
          {cita.modalidad === 'VIRTUAL' && cita.link_videollamada && cita.estado !== 'CANCELADA' && cita.estado !== 'NO_ASISTIO' && (
            <Button data-guia-id="btn-fila-agenda-sala" onClick={() => window.open(`/sala-virtual/${cita.id}`, '_blank', 'noopener,noreferrer')}>
              Ingresar a la sala virtual
            </Button>
          )}
          {cita.estado === 'CONFIRMADA' && !cita.tiene_consulta && (
            <Button data-guia-id="btn-fila-agenda-atender" onClick={() => setCitaAAtender(cita)}>Atender</Button>
          )}
          {cita.consulta_id !== null && (
            <Button data-guia-id="btn-fila-agenda-consulta" variante="secundario" onClick={() => setConsultaDetalle(cita.consulta_id)}>Ver consulta</Button>
          )}
        </div>
      ),
    },
  ]

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Mi agenda</h1>
        <p className="mt-1 text-sm text-slate-600">
          Consulta tus citas por fecha y estado.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <input
          data-guia-id="filtro-agenda-fecha"
          aria-label="Fecha de la agenda"
          type="date"
          value={fecha}
          className={inputClass}
          onChange={(evento) => {
            setFecha(evento.target.value)
            setPage(1)
          }}
        />
        <select
          aria-label="Filtrar por estado"
          value={estado}
          className={inputClass}
          onChange={(evento) => {
            setEstado(evento.target.value as EstadoCita | '')
            setPage(1)
          }}
        >
          <option value="">Todos los estados</option>
          {ESTADOS_CITA.map((item) => (
            <option key={item.valor} value={item.valor}>{item.etiqueta}</option>
          ))}
        </select>
      </div>

      <DataTable
        filas={query.data?.results}
        columnas={columnas}
        claveFila={(cita) => cita.id}
        cargando={query.isLoading}
        error={query.isError ? mensajeDeError(query.error) : null}
        textoVacio="No tienes citas para los filtros seleccionados."
      />
      {query.isError && (
        <Button variante="secundario" onClick={() => void query.refetch()}>
          Reintentar
        </Button>
      )}
      <Pagination
        pagina={page}
        total={query.data?.count ?? 0}
        onCambiar={setPage}
      />

      {detalle && (
        <AgendaDetalleModal cita={detalle} onClose={() => setDetalle(null)} />
      )}
      {citaAAtender && (
        <ConsultaFormModal
          cita={citaAAtender}
          onClose={() => setCitaAAtender(null)}
          onSuccess={(consulta) => {
            setCitaAAtender(null)
            setConsultaDetalle(consulta.id)
          }}
        />
      )}
      {consultaDetalle !== null && (
        <ConsultaDetalleModal
          consultaId={consultaDetalle}
          onClose={() => setConsultaDetalle(null)}
        />
      )}
    </section>
  )
}
