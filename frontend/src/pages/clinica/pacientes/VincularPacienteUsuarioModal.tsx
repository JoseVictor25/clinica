import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { pacientesApi, type Paciente } from '@/api/modules/pacientes'
import { usuariosApi } from '@/api/modules/usuarios'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { mensajeDeError } from '@/lib/errorMessages'
import { ROL_PACIENTE } from '@/lib/roles'

export function VincularPacienteUsuarioModal({ paciente, onClose }: { paciente: Paciente; onClose: () => void }) {
  const [usuarioId, setUsuarioId] = useState('')
  const qc = useQueryClient()
  const usuarios = useQuery({ queryKey: ['usuarios', 'elegibles-paciente'], queryFn: () => usuariosApi.listar({ page_size: 100 }) })
  const elegibles = useMemo(() => usuarios.data?.results.filter((u) => u.estado && u.roles.includes(ROL_PACIENTE) && !u.paciente_vinculado) ?? [], [usuarios.data])
  const vincular = useMutation({
    mutationFn: () => pacientesApi.vincularUsuario(paciente.id, Number(usuarioId)),
    onSuccess: (respuesta) => { toast.success(respuesta.mensaje); void qc.invalidateQueries({ queryKey: ['pacientes'] }); onClose() },
    onError: (error) => toast.error(mensajeDeError(error)),
  })
  return <Modal titulo="Vincular cuenta de paciente" onClose={onClose}>
    <div className="space-y-4">
      <p className="text-sm text-slate-600">Paciente: <strong>{paciente.nombre} {paciente.apellido}</strong>. La vinculación no puede reemplazarse ni eliminarse.</p>
      {usuarios.isError && <p role="alert" className="text-sm text-red-700">{mensajeDeError(usuarios.error)}</p>}
      <label className="block text-sm font-medium text-slate-700">Cuenta con rol Paciente
        <select className={`${inputClass} mt-1`} value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)} disabled={usuarios.isLoading}>
          <option value="">{usuarios.isLoading ? 'Cargando…' : 'Selecciona una cuenta'}</option>
          {elegibles.map((u) => <option key={u.id} value={u.id}>{u.username} · {u.email}</option>)}
        </select>
      </label>
      {!usuarios.isLoading && elegibles.length === 0 && <p className="text-sm text-slate-500">No hay cuentas activas y disponibles con el rol Paciente.</p>}
      <div className="flex justify-end gap-2"><Button variante="secundario" onClick={onClose}>Cancelar</Button><Button disabled={!usuarioId} cargando={vincular.isPending} onClick={() => vincular.mutate()}>Vincular</Button></div>
    </div>
  </Modal>
}
