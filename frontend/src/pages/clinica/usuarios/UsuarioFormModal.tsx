import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { rolesApi } from '@/api/modules/roles'
import {
  usuariosApi,
  type ActualizarUsuarioInput,
  type UsuarioClinica,
} from '@/api/modules/usuarios'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'
import { aplicarErroresDeApi } from '@/lib/formErrors'

interface Props {
  /** null indica que se creará un usuario. */
  usuario: UsuarioClinica | null
  onClose: () => void
}

interface Valores {
  username: string
  email: string
  password: string
  confirmarPassword: string
  roles: string[]
}

const CAMPOS = [
  'username',
  'email',
  'password',
  'confirmarPassword',
  'roles',
] as const

export function UsuarioFormModal({ usuario, onClose }: Props) {
  const queryClient = useQueryClient()
  const {
    usuario: sesion,
    actualizarPerfil,
  } = useAuth()

  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)
  const creando = usuario === null

  const {
    register,
    handleSubmit,
    getValues,
    setError,
    formState: { errors },
  } = useForm<Valores>({
    defaultValues: {
      username: usuario?.username ?? '',
      email: usuario?.email ?? '',
      password: '',
      confirmarPassword: '',
      roles: [],
    },
  })

  const roles = useQuery({
    queryKey: ['roles', 'activos'],
    queryFn: () => rolesApi.listarTodos(true),
    enabled: creando,
  })

  const guardar = useMutation({
    mutationFn: async (valores: Valores): Promise<UsuarioClinica> => {
      if (usuario) {
        const datos: ActualizarUsuarioInput = {
          email: valores.email.trim(),
        }

        // Una contraseña vacía conserva la actual.
        if (valores.password !== '') {
          datos.password = valores.password
        }

        return usuariosApi.actualizar(usuario.id, datos)
      }

      const seleccionados = valores.roles.map(Number)

      const rolesValidos = seleccionados.every((id) =>
        roles.data?.some((rol) => rol.id === id && rol.estado),
      )

      if (!rolesValidos) {
        throw new Error(
          'Uno de los roles seleccionados ya no está disponible.',
        )
      }

      return usuariosApi.crear({
        username: valores.username.trim(),
        email: valores.email.trim(),
        password: valores.password,
        estado: true,
        roles: seleccionados,
      })
    },

    onSuccess: async (guardado) => {
      toast.success(
        creando ? 'Usuario creado.' : 'Usuario actualizado.',
      )

      if (guardado.id === sesion?.id) {
        try {
          await actualizarPerfil()
        } catch {
          toast.warning(
            'El cambio se guardó, pero no se pudo actualizar tu perfil. Recarga la página.',
          )
        }
      }

      void queryClient.invalidateQueries({
        queryKey: ['usuarios'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['usuario-roles'],
      })

      onClose()
    },

    onError: (error) => {
      setErrorGeneral(
        aplicarErroresDeApi(error, setError, CAMPOS, {
          usuario_duplicado: 'username',
          email_duplicado: 'email',
        }),
      )
    },
  })

  function cerrar() {
    if (!guardar.isPending) {
      onClose()
    }
  }

  const bloquearGuardado =
    creando && (roles.isPending || roles.isError)

  return (
    <Modal
      titulo={creando ? 'Nuevo usuario' : 'Editar usuario'}
      onClose={cerrar}
    >
      <form
        className="space-y-4"
        noValidate
        onSubmit={handleSubmit((valores) => {
          if (guardar.isPending || bloquearGuardado) return

          setErrorGeneral(null)
          guardar.mutate(valores)
        })}
      >
        {errorGeneral && (
          <p
            role="alert"
            className="rounded-md bg-red-50 p-3 text-sm text-red-700"
          >
            {errorGeneral}
          </p>
        )}

        <Field
          id="username"
          label="Nombre de usuario"
          error={errors.username?.message}
        >
          <input
            id="username"
            className={inputClass}
            autoComplete="off"
            readOnly={!creando}
            maxLength={150}
            aria-invalid={Boolean(errors.username)}
            aria-describedby={
              errors.username ? 'username-error' : undefined
            }
            {...register('username', {
              validate: (valor) =>
                valor.trim().length > 0 ||
                'El nombre de usuario es obligatorio.',
              maxLength: {
                value: 150,
                message: 'Máximo 150 caracteres.',
              },
            })}
          />
        </Field>

        {!creando && (
          <p className="text-xs text-slate-500">
            El nombre de usuario no se puede modificar.
          </p>
        )}

        <Field
          id="email"
          label="Correo electrónico"
          error={errors.email?.message}
        >
          <input
            id="email"
            type="email"
            className={inputClass}
            autoComplete="off"
            maxLength={254}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={
              errors.email ? 'email-error' : undefined
            }
            {...register('email', {
              required: 'El correo es obligatorio.',
              validate: (valor) =>
                /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valor.trim()) ||
                'Introduce un correo electrónico válido.',
              maxLength: {
                value: 254,
                message: 'Máximo 254 caracteres.',
              },
            })}
          />
        </Field>

        <Field
          id="password"
          label={creando ? 'Contraseña' : 'Nueva contraseña (opcional)'}
          error={errors.password?.message}
        >
          <input
            id="password"
            type="password"
            className={inputClass}
            autoComplete="new-password"
            aria-invalid={Boolean(errors.password)}
            aria-describedby={
              errors.password ? 'password-error' : undefined
            }
            {...register('password', {
              validate: (valor) =>
                !creando ||
                valor.length > 0 ||
                'La contraseña es obligatoria.',
            })}
          />
        </Field>

        <Field
          id="confirmarPassword"
          label="Confirmar contraseña"
          error={errors.confirmarPassword?.message}
        >
          <input
            id="confirmarPassword"
            type="password"
            className={inputClass}
            autoComplete="new-password"
            aria-invalid={Boolean(errors.confirmarPassword)}
            aria-describedby={
              errors.confirmarPassword
                ? 'confirmarPassword-error'
                : undefined
            }
            {...register('confirmarPassword', {
              validate: (valor) =>
                valor === getValues('password') ||
                'Las contraseñas no coinciden.',
            })}
          />
        </Field>

        <p className="text-xs text-slate-500">
          {creando
            ? 'El servidor verificará los requisitos de seguridad de la contraseña.'
            : 'Deja ambos campos de contraseña vacíos para conservar la actual.'}
        </p>

        {creando && (
          <fieldset
            className="space-y-2"
            disabled={guardar.isPending}
          >
            <legend className="text-sm font-medium text-slate-700">
              Roles iniciales
            </legend>

            {roles.isPending && (
              <p role="status" className="text-sm text-slate-600">
                Cargando roles…
              </p>
            )}

            {roles.isError && (
              <div role="alert" className="space-y-2">
                <p className="text-sm text-red-700">
                  {mensajeDeError(roles.error)}
                </p>
                <Button
                  variante="secundario"
                  disabled={roles.isFetching}
                  onClick={() => void roles.refetch()}
                >
                  Reintentar
                </Button>
              </div>
            )}

            {roles.data?.map((rol) => (
              <label
                key={rol.id}
                className="flex items-center gap-2 text-sm text-slate-700"
              >
                <input
                  type="checkbox"
                  value={String(rol.id)}
                  {...register('roles')}
                />
                {rol.nombre}
              </label>
            ))}

            {roles.isSuccess && roles.data.length === 0 && (
              <p className="text-sm text-slate-600">
                No hay roles activos disponibles.
              </p>
            )}

            {errors.roles?.message && (
              <p role="alert" className="text-sm text-red-600">
                {errors.roles.message}
              </p>
            )}

            <p className="text-xs text-slate-500">
              Puedes crear el usuario sin roles y asignárselos después.
            </p>
          </fieldset>
        )}

        {!creando && (
          <p className="text-sm text-slate-600">
            Los roles se administran desde el botón «Roles» del listado
            de usuarios.
          </p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button
            variante="secundario"
            onClick={cerrar}
            disabled={guardar.isPending}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            cargando={guardar.isPending}
            disabled={bloquearGuardado}
          >
            {creando ? 'Crear usuario' : 'Guardar cambios'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
