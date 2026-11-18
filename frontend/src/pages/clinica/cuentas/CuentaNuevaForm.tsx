import { useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { rolesApi } from '@/api/modules/roles'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { inputClass } from '@/components/ui/styles'
import { mensajeDeError } from '@/lib/errorMessages'
import { correoValido, passwordsCoinciden, usuarioObligatorio } from './validacionesCuenta'

export interface ValoresCuentaNueva {
  username: string
  email: string
  password: string
  roles: number[]
}
type ValoresFormulario = ValoresCuentaNueva & { confirmarPassword: string }

interface Props {
  permiteRoles: boolean
  emailInicial?: string
  rolObligatorio?: string
  rolesPermitidos?: string[]
  cargando: boolean
  error?: string | null
  textoGuardar?: string
  onGuardar: (valores: ValoresCuentaNueva) => void
  onCancelar: () => void
}

export function CuentaNuevaForm({
  permiteRoles,
  emailInicial = '',
  rolObligatorio,
  rolesPermitidos,
  cargando,
  error,
  textoGuardar = 'Crear cuenta',
  onGuardar,
  onCancelar,
}: Props) {
  const { register, handleSubmit, getValues, formState: { errors } } = useForm<ValoresFormulario>({
    defaultValues: { username: '', email: emailInicial, password: '', confirmarPassword: '', roles: [] },
  })
  const roles = useQuery({
    queryKey: ['roles', 'activos'],
    queryFn: () => rolesApi.listarTodos(true),
    enabled: permiteRoles,
  })
  const rolesVisibles = roles.data?.filter(
    (rol) => !rolesPermitidos || rolesPermitidos.includes(rol.nombre),
  ) ?? []
  const obligatorioDisponible = rolesVisibles.find(
    (rol) => rol.nombre === rolObligatorio,
  )

  return <form className="space-y-4" noValidate onSubmit={handleSubmit((valores) => {
    const seleccionados = valores.roles.map(Number)
    if (obligatorioDisponible && !seleccionados.includes(obligatorioDisponible.id)) seleccionados.push(obligatorioDisponible.id)
    onGuardar({ username: valores.username, email: valores.email, password: valores.password, roles: seleccionados })
  })}>
    {error && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <Field id="cuenta-username" label="Nombre de usuario" error={errors.username?.message}>
      <input id="cuenta-username" className={inputClass} maxLength={150} autoComplete="off" {...register('username', { validate: usuarioObligatorio })} />
    </Field>
    <Field id="cuenta-email" label="Correo electrónico" error={errors.email?.message}>
      <input id="cuenta-email" type="email" className={inputClass} maxLength={254} autoComplete="off" {...register('email', { required: 'El correo es obligatorio.', validate: correoValido })} />
    </Field>
    <Field id="cuenta-password" label="Contraseña" error={errors.password?.message}>
      <input id="cuenta-password" type="password" className={inputClass} autoComplete="new-password" {...register('password', { required: 'La contraseña es obligatoria.' })} />
    </Field>
    <Field id="cuenta-confirmar" label="Confirmar contraseña" error={errors.confirmarPassword?.message}>
      <input id="cuenta-confirmar" type="password" className={inputClass} autoComplete="new-password" {...register('confirmarPassword', { validate: (valor) => passwordsCoinciden(valor, getValues('password')) })} />
    </Field>
    <p className="text-xs text-slate-500">El servidor verificará los requisitos de seguridad de la contraseña.</p>
    {permiteRoles && <fieldset className="space-y-2">
      <legend className="text-sm font-medium text-slate-700">Roles iniciales</legend>
      {roles.isLoading && <p className="text-sm text-slate-600">Cargando roles…</p>}
      {roles.isError && <p role="alert" className="text-sm text-red-700">{mensajeDeError(roles.error)}</p>}
      {rolesVisibles.map((rol) => {
        const obligatorio = rol.nombre === rolObligatorio
        return <label key={rol.id} className="flex items-center gap-2 text-sm">
          <input type="checkbox" value={rol.id} checked={obligatorio ? true : undefined} disabled={obligatorio} {...(!obligatorio ? register('roles') : {})} />
          {rol.nombre}{obligatorio && ' (obligatorio)'}
        </label>
      })}
      {rolObligatorio && <p className="rounded-md bg-blue-50 p-3 text-xs text-blue-800">El rol {rolObligatorio} es obligatorio por el cargo del Personal y no se puede desmarcar.</p>}
      {!rolObligatorio && <p className="text-xs text-slate-500">El cargo Otro no asigna un rol de acceso. La cuenta se creará sin roles.</p>}
      <p className="text-xs text-slate-500">Paciente se asigna únicamente desde el registro de Pacientes.</p>
    </fieldset>}
    {!permiteRoles && <p className="rounded-md bg-blue-50 p-3 text-sm text-blue-800">La cuenta recibirá automáticamente el rol Paciente.</p>}
    <div className="flex justify-end gap-2 pt-2"><Button variante="secundario" disabled={cargando} onClick={onCancelar}>Cancelar</Button><Button type="submit" cargando={cargando} disabled={permiteRoles && roles.isLoading}>{textoGuardar}</Button></div>
  </form>
}
