import { useMutation } from '@tanstack/react-query'
import { Eye, HelpCircle, Maximize2, Minus, Send, Sparkles, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useLocation } from 'react-router-dom'
import { asistenteApi, type AsistenteRespuesta } from '@/api/modules/asistente'
import { useAuth } from '@/hooks/useAuth'
import { limpiarResaltadoGuia, resaltarElementoGuia } from '@/lib/guiaHighlight'

type EstadoPanel = 'cerrado' | 'abierto' | 'minimizado'

interface MensajeChat {
  id: number
  autor: 'usuario' | 'asistente' | 'error'
  texto: string
  respuesta?: AsistenteRespuesta
  otraInterfaz?: boolean
}

const ANCHO_PANEL = 380
const ALTO_PANEL = 500
const ALTO_CABECERA = 56
const MARGEN = 16

function normalizarRuta(ruta: string): string {
  const limpia = ruta.trim().replace(/\/+$/, '')
  return limpia === '' ? '/' : limpia
}

function rutasCoinciden(rutaObjetivo: string | null, rutaActual: string): boolean {
  if (!rutaObjetivo) return false
  const objetivo = normalizarRuta(rutaObjetivo)
  const actual = normalizarRuta(rutaActual)
  if (objetivo === actual) return true
  return objetivo !== '/' && actual.startsWith(`${objetivo}/`)
}

function acotarPosicion(x: number, y: number, ancho: number, alto: number) {
  const maxX = Math.max(MARGEN, window.innerWidth - ancho - MARGEN)
  const maxY = Math.max(MARGEN, window.innerHeight - alto - MARGEN)
  return {
    x: Math.min(maxX, Math.max(MARGEN, x)),
    y: Math.min(maxY, Math.max(MARGEN, y)),
  }
}

