import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { historialConsultasApi } from '@/api/modules/historialConsultas'
import { Pagination } from '@/components/data/Pagination'
import { Button } from '@/components/ui/Button'
import { inputClass } from '@/components/ui/styles'
import { mensajeDeError } from '@/lib/errorMessages'
import { RecetaDetalleModal } from './RecetaDetalleModal'

export function HistorialConsultasPage() {
  const navigate = useNavigate()
  const { pacienteId: pacienteIdTexto } = useParams()
  const pacienteId = Number(pacienteIdTexto)
  const [page, setPage] = useState(1)
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')
  const [medicoId, setMedicoId] = useState('')
  const [ordering, setOrdering] = useState<'fecha' | '-fecha'>('-fecha')
  const [recetaId, setRecetaId] = useState<number | null>(null)

  const query = useQuery({
    queryKey: ['historial-consultas', pacienteId, { page, fechaDesde, fechaHasta, medicoId, ordering }],
    queryFn: () => historialConsultasApi.obtenerHistorialConsultas(pacienteId, {
      page,
      fecha_desde: fechaDesde || undefined,
      fecha_hasta: fechaHasta || undefined,
      medico_id: medicoId ? Number(medicoId) : undefined,
      ordering,
    }),
    enabled: Number.isInteger(pacienteId) && pacienteId > 0,
  })

  const reiniciarPagina = () => setPage(1)

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Historial de consultas</h1>
          {query.data && (
            <p className="mt-1 text-sm text-slate-600">
              {query.data.paciente.apellido}, {query.data.paciente.nombre} · CI {query.data.paciente.ci}
            </p>
          )}
        </div>
        <Button variante="secundario" onClick={() => navigate('/pacientes')}>Volver a pacientes</Button>
      </div>

      <div className="grid gap-3 rounded-md border border-slate-200 bg-white p-4 md:grid-cols-4">
        <label className="text-sm font-medium text-slate-700">
          Desde
          <input type="date" className={`${inputClass} mt-1`} value={fechaDesde} onChange={(e) => { setFechaDesde(e.target.value); reiniciarPagina() }} />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Hasta
          <input type="date" className={`${inputClass} mt-1`} value={fechaHasta} onChange={(e) => { setFechaHasta(e.target.value); reiniciarPagina() }} />
        </label>
        <label className="text-sm font-medium text-slate-700">
          ID del médico
          <input type="number" min="1" className={`${inputClass} mt-1`} value={medicoId} onChange={(e) => { setMedicoId(e.target.value); reiniciarPagina() }} placeholder="Todos" />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Orden
          <select className={`${inputClass} mt-1`} value={ordering} onChange={(e) => { setOrdering(e.target.value as 'fecha' | '-fecha'); reiniciarPagina() }}>
            <option value="-fecha">Más recientes primero</option>
            <option value="fecha">Más antiguas primero</option>
          </select>
        </label>
      </div>

      {query.isLoading && <p className="text-sm text-slate-600">Cargando historial…</p>}
      {query.isError && (
        <div className="space-y-3 rounded-md bg-red-50 p-4">
          <p role="alert" className="text-sm text-red-700">{mensajeDeError(query.error)}</p>
          <Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button>
        </div>
      )}
      {query.data?.results.length === 0 && (
        <p className="rounded-md bg-slate-50 p-4 text-sm text-slate-600">
          No existen consultas para los filtros seleccionados.
        </p>
      )}
      <div className="space-y-4">
        {query.data?.results.map((consulta) => (
          <article key={consulta.id} className="rounded-md border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h2 className="font-semibold">Consulta #{consulta.id}</h2>
                <p className="text-sm text-slate-600">{new Date(consulta.fecha).toLocaleString()}</p>
              </div>
              <p className="text-sm"><span className="font-medium">Médico:</span> {consulta.medico.nombre} · {consulta.medico.especialidad}</p>
            </div>
            <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
              <div><dt className="font-medium text-slate-500">Motivo</dt><dd className="whitespace-pre-wrap">{consulta.motivo}</dd></div>
              <div><dt className="font-medium text-slate-500">Diagnóstico</dt><dd className="whitespace-pre-wrap">{consulta.diagnostico}</dd></div>
              <div className="md:col-span-2"><dt className="font-medium text-slate-500">Observación</dt><dd className="whitespace-pre-wrap">{consulta.observacion}</dd></div>
              <div className="md:col-span-2"><dt className="font-medium text-slate-500">Cita</dt><dd>{consulta.cita ? `${consulta.cita.fecha} ${consulta.cita.hora.slice(0, 5)} · ${consulta.cita.estado}` : 'Consulta sin cita asociada'}</dd></div>
            </dl>
            <section className="mt-4 border-t border-slate-200 pt-4">
              <h3 className="font-medium">Recetas</h3>
              {consulta.recetas.length === 0 ? <p className="mt-2 text-sm text-slate-500">Sin recetas.</p> : (
                <div className="mt-2 space-y-3">
                  {consulta.recetas.map((receta) => (
                    <div key={receta.id} className="rounded bg-slate-50 p-3 text-sm">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div><p className="font-medium">Receta #{receta.id}</p><p>{receta.indicaciones || 'Sin indicaciones generales'}</p></div>
                        {receta.puede_ver_detalle && <Button variante="secundario" onClick={() => setRecetaId(receta.id)}>Ver detalle y alergias</Button>}
                      </div>
                      <ul className="mt-2 list-disc space-y-1 pl-5">
                        {receta.medicamentos.map((medicamento) => (
                          <li key={medicamento.id}>{medicamento.nombre_medicamento}: {medicamento.dosis}, {medicamento.frecuencia}, durante {medicamento.duracion}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </article>
        ))}
      </div>
      <Pagination pagina={page} total={query.data?.count ?? 0} onCambiar={setPage} />
      {recetaId !== null && <RecetaDetalleModal recetaId={recetaId} onClose={() => setRecetaId(null)} />}
    </section>
  )
}
