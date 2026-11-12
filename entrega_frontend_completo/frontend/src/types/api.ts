/** Respuesta paginada estándar de DRF (PageNumberPagination, PAGE_SIZE=20). */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
export interface ListParams {
  page?: number
  search?: string
  ordering?: string
  [filtro: string]: string | number | boolean | undefined
}