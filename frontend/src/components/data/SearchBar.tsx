import { useEffect, useState } from 'react'
import { inputClass } from '@/components/ui/styles'

interface Props {
  valor: string
  onBuscar: (texto: string) => void
  placeholder?: string
}

/** Campo de búsqueda con espera de 400 ms antes de consultar a la API. */
export function SearchBar({ valor, onBuscar, placeholder = 'Buscar…' }: Props) {
  const [texto, setTexto] = useState(valor)

  useEffect(() => {
    const limpio = texto.trim()
    if (limpio === valor) return
    const temporizador = setTimeout(() => onBuscar(limpio), 400)
    return () => clearTimeout(temporizador)
  }, [texto, valor, onBuscar])

  return (
    <input
      type="search"
      value={texto}
      onChange={(e) => setTexto(e.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
      className={`${inputClass} max-w-xs`}
    />
  )
}