export function AsistenteGuia() {
  const { usuario } = useAuth()
  const location = useLocation()

  const [estado, setEstado] = useState<EstadoPanel>('cerrado')
  const [entrada, setEntrada] = useState('')
  const [mensajes, setMensajes] = useState<MensajeChat[]>([])
  const [posicion, setPosicion] = useState(() =>
    acotarPosicion(
      window.innerWidth - ANCHO_PANEL - 24,
      window.innerHeight - ALTO_PANEL - 24,
      ANCHO_PANEL,
      ALTO_PANEL,
    ),
  )

  const arrastreRef = useRef<{
    activo: boolean
    offsetX: number
    offsetY: number
    ancho: number
    alto: number
    movio: boolean
  }>({ activo: false, offsetX: 0, offsetY: 0, ancho: ANCHO_PANEL, alto: ALTO_PANEL, movio: false })
  const finMensajesRef = useRef<HTMLDivElement | null>(null)
  const contadorIdRef = useRef(1)

  const aplicarResaltadoRespuesta = useCallback(
    (respuesta: AsistenteRespuesta, rutaActual: string) => {
      if (!respuesta.id_accion && !respuesta.id_menu) return
      const coincideRuta = rutasCoinciden(respuesta.ruta_objetivo, rutaActual)

      if (coincideRuta && respuesta.id_accion) {
        const resaltado = resaltarElementoGuia(respuesta.id_accion, 5000)
        if (!resaltado) {
          // Si la acción está dentro de una pestaña aún no activa del portal del paciente,
          // resaltar primero la pestaña correspondiente antes de caer al menú lateral.
          if (
            respuesta.id_accion === 'btn-fila-portal-estudios' ||
            respuesta.id_accion === 'btn-fila-portal-sala'
          ) {
            if (resaltarElementoGuia('tab-portal-citas', 5000)) return
          } else if (
            respuesta.id_accion === 'btn-fila-portal-receta' ||
            respuesta.id_accion === 'btn-fila-portal-ver-estudio'
          ) {
            if (resaltarElementoGuia('tab-portal-consultas', 5000)) return
          }
          if (respuesta.id_menu) {
            resaltarElementoGuia(respuesta.id_menu, 5000)
          }
        }
        return
      }
      if (respuesta.id_menu) {
        resaltarElementoGuia(respuesta.id_menu, 5000)
      }
    },
    [],
  )

  const consultarMutation = useMutation({
    mutationFn: (texto: string) => {
      const pestanaActiva = document
        .querySelector<HTMLElement>('[data-guia-pestana-activa]')
        ?.getAttribute('data-guia-pestana-activa')
        ?.trim()
      const contextoRuta = pestanaActiva
        ? `${location.pathname} | pestaña: ${pestanaActiva}`
        : location.pathname
      return asistenteApi.consultar(texto, contextoRuta)
    },
    onSuccess: (respuesta) => {
      const otraInterfaz =
        respuesta.ruta_objetivo !== null &&
        !rutasCoinciden(respuesta.ruta_objetivo, location.pathname)

      contadorIdRef.current += 1
      setMensajes((prev) => [
        ...prev,
        {
          id: contadorIdRef.current,
          autor: 'asistente',
          texto: respuesta.explicacion,
          respuesta,
          otraInterfaz,
        },
      ])
      aplicarResaltadoRespuesta(respuesta, location.pathname)
    },
    onError: () => {
      contadorIdRef.current += 1
      setMensajes((prev) => [
        ...prev,
        {
          id: contadorIdRef.current,
          autor: 'error',
          texto:
            'El asistente guía no está disponible temporalmente. Puedes continuar trabajando con normalidad.',
        },
      ])
    },
  })

  useEffect(() => {
    finMensajesRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes, consultarMutation.isPending])

  useEffect(() => {
    const alRedimensionar = () => {
      const alto = estado === 'minimizado' ? ALTO_CABECERA : ALTO_PANEL
      setPosicion((pos) => acotarPosicion(pos.x, pos.y, ANCHO_PANEL, alto))
    }
    window.addEventListener('resize', alRedimensionar)
    return () => window.removeEventListener('resize', alRedimensionar)
  }, [estado])

  useEffect(() => {
    const alMover = (evento: PointerEvent) => {
      const d = arrastreRef.current
      if (!d.activo) return
      d.movio = true
      setPosicion(
        acotarPosicion(evento.clientX - d.offsetX, evento.clientY - d.offsetY, d.ancho, d.alto),
      )
    }
    const alSoltar = () => {
      arrastreRef.current.activo = false
    }
    window.addEventListener('pointermove', alMover)
    window.addEventListener('pointerup', alSoltar)
    return () => {
      window.removeEventListener('pointermove', alMover)
      window.removeEventListener('pointerup', alSoltar)
    }
  }, [])

  useEffect(() => {
    return () => limpiarResaltadoGuia()
  }, [])

  // Precondición: usuario autenticado con clínica y rol activo.
  if (!usuario || usuario.esAdminSistema || !usuario.clinicaId || usuario.roles.length === 0) {
    return null
  }

  const iniciarArrastre = (
    evento: React.PointerEvent<HTMLElement>,
    ancho: number,
    alto: number,
  ) => {
    evento.preventDefault()
    arrastreRef.current = {
      activo: true,
      offsetX: evento.clientX - posicion.x,
      offsetY: evento.clientY - posicion.y,
      ancho,
      alto,
      movio: false,
    }
  }

  const abrirPanel = () => {
    setPosicion((pos) => acotarPosicion(pos.x, pos.y, ANCHO_PANEL, ALTO_PANEL))
    setEstado('abierto')
  }

  const minimizarPanel = () => {
    setEstado('minimizado')
  }

  const cerrarPanel = () => {
    limpiarResaltadoGuia()
    setEstado('cerrado')
  }

  const enviarConsulta = (evento: React.FormEvent) => {
    evento.preventDefault()
    const texto = entrada.trim()
    if (!texto || consultarMutation.isPending) return

    contadorIdRef.current += 1
    setMensajes((prev) => [
      ...prev,
      { id: contadorIdRef.current, autor: 'usuario', texto },
    ])
    setEntrada('')
    consultarMutation.mutate(texto)
  }

  return createPortal(
    <div className="pointer-events-none fixed inset-0 z-[9999]">
      {estado === 'cerrado' && (
        <button
          type="button"
          onClick={abrirPanel}
          aria-label="Abrir Asistente Guía"
          title="Asistente Guía IA"
          className="pointer-events-auto fixed bottom-6 right-6 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <HelpCircle className="h-7 w-7" aria-hidden="true" />
        </button>
      )}

      {(estado === 'abierto' || estado === 'minimizado') && (
        <section
          aria-label="Asistente Guía interactivo"
          style={{
            left: `${posicion.x}px`,
            top: `${posicion.y}px`,
            width: `min(${ANCHO_PANEL}px, calc(100vw - 32px))`,
            ...(estado === 'abierto'
              ? { height: `min(${ALTO_PANEL}px, calc(100vh - 32px))` }
              : {}),
          }}
          className="pointer-events-auto fixed flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl"
        >
          <header className="flex items-center justify-between gap-2 bg-blue-700 px-3 py-2.5 text-white">
            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-label="Arrastrar panel del asistente"
                title="Arrastra desde aquí para mover el panel"
                onPointerDown={(e) =>
                  iniciarArrastre(
                    e,
                    ANCHO_PANEL,
                    estado === 'minimizado' ? ALTO_CABECERA : ALTO_PANEL,
                  )
                }
                className="cursor-grab rounded px-1 py-0.5 text-lg leading-none text-blue-100 hover:bg-blue-600 active:cursor-grabbing"
              >
                ⠿
              </button>
              <Sparkles className="h-4 w-4 text-blue-200" aria-hidden="true" />
              <div className="leading-tight">
                <h2 className="text-sm font-semibold">Asistente Guía</h2>
                <p className="text-[11px] text-blue-100">
                  {usuario.roles.join(', ')}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {estado === 'abierto' ? (
                <button
                  type="button"
                  aria-label="Minimizar asistente"
                  title="Minimizar"
                  onClick={minimizarPanel}
                  className="rounded p-1 text-blue-100 hover:bg-blue-600"
                >
                  <Minus className="h-4 w-4" aria-hidden="true" />
                </button>
              ) : (
                <button
                  type="button"
                  aria-label="Expandir asistente"
                  title="Expandir"
                  onClick={abrirPanel}
                  className="rounded p-1 text-blue-100 hover:bg-blue-600"
                >
                  <Maximize2 className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
              <button
                type="button"
                aria-label="Cerrar asistente"
                title="Cerrar"
                onClick={cerrarPanel}
                className="rounded p-1 text-blue-100 hover:bg-blue-600"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </header>

          {estado === 'abierto' && (
            <>
              <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-3 text-sm select-text">
            {mensajes.length === 0 && (
              <div className="rounded-lg border border-blue-100 bg-blue-50/70 p-3 text-xs text-slate-700">
                <p className="font-medium text-blue-900">¿En qué te ayudo?</p>
                <p className="mt-1">
                  Pregúntame para qué sirve cualquier módulo u opción, o cómo realizar un proceso permitido para tu rol y te señalaré en pantalla dónde empezar.
                </p>
              </div>
            )}

            {mensajes.map((msg) => {
              if (msg.autor === 'usuario') {
                return (
                  <div key={msg.id} className="flex justify-end">
                    <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-blue-600 px-3 py-2 text-xs text-white">
                      {msg.texto}
                    </div>
                  </div>
                )
              }

              if (msg.autor === 'error') {
                return (
                  <div
                    key={msg.id}
                    role="alert"
                    className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"
                  >
                    {msg.texto}
                  </div>
                )
              }

              const r = msg.respuesta
              const tieneGuiaVisual = Boolean(r && (r.id_accion || r.id_menu))

              return (
                <div
                  key={msg.id}
                  className="space-y-2 px-1 py-1 text-xs text-slate-800"
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.texto}</p>

                  {msg.otraInterfaz && r?.ruta_objetivo && (
                    <p className="text-[11px] text-blue-700">
                      Esta funcionalidad se encuentra en otro módulo ({r.ruta_objetivo}). Te señalé el acceso en el menú lateral.
                    </p>
                  )}

                  {r && r.pasos.length > 0 && (
                    <ol className="list-decimal space-y-1 pl-4 text-slate-700">
                      {r.pasos.map((paso, idx) => (
                        <li key={idx}>{paso}</li>
                      ))}
                    </ol>
                  )}

                  {tieneGuiaVisual && r && (
                    <div className="pt-1">
                      <button
                        type="button"
                        onClick={() => aplicarResaltadoRespuesta(r, location.pathname)}
                        className="inline-flex items-center gap-1.5 rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-medium text-blue-700 hover:bg-blue-100"
                      >
                        <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                        <span>Mostrar en pantalla</span>
                      </button>
                    </div>
                  )}
                </div>
              )
            })}

            {consultarMutation.isPending && (
              <div className="px-1 py-1 text-xs text-slate-500">
                Consultando al asistente guía…
              </div>
            )}

            <div ref={finMensajesRef} />
          </div>

          <form
            onSubmit={enviarConsulta}
            className="flex items-center gap-2 border-t border-slate-200 bg-white p-2.5"
          >
            <input
              type="text"
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              placeholder="Escribe tu pregunta sobre el sistema…"
              aria-label="Consulta para el asistente guía"
              maxLength={1000}
              disabled={consultarMutation.isPending}
              className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!entrada.trim() || consultarMutation.isPending}
              aria-label="Enviar consulta"
              className="inline-flex items-center justify-center rounded-md bg-blue-600 p-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </button>
          </form>
            </>
          )}
        </section>
      )}
    </div>,
    document.body,
  )
}
