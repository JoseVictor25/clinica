import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { normalizarError } from '@/api/errors'
import { citasApi, type Cita, type CitaReprogramarInput } from '@/api/modules/citas'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { aplicarErroresDeApi } from '@/lib/formErrors'
import { mensajeDeError } from '@/lib/errorMessages'
import { fechaLocalActual } from './fechaLocal'
import { HorariosDisponibles } from './HorariosDisponibles'

const esquema = z.object({
  fecha: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Selecciona una fecha.'),
  hora: z.string().regex(/^\d{2}:\d{2}$/, 'Selecciona un horario disponible.'),
})
type Valores = z.infer<typeof esquema>
const CAMPOS = ['fecha', 'hora'] as const

export function ReprogramarCitaModal({
  cita,
  onClose,
}: {
  cita: Cita
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)
  const horaActual = cita.hora.slice(0, 5)
  const fechaAnterior = useRef(cita.fecha)
  const {
    control,
    register,
    handleSubmit,
    setValue,
    setError,
    formState: { errors },
  } = useForm<Valores>({
    resolver: zodResolver(esquema),
    defaultValues: { fecha: cita.fecha, hora: horaActual },
  })
  const fecha = useWatch({ control, name: 'fecha' })
  const hora = useWatch({ control, name: 'hora' })
  const puedeConsultar = /^\d{4}-\d{2}-\d{2}$/.test(fecha)

  const disponibilidad = useQuery({
    queryKey: ['citas', 'disponibilidad', cita.paciente_id, cita.medico_id, fecha, cita.id],
    queryFn: () => citasApi.disponibilidad(
      cita.paciente_id,
      cita.medico_id,
      fecha,
      cita.id,
    ),
    enabled: puedeConsultar,
    retry: false,
  })

  useEffect(() => {
    if (fechaAnterior.current !== fecha) {
      fechaAnterior.current = fecha
      setValue('hora', '')
    }
  }, [fecha, setValue])

  const guardar = useMutation({
    mutationFn: (valores: Valores) => citasApi.reprogramar(cita.id, {
      fecha: valores.fecha,
      hora: valores.hora,
    } satisfies CitaReprogramarInput),
    onSuccess: () => {
      toast.success('Cita reprogramada correctamente.')
      void qc.invalidateQueries({ queryKey: ['citas'] })
      onClose()
    },
    onError: (error) => {
      const normalizado = normalizarError(error)
      if (
        normalizado.code === 'horario_no_disponible'
        || normalizado.code === 'paciente_no_disponible'
      ) {
        setValue('hora', '', { shouldValidate: true })
        void disponibilidad.refetch()
      }
      setErrorGeneral(aplicarErroresDeApi(error, setError, CAMPOS, {
        fecha_cita_pasada: 'fecha',
        hora_cita_pasada: 'hora',
        fuera_horario: 'hora',
        horario_no_disponible: 'hora',
        paciente_no_disponible: 'hora',
      }))
    },
  })

  const enviar = (valores: Valores) => {
    setErrorGeneral(null)
    if (valores.fecha === cita.fecha && valores.hora === horaActual) {
      setError('hora', {
        type: 'manual',
        message: 'Selecciona una fecha u hora diferente.',
      })
      return
    }
    guardar.mutate(valores)
  }

  return (
    <Modal titulo="Reprogramar cita" onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit(enviar)} noValidate>
        {errorGeneral && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{errorGeneral}</p>}
        <div className="rounded bg-slate-50 p-3 text-sm">
          <p><span className="font-medium">Paciente:</span> {cita.paciente_nombre}</p>
          <p><span className="font-medium">Médico:</span> {cita.medico_nombre}</p>
          <p><span className="font-medium">Horario actual:</span> {cita.fecha} {horaActual}</p>
        </div>
        <Field id="fecha-reprogramar" label="Nueva fecha" error={errors.fecha?.message}>
          <input
            id="fecha-reprogramar"
            type="date"
            min={fechaLocalActual()}
            className={inputClass}
            {...register('fecha')}
          />
        </Field>
        <Field id="hora-reprogramar" label="Nuevo horario" error={errors.hora?.message}>
          <input type="hidden" {...register('hora')} />
          <HorariosDisponibles
            horarios={disponibilidad.data?.horarios ?? []}
            seleccionado={hora}
            cargando={disponibilidad.isFetching}
            error={disponibilidad.isError ? mensajeDeError(disponibilidad.error) : null}
            listo={puedeConsultar}
            onSeleccionar={(valor) => setValue('hora', valor, { shouldValidate: true })}
          />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variante="secundario" onClick={onClose} disabled={guardar.isPending}>Cancelar</Button>
          <Button type="submit" cargando={guardar.isPending} disabled={!hora}>Reprogramar</Button>
        </div>
      </form>
    </Modal>
  )
}
