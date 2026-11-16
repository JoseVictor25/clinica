import { useQuery } from '@tanstack/react-query'
import { pacientesApi, SEXOS } from '@/api/modules/pacientes'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'
import { puedeConsultarAlergias, puedeConsultarEnfermedades } from '@/lib/roles'
import { AlergiasPanel } from './AlergiasPanel'
import { EnfermedadesPanel } from './EnfermedadesPanel'

export function PacienteDetalleModal({ id, onClose }: { id: number; onClose: () => void }) {
  const { usuario } = useAuth()
  const mostrarEnfermedades = Boolean(usuario && puedeConsultarEnfermedades(usuario))
  const mostrarAlergias = Boolean(usuario && puedeConsultarAlergias(usuario))
  const q = useQuery({ queryKey: ['pacientes', id], queryFn: () => pacientesApi.obtener(id) })
  return <Modal titulo="Detalle del paciente" onClose={onClose}>{q.isLoading ? <p>Cargando…</p> : q.isError ? <p role="alert">{mensajeDeError(q.error)}</p> : q.data && <><dl className="grid grid-cols-2 gap-3 text-sm">
    <dt className="font-medium">Nombre</dt><dd>{q.data.nombre} {q.data.apellido}</dd><dt className="font-medium">CI</dt><dd>{q.data.ci}</dd><dt className="font-medium">Sexo</dt><dd>{SEXOS.find((s) => s.valor === q.data.sexo)?.etiqueta}</dd><dt className="font-medium">Nacimiento</dt><dd>{q.data.fecha_nacimiento}</dd><dt className="font-medium">Teléfono</dt><dd>{q.data.telefono}</dd><dt className="font-medium">Correo</dt><dd>{q.data.email || 'Sin correo'}</dd><dt className="font-medium">Estado</dt><dd>{q.data.estado ? 'Activo' : 'Inactivo'}</dd>
  </dl>{mostrarEnfermedades && <EnfermedadesPanel pacienteId={id} />}{mostrarAlergias && <AlergiasPanel pacienteId={id} />}</>}<div className="mt-5 flex justify-end"><Button variante="secundario" onClick={onClose}>Cerrar</Button></div></Modal>
}
