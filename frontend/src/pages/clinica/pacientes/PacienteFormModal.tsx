import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { pacientesApi, SEXOS, type Paciente } from '@/api/modules/pacientes'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { aplicarErroresDeApi } from '@/lib/formErrors'

const hoy = new Date().toISOString().slice(0, 10)
const esquema = z.object({
  ci: z.string().trim().min(1, 'La CI es obligatoria.').max(20), nombre: z.string().trim().min(1, 'El nombre es obligatorio.').max(100), apellido: z.string().trim().min(1, 'El apellido es obligatorio.').max(100),
  sexo: z.enum(['M', 'F', 'OTRO']), fecha_nacimiento: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).refine((v) => v <= hoy, 'La fecha no puede ser futura.'), telefono: z.string().trim().min(1, 'El teléfono es obligatorio.').max(30),
  email: z.union([z.literal(''), z.string().email('Correo inválido.')]), estado: z.boolean(),
})
type Valores = z.infer<typeof esquema>
const CAMPOS = ['ci', 'nombre', 'apellido', 'sexo', 'fecha_nacimiento', 'telefono', 'email', 'estado'] as const

export function PacienteFormModal({ paciente, onClose }: { paciente: Paciente | null; onClose: () => void }) {
  const qc = useQueryClient(); const [error, setErrorGeneral] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Valores>({ resolver: zodResolver(esquema), defaultValues: paciente ?? { ci: '', nombre: '', apellido: '', sexo: 'OTRO', fecha_nacimiento: '', telefono: '', email: '', estado: true } })
  const guardar = useMutation({ mutationFn: (v: Valores) => paciente ? pacientesApi.actualizar(paciente.id, v) : pacientesApi.crear(v), onSuccess: () => { toast.success(paciente ? 'Paciente actualizado.' : 'Paciente registrado con su historia clínica.'); void qc.invalidateQueries({ queryKey: ['pacientes'] }); onClose() }, onError: (e) => setErrorGeneral(aplicarErroresDeApi(e, setError, CAMPOS, { ci_duplicada: 'ci', fecha_nacimiento_invalida: 'fecha_nacimiento' })) })
  return <Modal titulo={paciente ? 'Editar paciente' : 'Registrar paciente'} onClose={onClose}><form className="space-y-4" onSubmit={handleSubmit((v) => guardar.mutate(v))} noValidate>
    {error && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {(['ci','nombre','apellido','telefono','email'] as const).map((n) => <Field key={n} id={n} label={{ci:'CI',nombre:'Nombre',apellido:'Apellido',telefono:'Teléfono',email:'Correo electrónico'}[n]} error={errors[n]?.message}><input id={n} type={n === 'email' ? 'email' : n === 'telefono' ? 'tel' : 'text'} className={inputClass} {...register(n)} /></Field>)}
    <Field id="sexo" label="Sexo" error={errors.sexo?.message}><select id="sexo" className={inputClass} {...register('sexo')}>{SEXOS.map((s) => <option key={s.valor} value={s.valor}>{s.etiqueta}</option>)}</select></Field>
    <Field id="fecha_nacimiento" label="Fecha de nacimiento" error={errors.fecha_nacimiento?.message}><input id="fecha_nacimiento" type="date" max={hoy} className={inputClass} {...register('fecha_nacimiento')} /></Field>
    {paciente && <label className="flex gap-2 text-sm"><input type="checkbox" {...register('estado')} />Paciente activo</label>}
    <div className="flex justify-end gap-2"><Button variante="secundario" onClick={onClose}>Cancelar</Button><Button type="submit" cargando={guardar.isPending}>Guardar</Button></div>
  </form></Modal>
}
