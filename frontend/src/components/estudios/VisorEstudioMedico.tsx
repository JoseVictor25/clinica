import { App, AppOptions, Index, ToolConfig, ViewConfig } from 'dwv'
import { Maximize2, Minimize2 } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'
import { TransformComponent, TransformWrapper } from 'react-zoom-pan-pinch'
import type { EstudioMedico } from '@/api/modules/estudiosMedicos'
import { Button } from '@/components/ui/Button'

interface Props {
  estudio: EstudioMedico
  archivoBlob: Blob
  blobUrl: string
  onDescargar: () => void
}

type HerramientaDicom = 'WindowLevel' | 'ZoomAndPan' | 'Scroll' | 'Draw'

const AYUDA_HERRAMIENTA: Record<HerramientaDicom, string> = {
  WindowLevel: 'Clic y arrastra para ajustar contraste y brillo (W/L).',
  ZoomAndPan: 'Rueda del mouse para zoom y arrastra para mover.',
  Scroll: 'Rueda del mouse o barra inferior para cambiar de corte.',
  Draw: 'Clic y arrastra sobre la imagen para trazar una regla.',
}

function claseBotonOscuro(activo = false): string {
  return [
    'rounded-md border px-3 py-1.5 text-xs font-medium transition-colors',
    'disabled:cursor-not-allowed disabled:opacity-40',
    activo
      ? 'border-blue-500 bg-blue-600 text-white'
      : 'border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700',
  ].join(' ')
}

function usePantallaCompleta(contenedorRef: RefObject<HTMLDivElement | null>) {
  const [enPantallaCompleta, setEnPantallaCompleta] = useState(false)

  useEffect(() => {
    const alCambiar = () => {
      const activo = document.fullscreenElement === contenedorRef.current
      setEnPantallaCompleta(activo)
      window.dispatchEvent(new Event('resize'))
      window.requestAnimationFrame(() => {
        window.dispatchEvent(new Event('resize'))
      })
    }

    document.addEventListener('fullscreenchange', alCambiar)
    return () => {
      document.removeEventListener('fullscreenchange', alCambiar)
    }
  }, [contenedorRef])

  const alternar = useCallback(async () => {
    const elemento = contenedorRef.current
    if (!elemento) return
    try {
      if (document.fullscreenElement === elemento) {
        await document.exitFullscreen()
      } else {
        await elemento.requestFullscreen()
      }
    } catch {
      /* el navegador puede bloquear fullscreen fuera de interacción */
    }
  }, [contenedorRef])

  return { enPantallaCompleta, alternar }
}

