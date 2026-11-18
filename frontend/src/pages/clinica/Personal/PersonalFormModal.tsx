import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
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
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
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
  onCreated?: (personal: Personal) => void
}

export function PersonalFormModal({ personal, onClose, onCreated }: Props) {
  const queryClient = useQueryClient()
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    control,
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

  const ciActual = useWatch({ control, name: 'ci' }).trim()
  const ciConsultada = useDebouncedValue(ciActual)
  const identidadAplicada = useRef<string | null>(null)
  const identidadQuery = useQuery({
    queryKey: ['identidad-paciente-por-ci', ciConsultada],
    queryFn: () => personalApi.identidadPorCi(ciConsultada),
    enabled: !personal && ciConsultada.length > 0,
    staleTime: 30_000,
  })
  const identidadEncontrada = Boolean(
    !personal &&
      identidadQuery.data?.encontrado &&
      identidadQuery.data.ci === ciActual,
  )

  useEffect(() => {
    if (personal || ciConsultada !== ciActual) return
    const identidad = identidadQuery.data
    if (identidad?.encontrado) {
      setValue('nombre', identidad.nombre, { shouldValidate: true })
      setValue('apellido', identidad.apellido, { shouldValidate: true })
      setValue('telefono', identidad.telefono, { shouldValidate: true })
      identidadAplicada.current = identidad.ci
      return
    }
    if (!identidadQuery.isFetching && identidadAplicada.current) {
      setValue('nombre', '')
      setValue('apellido', '')
      setValue('telefono', '')
      identidadAplicada.current = null
    }
  }, [ciActual, ciConsultada, identidadQuery.data, identidadQuery.isFetching, personal, setValue])

  const guardar = useMutation({
    mutationFn: (valores: Valores) =>
      personal
        ? personalApi.actualizar(personal.id, valores)
        : personalApi.crear(valores),

    onSuccess: (guardado) => {
      toast.success(
        personal ? 'Personal actualizado.' : 'Personal registrado.',
      )

      void queryClient.invalidateQueries({
        queryKey: ['personal'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['medicos'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['pacientes'],
      })

      onClose()
      if (!personal) onCreated?.(guardado)
    },

    onError: (error) => {
      setErrorGeneral(
        aplicarErroresDeApi(error, setError, CAMPOS, {
          ci_duplicada: 'ci',
          ci_no_modificable: 'ci',
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
              className={`${inputClass} ${
                (personal && campo.nombre === 'ci') ||
                (identidadEncontrada && campo.nombre !== 'ci')
                  ? 'bg-slate-100 text-slate-600'
                  : ''
              }`}
              readOnly={
                Boolean(personal && campo.nombre === 'ci') ||
                (identidadEncontrada && campo.nombre !== 'ci')
              }
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

        {!personal && identidadEncontrada && (
          <p className="rounded-md bg-blue-50 p-3 text-sm text-blue-700">
            CI encontrada en Pacientes. Nombre, apellido y teléfono se
            completaron con la identidad existente.
          </p>
        )}

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

        <input type="hidden" {...register('estado')} />

        {personal && (
          <p className="rounded-md bg-slate-50 p-3 text-xs text-slate-600">
            Estado actual: {personal.estado ? 'Activo' : 'Inactivo'}. Finaliza
            o reactiva la relación laboral desde el listado de Personal.
          </p>
        )}

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
