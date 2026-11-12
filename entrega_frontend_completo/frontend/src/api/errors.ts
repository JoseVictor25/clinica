import axios from 'axios'

export type FieldErrors = Record<string, string[]>

export class ApiError extends Error {
  status: number
  code: string | null
  fieldErrors: FieldErrors
  /** Campo "detalles" del backend (p. ej. usuarios_activos y max_usuarios). */
  details: Record<string, unknown>
  data: unknown

  constructor(init: {
    status: number
    message: string
    code?: string | null
    fieldErrors?: FieldErrors
    details?: Record<string, unknown>
    data?: unknown
  }) {
    super(init.message)
    this.name = 'ApiError'
    this.status = init.status
    this.code = init.code ?? null
    this.fieldErrors = init.fieldErrors ?? {}
    this.details = init.details ?? {}
    this.data = init.data
  }
}

const CLAVES_RESERVADAS = new Set([
  'codigo', 'code', 'mensaje', 'message', 'detail', 'detalle', 'detalles', 'error', 'errors', 'errores',
])

function texto(valor: unknown): string | null {
  return typeof valor === 'string' && valor.trim() ? valor : null
}

function aLista(valor: unknown): string[] | null {
  if (typeof valor === 'string') return [valor]
  if (Array.isArray(valor) && valor.length > 0 && valor.every((v) => typeof v === 'string')) {
    return valor as string[]
  }
  return null
}

function objeto(valor: unknown): Record<string, unknown> | null {
  return valor && typeof valor === 'object' && !Array.isArray(valor)
    ? (valor as Record<string, unknown>)
    : null
}

function camposDe(origen: Record<string, unknown>, excluirReservadas: boolean): FieldErrors {
  const resultado: FieldErrors = {}
  for (const [clave, valor] of Object.entries(origen)) {
    if (excluirReservadas && CLAVES_RESERVADAS.has(clave)) continue
    const lista = aLista(valor)
    if (lista) resultado[clave] = lista
  }
  return resultado
}

// Formato del backend: {"codigo": "...", "mensaje": "...", "detalles": {...}}.
// Para datos_invalidos se asume que "detalles" trae {campo: [mensajes]} (por confirmar en Swagger).
// También se tolera el formato estándar de DRF ({detail} o {campo: [..]}).
function interpretar(data: unknown) {
  if (typeof data === 'string') {
    // Respuestas HTML (p. ej. el 404 de Django en modo DEBUG) no se muestran al usuario.
    const esHtml = /^\s*<(!doctype|html)/i.test(data)
    return { code: null, message: esHtml ? null : texto(data), fieldErrors: {} as FieldErrors, details: {} }
  }
  const raiz = objeto(data)
  if (!raiz) return { code: null, message: null, fieldErrors: {} as FieldErrors, details: {} }

  const code = texto(raiz.codigo) ?? texto(raiz.code)
  const message = texto(raiz.mensaje) ?? texto(raiz.message) ?? texto(raiz.detail) ?? texto(raiz.detalle)
  const details = objeto(raiz.detalles) ?? {}
  const fieldErrors = { ...camposDe(raiz, true), ...camposDe(details, false) }

  return { code, message, fieldErrors, details }
}

export function normalizarError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return new ApiError({ status: 0, code: 'red', message: 'No se pudo conectar con el servidor.' })
    }
    const { status, data } = error.response
    const { code, message, fieldErrors, details } = interpretar(data)
    return new ApiError({
      status,
      code,
      message: message ?? 'Ocurrió un error inesperado.',
      fieldErrors,
      details,
      data,
    })
  }

  return new ApiError({
    status: 0,
    message: error instanceof Error ? error.message : 'Ocurrió un error inesperado.',
  })
}