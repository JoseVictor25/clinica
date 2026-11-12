import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { rolesApi, type Rol } from '@/api/modules/roles'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { useAuth } from '@/hooks/useAuth'
import { aplicarErroresDeApi } from '@/lib/formErrors'

const esquema = z.object({
  nombre: z
    .string()
    .trim()
    .min(1, 'El nombre es obligatorio.')
    .max(80, 'Máximo 80 caracteres.'),
  descripcion: z.string(),
  estado: z.boolean(),
})

type Valores = z.infer<typeof esquema>

const CAMPOS = ['nombre', 'descripcion', 'estado'] as const

interface Props {
  /** null indica que se creará un rol. */
  rol: Rol | null
  onClose: () => void
}

export function RolFormModal({ rol, onClose }: Props) {
  const queryClient = useQueryClient()
  const { actualizarPerfil } = useAuth()
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)

  const esBase = rol?.es_base === true

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Valores>({
    resolver: zodResolver(esquema),
    defaultValues: {
      nombre: rol?.nombre ?? '',
      descripcion: rol?.descripcion ?? '',
      estado: rol?.estado ?? true,
    },
  })

  const guardar = useMutation({
    mutationFn: (valores: Valores) => {
      if (!rol) {
        return rolesApi.crear(valores)
      }

      // En los roles base solo se envía la descripción.
      if (rol.es_base) {
        return rolesApi.actualizar(rol.id, {
          descripcion: valores.descripcion,
        })
      }

      return rolesApi.actualizar(rol.id, valores)
    },

    onSuccess: async () => {
      toast.success(rol ? 'Rol actualizado.' : 'Rol creado.')

      // Renombrar o desactivar un rol puede cambiar el perfil mostrado.
      try {
        await actualizarPerfil()
      } catch {
        toast.warning(
          'El rol se guardó, pero no se pudo actualizar el perfil. Recarga la página.',
        )
      }

      void queryClient.invalidateQueries({
        queryKey: ['roles'],
      })
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
          rol_duplicado: 'nombre',
        }),
      )
    },
  })

  function cerrar() {
    if (!guardar.isPending) {
      onClose()
    }
  }

  return (
    <Modal
      titulo={rol ? 'Editar rol' : 'Nuevo rol'}
      onClose={cerrar}
    >
      <form
        className="space-y-4"
        noValidate
        onSubmit={handleSubmit((valores) => {
          if (guardar.isPending) return

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

        {esBase && (
          <p className="rounded-md bg-blue-50 p-3 text-sm text-blue-800">
            Este es un rol base. Solo puedes modificar su descripción.
          </p>
        )}

        <Field
          id="nombre"
          label="Nombre"
          error={errors.nombre?.message}
        >
          <input
            id="nombre"
            className={inputClass}
            maxLength={80}
            readOnly={esBase}
            aria-invalid={Boolean(errors.nombre)}
            aria-describedby={
              errors.nombre ? 'nombre-error' : undefined
            }
            {...register('nombre')}
          />
        </Field>

        <Field
          id="descripcion"
          label="Descripción"
          error={errors.descripcion?.message}
        >
          <textarea
            id="descripcion"
            rows={3}
            className={inputClass}
            aria-invalid={Boolean(errors.descripcion)}
            aria-describedby={
              errors.descripcion ? 'descripcion-error' : undefined
            }
            {...register('descripcion')}
          />
        </Field>

        {esBase ? (
          <p className="text-sm text-slate-600">
            Estado: {rol?.estado ? 'Activo' : 'Inactivo'}.
          </p>
        ) : (
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              {...register('estado')}
            />
            Rol activo
          </label>
        )}

        <p className="text-xs text-slate-500">
          Los permisos de las operaciones están definidos en el backend.
          Crear un rol personalizado no añade permisos automáticamente.
        </p>

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
          >
            Guardar
          </Button>
        </div>
      </form>
    </Modal>
  )
}