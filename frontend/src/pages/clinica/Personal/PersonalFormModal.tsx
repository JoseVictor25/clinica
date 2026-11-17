import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import {
  CARGOS_PERSONAL,
  personalApi,
  type Personal,
} from '@/api/modules/personal'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { aplicarErroresDeApi } from '@/lib/formErrors'

const esquema = z.object({
  ci: z.string().trim()
    .min(1, 'La CI es obligatoria.')
    .max(20, 'Máximo 20 caracteres.'),
  nombre: z.string().trim()
    .min(1, 'El nombre es obligatorio.')
    .max(100, 'Máximo 100 caracteres.'),
  apellido: z.string().trim()
    .min(1, 'El apellido es obligatorio.')
    .max(100, 'Máximo 100 caracteres.'),
  telefono: z.string().trim()
    .min(1, 'El teléfono es obligatorio.')
    .max(30, 'Máximo 30 caracteres.'),
  cargo: z.enum([
    'MEDICO',
    'ENFERMERIA',
    'RECEPCION',
    'CONDUCTOR',
    'OTRO',
  ]),
  fecha_ingreso: z.string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, 'Indica una fecha válida.'),
  estado: z.boolean(),
})

type Valores = z.infer<typeof esquema>

const CAMPOS = [
  'ci',
  'nombre',
  'apellido',
  'telefono',
  'cargo',
  'fecha_ingreso',
  'estado',
] as const

const CAMPOS_TEXTO = [
  { nombre: 'ci', etiqueta: 'CI', maximo: 20 },
  { nombre: 'nombre', etiqueta: 'Nombre', maximo: 100 },
  { nombre: 'apellido', etiqueta: 'Apellido', maximo: 100 },
  { nombre: 'telefono', etiqueta: 'Teléfono', maximo: 30 },
] as const

interface Props {
  /** null indica que se creará un registro. */
  personal: Personal | null
  onClose: () => void
}

export function PersonalFormModal({ personal, onClose }: Props) {
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
      ci: personal?.ci ?? '',
      nombre: personal?.nombre ?? '',
      apellido: personal?.apellido ?? '',
      telefono: personal?.telefono ?? '',
      cargo: personal?.cargo ?? 'OTRO',
      fecha_ingreso: personal?.fecha_ingreso ?? '',
      estado: personal?.estado ?? true,
    },
  })

  const guardar = useMutation({
    mutationFn: (valores: Valores) =>
      personal
        ? personalApi.actualizar(personal.id, valores)
        : personalApi.crear(valores),

    onSuccess: () => {
      toast.success(
        personal ? 'Personal actualizado.' : 'Personal registrado.',
      )

      void queryClient.invalidateQueries({
        queryKey: ['personal'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['medicos'],
      })

      onClose()
    },

    onError: (error) => {
      setErrorGeneral(
        aplicarErroresDeApi(error, setError, CAMPOS, {
          ci_duplicada: 'ci',
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
      titulo={personal ? 'Editar personal' : 'Registrar personal'}
      onClose={cerrar}
    >
      <form
        className="max-h-[75vh] space-y-4 overflow-y-auto pr-1"
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

        {CAMPOS_TEXTO.map((campo) => (
          <Field
            key={campo.nombre}
            id={campo.nombre}
            label={campo.etiqueta}
            error={errors[campo.nombre]?.message}
          >
            <input
              id={campo.nombre}
              type={campo.nombre === 'telefono' ? 'tel' : 'text'}
              className={inputClass}
              maxLength={campo.maximo}
              aria-invalid={Boolean(errors[campo.nombre])}
              aria-describedby={
                errors[campo.nombre]
                  ? `${campo.nombre}-error`
                  : undefined
              }
              {...register(campo.nombre)}
            />
          </Field>
        ))}

        <Field
          id="cargo"
          label="Cargo"
          error={errors.cargo?.message}
        >
          <select
            id="cargo"
            className={inputClass}
            aria-invalid={Boolean(errors.cargo)}
            aria-describedby={
              errors.cargo ? 'cargo-error' : undefined
            }
            {...register('cargo')}
          >
            {CARGOS_PERSONAL.map((cargo) => (
              <option key={cargo.valor} value={cargo.valor}>
                {cargo.etiqueta}
              </option>
            ))}
          </select>
        </Field>

        <Field
          id="fecha_ingreso"
          label="Fecha de ingreso"
          error={errors.fecha_ingreso?.message}
        >
          <input
            id="fecha_ingreso"
            type="date"
            className={inputClass}
            aria-invalid={Boolean(errors.fecha_ingreso)}
            aria-describedby={
              errors.fecha_ingreso
                ? 'fecha_ingreso-error'
                : undefined
            }
            {...register('fecha_ingreso')}
          />
        </Field>

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" {...register('estado')} />
          Personal activo
        </label>

        <p className="text-xs text-slate-500">
          La cuenta de acceso se vincula desde el listado de personal.
          Elegir el cargo Médico no crea automáticamente su registro
          profesional ni asigna roles de acceso.
        </p>

        <div className="flex justify-end gap-2 pt-2">
          <Button
            variante="secundario"
            disabled={guardar.isPending}
            onClick={cerrar}
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
