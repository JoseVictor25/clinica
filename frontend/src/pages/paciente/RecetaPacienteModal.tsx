import { useQuery } from '@tanstack/react-query'
import { portalPacienteApi } from '@/api/modules/portalPaciente'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { mensajeDeError } from '@/lib/errorMessages'

export function RecetaPacienteModal({ id, onClose }: { id: number; onClose: () => void }) {
  const query = useQuery({ queryKey: ['portal-paciente', 'receta', id], queryFn: () => portalPacienteApi.miReceta(id) })
  return <Modal titulo="Detalle de receta" onClose={onClose}><div className="space-y-4 text-sm">
    {query.isLoading && <p>Cargando receta…</p>}
    {query.isError && <><p role="alert" className="text-red-700">{mensajeDeError(query.error)}</p><Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button></>}
    {query.data && <><p><strong>Fecha:</strong> {new Date(query.data.fecha).toLocaleString()}</p><p><strong>Médico:</strong> {query.data.medico.nombre} · {query.data.medico.especialidad}</p><p><strong>Indicaciones:</strong> {query.data.indicaciones || 'Sin indicaciones generales'}</p><div><strong>Medicamentos</strong><ul className="mt-2 list-disc space-y-1 pl-5">{query.data.medicamentos.map((m) => <li key={m.id}>{m.nombre_medicamento}: {m.dosis}, {m.frecuencia}, durante {m.duracion}</li>)}</ul></div></>}
    <div className="flex justify-end"><Button variante="secundario" onClick={onClose}>Cerrar</Button></div>
  </div></Modal>
}
