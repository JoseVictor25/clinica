import type { ReactNode } from 'react'

interface Props {
  id: string
  label: string
  error?: string
  children: ReactNode
}

/** Etiqueta + control + mensaje de error asociado (accesible). */
export function Field({ id, label, error, children }: Props) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  )
}