import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { rolesApi, type Rol } from '@/api/modules/roles'
import { DataTable, type Columna } from '@/components/data/DataTable'
import { Pagination } from '@/components/data/Pagination'
import { SearchBar } from '@/components/data/SearchBar'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { useListaPaginada } from '@/hooks/useListaPaginada'
import { mensajeDeError } from '@/lib/errorMessages'
import { RolFormModal } from './RolFormModal'

export function RolesPage() {
  const queryClient = useQueryClient()

  const {
    page,
    setPage,
    search,
    setSearch,
    query,
  } = useListaPaginada('roles', rolesApi.listar)

  // undefined: cerrado; null: crear; objeto: editar.
  const [formulario, setFormulario] = useState<
    Rol | null | undefined
  >(undefined)

  const [aEliminar, setAEliminar] = useState<Rol | null>(null)

  const eliminar = useMutation({
    mutationFn: (id: number) => rolesApi.eliminar(id),

    onSuccess: () => {
      toast.success('Rol eliminado.')
      setAEliminar(null)

      void queryClient.invalidateQueries({
        queryKey: ['roles'],
      })
    },

    onError: (error) => {
      toast.error(mensajeDeError(error))
    },
  })

  const columnas: Columna<Rol>[] = [
    {
      encabezado: 'Nombre',
      celda: (fila) => (
        <span className="font-medium text-slate-900">
          {fila.nombre}
        </span>
      ),
    },
    {
      encabezado: 'Descripción',
      celda: (fila) => fila.descripcion || '—',
    },
    {
      encabezado: 'Tipo',
      celda: (fila) => (
        <span className="text-sm">
          {fila.es_base ? 'Base' : 'Personalizado'}
        </span>
      ),
    },
    {
      encabezado: 'Estado',
      celda: (fila) => (
        <span
          className={`rounded-full px-2 py-1 text-xs font-medium ${
            fila.estado
              ? 'bg-green-100 text-green-700'
              : 'bg-slate-100 text-slate-600'
          }`}
        >
          {fila.estado ? 'Activo' : 'Inactivo'}
        </span>
      ),
    },
    {
      encabezado: 'Acciones',
      className: 'text-right',
      celda: (fila) => (
        <div className="flex justify-end gap-2">
          <Button
            variante="secundario"
            disabled={eliminar.isPending}
            onClick={() => setFormulario(fila)}
          >
            {fila.es_base ? 'Editar descripción' : 'Editar'}
          </Button>

          {!fila.es_base && (
            <Button
              variante="peligro"
              disabled={eliminar.isPending}
              onClick={() => setAEliminar(fila)}
            >
              Eliminar
            </Button>
          )}
        </div>
      ),
    },
  ]

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-900">
          Roles
        </h1>

        <Button
          disabled={eliminar.isPending}
          onClick={() => setFormulario(null)}
        >
          Nuevo rol
        </Button>
      </div>

      <p className="text-sm text-slate-600">
        Los roles base solo permiten editar su descripción.
        Los roles con usuarios asignados no pueden eliminarse.
      </p>

      <SearchBar
        valor={search}
        onBuscar={setSearch}
        placeholder="Buscar por nombre o descripción…"
      />

      <DataTable
        filas={query.data?.results}
        columnas={columnas}
        claveFila={(fila) => fila.id}
        cargando={query.isLoading}
        error={
          query.isError ? mensajeDeError(query.error) : null
        }
        textoVacio={
          search
            ? 'No se encontraron roles.'
            : 'No hay roles registrados.'
        }
      />

      {query.isError && (
        <Button
          variante="secundario"
          disabled={query.isFetching}
          onClick={() => void query.refetch()}
        >
          Reintentar
        </Button>
      )}

      <Pagination
        pagina={page}
        total={query.data?.count ?? 0}
        onCambiar={setPage}
      />

      {formulario !== undefined && (
        <RolFormModal
          rol={formulario}
          onClose={() => setFormulario(undefined)}
        />
      )}

      {aEliminar && (
        <ConfirmDialog
          titulo="Eliminar rol"
          mensaje={`¿Quieres eliminar el rol "${aEliminar.nombre}"? No podrá eliminarse si tiene usuarios asignados.`}
          textoConfirmar="Eliminar rol"
          cargando={eliminar.isPending}
          onConfirmar={() => {
            if (!eliminar.isPending) {
              eliminar.mutate(aEliminar.id)
            }
          }}
          onCancelar={() => {
            if (!eliminar.isPending) {
              setAEliminar(null)
            }
          }}
        />
      )}
    </section>
  )
}