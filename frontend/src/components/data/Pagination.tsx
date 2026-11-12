import { Button } from '@/components/ui/Button'

interface Props {
  pagina: number
  total: number
  tamano?: number
  onCambiar: (pagina: number) => void
}

export function Pagination({ pagina, total, tamano = 20, onCambiar }: Props) {
  if (total === 0) return null
  const paginas = Math.max(1, Math.ceil(total / tamano))

  return (
    <nav aria-label="Paginación" className="mt-4 flex items-center justify-between text-sm text-slate-600">
      <span>
        {total} {total === 1 ? 'registro' : 'registros'} · Página {pagina} de {paginas}
      </span>
      <div className="flex gap-2">
        <Button variante="secundario" disabled={pagina <= 1} onClick={() => onCambiar(pagina - 1)}>
          Anterior
        </Button>
        <Button variante="secundario" disabled={pagina >= paginas} onClick={() => onCambiar(pagina + 1)}>
          Siguiente
        </Button>
      </div>
    </nav>
  )
}