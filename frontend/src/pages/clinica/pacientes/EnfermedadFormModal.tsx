import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import {
  enfermedadesApi,
  SEVERIDADES_ENFERMEDAD,
  TIPOS_ENFERMEDAD,
  type Enfermedad,
  type EnfermedadInput,
} from '@/api/modules/enfermedades'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { aplicarErroresDeApi } from '@/lib/formErrors'

const hoy = new Date().toISOString().slice(0, 10)
const esquema = z.object({
  nombre: z.string().trim().min(1, 'El nombre es obligatorio.').max(150),
  tipo: z.enum(['CRONICA', 'AGUDA', 'HEREDITARIA', 'INFECCIOSA', 'OTRA']),
  severidad: z.enum(['LEVE', 'MODERADA', 'GRAVE']),
  fecha_deteccion: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'La fecha es obligatoria.').refine((valor) => valor <= hoy, 'La fecha no puede ser futura.'),
})

type Valores = z.infer<typeof esquema>
const CAMPOS = ['nombre', 'tipo', 'severidad', 'fecha_deteccion'] as const

interface Props {
  pacienteId: number
  enfermedad: Enfermedad | null
  onClose: () => void
}

export function EnfermedadFormModal({ pacienteId, enfermedad, onClose }: Props) {
  const queryClient = useQueryClient()
  const [error, setErrorGeneral] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Valores>({
    resolver: zodResolver(esquema),
    defaultValues: enfermedad ?? {
      nombre: '',
      tipo: 'OTRA',
      severidad: 'LEVE',
      fecha_deteccion: hoy,
    },
  })
  const guardar = useMutation({
    mutationFn: (valores: EnfermedadInput) => enfermedad
      ? enfermedadesApi.actualizar(pacienteId, enfermedad.id, valores)
      : enfermedadesApi.crear(pacienteId, valores),
    onSuccess: () => {
      toast.success(enfermedad ? 'Enfermedad actualizada.' : 'Enfermedad registrada.')
      void queryClient.invalidateQueries({ queryKey: ['enfermedades', pacienteId] })
      onClose()
    },
    onError: (fallo) => setErrorGeneral(aplicarErroresDeApi(
      fallo,
      setError,
      CAMPOS,
      { fecha_deteccion_invalida: 'fecha_deteccion' },
    )),
  })

  return <Modal titulo={enfermedad ? 'Editar enfermedad' : 'Registrar enfermedad'} onClose={onClose}>
    <form className="space-y-4" onSubmit={handleSubmit((valores) => guardar.mutate(valores))} noValidate>
      {error && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <Field id="enfermedad-nombre" label="Nombre" error={errors.nombre?.message}>
        <input id="enfermedad-nombre" className={inputClass} {...register('nombre')} />
      </Field>
      <Field id="enfermedad-tipo" label="Tipo" error={errors.tipo?.message}>
        <select id="enfermedad-tipo" className={inputClass} {...register('tipo')}>
          {TIPOS_ENFERMEDAD.map((opcion) => <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>)}
        </select>
      </Field>
      <Field id="enfermedad-severidad" label="Severidad" error={errors.severidad?.message}>
        <select id="enfermedad-severidad" className={inputClass} {...register('severidad')}>
          {SEVERIDADES_ENFERMEDAD.map((opcion) => <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>)}
        </select>
      </Field>
      <Field id="enfermedad-fecha" label="Fecha de detección" error={errors.fecha_deteccion?.message}>
        <input id="enfermedad-fecha" type="date" max={hoy} className={inputClass} {...register('fecha_deteccion')} />
      </Field>
      <div className="flex justify-end gap-2">
        <Button variante="secundario" onClick={onClose}>Cancelar</Button>
        <Button type="submit" cargando={guardar.isPending}>Guardar</Button>
      </div>
    </form>
  </Modal>
}
