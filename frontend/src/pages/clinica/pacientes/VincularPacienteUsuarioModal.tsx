import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { pacientesApi, type Paciente } from '@/api/modules/pacientes'
import { usuariosApi } from '@/api/modules/usuarios'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { mensajeDeError } from '@/lib/errorMessages'
import { CuentaNuevaForm, type ValoresCuentaNueva } from '../cuentas/CuentaNuevaForm'
import { UsuarioFormModal } from '../usuarios/UsuarioFormModal'

type Modo = 'inicio' | 'crear' | 'vincular'

export function VincularPacienteUsuarioModal({ paciente, onClose }: { paciente: Paciente; onClose: () => void }) {
  const qc = useQueryClient()
  const [modo, setModo] = useState<Modo>('inicio')
  const [error, setError] = useState<string | null>(null)
  const [administrar, setAdministrar] = useState(false)
  const usuarioCompleto = useQuery({
    queryKey: ['usuarios', paciente.cuenta?.id],
    queryFn: () => usuariosApi.obtener(paciente.cuenta!.id),
    enabled: administrar && paciente.cuenta !== null,
  })
  const elegibles = useQuery({
    queryKey: ['pacientes', paciente.id, 'cuentas-elegibles'],
    queryFn: () => pacientesApi.cuentasElegibles(paciente.id),
    enabled: modo === 'vincular',
  })
  const cuentaElegible = elegibles.data?.results[0]
  const refrescar = () => {
    void qc.invalidateQueries({ queryKey: ['pacientes'] })
    void qc.invalidateQueries({ queryKey: ['usuarios'] })
  }
  const crear = useMutation({
    mutationFn: (v: ValoresCuentaNueva) => pacientesApi.crearCuenta(paciente.id, { username: v.username, email: v.email, password: v.password }),
    onSuccess: () => { toast.success('Cuenta de paciente creada y vinculada.'); refrescar(); onClose() },
    onError: (e) => setError(mensajeDeError(e)),
  })
  const vincular = useMutation({
    mutationFn: () => pacientesApi.vincularUsuario(paciente.id, cuentaElegible!.id),
    onSuccess: (r) => { toast.success(r.mensaje); refrescar(); onClose() },
    onError: (e) => setError(mensajeDeError(e)),
  })

  if (administrar && usuarioCompleto.data) {
    return <UsuarioFormModal usuario={usuarioCompleto.data} onClose={() => setAdministrar(false)} />
  }

  return <Modal titulo="Cuenta de acceso del paciente" onClose={onClose}><div className="space-y-4">
    <p className="text-sm text-slate-700">Paciente: <strong>{paciente.nombre} {paciente.apellido}</strong> · CI {paciente.ci}</p>
    {error && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {paciente.cuenta ? <>
      <div className="rounded-md border border-slate-200 p-4 text-sm">
        <p><strong>Usuario:</strong> {paciente.cuenta.username}</p>
        <p><strong>Correo:</strong> {paciente.cuenta.email}</p>
        <p><strong>Estado:</strong> {paciente.cuenta.estado ? 'Activo' : 'Inactivo'}</p>
        <p><strong>Roles:</strong> {paciente.cuenta.roles.join(', ') || 'Sin roles'}</p>
      </div>
      <p className="text-xs text-slate-500">El vínculo del paciente no puede reemplazarse ni eliminarse desde este flujo.</p>
      <div className="flex justify-end gap-2"><Button variante="secundario" onClick={onClose}>Cerrar</Button><Button cargando={usuarioCompleto.isLoading} onClick={() => setAdministrar(true)}>Administrar cuenta</Button></div>
    </> : modo === 'inicio' ? <>
      <p className="text-sm text-slate-600">Puedes crear una cuenta nueva con rol Paciente o vincular una cuenta cuya identidad ya esté verificada por Personal con la misma CI.</p>
      <div className="flex justify-end gap-2"><Button variante="secundario" onClick={onClose}>Más tarde</Button><Button variante="secundario" onClick={() => setModo('vincular')}>Vincular existente</Button><Button onClick={() => setModo('crear')}>Crear cuenta</Button></div>
    </> : modo === 'crear' ? <CuentaNuevaForm permiteRoles={false} emailInicial={paciente.email} cargando={crear.isPending} error={error} onGuardar={(v) => { setError(null); crear.mutate(v) }} onCancelar={() => setModo('inicio')} /> : <>
      <p className="text-sm text-slate-600">Cuenta verificada mediante el Personal con CI {paciente.ci}. Al vincular, se asignará el rol Paciente si falta.</p>
      {elegibles.isLoading && <p role="status" className="text-sm text-slate-600">Buscando la cuenta asociada a la misma CI…</p>}
      {elegibles.isError && <p className="text-sm text-red-700">{mensajeDeError(elegibles.error)}</p>}
      {cuentaElegible && <div className="rounded-md border border-slate-200 p-4 text-sm"><p><strong>Usuario:</strong> {cuentaElegible.username}</p><p><strong>Correo:</strong> {cuentaElegible.email}</p><p><strong>Estado:</strong> Activo</p></div>}
      {elegibles.data?.count === 0 && <p className="text-sm text-slate-500">El Personal con esta CI todavía no tiene una cuenta disponible. Créala desde Personal o crea una cuenta nueva para este Paciente.</p>}
      <div className="flex justify-end gap-2"><Button variante="secundario" onClick={() => setModo('inicio')}>Cancelar</Button><Button disabled={!cuentaElegible} cargando={vincular.isPending} onClick={() => vincular.mutate()}>Vincular cuenta</Button></div>
    </>}
  </div></Modal>
}
