import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { pacientesApi, SEXOS, type Paciente } from '@/api/modules/pacientes'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { aplicarErroresDeApi } from '@/lib/formErrors'

const hoy = new Date().toISOString().slice(0, 10)
const esquema = z.object({
  ci: z.string().trim().min(1, 'La CI es obligatoria.').max(20),
  nombre: z.string().trim().min(1, 'El nombre es obligatorio.').max(100),
  apellido: z.string().trim().min(1, 'El apellido es obligatorio.').max(100),
  sexo: z.enum(['M', 'F', 'OTRO']),
  fecha_nacimiento: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .refine((value) => value <= hoy, 'La fecha no puede ser futura.'),
  telefono: z.string().trim().min(1, 'El teléfono es obligatorio.').max(30),
  email: z.union([z.literal(''), z.string().email('Correo inválido.')]),
  estado: z.boolean(),
})

type Valores = z.infer<typeof esquema>
const CAMPOS = [
  'ci',
  'nombre',
  'apellido',
  'sexo',
  'fecha_nacimiento',
  'telefono',
  'email',
  'estado',
] as const

interface Props {
  paciente: Paciente | null
  onClose: () => void
  onCreated?: (paciente: Paciente) => void
}

export function PacienteFormModal({ paciente, onClose, onCreated }: Props) {
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
      ci: paciente?.ci ?? '',
      nombre: paciente?.nombre ?? '',
      apellido: paciente?.apellido ?? '',
      sexo: paciente?.sexo ?? 'OTRO',
      fecha_nacimiento: paciente?.fecha_nacimiento ?? '',
      telefono: paciente?.telefono ?? '',
      email: paciente?.email ?? '',
      estado: paciente?.estado ?? true,
    },
  })

  const ciActual = useWatch({ control, name: 'ci' }).trim()
  const ciConsultada = useDebouncedValue(ciActual)
  const identidadAplicada = useRef<string | null>(null)
  const correoAplicado = useRef(false)
  const identidadQuery = useQuery({
    queryKey: ['identidad-personal-por-ci', ciConsultada],
    queryFn: () => pacientesApi.identidadPorCi(ciConsultada),
    enabled: ciConsultada.length > 0,
    staleTime: 30_000,
  })
  const identidadEncontrada = Boolean(
    !paciente &&
      identidadQuery.data?.encontrado &&
      identidadQuery.data.ci === ciActual,
  )
  const correoDeCuentaCompartida = Boolean(
    identidadQuery.data?.encontrado &&
      identidadQuery.data.ci === ciActual &&
      identidadQuery.data.email,
  )

  useEffect(() => {
    if (ciConsultada !== ciActual) return
    const identidad = identidadQuery.data
    if (paciente) {
      if (identidad?.encontrado && identidad.email) {
        setValue('email', identidad.email, { shouldValidate: true })
      }
      return
    }
    if (identidad?.encontrado) {
      setValue('nombre', identidad.nombre, { shouldValidate: true })
      setValue('apellido', identidad.apellido, { shouldValidate: true })
      setValue('telefono', identidad.telefono, { shouldValidate: true })
      if (identidad.email) {
        setValue('email', identidad.email, { shouldValidate: true })
        correoAplicado.current = true
      } else if (correoAplicado.current) {
        setValue('email', '')
        correoAplicado.current = false
      }
      identidadAplicada.current = identidad.ci
      return
    }
    if (!identidadQuery.isFetching && identidadAplicada.current) {
      setValue('nombre', '')
      setValue('apellido', '')
      setValue('telefono', '')
      if (correoAplicado.current) setValue('email', '')
      correoAplicado.current = false
      identidadAplicada.current = null
    }
  }, [ciActual, ciConsultada, identidadQuery.data, identidadQuery.isFetching, paciente, setValue])

  const guardar = useMutation({
    mutationFn: (values: Valores) =>
      paciente
        ? pacientesApi.actualizar(paciente.id, values)
        : pacientesApi.crear(values),
    onSuccess: (guardado) => {
      toast.success(
        paciente
          ? 'Paciente actualizado.'
          : 'Paciente registrado con su historia clínica.',
      )
      void queryClient.invalidateQueries({ queryKey: ['pacientes'] })
      void queryClient.invalidateQueries({ queryKey: ['personal'] })
      onClose()
      if (!paciente) onCreated?.(guardado)
    },
    onError: (error) =>
      setErrorGeneral(
        aplicarErroresDeApi(error, setError, CAMPOS, {
          ci_duplicada: 'ci',
          ci_no_modificable: 'ci',
          fecha_nacimiento_invalida: 'fecha_nacimiento',
        }),
      ),
  })

  const camposTexto = [
    { nombre: 'ci', etiqueta: 'CI', tipo: 'text' },
    { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'text' },
    { nombre: 'apellido', etiqueta: 'Apellido', tipo: 'text' },
    { nombre: 'telefono', etiqueta: 'Teléfono', tipo: 'tel' },
    { nombre: 'email', etiqueta: 'Correo electrónico', tipo: 'email' },
  ] as const

  return (
    <Modal
      titulo={paciente ? 'Editar paciente' : 'Registrar paciente'}
      onClose={onClose}
    >
      <form
        className="max-h-[75vh] space-y-4 overflow-y-auto pr-1"
        onSubmit={handleSubmit((values) => guardar.mutate(values))}
        noValidate
      >
        {errorGeneral && (
          <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
            {errorGeneral}
          </p>
        )}

        {camposTexto.map((campo) => {
          const identidadBloqueada =
            identidadEncontrada &&
            (campo.nombre === 'nombre' ||
              campo.nombre === 'apellido' ||
              campo.nombre === 'telefono' ||
              campo.nombre === 'email')
          const soloLectura =
            (Boolean(paciente) && campo.nombre === 'ci') ||
            ((Boolean(paciente?.cuenta) || correoDeCuentaCompartida) &&
              campo.nombre === 'email') ||
            identidadBloqueada
          return (
            <Field
              key={campo.nombre}
              id={campo.nombre}
              label={campo.etiqueta}
              error={errors[campo.nombre]?.message}
            >
              <input
                id={campo.nombre}
                type={campo.tipo}
                className={`${inputClass} ${
                  soloLectura ? 'bg-slate-100 text-slate-600' : ''
                }`}
                readOnly={soloLectura}
                {...register(campo.nombre)}
              />
            </Field>
          )
        })}

        {!paciente && identidadEncontrada && (
          <p className="rounded-md bg-blue-50 p-3 text-sm text-blue-700">
            Datos completados desde Personal. El correo pertenece a la cuenta
            vinculada.
          </p>
        )}

        <Field id="sexo" label="Sexo" error={errors.sexo?.message}>
          <select id="sexo" className={inputClass} {...register('sexo')}>
            {SEXOS.map((sexo) => (
              <option key={sexo.valor} value={sexo.valor}>
                {sexo.etiqueta}
              </option>
            ))}
          </select>
        </Field>

        <Field
          id="fecha_nacimiento"
          label="Fecha de nacimiento"
          error={errors.fecha_nacimiento?.message}
        >
          <input
            id="fecha_nacimiento"
            type="date"
            max={hoy}
            className={inputClass}
            {...register('fecha_nacimiento')}
          />
        </Field>

        {paciente && (
          <label className="flex gap-2 text-sm">
            <input type="checkbox" {...register('estado')} />
            Paciente activo
          </label>
        )}

        <div className="flex justify-end gap-2">
          <Button variante="secundario" onClick={onClose}>
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
