import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { normalizarError } from '@/api/errors'
import { cambiarPassword } from '@/api/modules/gestion'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { inputClass } from '@/components/ui/styles'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'

export function CuentaPage() {
  const { usuario, actualizarPerfil } = useAuth()
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [confirmacion, setConfirmacion] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [errores, setErrores] = useState<Record<string, string>>({})
  const refrescar = useMutation({ mutationFn: actualizarPerfil, onError: (fallo) => toast.error(mensajeDeError(fallo)) })
  const guardar = useMutation({
    mutationFn: () => cambiarPassword({ password_actual: actual, password_nueva: nueva }),
    onSuccess: () => { toast.success('Contraseña actualizada.'); setActual(''); setNueva(''); setConfirmacion(''); setErrores({}); setError(null) },
    onError: (fallo) => {
      const normalizado = normalizarError(fallo)
      const campos: Record<string, string> = {}
      for (const [campo, mensajes] of Object.entries(normalizado.fieldErrors)) campos[campo] = mensajes.join(' ')
      if (campos.password) campos.password_nueva = campos.password
      if (normalizado.code === 'password_actual_invalida') campos.password_actual = mensajeDeError(fallo)
      setErrores(campos); setError(mensajeDeError(fallo))
    },
  })
  if (!usuario) return null
  return <section className="max-w-xl space-y-6">
    <h1 className="text-2xl font-semibold">Mi cuenta</h1>
    <dl className="space-y-2 rounded-xl border border-slate-200 bg-white p-5 text-sm">
      <dt className="font-semibold">Usuario</dt><dd>{usuario.username}</dd>
      <dt className="font-semibold">Correo</dt><dd>{usuario.email}</dd>
      <dt className="font-semibold">Clínica</dt><dd>{usuario.clinicaNombre ?? 'Administración del sistema'}</dd>
      <dt className="font-semibold">Roles</dt><dd>{usuario.esAdminSistema ? 'Administrador del sistema' : usuario.roles.join(', ') || 'Sin roles activos'}</dd>
      {usuario.clinicaId !== null && <><dt className="font-semibold">Suscripción</dt><dd>{usuario.suscripcionVigente ? `Vigente hasta ${usuario.suscripcionFin}` : 'Sin suscripción vigente'}</dd></>}
    </dl>
    <Button variante="secundario" cargando={refrescar.isPending} onClick={() => refrescar.mutate()}>Actualizar perfil</Button>
    <form className="space-y-4 rounded-xl border border-slate-200 bg-white p-5" onSubmit={(evento) => {
      evento.preventDefault()
      if (guardar.isPending) return
      setError(null); setErrores({})
      if (nueva !== confirmacion) { setErrores({ confirmacion: 'Las contraseñas no coinciden.' }); return }
      if (actual === nueva) { setErrores({ password_nueva: 'La nueva contraseña debe ser diferente de la actual.' }); return }
      guardar.mutate()
    }}>
      <h2 className="text-lg font-semibold">Cambiar contraseña</h2>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <Field id="password-actual" label="Contraseña actual" error={errores.password_actual}>
        <input id="password-actual" type="password" autoComplete="current-password" className={inputClass} required value={actual} onChange={(e) => setActual(e.target.value)} />
      </Field>
      <Field id="password-nueva" label="Nueva contraseña" error={errores.password_nueva}>
        <input id="password-nueva" type="password" autoComplete="new-password" className={inputClass} required value={nueva} onChange={(e) => setNueva(e.target.value)} />
      </Field>
      <Field id="password-confirmacion" label="Confirmar nueva contraseña" error={errores.confirmacion}>
        <input id="password-confirmacion" type="password" autoComplete="new-password" className={inputClass} required value={confirmacion} onChange={(e) => setConfirmacion(e.target.value)} />
      </Field>
      <Button type="submit" cargando={guardar.isPending}>Actualizar contraseña</Button>
    </form>
  </section>
}