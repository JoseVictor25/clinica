import { useQuery } from '@tanstack/react-query'
import { suscripcionesApi } from '@/api/modules/suscripciones'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { mensajeDeError } from '@/lib/errorMessages'

export function SuscripcionDetalleModal({ id, onClose }: { id: number; onClose: () => void }) {
  const detalle = useQuery({ queryKey: ['suscripciones', 'detalle', id], queryFn: () => suscripcionesApi.obtener(id) })
  return <Modal titulo="Detalle de suscripción" onClose={onClose}>
    {detalle.isPending && <p role="status">Cargando…</p>}
    {detalle.isError && <div role="alert"><p>{mensajeDeError(detalle.error)}</p><Button onClick={() => void detalle.refetch()}>Reintentar</Button></div>}
    {detalle.data && <dl className="space-y-2 text-sm">
      <dt className="font-semibold">Clínica</dt><dd>{detalle.data.clinica_nombre}</dd>
      <dt className="font-semibold">Plan</dt><dd>{detalle.data.plan_nombre}</dd>
      <dt className="font-semibold">Inicio</dt><dd>{detalle.data.fecha_inicio}</dd>
      <dt className="font-semibold">Fin</dt><dd>{detalle.data.fecha_fin}</dd>
      <dt className="font-semibold">Estado registrado</dt><dd>{detalle.data.estado}</dd>
    </dl>}
    <div className="mt-4 flex justify-end"><Button variante="secundario" onClick={onClose}>Cerrar</Button></div>
  </Modal>
}