interface Props {
  horarios: string[]
  seleccionado: string
  cargando: boolean
  error: string | null
  listo: boolean
  onSeleccionar: (hora: string) => void
}

export function HorariosDisponibles({
  horarios,
  seleccionado,
  cargando,
  error,
  listo,
  onSeleccionar,
}: Props) {
  if (!listo) {
    return <p className="text-sm text-slate-500">Selecciona paciente, médico y fecha para consultar horarios.</p>
  }
  if (cargando) return <p role="status" className="text-sm text-slate-500">Consultando horarios…</p>
  if (error) return <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>
  if (horarios.length === 0) return <p className="text-sm text-slate-500">No existen horarios disponibles para la fecha seleccionada.</p>

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Horarios disponibles">
      {horarios.map((hora) => (
        <button
          key={hora}
          type="button"
          aria-pressed={seleccionado === hora}
          className={`rounded-md border px-3 py-2 text-sm ${seleccionado === hora ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}
          onClick={() => onSeleccionar(hora)}
        >
          {hora}
        </button>
      ))}
    </div>
  )
}
