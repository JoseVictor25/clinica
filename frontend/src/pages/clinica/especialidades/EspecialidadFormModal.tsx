import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { especialidadesApi, type Especialidad } from '@/api/modules/especialidades'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { aplicarErroresDeApi } from '@/lib/formErrors'

const esquema = z.object({
  nombre: z.string().trim().min(1, 'El nombre es obligatorio.').max(100, 'Máximo 100 caracteres.'),
  descripcion: z.string(),
  estado: z.boolean(),
})
type Valores = z.infer<typeof esquema>

const CAMPOS = ['nombre', 'descripcion', 'estado'] as const

interface Props {
  /** null = crear una nueva. */
  especialidad: Especialidad | null
  onClose: () => void
}

export function EspecialidadFormModal({ especialidad, onClose }: Props) {
  const queryClient = useQueryClient()
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Valores>({
    resolver: zodResolver(esquema),
    defaultValues: {
      nombre: especialidad?.nombre ?? '',
      descripcion: especialidad?.descripcion ?? '',
      estado: especialidad?.estado ?? true,
    },
  })

  const guardar = useMutation({
    mutationFn: (valores: Valores) =>
      especialidad
        ? especialidadesApi.actualizar(especialidad.id, valores)
        : especialidadesApi.crear(valores),
    onSuccess: () => {
      toast.success(especialidad ? 'Especialidad actualizada.' : 'Especialidad creada.')
      void queryClient.invalidateQueries({ queryKey: ['especialidades'] })
      onClose()
    },
    onError: (error) => {
      setErrorGeneral(aplicarErroresDeApi(error, setError, CAMPOS, { especialidad_duplicada: 'nombre' }))
    },
  })

  return (
    <Modal titulo={especialidad ? 'Editar especialidad' : 'Nueva especialidad'} onClose={onClose}>
      <form
        onSubmit={handleSubmit((valores) => {
          setErrorGeneral(null)
          guardar.mutate(valores)
        })}
        className="space-y-4"
        noValidate
      >
        {errorGeneral && (
          <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            {errorGeneral}
          </p>
        )}

        <Field id="nombre" label="Nombre" error={errors.nombre?.message}>
          <input
            id="nombre"
            className={inputClass}
            aria-invalid={errors.nombre ? 'true' : 'false'}
            aria-describedby={errors.nombre ? 'nombre-error' : undefined}
            {...register('nombre')}
          />
        </Field>

        <Field id="descripcion" label="Descripción" error={errors.descripcion?.message}>
          <textarea id="descripcion" rows={3} className={inputClass} {...register('descripcion')} />
        </Field>

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" {...register('estado')} />
          Activa
        </label>

        <div className="flex justify-end gap-2 pt-2">
          <Button variante="secundario" onClick={onClose} disabled={guardar.isPending}>
            Cancelar
          </Button>
          <Button type="submit" cargando={guardar.isPending}>
            Guardar
          </Button>
        </div>
      </form>
    </Modal>
  )
}