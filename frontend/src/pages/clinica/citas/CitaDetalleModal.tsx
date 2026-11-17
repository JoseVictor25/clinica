import type { Cita } from '@/api/modules/citas'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'

export function CitaDetalleModal({
  cita,
  onClose,
}: {
  cita: Cita
  onClose: () => void
}) {
  return (
    <Modal titulo="Detalle de la cita" onClose={onClose}>
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div><dt className="font-medium text-slate-500">Paciente</dt><dd>{cita.paciente_nombre}</dd></div>
        <div><dt className="font-medium text-slate-500">Médico</dt><dd>{cita.medico_nombre}</dd></div>
        <div><dt className="font-medium text-slate-500">Especialidad</dt><dd>{cita.especialidad_nombre}</dd></div>
        <div><dt className="font-medium text-slate-500">Estado</dt><dd>{cita.estado_display}</dd></div>
        <div><dt className="font-medium text-slate-500">Fecha</dt><dd>{cita.fecha}</dd></div>
        <div><dt className="font-medium text-slate-500">Hora</dt><dd>{cita.hora.slice(0, 5)}</dd></div>
        <div className="sm:col-span-2"><dt className="font-medium text-slate-500">Motivo</dt><dd>{cita.motivo}</dd></div>
      </dl>
      <div className="mt-6 flex justify-end">
        <Button variante="secundario" onClick={onClose}>Cerrar</Button>
      </div>
    </Modal>
  )
}
