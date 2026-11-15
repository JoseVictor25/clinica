import { useEffect, useRef, type ReactNode } from 'react'

interface Props {
  titulo: string
  onClose: () => void
  children: ReactNode
}

export function Modal({ titulo, onClose, children }: Props) {
  const contenedor = useRef<HTMLDivElement>(null)
  const cerrar = useRef(onClose)

  useEffect(() => {
    cerrar.current = onClose
  }, [onClose])

  useEffect(() => {
    contenedor.current?.focus()
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key === 'Escape') cerrar.current()
    }
    document.addEventListener('keydown', alTeclear)
    return () => document.removeEventListener('keydown', alTeclear)
  }, [])

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={contenedor}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-lg outline-none"
      >
        <h2 className="mb-4 text-lg font-semibold text-slate-900">{titulo}</h2>
        {children}
      </div>
    </div>
  )
}