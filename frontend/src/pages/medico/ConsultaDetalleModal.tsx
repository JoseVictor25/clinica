import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import type { Receta } from '@/api/modules/recetas'
import { consultasApi } from '@/api/modules/consultas'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { mensajeDeError } from '@/lib/errorMessages'
import { RecetaDetalleModal } from './RecetaDetalleModal'
import { RecetaFormModal } from './RecetaFormModal'

export function ConsultaDetalleModal({
  consultaId,
  onClose,
}: {
  consultaId: number
  onClose: () => void
}) {
  const [emitiendoReceta, setEmitiendoReceta] = useState(false)
  const [recetaSeleccionada, setRecetaSeleccionada] = useState<number | null>(null)
  const query = useQuery({
    queryKey: ['consulta', consultaId],
    queryFn: () => consultasApi.obtener(consultaId),
  })

  const recetaCreada = (receta: Receta) => {
    setEmitiendoReceta(false)
    setRecetaSeleccionada(receta.id)
  }

  return <>
    <Modal titulo="Detalle de la consulta" onClose={onClose}>
      {query.isLoading && <p className="text-sm text-slate-600">Cargando consulta…</p>}
      {query.isError && (
        <div className="space-y-3">
          <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{mensajeDeError(query.error)}</p>
          <Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button>
        </div>
      )}
      {query.data && (
        <div className="space-y-5">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div><dt className="font-medium text-slate-500">Paciente</dt><dd>{query.data.paciente_nombre}</dd></div>
          <div><dt className="font-medium text-slate-500">Médico</dt><dd>{query.data.medico_nombre}</dd></div>
          <div><dt className="font-medium text-slate-500">Fecha</dt><dd>{new Date(query.data.fecha).toLocaleString()}</dd></div>
          <div><dt className="font-medium text-slate-500">Estado de la cita</dt><dd>Atendida</dd></div>
          <div className="sm:col-span-2"><dt className="font-medium text-slate-500">Motivo</dt><dd className="whitespace-pre-wrap">{query.data.motivo}</dd></div>
          <div className="sm:col-span-2"><dt className="font-medium text-slate-500">Observación</dt><dd className="whitespace-pre-wrap">{query.data.observacion}</dd></div>
          <div className="sm:col-span-2"><dt className="font-medium text-slate-500">Diagnóstico</dt><dd className="whitespace-pre-wrap">{query.data.diagnostico}</dd></div>
        </dl>
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold">Recetas</h3>
            <Button onClick={() => setEmitiendoReceta(true)}>Emitir receta</Button>
          </div>
          {query.data.recetas.length === 0 ? (
            <p className="rounded bg-slate-50 p-3 text-sm text-slate-600">Esta consulta todavía no tiene recetas.</p>
          ) : (
            <div className="space-y-2">
              {query.data.recetas.map((receta) => (
                <article key={receta.id} className="flex items-center justify-between gap-3 rounded border border-slate-200 p-3 text-sm">
                  <div>
                    <p className="font-medium">Receta #{receta.id} · {new Date(receta.fecha).toLocaleString()}</p>
                    <p className="text-slate-600">{receta.cantidad_medicamentos} medicamento(s) · {receta.indicaciones || 'Sin indicaciones generales'}</p>
                  </div>
                  <Button variante="secundario" onClick={() => setRecetaSeleccionada(receta.id)}>Ver</Button>
                </article>
              ))}
            </div>
          )}
        </section>
        </div>
      )}
      <div className="mt-6 flex justify-end">
        <Button variante="secundario" onClick={onClose}>Cerrar</Button>
      </div>
    </Modal>
    {emitiendoReceta && query.data && (
      <RecetaFormModal consulta={query.data} onClose={() => setEmitiendoReceta(false)} onSuccess={recetaCreada} />
    )}
    {recetaSeleccionada !== null && (
      <RecetaDetalleModal recetaId={recetaSeleccionada} onClose={() => setRecetaSeleccionada(null)} />
    )}
  </>
}
