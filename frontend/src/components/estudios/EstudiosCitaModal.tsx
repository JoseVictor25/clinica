import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { toast } from 'sonner'
import {
  estudiosMedicosApi,
  TIPOS_ESTUDIO,
  type EstudioMedico,
  type TipoEstudio,
} from '@/api/modules/estudiosMedicos'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { mensajeDeError } from '@/lib/errorMessages'

const ESTADOS_CERRADOS = new Set(['ATENDIDA', 'CANCELADA', 'NO_ASISTIO'])

export interface CitaParaEstudios {
  id: number
  fecha: string
  hora: string
  estado: string
  estado_display?: string
  paciente_nombre?: string
}

export function EstudiosCitaModal({
  cita,
  onClose,
}: {
  cita: CitaParaEstudios
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const inputArchivoRef = useRef<HTMLInputElement | null>(null)
  const [tipoEstudio, setTipoEstudio] = useState<TipoEstudio>('RADIOGRAFIA')
  const [archivo, setArchivo] = useState<File | null>(null)

  const citaCerrada = ESTADOS_CERRADOS.has(cita.estado)

  const query = useQuery({
    queryKey: ['estudios-medicos', 'cita', cita.id],
    queryFn: () => estudiosMedicosApi.listar({ cita_id: cita.id, page_size: 100 }),
  })

  const subir = useMutation({
    mutationFn: () => {
      if (!archivo) throw new Error('Selecciona un archivo.')
      return estudiosMedicosApi.subir({
        tipo_estudio: tipoEstudio,
        cita_id: cita.id,
        archivo,
      })
    },
    onSuccess: () => {
      toast.success('Estudio médico subido correctamente.')
      setArchivo(null)
      if (inputArchivoRef.current) inputArchivoRef.current.value = ''
      void queryClient.invalidateQueries({ queryKey: ['estudios-medicos', 'cita', cita.id] })
    },
    onError: (err) => toast.error(mensajeDeError(err)),
  })

  const eliminar = useMutation({
    mutationFn: (id: number) => estudiosMedicosApi.eliminar(id),
    onSuccess: () => {
      toast.success('Estudio eliminado.')
      void queryClient.invalidateQueries({ queryKey: ['estudios-medicos', 'cita', cita.id] })
    },
    onError: (err) => toast.error(mensajeDeError(err)),
  })

  const abrirVisor = (estudio: EstudioMedico) => {
    window.open(`/estudios/${estudio.id}/visor`, '_blank', 'noopener,noreferrer')
  }

  return (
    <Modal titulo={`Estudios médicos · Cita ${cita.fecha} ${cita.hora.slice(0, 5)}`} onClose={onClose}>
      <div className="space-y-5">
        {cita.paciente_nombre && (
          <p className="text-sm text-slate-700">
            <span className="font-medium">Paciente:</span> {cita.paciente_nombre}
          </p>
        )}

        {citaCerrada ? (
          <p className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Esta cita ya está en estado <strong>{cita.estado_display ?? cita.estado}</strong>. No es posible subir ni modificar estudios; solo puedes consultar los archivos cargados.
          </p>
        ) : (
          <form
            className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-3"
            onSubmit={(e) => {
              e.preventDefault()
              if (!archivo) {
                toast.error('Selecciona un archivo (.dcm, .png, .jpg o .pdf).')
                return
              }
              subir.mutate()
            }}
          >
            <h3 className="text-sm font-semibold text-slate-900">Subir nuevo estudio</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field id="nuevo-tipo-estudio" label="Tipo de estudio">
                <select
                  id="nuevo-tipo-estudio"
                  className={inputClass}
                  value={tipoEstudio}
                  onChange={(e) => setTipoEstudio(e.target.value as TipoEstudio)}
                >
                  {TIPOS_ESTUDIO.map((t) => (
                    <option key={t.valor} value={t.valor}>{t.etiqueta}</option>
                  ))}
                </select>
              </Field>
              <Field id="nuevo-archivo-estudio" label="Archivo (.dcm, .png, .jpg, .pdf)">
                <input
                  ref={inputArchivoRef}
                  id="nuevo-archivo-estudio"
                  type="file"
                  accept=".dcm,.png,.jpg,.jpeg,.pdf"
                  className={inputClass}
                  onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
                />
              </Field>
            </div>
            <div className="flex justify-end">
              <Button type="submit" cargando={subir.isPending} disabled={!archivo}>
                Subir estudio
              </Button>
            </div>
          </form>
        )}

        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-900">Estudios cargados</h3>
          {query.isLoading && <p className="text-sm text-slate-600">Cargando estudios…</p>}
          {query.isError && (
            <p role="alert" className="text-sm text-red-700">{mensajeDeError(query.error)}</p>
          )}
          {query.data && query.data.results.length === 0 && (
            <p className="rounded bg-slate-50 p-3 text-sm text-slate-500">
              Aún no hay estudios subidos para esta cita.
            </p>
          )}
          {query.data?.results.map((estudio) => (
            <article
              key={estudio.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-200 bg-white p-3 text-sm"
            >
              <div className="space-y-0.5">
                <p className="font-medium text-slate-900">{estudio.nombre_archivo}</p>
                <p className="text-xs text-slate-600">
                  {estudio.tipo_estudio_display} · {estudio.formato_display} · {estudio.estado_display}
                </p>
                {estudio.observacion_lectura && (
                  <p className="mt-1 text-xs text-slate-700">
                    <span className="font-medium">Lectura:</span> {estudio.observacion_lectura}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button variante="secundario" onClick={() => abrirVisor(estudio)}>
                  Ver estudio
                </Button>
                {estudio.puede_modificar && (
                  <Button
                    variante="peligro"
                    cargando={eliminar.isPending}
                    onClick={() => eliminar.mutate(estudio.id)}
                  >
                    Eliminar
                  </Button>
                )}
              </div>
            </article>
          ))}
        </div>

        <div className="flex justify-end">
          <Button variante="secundario" onClick={onClose}>Cerrar</Button>
        </div>
      </div>
    </Modal>
  )
}
