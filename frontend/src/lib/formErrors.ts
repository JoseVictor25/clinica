import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'
import { normalizarError } from '@/api/errors'
import { mensajeDeError } from './errorMessages'

/**
 * Asigna los errores del backend a los campos del formulario.
 * - campos: nombres de campo que existen en el formulario.
 * - porCodigo: código de error de negocio -> campo (p. ej. especialidad_duplicada -> nombre).
 * Devuelve un mensaje general si algún error no corresponde a un campo, o null si todo quedó asignado.
 */
export function aplicarErroresDeApi<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  campos: readonly string[],
  porCodigo: Record<string, string> = {},
): string | null {
  const e = normalizarError(error)

  const campoDelCodigo = e.code ? porCodigo[e.code] : undefined
  if (campoDelCodigo && campos.includes(campoDelCodigo)) {
    setError(campoDelCodigo as Path<T>, { type: 'server', message: mensajeDeError(e) })
    return null
  }

  let aplicado = false
  let sinCampo: string[] = []
  for (const [campo, mensajes] of Object.entries(e.fieldErrors)) {
    if (campos.includes(campo)) {
      setError(campo as Path<T>, { type: 'server', message: mensajes.join(' ') })
      aplicado = true
    } else {
      sinCampo = sinCampo.concat(mensajes)
    }
  }

  if (sinCampo.length > 0) return sinCampo.join(' ')
  return aplicado ? null : mensajeDeError(e)
}