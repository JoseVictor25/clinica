import type { ReactNode } from 'react'

export interface Columna<T> {
  encabezado: string
  celda: (fila: T) => ReactNode
  className?: string
}

interface Props<T> {
  filas: T[] | undefined
  columnas: Columna<T>[]
  claveFila: (fila: T) => string | number
  cargando: boolean
  error?: string | null
  textoVacio?: string
}

export function DataTable<T>({
  filas,
  columnas,
  claveFila,
  cargando,
  error,
  textoVacio = 'No hay registros para mostrar.',
}: Props<T>) {
  if (error) {
    return (
      <p role="alert" className="rounded-md bg-red-50 p-4 text-sm text-red-700">
        {error}
      </p>
    )
  }
  if (cargando && !filas) {
    return (
      <p role="status" className="p-6 text-center text-sm text-slate-500">
        Cargando…
      </p>
    )
  }
  if (!filas || filas.length === 0) {
    return <p className="p-6 text-center text-sm text-slate-500">{textoVacio}</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {columnas.map((c) => (
              <th key={c.encabezado} scope="col" className={`px-4 py-3 text-left font-medium text-slate-600 ${c.className ?? ''}`}>
                {c.encabezado}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {filas.map((fila) => (
            <tr key={claveFila(fila)}>
              {columnas.map((c) => (
                <td key={c.encabezado} className={`px-4 py-3 text-slate-700 ${c.className ?? ''}`}>
                  {c.celda(fila)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}