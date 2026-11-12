import type { ButtonHTMLAttributes } from 'react'

type Variante = 'primario' | 'secundario' | 'peligro'

const ESTILOS: Record<Variante, string> = {
  primario: 'bg-blue-600 text-white hover:bg-blue-700',
  secundario: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50',
  peligro: 'bg-red-600 text-white hover:bg-red-700',
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante
  cargando?: boolean
}

export function Button({ variante = 'primario', cargando = false, disabled, className = '', children, ...resto }: Props) {
  return (
    <button
      type="button"
      disabled={disabled || cargando}
      className={`rounded-md px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 ${ESTILOS[variante]} ${className}`}
      {...resto}
    >
      {cargando ? 'Procesando…' : children}
    </button>
  )
}