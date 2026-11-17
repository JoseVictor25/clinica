import { useQuery } from '@tanstack/react-query'
import { recetasApi } from '@/api/modules/recetas'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { mensajeDeError } from '@/lib/errorMessages'

export function RecetaDetalleModal({ recetaId, onClose }: { recetaId: number; onClose: () => void }) {
  const query = useQuery({
    queryKey: ['receta', recetaId],
    queryFn: () => recetasApi.obtenerReceta(recetaId),
  })

  return (
    <Modal titulo="Detalle de la receta" onClose={onClose}>
      {query.isLoading && <p className="text-sm text-slate-600">Cargando receta…</p>}
      {query.isError && (
        <div className="space-y-3">
          <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{mensajeDeError(query.error)}</p>
          <Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button>
        </div>
      )}
      {query.data && (
        <div className="space-y-4 text-sm">
          <div className="grid gap-2 rounded bg-slate-50 p-3 sm:grid-cols-2">
            <p><span className="font-medium">Paciente:</span> {query.data.paciente_nombre}</p>
            <p><span className="font-medium">Fecha:</span> {new Date(query.data.fecha).toLocaleString()}</p>
            <p className="sm:col-span-2"><span className="font-medium">Indicaciones:</span> {query.data.indicaciones || 'Sin indicaciones generales'}</p>
          </div>
          {query.data.advertencias_alergia.length > 0 && (
            <section role="alert" aria-label="Advertencias de alergias" className="rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-900">
              <h3 className="font-semibold">Advertencias de alergias</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {query.data.advertencias_alergia.map((advertencia) => (
                  <li key={`${advertencia.alergia_id}-${advertencia.medicamento}`}>
                    {advertencia.mensaje} Severidad: {advertencia.severidad}.
                  </li>
                ))}
              </ul>
            </section>
          )}
          <section>
            <h3 className="mb-2 font-semibold">Medicamentos</h3>
            <div className="space-y-2">
              {query.data.medicamentos.map((medicamento) => (
                <article key={medicamento.id} className="rounded border border-slate-200 p-3">
                  <p className="font-medium">{medicamento.nombre_medicamento}</p>
                  <p>Dosis: {medicamento.dosis}</p>
                  <p>Frecuencia: {medicamento.frecuencia}</p>
                  <p>Duración: {medicamento.duracion}</p>
                </article>
              ))}
            </div>
          </section>
        </div>
      )}
      <div className="mt-6 flex justify-end"><Button variante="secundario" onClick={onClose}>Cerrar</Button></div>
    </Modal>
  )
}
