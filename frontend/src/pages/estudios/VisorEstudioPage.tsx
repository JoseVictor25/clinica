import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { estudiosMedicosApi } from '@/api/modules/estudiosMedicos'
import { AsistenteGuia } from '@/components/asistente/AsistenteGuia'
import { VisorEstudioMedico } from '@/components/estudios/VisorEstudioMedico'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { inputClass } from '@/components/ui/styles'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'
import { esMedico } from '@/lib/roles'

export function VisorEstudioPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { estudioId: estudioIdTexto } = useParams()
  const estudioId = Number(estudioIdTexto)
  const { usuario } = useAuth()
  const medico = Boolean(usuario && esMedico(usuario))

  const [observacion, setObservacion] = useState('')
  const [blobUrl, setBlobUrl] = useState<string | null>(null)

  const estudioQuery = useQuery({
    queryKey: ['estudio-medico', estudioId],
    queryFn: () => estudiosMedicosApi.obtener(estudioId),
    enabled: Number.isInteger(estudioId) && estudioId > 0,
    retry: false,
  })

  const archivoQuery = useQuery({
    queryKey: ['estudio-medico', 'archivo', estudioId],
    queryFn: () => estudiosMedicosApi.descargarArchivoBlob(estudioId),
    enabled: Boolean(estudioQuery.data),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  useEffect(() => {
    if (estudioQuery.data) {
      setObservacion(estudioQuery.data.observacion_lectura ?? '')
    }
  }, [estudioQuery.data])

  useEffect(() => {
    if (!archivoQuery.data) {
      setBlobUrl(null)
      return
    }
    const url = URL.createObjectURL(archivoQuery.data)
    setBlobUrl(url)
    return () => {
      URL.revokeObjectURL(url)
    }
  }, [archivoQuery.data])

  const guardarLectura = useMutation({
    mutationFn: () =>
      estudiosMedicosApi.revisar(estudioId, {
        observacion_lectura: observacion.trim(),
      }),
    onSuccess: (actualizado) => {
      toast.success('Lectura del estudio guardada correctamente.')
      void queryClient.invalidateQueries({ queryKey: ['estudio-medico', estudioId] })
      if (actualizado.cita_id) {
        void queryClient.invalidateQueries({
          queryKey: ['estudios-medicos', 'cita', actualizado.cita_id],
        })
      }
    },
    onError: (err) => toast.error(mensajeDeError(err)),
  })

  const descargarArchivo = () => {
    if (!blobUrl || !estudioQuery.data) return
    const enlace = document.createElement('a')
    enlace.href = blobUrl
    enlace.download = estudioQuery.data.nombre_archivo
    document.body.appendChild(enlace)
    enlace.click()
    enlace.remove()
  }

  const cerrarVentana = () => {
    window.close()
    navigate(medico ? '/mi-agenda' : '/mi-informacion')
  }

  if (!Number.isInteger(estudioId) || estudioId <= 0) {
    return <p className="p-6 text-sm text-red-700">Identificador de estudio inválido.</p>
  }

  if (estudioQuery.isLoading) {
    return <p className="p-6 text-sm text-slate-600">Cargando estudio médico…</p>
  }

  if (estudioQuery.isError || !estudioQuery.data) {
    return (
      <div className="mx-auto max-w-xl space-y-3 p-6">
        <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          {estudioQuery.isError ? mensajeDeError(estudioQuery.error) : 'No se pudo cargar el estudio médico.'}
        </p>
        <div className="flex gap-2">
          <Button variante="secundario" onClick={() => void estudioQuery.refetch()}>Reintentar</Button>
          <Button variante="secundario" onClick={cerrarVentana}>Cerrar</Button>
        </div>
      </div>
    )
  }

  const estudio = estudioQuery.data

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-white px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">
            {estudio.tipo_estudio_display} · {estudio.nombre_archivo}
          </h1>
          <p className="text-xs text-slate-600">
            Paciente: {estudio.paciente_nombre} · Formato: {estudio.formato_display}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button data-guia-id="btn-visor-descargar" variante="secundario" disabled={!blobUrl} onClick={descargarArchivo}>
            Descargar
          </Button>
          <Button variante="secundario" onClick={cerrarVentana}>
            Cerrar ventana
          </Button>
        </div>
      </header>

      <main className="flex flex-1 flex-col gap-4 p-4 lg:flex-row">
        <section className={medico ? 'w-full lg:w-[70%]' : 'w-full'}>
          {archivoQuery.isLoading && (
            <div className="flex min-h-[520px] items-center justify-center rounded-lg border bg-white text-sm text-slate-600">
              Descargando archivo desde el servidor…
            </div>
          )}
          {archivoQuery.isError && (
            <div className="space-y-3 rounded-lg border bg-white p-6">
              <p role="alert" className="text-sm text-red-700">{mensajeDeError(archivoQuery.error)}</p>
              <Button variante="secundario" onClick={() => void archivoQuery.refetch()}>Reintentar</Button>
            </div>
          )}
          {archivoQuery.data && blobUrl && (
            <VisorEstudioMedico
              estudio={estudio}
              archivoBlob={archivoQuery.data}
              blobUrl={blobUrl}
              onDescargar={descargarArchivo}
            />
          )}
        </section>

        {medico && (
          <aside className="w-full space-y-4 rounded-lg border bg-white p-4 shadow-sm lg:w-[30%]">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Lectura e informe médico</h2>
              <p className="mt-1 text-xs text-slate-600">
                Registra tus conclusiones clínicas tras analizar el estudio.
              </p>
            </div>

            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault()
                guardarLectura.mutate()
              }}
            >
              <div className="space-y-1">
                <p className="text-sm font-medium text-slate-900">Estado de revisión:</p>
                <p className="text-sm text-slate-900">{estudio.estado_display}</p>
              </div>
              <Field id="estudio-observacion" label="Observación / Lectura">
                <textarea
                  id="estudio-observacion"
                  rows={8}
                  className={inputClass}
                  placeholder="Escribe hallazgos, interpretación o conclusiones del estudio..."
                  value={observacion}
                  onChange={(e) => setObservacion(e.target.value)}
                />
              </Field>
              <div className="flex justify-end">
                <Button data-guia-id="btn-visor-guardar-lectura" type="submit" cargando={guardarLectura.isPending}>
                  Guardar lectura
                </Button>
              </div>
            </form>

            {estudio.medico_nombre && (
              <p className="border-t pt-3 text-xs text-slate-500">
                Última lectura por: <span className="font-medium text-slate-700">{estudio.medico_nombre}</span>
              </p>
            )}
          </aside>
        )}
      </main>
      <AsistenteGuia />
    </div>
  )
}
