/**
 * Controlador de resaltado visual animado (5 segundos) sobre elementos con data-guia-id.
 */

const CLASE_RESALTADO = 'guia-resaltado-activo'

let elementoActivo: HTMLElement | null = null
let temporizadorActivo: number | null = null
let listenerClickActivo: (() => void) | null = null

export function limpiarResaltadoGuia(): void {
  if (temporizadorActivo !== null) {
    window.clearTimeout(temporizadorActivo)
    temporizadorActivo = null
  }
  if (elementoActivo) {
    elementoActivo.classList.remove(CLASE_RESALTADO)
    if (listenerClickActivo) {
      elementoActivo.removeEventListener('click', listenerClickActivo)
    }
    elementoActivo = null
  }
  listenerClickActivo = null
}

export function resaltarElementoGuia(guiaId: string | null | undefined, duracionMs = 5000): boolean {
  limpiarResaltadoGuia()
  if (!guiaId) return false

  const selector = `[data-guia-id="${CSS.escape(guiaId)}"]`
  const elemento = document.querySelector<HTMLElement>(selector)
  if (!elemento) {
    // FE-02: si el componente no existe en el DOM activo, omitir sin error.
    return false
  }

  elemento.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })
  elemento.classList.add(CLASE_RESALTADO)
  elementoActivo = elemento

  const alHacerClic = () => {
    limpiarResaltadoGuia()
  }
  listenerClickActivo = alHacerClic
  elemento.addEventListener('click', alHacerClic, { once: true })

  temporizadorActivo = window.setTimeout(() => {
    limpiarResaltadoGuia()
  }, duracionMs)

  return true
}
