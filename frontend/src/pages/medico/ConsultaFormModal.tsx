import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { normalizarError } from '@/api/errors'
import { consultasApi, type Consulta, type ConsultaCrearInput } from '@/api/modules/consultas'
import type { Cita } from '@/api/modules/citas'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { aplicarErroresDeApi } from '@/lib/formErrors'

const esquema = z.object({
  motivo: z.string().trim().min(1, 'El motivo es obligatorio.'),
  observacion: z.string().trim().min(1, 'La observación es obligatoria.'),
  diagnostico: z.string().trim().min(1, 'El diagnóstico es obligatorio.'),
})

type Valores = z.infer<typeof esquema>
const CAMPOS = ['motivo', 'observacion', 'diagnostico'] as const

interface Props {
  cita: Cita
  onClose: () => void
  onSuccess: (consulta: Consulta) => void
}

export function ConsultaFormModal({ cita, onClose, onSuccess }: Props) {
  const queryClient = useQueryClient()
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Valores>({
    resolver: zodResolver(esquema),
    defaultValues: { motivo: cita.motivo, observacion: '', diagnostico: '' },
  })

  const guardar = useMutation({
    mutationFn: (valores: Valores) => consultasApi.crear({
      cita_id: cita.id,
      ...valores,
    } as ConsultaCrearInput),
    onSuccess: (consulta) => {
      toast.success('Consulta registrada y cita marcada como atendida.')
      void queryClient.invalidateQueries({ queryKey: ['mi-agenda'] })
      onSuccess(consulta)
    },
    onError: (fallo) => {
      const error = normalizarError(fallo)
      if (error.code === 'consulta_ya_registrada') {
        toast.error('La cita ya tiene una consulta registrada. Se actualizará la agenda.')
        void queryClient.invalidateQueries({ queryKey: ['mi-agenda'] })
        onClose()
        return
      }
      setErrorGeneral(aplicarErroresDeApi(fallo, setError, CAMPOS))
    },
  })

  return (
    <Modal titulo="Registrar consulta" onClose={onClose}>
      <div className="mb-4 grid gap-2 rounded-md bg-slate-50 p-3 text-sm sm:grid-cols-2">
        <p><span className="font-medium">Paciente:</span> {cita.paciente_nombre}</p>
        <p><span className="font-medium">Especialidad:</span> {cita.especialidad_nombre}</p>
        <p><span className="font-medium">Fecha:</span> {cita.fecha}</p>
        <p><span className="font-medium">Hora:</span> {cita.hora.slice(0, 5)}</p>
        <p className="sm:col-span-2"><span className="font-medium">Motivo de la cita:</span> {cita.motivo}</p>
      </div>
      <form className="space-y-4" onSubmit={handleSubmit((valores) => guardar.mutate(valores))} noValidate>
        {errorGeneral && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{errorGeneral}</p>}
        <Field id="consulta-motivo" label="Motivo de consulta" error={errors.motivo?.message}>
          <textarea id="consulta-motivo" rows={2} className={inputClass} {...register('motivo')} />
        </Field>
        <Field id="consulta-observacion" label="Observación" error={errors.observacion?.message}>
          <textarea id="consulta-observacion" rows={4} className={inputClass} {...register('observacion')} />
        </Field>
        <Field id="consulta-diagnostico" label="Diagnóstico" error={errors.diagnostico?.message}>
          <textarea id="consulta-diagnostico" rows={3} className={inputClass} {...register('diagnostico')} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variante="secundario" onClick={onClose}>Cancelar</Button>
          <Button type="submit" cargando={guardar.isPending}>Registrar consulta</Button>
        </div>
      </form>
    </Modal>
  )
}
