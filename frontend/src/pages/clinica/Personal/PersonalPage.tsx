import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import {
  CARGOS_PERSONAL,
  personalApi,
  type Personal,
} from '@/api/modules/personal'
import { DataTable, type Columna } from '@/components/data/DataTable'
import { Pagination } from '@/components/data/Pagination'
import { SearchBar } from '@/components/data/SearchBar'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { useListaPaginada } from '@/hooks/useListaPaginada'
import { mensajeDeError } from '@/lib/errorMessages'
import { PersonalFormModal } from './PersonalFormModal'
import { VincularUsuarioModal } from './VincularUsuarioModal'

function mostrarFecha(fecha: string): string {
  const [anio, mes, dia] = fecha.split('-')
  return `${dia}/${mes}/${anio}`
}

export function PersonalPage() {
  const queryClient = useQueryClient()

  const {
    page,
    setPage,
    search,
    setSearch,
    query,
  } = useListaPaginada('personal', personalApi.listar)

  // undefined: cerrado; null: crear; objeto: editar.
  const [formulario, setFormulario] = useState<
    Personal | null | undefined
  >(undefined)

  const [aVincular, setAVincular] = useState<Personal | null>(null)
  const [aEliminar, setAEliminar] = useState<Personal | null>(null)

  const eliminar = useMutation({
    mutationFn: (id: number) => personalApi.eliminar(id),

    onSuccess: () => {
      toast.success('Registro de personal eliminado.')
      setAEliminar(null)

      void queryClient.invalidateQueries({
        queryKey: ['personal'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['usuarios'],
      })
    },

    onError: (error) => {
      toast.error(mensajeDeError(error))
    },
  })

  const columnas: Columna<Personal>[] = [
    {
      encabezado: 'Personal',
      celda: (fila) => (
        <span className="font-medium text-slate-900">
          {fila.apellido}, {fila.nombre}
        </span>
      ),
    },
    {
      encabezado: 'CI',
      celda: (fila) => fila.ci,
    },
    {
      encabezado: 'Teléfono',
      celda: (fila) => fila.telefono,
    },
    {
      encabezado: 'Cargo',
      celda: (fila) =>
        CARGOS_PERSONAL.find(
          (cargo) => cargo.valor === fila.cargo,
        )?.etiqueta ?? fila.cargo,
    },
    {
      encabezado: 'Ingreso',
      celda: (fila) => mostrarFecha(fila.fecha_ingreso),
    },
    {
      encabezado: 'Cuenta',
      celda: (fila) =>
        fila.usuario === null
          ? 'Sin vincular'
          : `Vinculada (ID ${fila.usuario})`,
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
        <div className="flex flex-wrap justify-end gap-2">
          <Button
            variante="secundario"
            disabled={eliminar.isPending}
            onClick={() => setFormulario(fila)}
          >
            Editar
          </Button>

          <Button
            variante="secundario"
            disabled={eliminar.isPending}
            onClick={() => setAVincular(fila)}
          >
            Cuenta
          </Button>

          <Button
            variante="peligro"
            disabled={eliminar.isPending}
            onClick={() => setAEliminar(fila)}
          >
            Eliminar
          </Button>
        </div>
      ),
    },
  ]

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-900">
          Personal
        </h1>

        <Button
          disabled={eliminar.isPending}
          onClick={() => setFormulario(null)}
        >
          Registrar personal
        </Button>
      </div>

      <p className="text-sm text-slate-600">
        Registra al personal de la clínica y vincula sus cuentas
        de acceso. El estado del personal y el de su cuenta de
        usuario se administran por separado.
      </p>

      <SearchBar
        valor={search}
        onBuscar={setSearch}
        placeholder="Buscar por CI, nombre, apellido o teléfono…"
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
            ? 'No se encontró personal.'
            : 'Todavía no hay personal registrado.'
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
        <PersonalFormModal
          personal={formulario}
          onClose={() => setFormulario(undefined)}
        />
      )}

      {aVincular && (
        <VincularUsuarioModal
          personal={aVincular}
          onClose={() => setAVincular(null)}
        />
      )}

      {aEliminar && (
        <ConfirmDialog
          titulo="Eliminar personal"
          mensaje={`¿Quieres eliminar a "${aEliminar.nombre} ${aEliminar.apellido}"? La eliminación es permanente y no elimina su cuenta de usuario. Si tiene un médico asociado u otras relaciones protegidas, el backend impedirá la operación.`}
          textoConfirmar="Eliminar personal"
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