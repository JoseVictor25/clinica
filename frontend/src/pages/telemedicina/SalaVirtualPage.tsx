import DailyIframe, { type DailyCall } from '@daily-co/daily-js'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useFieldArray, useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'
import { normalizarError } from '@/api/errors'
import { citasApi, type Cita } from '@/api/modules/citas'
import { consultasApi, type ConsultaCrearInput } from '@/api/modules/consultas'
import { estudiosMedicosApi } from '@/api/modules/estudiosMedicos'
import { recetasApi } from '@/api/modules/recetas'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { inputClass } from '@/components/ui/styles'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'
import { aplicarErroresDeApi } from '@/lib/formErrors'
import { esMedico } from '@/lib/roles'
import { RecetaDetalleModal } from '@/pages/medico/RecetaDetalleModal'
import { RecetaFormModal } from '@/pages/medico/RecetaFormModal'

let limpiezaDailyPendiente: Promise<void> = Promise.resolve()

function DailySala({
  link,
  displayName,
}: {
  link: string
  displayName: string
}) {
  const contenedorRef = useRef<HTMLDivElement | null>(null)
  const [finalizada, setFinalizada] = useState(false)
  const [errorCarga, setErrorCarga] = useState<string | null>(null)
  const [reintento, setReintento] = useState(0)

  useEffect(() => {
    if (finalizada || !contenedorRef.current) return
    let cancelado = false
    let callFrame: DailyCall | null = null
    setErrorCarga(null)

    const iniciar = async () => {
      try {
        await limpiezaDailyPendiente
        const instanciaPrevia = DailyIframe.getCallInstance()
        if (instanciaPrevia) {
          await instanciaPrevia.destroy()
        }
        if (cancelado || !contenedorRef.current) return

        contenedorRef.current.innerHTML = ''
        let unido = false
        let ultimoError: string | null = null

        callFrame = DailyIframe.createFrame(contenedorRef.current, {
          iframeStyle: {
            width: '100%',
            height: '100%',
            border: '0',
          },
          showLeaveButton: true,
          showFullscreenButton: true,
        })

        callFrame.on('joined-meeting', () => {
          unido = true
        })

        callFrame.on('left-meeting', () => {
          if (cancelado) return
          const frame = callFrame
          callFrame = null
          if (frame) {
            limpiezaDailyPendiente = frame.destroy().catch(() => {})
          }
          if (unido) {
            setFinalizada(true)
          } else {
            setErrorCarga(
              ultimoError || 'La sala se cerró antes de completar la conexión a Daily.co.',
            )
          }
        })

        callFrame.on('error', (evento) => {
          if (cancelado) return
          const msg = (evento as { errorMsg?: string; error?: { msg?: string } } | undefined)?.errorMsg
            ?? (evento as { error?: { msg?: string } } | undefined)?.error?.msg
          ultimoError = msg ? `Daily.co: ${msg}` : 'No se pudo conectar a la videollamada en Daily.co.'
          setErrorCarga(ultimoError)
        })

        await callFrame.join({
          url: link,
          userName: displayName,
          startVideoOff: false,
          startAudioOff: false,
        })
      } catch (err) {
        if (!cancelado) {
          const detalle = err instanceof Error ? err.message : ''
          setErrorCarga(
            detalle
              ? `Error al inicializar la sala de videollamada: ${detalle}`
              : 'Error al inicializar la sala de videollamada.',
          )
        }
      }
    }

    void iniciar()

    return () => {
      cancelado = true
      if (callFrame) {
        const frame = callFrame
        callFrame = null
        limpiezaDailyPendiente = frame.destroy().catch(() => {})
      }
    }
  }, [link, displayName, finalizada, reintento])

  if (finalizada) {
    return (
      <div className="flex h-full min-h-[480px] flex-col items-center justify-center gap-4 rounded-lg border bg-white p-6 text-center shadow-sm">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold text-slate-900">Videollamada finalizada</h2>
          <p className="text-sm text-slate-600">
            Has finalizado la videollamada. Puedes volver a conectarte si lo necesitas.
          </p>
        </div>
        <Button onClick={() => setFinalizada(false)}>Volver a la videollamada</Button>
      </div>
    )
  }

  if (errorCarga) {
    return (
      <div className="flex h-full min-h-[480px] flex-col items-center justify-center gap-3 rounded-lg border bg-white p-6 text-center shadow-sm">
        <p className="text-sm text-red-700">{errorCarga}</p>
        <Button variante="secundario" onClick={() => setReintento((n) => n + 1)}>Reintentar</Button>
      </div>
    )
  }

  return (
    <div
      ref={contenedorRef}
      className="h-full min-h-[480px] w-full overflow-hidden rounded-lg border bg-black shadow-sm"
    />
  )
}

