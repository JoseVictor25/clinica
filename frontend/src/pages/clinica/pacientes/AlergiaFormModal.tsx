import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import {
  alergiasApi,
  SEVERIDADES_ALERGIA,
  TIPOS_ALERGIA,
  type Alergia,
  type AlergiaInput,
} from '@/api/modules/alergias'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { aplicarErroresDeApi } from '@/lib/formErrors'

const esquema = z.object({
  nombre: z.string().trim().min(1, 'El nombre es obligatorio.').max(150),
  tipo: z.enum(['MEDICAMENTO', 'ALIMENTO', 'AMBIENTAL', 'OTRA']),
  severidad: z.enum(['LEVE', 'MODERADA', 'GRAVE']),
  descripcion: z.string(),
})

type Valores = z.infer<typeof esquema>
const CAMPOS = ['nombre', 'tipo', 'severidad', 'descripcion'] as const

interface Props {
  pacienteId: number
  alergia: Alergia | null
  onClose: () => void
}

export function AlergiaFormModal({ pacienteId, alergia, onClose }: Props) {
  const queryClient = useQueryClient()
  const [error, setErrorGeneral] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Valores>({
    resolver: zodResolver(esquema),
    defaultValues: alergia ?? {
      nombre: '',
      tipo: 'OTRA',
      severidad: 'LEVE',
      descripcion: '',
    },
  })
  const guardar = useMutation({
    mutationFn: (valores: AlergiaInput) => alergia
      ? alergiasApi.actualizar(pacienteId, alergia.id, valores)
      : alergiasApi.crear(pacienteId, valores),
    onSuccess: () => {
      toast.success(alergia ? 'Alergia actualizada.' : 'Alergia registrada.')
      void queryClient.invalidateQueries({ queryKey: ['alergias', pacienteId] })
      onClose()
    },
    onError: (fallo) => setErrorGeneral(aplicarErroresDeApi(
      fallo,
      setError,
      CAMPOS,
      { alergia_duplicada: 'nombre' },
    )),
  })

  return <Modal titulo={alergia ? 'Editar alergia' : 'Registrar alergia'} onClose={onClose}>
    <form className="space-y-4" onSubmit={handleSubmit((valores) => guardar.mutate(valores))} noValidate>
      {error && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <Field id="alergia-nombre" label="Nombre" error={errors.nombre?.message}>
        <input id="alergia-nombre" className={inputClass} {...register('nombre')} />
      </Field>
      <Field id="alergia-tipo" label="Tipo" error={errors.tipo?.message}>
        <select id="alergia-tipo" className={inputClass} {...register('tipo')}>
          {TIPOS_ALERGIA.map((opcion) => <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>)}
        </select>
      </Field>
      <Field id="alergia-severidad" label="Severidad" error={errors.severidad?.message}>
        <select id="alergia-severidad" className={inputClass} {...register('severidad')}>
          {SEVERIDADES_ALERGIA.map((opcion) => <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>)}
        </select>
      </Field>
      <Field id="alergia-descripcion" label="Descripción" error={errors.descripcion?.message}>
        <textarea id="alergia-descripcion" rows={3} className={inputClass} {...register('descripcion')} />
      </Field>
      <div className="flex justify-end gap-2">
        <Button variante="secundario" onClick={onClose}>Cancelar</Button>
        <Button type="submit" cargando={guardar.isPending}>Guardar</Button>
      </div>
    </form>
  </Modal>
}