function BotonPantallaCompleta({
  activo,
  onClick,
}: {
  activo: boolean
  onClick: () => void
}) {
  return (
    <button
      data-guia-id="btn-visor-pantalla-completa"
      type="button"
      className={`${claseBotonOscuro(activo)} ml-auto inline-flex items-center gap-1.5`}
      onClick={onClick}
    >
      {activo ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
      <span>{activo ? 'Salir de pantalla completa' : 'Pantalla completa'}</span>
    </button>
  )
}

let contadorInstanciasDicom = 0

function VisorDicom({
  estudio,
  archivoBlob,
}: {
  estudio: EstudioMedico
  archivoBlob: Blob
}) {
  const visorRef = useRef<HTMLDivElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const appRef = useRef<App | null>(null)
  const { enPantallaCompleta, alternar } = usePantallaCompleta(visorRef)
  const [herramienta, setHerramienta] = useState<HerramientaDicom>('WindowLevel')
  const [estadoCarga, setEstadoCarga] = useState<'cargando' | 'listo' | 'error'>('cargando')
  const [errorDicom, setErrorDicom] = useState<string | null>(null)
  const [cortes, setCortes] = useState<{ actual: number; total: number; dim: number }>({
    actual: 1,
    total: 1,
    dim: 2,
  })

  const irACorte = useCallback((objetivo: number) => {
    const app = appRef.current
    if (!app) return
    try {
      const vc = app.getActiveLayerGroup()?.getActiveViewLayer()?.getViewController()
      if (!vc) return
      const size = vc.getImageSize()
      const totalZ = size.get(2) || 1
      const totalT = size.length() > 3 ? (size.get(3) || 1) : 1
      const dim = totalZ > 1 ? 2 : totalT > 1 ? 3 : 2
      const total = Math.max(size.get(dim) || 1, 1)
      if (total <= 1) return

      const clamped = Math.min(total, Math.max(1, objetivo))
      const valores = [...vc.getCurrentIndex().getValues()]
      valores[dim] = clamped - 1
      vc.setCurrentIndex(new Index(valores))
      setCortes({ actual: clamped, total, dim })
    } catch {
      /* ignorar si aún no está listo */
    }
  }, [])

  useEffect(() => {
    const contenedor = containerRef.current
    if (!contenedor) return

    let cancelado = false
    contenedor.innerHTML = ''

    // Cada montaje usa su propio nodo y su propio id sin guiones para que
    // una carga asíncrona previa (p. ej. StrictMode) nunca dibuje una capa fantasma.
    contadorInstanciasDicom += 1
    const layerId = `dwvLayer${contadorInstanciasDicom}`
    const nodoMontaje = document.createElement('div')
    nodoMontaje.id = layerId
    nodoMontaje.className = 'dwv-layer-group'
    contenedor.appendChild(nodoMontaje)

    const app = new App()
    appRef.current = app

    const actualizarCortes = () => {
      try {
        const vc = app.getActiveLayerGroup()?.getActiveViewLayer()?.getViewController()
        if (!vc) return
        const size = vc.getImageSize()
        const totalZ = size.get(2) || 1
        const totalT = size.length() > 3 ? (size.get(3) || 1) : 1
        const dim = totalZ > 1 ? 2 : totalT > 1 ? 3 : 2
        const total = Math.max(size.get(dim) || 1, 1)
        const indice = vc.getCurrentIndex().get(dim) ?? 0
        const actual = Math.min(total, Math.max(1, indice + 1))
        setCortes({ actual, total, dim })
      } catch {
        /* ignorar si aún no hay controlador */
      }
    }

    const viewConfig = new ViewConfig(layerId)
    const options = new AppOptions({ '*': [viewConfig] })
    options.tools = {
      Scroll: new ToolConfig(),
      ZoomAndPan: new ToolConfig(),
      WindowLevel: new ToolConfig(),
      Draw: new ToolConfig(['Ruler']),
    }

    try {
      app.init(options)

      app.addEventListener('load', () => {
        if (cancelado) return
        setEstadoCarga('listo')
        setErrorDicom(null)
        app.setTool('WindowLevel')
        setHerramienta('WindowLevel')
        actualizarCortes()
        window.requestAnimationFrame(() => {
          if (!cancelado) {
            app.onResize()
            actualizarCortes()
          }
        })
      })

      app.addEventListener('positionchange', () => {
        if (cancelado) return
        actualizarCortes()
      })

      app.addEventListener('loadend', () => {
        if (cancelado) return
        setEstadoCarga('listo')
        actualizarCortes()
      })

      app.addEventListener('error', () => {
        if (cancelado) return
        setEstadoCarga('error')
        setErrorDicom('No se pudo decodificar el archivo DICOM.')
      })

      const archivo = new File([archivoBlob], estudio.nombre_archivo, {
        type: 'application/dicom',
      })
      app.loadFiles([archivo])
    } catch {
      setEstadoCarga('error')
      setErrorDicom('Error al inicializar el visor DICOM.')
    }

    const manejarResize = () => {
      appRef.current?.onResize()
    }
    window.addEventListener('resize', manejarResize)

    return () => {
      cancelado = true
      window.removeEventListener('resize', manejarResize)
      try {
        app.reset()
      } catch {
        /* ignorar al desmontar */
      }
      nodoMontaje.remove()
      appRef.current = null
    }
  }, [archivoBlob, estudio.nombre_archivo])

  useEffect(() => {
    const contenedor = containerRef.current
    if (!contenedor) return
    const manejarWheel = (evento: WheelEvent) => {
      if (herramienta === 'Scroll' && cortes.total > 1) {
        evento.preventDefault()
        evento.stopPropagation()
        const delta = evento.deltaY > 0 ? 1 : -1
        irACorte(cortes.actual + delta)
        return
      }
      if (herramienta === 'ZoomAndPan') {
        evento.preventDefault()
      }
    }
    contenedor.addEventListener('wheel', manejarWheel, { passive: false, capture: true })
    return () => {
      contenedor.removeEventListener('wheel', manejarWheel, { capture: true })
    }
  }, [herramienta, cortes.actual, cortes.total, irACorte])

  const seleccionarHerramienta = (tool: HerramientaDicom) => {
    setHerramienta(tool)
    const app = appRef.current
    if (!app) return
    const layerGroup = app.getActiveLayerGroup()
    if (layerGroup) {
      if (tool === 'Draw') {
        const drawLayer = layerGroup.getDrawLayers()[0]
        if (drawLayer) {
          layerGroup.setActiveLayerById(drawLayer.getId())
        }
      } else {
        const viewLayer = layerGroup.getViewLayers()[0]
        if (viewLayer) {
          layerGroup.setActiveLayerById(viewLayer.getId())
        }
      }
    }
    app.setTool(tool)
    if (tool === 'Draw') {
      app.setToolFeatures({ shapeName: 'Ruler' })
    }
  }

  const restablecerVista = () => {
    const app = appRef.current
    if (!app) return
    app.resetDisplay()
    app.onResize()
  }

  return (
    <div
      ref={visorRef}
      className={`flex flex-col overflow-hidden border border-slate-800 bg-slate-900 shadow-sm ${
        enPantallaCompleta ? 'h-screen w-screen rounded-none' : 'rounded-lg'
      }`}
    >
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 bg-slate-900 px-3 py-2">
        <button
          data-guia-id="btn-visor-contraste"
          type="button"
          className={claseBotonOscuro(herramienta === 'WindowLevel')}
          onClick={() => seleccionarHerramienta('WindowLevel')}
        >
          Contraste (W/L)
        </button>
        <button
          data-guia-id="btn-visor-zoom"
          type="button"
          className={claseBotonOscuro(herramienta === 'ZoomAndPan')}
          onClick={() => seleccionarHerramienta('ZoomAndPan')}
        >
          Zoom / Mover
        </button>
        <button
          data-guia-id="btn-visor-cortes"
          type="button"
          className={claseBotonOscuro(herramienta === 'Scroll')}
          disabled={cortes.total <= 1}
          onClick={() => seleccionarHerramienta('Scroll')}
        >
          Cortes (Scroll)
        </button>
        <button
          data-guia-id="btn-visor-regla"
          type="button"
          className={claseBotonOscuro(herramienta === 'Draw')}
          onClick={() => seleccionarHerramienta('Draw')}
        >
          Regla / Medición
        </button>
        <button
          data-guia-id="btn-visor-restablecer"
          type="button"
          className={claseBotonOscuro(false)}
          onClick={restablecerVista}
        >
          Restablecer
        </button>
        <BotonPantallaCompleta activo={enPantallaCompleta} onClick={() => void alternar()} />
      </div>

      <div
        className={`relative w-full overflow-hidden bg-black ${
          enPantallaCompleta ? 'flex-1 min-h-0' : 'h-[74vh] min-h-[500px]'
        }`}
      >
        {estadoCarga === 'cargando' && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/70 text-sm text-white">
            Cargando estudio DICOM…
          </div>
        )}
        {errorDicom && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950 p-6 text-sm text-red-400">
            {errorDicom}
          </div>
        )}
        <div
          ref={containerRef}
          className={`h-full w-full ${herramienta === 'Draw' ? '' : 'dwv-modo-imagen'}`}
        />
        {estadoCarga === 'listo' && !errorDicom && (
          <p className="pointer-events-none absolute bottom-2.5 left-3 z-10 rounded bg-black/50 px-2 py-1 text-[11px] text-slate-200/80">
            {AYUDA_HERRAMIENTA[herramienta]}
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-300">
        {cortes.total > 1 ? (
          <>
            <button
              type="button"
              className={claseBotonOscuro(false)}
              disabled={cortes.actual <= 1}
              onClick={() => irACorte(cortes.actual - 1)}
            >
              ◀ Anterior
            </button>
            <input
              type="range"
              min={1}
              max={cortes.total}
              value={cortes.actual}
              onChange={(e) => irACorte(Number(e.target.value))}
              aria-label="Seleccionar corte DICOM"
              className="flex-1 min-w-[160px] accent-blue-500"
            />
            <button
              type="button"
              className={claseBotonOscuro(false)}
              disabled={cortes.actual >= cortes.total}
              onClick={() => irACorte(cortes.actual + 1)}
            >
              Siguiente ▶
            </button>
            <span className="ml-1 rounded-full bg-slate-800 px-2.5 py-1 font-medium text-blue-300">
              Corte {cortes.actual} / {cortes.total}
            </span>
          </>
        ) : (
          <span className="text-slate-400">Corte 1 / 1 (imagen única)</span>
        )}
      </div>
    </div>
  )
}

function VisorImagen({
  estudio,
  blobUrl,
}: {
  estudio: EstudioMedico
  blobUrl: string
}) {
  const visorRef = useRef<HTMLDivElement | null>(null)
  const { enPantallaCompleta, alternar } = usePantallaCompleta(visorRef)
  const [brillo, setBrillo] = useState(100)
  const [contraste, setContraste] = useState(100)
  const [negativo, setNegativo] = useState(false)

  const filtroCss = `brightness(${brillo}%) contrast(${contraste}%) invert(${negativo ? 100 : 0}%)`

  return (
    <TransformWrapper initialScale={1} minScale={0.5} maxScale={6} centerOnInit>
      {({ zoomIn, zoomOut, resetTransform }) => (
        <div
          ref={visorRef}
          className={`flex flex-col overflow-hidden border border-slate-800 bg-slate-900 shadow-sm ${
            enPantallaCompleta ? 'h-screen w-screen rounded-none' : 'h-full rounded-lg'
          }`}
        >
          <div className="flex flex-wrap items-center gap-3 border-b border-slate-800 bg-slate-900 px-3 py-2 text-sm">
            <div className="flex items-center gap-1.5">
              <button type="button" className={claseBotonOscuro(false)} onClick={() => zoomIn()}>Zoom +</button>
              <button type="button" className={claseBotonOscuro(false)} onClick={() => zoomOut()}>Zoom -</button>
            </div>
            <label className="flex items-center gap-2 text-xs text-slate-200">
              Brillo ({brillo}%)
              <input
                type="range"
                min={30}
                max={200}
                value={brillo}
                onChange={(e) => setBrillo(Number(e.target.value))}
                className="accent-blue-500"
              />
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-200">
              Contraste ({contraste}%)
              <input
                type="range"
                min={30}
                max={250}
                value={contraste}
                onChange={(e) => setContraste(Number(e.target.value))}
                className="accent-blue-500"
              />
            </label>
            <button
              type="button"
              className={claseBotonOscuro(negativo)}
              onClick={() => setNegativo((v) => !v)}
            >
              {negativo ? 'Negativo: ON' : 'Negativo'}
            </button>
            <button
              type="button"
              className={claseBotonOscuro(false)}
              onClick={() => {
                setBrillo(100)
                setContraste(100)
                setNegativo(false)
                resetTransform()
              }}
            >
              Restablecer
            </button>
            <BotonPantallaCompleta activo={enPantallaCompleta} onClick={() => void alternar()} />
          </div>

          <div
            className={`flex flex-1 items-center justify-center overflow-hidden bg-black ${
              enPantallaCompleta ? 'min-h-0' : 'min-h-[540px]'
            }`}
          >
            <TransformComponent
              wrapperStyle={{ width: '100%', height: '100%', minHeight: enPantallaCompleta ? '100%' : '520px' }}
              contentStyle={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <img
                src={blobUrl}
                alt={estudio.nombre_archivo}
                style={{ filter: filtroCss }}
                className={`${enPantallaCompleta ? 'max-h-[90vh]' : 'max-h-[75vh]'} max-w-full object-contain select-none`}
              />
            </TransformComponent>
          </div>
        </div>
      )}
    </TransformWrapper>
  )
}

function VisorPdf({
  estudio,
  blobUrl,
  onDescargar,
}: {
  estudio: EstudioMedico
  blobUrl: string
  onDescargar: () => void
}) {
  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-white p-2.5 text-sm shadow-sm">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Documento PDF · {estudio.nombre_archivo}
        </span>
        <Button variante="secundario" onClick={onDescargar}>Descargar PDF</Button>
      </div>
      <iframe
        title={estudio.nombre_archivo}
        src={blobUrl}
        className="h-[78vh] min-h-[520px] w-full rounded-lg border bg-white shadow-sm"
      />
    </div>
  )
}

export function VisorEstudioMedico({
  estudio,
  archivoBlob,
  blobUrl,
  onDescargar,
}: Props) {
  if (estudio.formato === 'DICOM') {
    return <VisorDicom estudio={estudio} archivoBlob={archivoBlob} />
  }
  if (estudio.formato === 'IMAGEN') {
    return <VisorImagen estudio={estudio} blobUrl={blobUrl} />
  }
  return <VisorPdf estudio={estudio} blobUrl={blobUrl} onDescargar={onDescargar} />
}
