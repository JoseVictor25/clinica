import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useFieldArray, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { normalizarError } from '@/api/errors'
import { recetasApi, type Receta } from '@/api/modules/recetas'
import type { Consulta } from '@/api/modules/consultas'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { mensajeDeError } from '@/lib/errorMessages'

const medicamento = z.object({
  nombre_medicamento: z.string().trim().min(1, 'El medicamento es obligatorio.').max(150, 'Máximo 150 caracteres.'),
  dosis: z.string().trim().min(1, 'La dosis es obligatoria.').max(50, 'Máximo 50 caracteres.'),
  frecuencia: z.string().trim().min(1, 'La frecuencia es obligatoria.').max(50, 'Máximo 50 caracteres.'),
  duracion: z.string().trim().min(1, 'La duración es obligatoria.').max(50, 'Máximo 50 caracteres.'),
})
const esquema = z.object({
  indicaciones: z.string().trim(),
  medicamentos: z.array(medicamento).min(1, 'Incluya al menos un medicamento.'),
})
type Valores = z.infer<typeof esquema>
const filaVacia = { nombre_medicamento: '', dosis: '', frecuencia: '', duracion: '' }

export function RecetaFormModal({ consulta, onClose, onSuccess }: {
  consulta: Consulta
  onClose: () => void
  onSuccess: (receta: Receta) => void
}) {
  const queryClient = useQueryClient()
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)
  const { register, control, handleSubmit, setError, formState: { errors } } = useForm<Valores>({
    resolver: zodResolver(esquema),
    defaultValues: { indicaciones: '', medicamentos: [{ ...filaVacia }] },
  })
  const { fields, append, remove } = useFieldArray({ control, name: 'medicamentos' })
  const guardar = useMutation({
    mutationFn: (valores: Valores) => recetasApi.crearReceta(consulta.id, valores),
    onSuccess: (receta) => {
      toast.success('Receta emitida correctamente.')
      void queryClient.invalidateQueries({ queryKey: ['consulta', consulta.id] })
      onSuccess(receta)
    },
    onError: (fallo) => {
      const error = normalizarError(fallo)
      const anidados = error.details.medicamentos
      if (Array.isArray(anidados)) {
        anidados.forEach((item, indice) => {
          if (!item || typeof item !== 'object') return
          Object.entries(item as Record<string, unknown>).forEach(([campo, mensajes]) => {
            if (['nombre_medicamento', 'dosis', 'frecuencia', 'duracion'].includes(campo) && Array.isArray(mensajes)) {
              setError(`medicamentos.${indice}.${campo}` as `medicamentos.${number}.nombre_medicamento`, {
                message: String(mensajes[0]),
              })
            }
          })
        })
      }
      setErrorGeneral(mensajeDeError(fallo))
    },
  })

  return (
    <Modal titulo="Emitir receta" onClose={onClose}>
      <div className="mb-4 rounded bg-slate-50 p-3 text-sm">
        <p><span className="font-medium">Paciente:</span> {consulta.paciente_nombre}</p>
        <p><span className="font-medium">Consulta:</span> #{consulta.id} · {new Date(consulta.fecha).toLocaleString()}</p>
      </div>
      <form className="space-y-4" onSubmit={handleSubmit((valores) => guardar.mutate(valores))} noValidate>
        {errorGeneral && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{errorGeneral}</p>}
        <Field id="receta-indicaciones" label="Indicaciones generales" error={errors.indicaciones?.message}>
          <textarea id="receta-indicaciones" rows={2} className={inputClass} {...register('indicaciones')} />
        </Field>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Medicamentos</h3>
            <Button variante="secundario" onClick={() => append({ ...filaVacia })}>Agregar medicamento</Button>
          </div>
          {fields.map((field, indice) => (
            <fieldset key={field.id} className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-2">
              <legend className="px-1 text-sm font-medium">Medicamento {indice + 1}</legend>
              <Field id={`med-${indice}-nombre`} label="Nombre" error={errors.medicamentos?.[indice]?.nombre_medicamento?.message}>
                <input id={`med-${indice}-nombre`} className={inputClass} {...register(`medicamentos.${indice}.nombre_medicamento`)} />
              </Field>
              <Field id={`med-${indice}-dosis`} label="Dosis" error={errors.medicamentos?.[indice]?.dosis?.message}>
                <input id={`med-${indice}-dosis`} className={inputClass} {...register(`medicamentos.${indice}.dosis`)} />
              </Field>
              <Field id={`med-${indice}-frecuencia`} label="Frecuencia" error={errors.medicamentos?.[indice]?.frecuencia?.message}>
                <input id={`med-${indice}-frecuencia`} className={inputClass} {...register(`medicamentos.${indice}.frecuencia`)} />
              </Field>
              <Field id={`med-${indice}-duracion`} label="Duración" error={errors.medicamentos?.[indice]?.duracion?.message}>
                <input id={`med-${indice}-duracion`} className={inputClass} {...register(`medicamentos.${indice}.duracion`)} />
              </Field>
              <div className="sm:col-span-2 flex justify-end">
                <Button variante="peligro" disabled={fields.length === 1} onClick={() => remove(indice)}>Eliminar</Button>
              </div>
            </fieldset>
          ))}
        </div>
        <div className="flex justify-end gap-2">
          <Button variante="secundario" onClick={onClose}>Cancelar</Button>
          <Button type="submit" cargando={guardar.isPending}>Emitir receta</Button>
        </div>
      </form>
    </Modal>
  )
}
