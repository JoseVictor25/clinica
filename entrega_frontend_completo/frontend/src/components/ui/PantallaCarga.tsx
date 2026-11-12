export function PantallaCarga({ texto = 'Cargando…' }: { texto?: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center" role="status" aria-live="polite">
      <p className="text-slate-500">{texto}</p>
    </div>
  )
}