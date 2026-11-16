import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { normalizarError } from '@/api/errors'
import { citasApi, type CitaCrearInput } from '@/api/modules/citas'
import { especialidadesApi } from '@/api/modules/especialidades'
import { medicosApi, todasLasPaginas } from '@/api/modules/gestion'
import { pacientesApi } from '@/api/modules/pacientes'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { aplicarErroresDeApi } from '@/lib/formErrors'
import { mensajeDeError } from '@/lib/errorMessages'
import { HorariosDisponibles } from './HorariosDisponibles'
import { fechaLocalActual } from './fechaLocal'

const esquema = z.object({
  paciente_id: z.number().int().positive('Selecciona un paciente.'),
  especialidad_id: z.number().int().positive('Selecciona una especialidad.'),
  medico_id: z.number().int().positive('Selecciona un médico.'),
  fecha: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Selecciona una fecha.'),
  hora: z.string().regex(/^\d{2}:\d{2}$/, 'Selecciona un horario disponible.'),
  motivo: z.string().trim().min(1, 'El motivo es obligatorio.').max(255, 'Máximo 255 caracteres.'),
})
type Valores = z.infer<typeof esquema>
const CAMPOS = ['paciente_id', 'medico_id', 'fecha', 'hora', 'motivo'] as const

export function CitaFormModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)
  const { control, register, handleSubmit, setValue, setError, formState: { errors } } = useForm<Valores>({
    resolver: zodResolver(esquema),
    defaultValues: { paciente_id: 0, especialidad_id: 0, medico_id: 0, fecha: '', hora: '', motivo: '' },
  })
  const pacienteId = useWatch({ control, name: 'paciente_id' })
  const especialidadId = useWatch({ control, name: 'especialidad_id' })
  const medicoId = useWatch({ control, name: 'medico_id' })
  const fecha = useWatch({ control, name: 'fecha' })
  const hora = useWatch({ control, name: 'hora' })

  const referencias = useQuery({
    queryKey: ['citas', 'referencias'],
    queryFn: async () => {
      const [pacientes, especialidades, medicos] = await Promise.all([
        todasLasPaginas(pacientesApi.listar, { estado: 'true', ordering: 'apellido' }),
        todasLasPaginas(especialidadesApi.listar, { ordering: 'nombre' }),
        todasLasPaginas(medicosApi.listar, { ordering: 'personal__apellido' }),
      ])
      return {
        pacientes: pacientes.filter((p) => p.estado),
        especialidades: especialidades.filter((e) => e.estado),
        medicos: medicos.filter((m) => m.estado),
      }
    },
  })
  const medicos = useMemo(
    () => referencias.data?.medicos.filter((m) => m.especialidad === Number(especialidadId)) ?? [],
    [especialidadId, referencias.data],
  )
  const puedeConsultar = Number(pacienteId) > 0 && Number(medicoId) > 0 && /^\d{4}-\d{2}-\d{2}$/.test(fecha)
  const disponibilidad = useQuery({
    queryKey: ['citas', 'disponibilidad', pacienteId, medicoId, fecha],
    queryFn: () => citasApi.disponibilidad(Number(pacienteId), Number(medicoId), fecha),
    enabled: puedeConsultar,
    retry: false,
  })

  useEffect(() => { setValue('medico_id', 0); setValue('hora', '') }, [especialidadId, setValue])
  useEffect(() => { setValue('hora', '') }, [medicoId, fecha, pacienteId, setValue])

  const guardar = useMutation({
    mutationFn: (valores: Valores) => citasApi.crear({
      paciente_id: Number(valores.paciente_id),
      medico_id: Number(valores.medico_id),
      fecha: valores.fecha,
      hora: valores.hora,
      motivo: valores.motivo.trim(),
    } satisfies CitaCrearInput),
    onSuccess: () => {
      toast.success('Cita creada correctamente.')
      void qc.invalidateQueries({ queryKey: ['citas'] })
      onClose()
    },
    onError: (error) => {
      const normalizado = normalizarError(error)
      const esConflictoDeDisponibilidad = (
        normalizado.code === 'horario_no_disponible'
        || normalizado.code === 'paciente_no_disponible'
      )
      if (esConflictoDeDisponibilidad) {
        setValue('hora', '', { shouldValidate: true })
        void qc.invalidateQueries({
          queryKey: ['citas', 'disponibilidad', pacienteId, medicoId, fecha],
        })
      }
      setErrorGeneral(aplicarErroresDeApi(error, setError, CAMPOS, {
        fecha_cita_pasada: 'fecha',
        hora_cita_pasada: 'hora',
        fuera_horario: 'hora',
        horario_no_disponible: 'hora',
        paciente_no_disponible: 'hora',
        paciente_inactivo: 'paciente_id',
        medico_inactivo: 'medico_id',
      }))
    },
  })

  return (
    <Modal titulo="Nueva cita" onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit((v) => { setErrorGeneral(null); guardar.mutate(v) })} noValidate>
        {errorGeneral && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{errorGeneral}</p>}
        {referencias.isError && <div className="space-y-2"><p role="alert" className="text-sm text-red-700">{mensajeDeError(referencias.error)}</p><Button variante="secundario" onClick={() => void referencias.refetch()}>Reintentar</Button></div>}
        <Field id="paciente_id" label="Paciente" error={errors.paciente_id?.message}>
          <select id="paciente_id" className={inputClass} disabled={referencias.isPending} {...register('paciente_id', { valueAsNumber: true })}>
            <option value={0}>Selecciona un paciente</option>
            {referencias.data?.pacientes.map((p) => <option key={p.id} value={p.id}>{p.apellido}, {p.nombre} — {p.ci}</option>)}
          </select>
        </Field>
        <Field id="especialidad_id" label="Especialidad" error={errors.especialidad_id?.message}>
          <select id="especialidad_id" className={inputClass} disabled={referencias.isPending} {...register('especialidad_id', { valueAsNumber: true })}>
            <option value={0}>Selecciona una especialidad</option>
            {referencias.data?.especialidades.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
          </select>
        </Field>
        <Field id="medico_id" label="Médico" error={errors.medico_id?.message}>
          <select id="medico_id" className={inputClass} disabled={!Number(especialidadId)} {...register('medico_id', { valueAsNumber: true })}>
            <option value={0}>Selecciona un médico</option>
            {medicos.map((m) => <option key={m.id} value={m.id}>{m.personal_nombre}</option>)}
          </select>
        </Field>
        <Field id="fecha" label="Fecha" error={errors.fecha?.message}>
          <input id="fecha" type="date" min={fechaLocalActual()} className={inputClass} {...register('fecha')} />
        </Field>
        <Field id="hora" label="Horario disponible" error={errors.hora?.message}>
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
        <Field id="motivo" label="Motivo" error={errors.motivo?.message}>
          <textarea id="motivo" rows={3} maxLength={255} className={inputClass} {...register('motivo')} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variante="secundario" onClick={onClose}>Cancelar</Button>
          <Button type="submit" cargando={guardar.isPending} disabled={referencias.isPending || !hora}>Crear cita</Button>
        </div>
      </form>
    </Modal>
  )
}
