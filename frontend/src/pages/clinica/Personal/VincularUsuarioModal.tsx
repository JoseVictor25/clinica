import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { personalApi, type Personal } from '@/api/modules/personal'
import { usuariosApi } from '@/api/modules/usuarios'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { mensajeDeError } from '@/lib/errorMessages'
import { ROL_CONDUCTOR, ROL_ENFERMERIA, ROL_MEDICO, ROL_RECEPCIONISTA } from '@/lib/roles'
import { CuentaNuevaForm, type ValoresCuentaNueva } from '../cuentas/CuentaNuevaForm'
import { UsuarioFormModal } from '../usuarios/UsuarioFormModal'

type Modo = 'inicio' | 'crear' | 'vincular'

const ROL_POR_CARGO: Partial<Record<Personal['cargo'], string>> = {
  MEDICO: ROL_MEDICO,
  RECEPCION: ROL_RECEPCIONISTA,
  ENFERMERIA: ROL_ENFERMERIA,
  CONDUCTOR: ROL_CONDUCTOR,
}

export function VincularUsuarioModal({ personal, onClose }: { personal: Personal; onClose: () => void }) {
  const qc = useQueryClient()
  const [modo, setModo] = useState<Modo>('inicio')
  const [error, setError] = useState<string | null>(null)
  const [administrar, setAdministrar] = useState(false)

  const usuarioCompleto = useQuery({
    queryKey: ['usuarios', personal.usuario],
    queryFn: () => usuariosApi.obtener(personal.usuario as number),
    enabled: administrar && personal.usuario !== null,
  })
  const elegibles = useQuery({
    queryKey: ['personal', personal.id, 'cuentas-elegibles'],
    queryFn: () => personalApi.cuentasElegibles(personal.id),
    enabled: modo === 'vincular',
  })
  const cuentaElegible = elegibles.data?.results[0]
  const refrescar = () => {
    void qc.invalidateQueries({ queryKey: ['personal'] })
    void qc.invalidateQueries({ queryKey: ['usuarios'] })
    void qc.invalidateQueries({ queryKey: ['medicos'] })
    void qc.invalidateQueries({ queryKey: ['horarios'] })
  }
  const crear = useMutation({
    mutationFn: (v: ValoresCuentaNueva) => personalApi.crearCuenta(personal.id, v),
    onSuccess: () => { toast.success('Cuenta creada y vinculada.'); refrescar(); onClose() },
    onError: (e) => setError(mensajeDeError(e)),
  })
  const vincular = useMutation({
    mutationFn: (id: number | null) => personalApi.vincularUsuario(personal.id, id),
    onSuccess: () => { toast.success('Cuenta vinculada.'); refrescar(); onClose() },
    onError: (e) => setError(mensajeDeError(e)),
  })

  if (administrar && usuarioCompleto.data) {
    return <UsuarioFormModal usuario={usuarioCompleto.data} onClose={() => setAdministrar(false)} />
  }

  return <><Modal titulo="Cuenta de acceso" onClose={onClose}>
    <div className="space-y-4">
      <p className="text-sm text-slate-700">Personal: <strong>{personal.nombre} {personal.apellido}</strong> · CI {personal.ci}</p>
      {error && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {personal.cuenta ? <>
        <div className="rounded-md border border-slate-200 p-4 text-sm">
          <p><strong>Usuario:</strong> {personal.cuenta.username}</p>
          <p><strong>Correo:</strong> {personal.cuenta.email}</p>
          <p><strong>Estado:</strong> {personal.cuenta.estado ? 'Activo' : 'Inactivo'}</p>
          <p><strong>Roles:</strong> {personal.cuenta.roles.join(', ') || 'Sin roles'}</p>
        </div>
        {usuarioCompleto.isError && <p className="text-sm text-red-700">{mensajeDeError(usuarioCompleto.error)}</p>}
        <p className="text-xs text-slate-500">El vínculo se conserva para mantener la identidad y el historial. Si esta persona deja de trabajar, usa «Finalizar relación» desde el listado de Personal.</p>
        <div className="flex flex-wrap justify-end gap-2">
          <Button variante="secundario" onClick={onClose}>Cerrar</Button>
          <Button variante="secundario" cargando={usuarioCompleto.isLoading} onClick={() => setAdministrar(true)}>Administrar cuenta</Button>
        </div>
      </> : modo === 'inicio' ? <>
        <p className="text-sm text-slate-600">Este registro todavía no tiene cuenta. Puedes crear una nueva o vincular una cuenta cuya identidad ya esté verificada por un Paciente con la misma CI.</p>
        <div className="flex justify-end gap-2"><Button variante="secundario" onClick={onClose}>Más tarde</Button><Button variante="secundario" onClick={() => setModo('vincular')}>Vincular existente</Button><Button onClick={() => setModo('crear')}>Crear cuenta</Button></div>
      </> : modo === 'crear' ? <CuentaNuevaForm permiteRoles rolObligatorio={ROL_POR_CARGO[personal.cargo]} rolesPermitidos={ROL_POR_CARGO[personal.cargo] ? [ROL_POR_CARGO[personal.cargo]!] : []} cargando={crear.isPending} error={error} onGuardar={(v) => { setError(null); crear.mutate(v) }} onCancelar={() => setModo('inicio')} /> : <>
        <p className="text-sm text-slate-600">Cuenta verificada mediante el Paciente con CI {personal.ci}.</p>
        {personal.estado && ROL_POR_CARGO[personal.cargo] && <p className="rounded-md bg-blue-50 p-3 text-xs text-blue-800">Al vincular, se asignará el rol {ROL_POR_CARGO[personal.cargo]} si todavía no existe.</p>}
        {elegibles.isLoading && <p role="status" className="text-sm text-slate-600">Buscando la cuenta asociada a la misma CI…</p>}
        {elegibles.isError && <p className="text-sm text-red-700">{mensajeDeError(elegibles.error)}</p>}
        {cuentaElegible && <div className="rounded-md border border-slate-200 p-4 text-sm"><p><strong>Usuario:</strong> {cuentaElegible.username}</p><p><strong>Correo:</strong> {cuentaElegible.email}</p><p><strong>Estado:</strong> {cuentaElegible.estado ? 'Activo' : 'Inactivo; se reactivará al vincular'}</p></div>}
        {elegibles.data?.count === 0 && <p className="text-sm text-slate-500">El Paciente con esta CI todavía no tiene una cuenta disponible. Créala desde Pacientes o crea una cuenta nueva para este Personal.</p>}
        <div className="flex justify-end gap-2"><Button variante="secundario" onClick={() => setModo('inicio')}>Cancelar</Button><Button disabled={!cuentaElegible} cargando={vincular.isPending} onClick={() => cuentaElegible && vincular.mutate(cuentaElegible.id)}>Vincular cuenta</Button></div>
      </>}
    </div>
  </Modal></>
}
