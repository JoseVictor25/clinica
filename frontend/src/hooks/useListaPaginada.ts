import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useState } from 'react'
import type { ListParams, Paginated } from '@/types/api'

/** Estado de página y búsqueda + consulta paginada contra la API (?page= y ?search=). */
export function useListaPaginada<T>(
  clave: string,
  listar: (params: ListParams) => Promise<Paginated<T>>,
) {
  const [page, setPage] = useState(1)
  const [search, setSearchEstado] = useState('')

  const query = useQuery({
    queryKey: [clave, { page, search }],
    queryFn: () => listar({ page, search: search || undefined }),
    placeholderData: keepPreviousData,
  })

  const setSearch = useCallback((valor: string) => {
    setSearchEstado(valor)
    setPage(1)
  }, [])

  // Si al eliminar se vacía la última página, retroceder una.
  useEffect(() => {
    if (query.data && query.data.results.length === 0 && page > 1) setPage(page - 1)
  }, [query.data, page])

  return { page, setPage, search, setSearch, query }
}