const medicamentoSchema = z.object({
  nombre_medicamento: z.string().trim().min(1, 'El medicamento es obligatorio.').max(150, 'Máximo 150 caracteres.'),
  dosis: z.string().trim().min(1, 'La dosis es obligatoria.').max(50, 'Máximo 50 caracteres.'),
  frecuencia: z.string().trim().min(1, 'La frecuencia es obligatoria.').max(50, 'Máximo 50 caracteres.'),
  duracion: z.string().trim().min(1, 'La duración es obligatoria.').max(50, 'Máximo 50 caracteres.'),
})

const esquemaConsulta = z.object({
  motivo: z.string().trim().min(1, 'El motivo es obligatorio.'),
  observacion: z.string().trim().min(1, 'La observación es obligatoria.'),
  diagnostico: z.string().trim().min(1, 'El diagnóstico es obligatorio.'),
  indicaciones: z.string().trim(),
  medicamentos: z.array(medicamentoSchema),
})

type ValoresConsulta = z.infer<typeof esquemaConsulta>
const CAMPOS_CONSULTA = ['motivo', 'observacion', 'diagnostico'] as const
const FILA_MEDICAMENTO = { nombre_medicamento: '', dosis: '', frecuencia: '', duracion: '' }

function PanelConsultaRegistrada({ consultaId }: { consultaId: number }) {
  const queryClient = useQueryClient()
  const [emitiendoReceta, setEmitiendoReceta] = useState(false)
  const [recetaSeleccionada, setRecetaSeleccionada] = useState<number | null>(null)

  const consultaQuery = useQuery({
    queryKey: ['consulta', consultaId],
    queryFn: () => consultasApi.obtener(consultaId),
  })

  if (consultaQuery.isLoading) {
    return <p className="text-sm text-slate-600">Cargando consulta registrada…</p>
  }

  if (consultaQuery.isError || !consultaQuery.data) {
    return (
      <div className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
        <p>{consultaQuery.isError ? mensajeDeError(consultaQuery.error) : 'No se pudo cargar la consulta.'}</p>
        <Button variante="secundario" onClick={() => void consultaQuery.refetch()}>Reintentar</Button>
      </div>
    )
  }

  const consulta = consultaQuery.data

  return (
    <>
      <div className="space-y-4">
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-900">
          <p className="font-medium">Consulta registrada correctamente.</p>
          <Link
            to={`/pacientes/${consulta.paciente_id}/historial`}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-block rounded-md border border-green-700 px-3 py-1 text-xs font-medium text-green-800 hover:bg-green-100"
          >
            Ver historial del paciente
          </Link>
        </div>

        <dl className="space-y-2 rounded-md border border-slate-200 p-3 text-sm">
          <div>
            <dt className="text-xs font-medium text-slate-500">Motivo</dt>
            <dd className="whitespace-pre-wrap text-slate-800">{consulta.motivo}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-slate-500">Observación</dt>
            <dd className="whitespace-pre-wrap text-slate-800">{consulta.observacion}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-slate-500">Diagnóstico</dt>
            <dd className="whitespace-pre-wrap text-slate-800">{consulta.diagnostico}</dd>
          </div>
        </dl>

        <section className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-900">Recetas emitidas</h3>
            <Button onClick={() => setEmitiendoReceta(true)}>Agregar receta</Button>
          </div>

          {consulta.recetas.length === 0 ? (
            <p className="rounded bg-slate-50 p-3 text-xs text-slate-600">
              Esta consulta todavía no tiene recetas.
            </p>
          ) : (
            <div className="space-y-2">
              {consulta.recetas.map((receta) => (
                <article
                  key={receta.id}
                  className="flex items-center justify-between gap-2 rounded border border-slate-200 p-2.5 text-xs"
                >
                  <div>
                    <p className="font-medium text-slate-900">Receta #{receta.id}</p>
                    <p className="text-slate-600">
                      {receta.cantidad_medicamentos} medicamento(s) · {receta.indicaciones || 'Sin indicaciones'}
                    </p>
                  </div>
                  <Button variante="secundario" onClick={() => setRecetaSeleccionada(receta.id)}>
                    Ver
                  </Button>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>

      {emitiendoReceta && (
        <RecetaFormModal
          consulta={consulta}
          onClose={() => setEmitiendoReceta(false)}
          onSuccess={(receta) => {
            setEmitiendoReceta(false)
            setRecetaSeleccionada(receta.id)
            void queryClient.invalidateQueries({ queryKey: ['consulta', consultaId] })
          }}
        />
      )}

      {recetaSeleccionada !== null && (
        <RecetaDetalleModal
          recetaId={recetaSeleccionada}
          onClose={() => setRecetaSeleccionada(null)}
        />
      )}
    </>
  )
}

function FormularioConsultaSala({ cita, onRegistrada }: { cita: Cita; onRegistrada: () => void }) {
  const queryClient = useQueryClient()
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)
  const { register, control, handleSubmit, reset, setError, formState: { errors } } = useForm<ValoresConsulta>({
    resolver: zodResolver(esquemaConsulta),
    defaultValues: {
      motivo: cita.motivo,
      observacion: '',
      diagnostico: '',
      indicaciones: '',
      medicamentos: [],
    },
  })

  const { fields, append, remove } = useFieldArray({ control, name: 'medicamentos' })

  useEffect(() => {
    reset({
      motivo: cita.motivo,
      observacion: '',
      diagnostico: '',
      indicaciones: '',
      medicamentos: [],
    })
  }, [cita.id, cita.motivo, reset])

  const guardar = useMutation({
    mutationFn: async (valores: ValoresConsulta) => {
      const consulta = await consultasApi.crear({
        cita_id: cita.id,
        motivo: valores.motivo,
        observacion: valores.observacion,
        diagnostico: valores.diagnostico,
      } as ConsultaCrearInput)

      if (valores.medicamentos.length > 0) {
        try {
          await recetasApi.crearReceta(consulta.id, {
            indicaciones: valores.indicaciones,
            medicamentos: valores.medicamentos,
          })
        } catch (errReceta) {
          toast.error(`La consulta se guardó, pero la receta no pudo emitirse: ${mensajeDeError(errReceta)}`)
          return consulta
        }
      }

      return consulta
    },
    onSuccess: (_consulta, valores) => {
      toast.success(
        valores.medicamentos.length > 0
          ? 'Consulta y receta registradas correctamente.'
          : 'Consulta registrada y cita marcada como atendida.',
      )
      void queryClient.invalidateQueries({ queryKey: ['mi-agenda'] })
      void queryClient.invalidateQueries({ queryKey: ['sala-virtual', cita.id] })
      onRegistrada()
    },
    onError: (fallo) => {
      const error = normalizarError(fallo)
      if (error.code === 'consulta_ya_registrada') {
        toast.error('La cita ya tiene una consulta registrada.')
        void queryClient.invalidateQueries({ queryKey: ['sala-virtual', cita.id] })
        return
      }
      setErrorGeneral(aplicarErroresDeApi(fallo, setError, CAMPOS_CONSULTA))
    },
  })

  if (cita.consulta_id !== null) {
    return <PanelConsultaRegistrada consultaId={cita.consulta_id} />
  }

  if (cita.estado !== 'CONFIRMADA') {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        La cita está en estado <strong>{cita.estado_display}</strong>. Debe estar <strong>Confirmada</strong> para registrar la consulta.
      </div>
    )
  }

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((valores) => {
        setErrorGeneral(null)
        guardar.mutate(valores)
      })}
      noValidate
    >
      {errorGeneral && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{errorGeneral}</p>}

      <Field id="sala-motivo" label="Motivo de consulta" error={errors.motivo?.message}>
        <textarea id="sala-motivo" rows={2} className={inputClass} {...register('motivo')} />
      </Field>
      <Field id="sala-observacion" label="Observaciones" error={errors.observacion?.message}>
        <textarea id="sala-observacion" rows={3} className={inputClass} {...register('observacion')} />
      </Field>
      <Field id="sala-diagnostico" label="Diagnóstico" error={errors.diagnostico?.message}>
        <textarea id="sala-diagnostico" rows={3} className={inputClass} {...register('diagnostico')} />
      </Field>

      <div className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-slate-900">Receta médica (opcional)</h3>
          <Button
            variante="secundario"
            onClick={() => append({ ...FILA_MEDICAMENTO })}
          >
            Agregar medicamento
          </Button>
        </div>

        {fields.length > 0 && (
          <Field id="sala-indicaciones" label="Indicaciones generales" error={errors.indicaciones?.message}>
            <textarea id="sala-indicaciones" rows={2} className={inputClass} {...register('indicaciones')} />
          </Field>
        )}

        {fields.map((field, indice) => (
          <fieldset key={field.id} className="grid gap-2 rounded border border-slate-200 bg-white p-3 sm:grid-cols-2">
            <legend className="px-1 text-xs font-medium text-slate-700">Medicamento {indice + 1}</legend>
            <Field
              id={`sala-med-${indice}-nombre`}
              label="Nombre"
              error={errors.medicamentos?.[indice]?.nombre_medicamento?.message}
            >
              <input id={`sala-med-${indice}-nombre`} className={inputClass} {...register(`medicamentos.${indice}.nombre_medicamento`)} />
            </Field>
            <Field
              id={`sala-med-${indice}-dosis`}
              label="Dosis"
              error={errors.medicamentos?.[indice]?.dosis?.message}
            >
              <input id={`sala-med-${indice}-dosis`} className={inputClass} {...register(`medicamentos.${indice}.dosis`)} />
            </Field>
            <Field
              id={`sala-med-${indice}-frecuencia`}
              label="Frecuencia"
              error={errors.medicamentos?.[indice]?.frecuencia?.message}
            >
              <input id={`sala-med-${indice}-frecuencia`} className={inputClass} {...register(`medicamentos.${indice}.frecuencia`)} />
            </Field>
            <Field
              id={`sala-med-${indice}-duracion`}
              label="Duración"
              error={errors.medicamentos?.[indice]?.duracion?.message}
            >
              <input id={`sala-med-${indice}-duracion`} className={inputClass} {...register(`medicamentos.${indice}.duracion`)} />
            </Field>
            <div className="sm:col-span-2 flex justify-end">
              <Button variante="peligro" onClick={() => remove(indice)}>Quitar</Button>
            </div>
          </fieldset>
        ))}
      </div>

      <div className="flex justify-end">
        <Button type="submit" cargando={guardar.isPending}>Guardar consulta</Button>
      </div>
    </form>
  )
}

function EstudiosCitaSala({ citaId }: { citaId: number }) {
  const estudiosQuery = useQuery({
    queryKey: ['estudios-medicos', 'cita', citaId],
    queryFn: () => estudiosMedicosApi.listar({ cita_id: citaId, page_size: 50 }),
  })

  return (
    <section className="mb-4 space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900">Estudios médicos de esta cita</h3>
        <button
          type="button"
          className="text-xs font-medium text-blue-700 hover:underline"
          onClick={() => void estudiosQuery.refetch()}
        >
          Actualizar
        </button>
      </div>
      {estudiosQuery.isLoading && (
        <p className="text-xs text-slate-500">Cargando estudios…</p>
      )}
      {estudiosQuery.isError && (
        <p className="text-xs text-red-700">{mensajeDeError(estudiosQuery.error)}</p>
      )}
      {estudiosQuery.data && estudiosQuery.data.results.length === 0 && (
        <p className="text-xs text-slate-500">
          El paciente aún no ha subido estudios para esta cita.
        </p>
      )}
      {estudiosQuery.data && estudiosQuery.data.results.length > 0 && (
        <div className="space-y-1.5">
          {estudiosQuery.data.results.map((estudio) => (
            <button
              key={estudio.id}
              type="button"
              onClick={() =>
                window.open(`/estudios/${estudio.id}/visor`, '_blank', 'noopener,noreferrer')
              }
              className="flex w-full items-center justify-between gap-2 rounded border border-slate-200 bg-white px-3 py-2 text-left text-xs hover:border-blue-400 hover:bg-blue-50"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-slate-900">{estudio.nombre_archivo}</p>
                <p className="text-slate-600">
                  {estudio.tipo_estudio_display} · {estudio.formato_display} · {estudio.estado_display}
                </p>
              </div>
              <span className="shrink-0 font-medium text-blue-700">Abrir visor</span>
            </button>
          ))}
        </div>
      )}
    </section>
  )
}

export function SalaVirtualPage() {
  const navigate = useNavigate()
  const { citaId: citaIdTexto } = useParams()
  const citaId = Number(citaIdTexto)
  const { usuario } = useAuth()
  const medico = Boolean(usuario && esMedico(usuario))

  const query = useQuery({
    queryKey: ['sala-virtual', citaId],
    queryFn: () => citasApi.obtenerSalaVirtual(citaId),
    enabled: Number.isInteger(citaId) && citaId > 0,
    retry: false,
  })

  const cerrarPestanaOVolver = () => {
    window.close()
    navigate(medico ? '/mi-agenda' : '/mi-informacion')
  }

  if (!Number.isInteger(citaId) || citaId <= 0) {
    return <p className="p-6 text-sm text-red-700">Identificador de cita inválido.</p>
  }

  if (query.isLoading) {
    return <p className="p-6 text-sm text-slate-600">Cargando sala virtual…</p>
  }

  if (query.isError || !query.data) {
    return (
      <div className="mx-auto max-w-xl space-y-3 p-6">
        <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          {query.isError ? mensajeDeError(query.error) : 'No se pudo cargar la sala virtual.'}
        </p>
        <div className="flex gap-2">
          <Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button>
          <Button variante="secundario" onClick={cerrarPestanaOVolver}>Volver</Button>
        </div>
      </div>
    )
  }

  const cita = query.data
  const nombreParticipante = medico
    ? (cita.medico_nombre || usuario?.username || 'Médico')
    : (cita.paciente_nombre || usuario?.username || 'Paciente')

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-white px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">Sala virtual de telemedicina</h1>
          <p className="text-xs text-slate-600">
            {cita.fecha} · {cita.hora.slice(0, 5)} · {cita.especialidad_nombre} ·{' '}
            {medico ? `Paciente: ${cita.paciente_nombre}` : `Médico: ${cita.medico_nombre}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variante="peligro" onClick={cerrarPestanaOVolver}>
            Cancelar videollamada
          </Button>
        </div>
      </header>

      <main className="flex flex-1 flex-col gap-4 p-4 lg:flex-row">
        <section className={medico ? 'h-[70vh] w-full lg:h-[calc(100vh-6.5rem)] lg:w-[60%]' : 'h-[calc(100vh-6.5rem)] w-full'}>
          {cita.link_videollamada ? (
            <DailySala
              link={cita.link_videollamada}
              displayName={nombreParticipante}
            />
          ) : (
            <div className="flex h-full items-center justify-center rounded-lg border bg-white p-6 text-sm text-slate-600">
              No hay enlace de videollamada disponible para esta cita.
            </div>
          )}
        </section>

        {medico && (
          <aside className="w-full overflow-y-auto rounded-lg border bg-white p-4 shadow-sm lg:max-h-[calc(100vh-6.5rem)] lg:w-[40%]">
            <h2 className="text-base font-semibold text-slate-900">Consulta y recetas</h2>
            <div className="my-3 grid gap-1 rounded-md bg-slate-50 p-3 text-xs text-slate-700">
              <p><span className="font-medium">Paciente:</span> {cita.paciente_nombre}</p>
              <p><span className="font-medium">Estado de la cita:</span> {cita.estado_display}</p>
              <p><span className="font-medium">Motivo inicial:</span> {cita.motivo}</p>
            </div>
            <EstudiosCitaSala citaId={cita.id} />
            <FormularioConsultaSala cita={cita} onRegistrada={() => void query.refetch()} />
          </aside>
        )}
      </main>
    </div>
  )
}
