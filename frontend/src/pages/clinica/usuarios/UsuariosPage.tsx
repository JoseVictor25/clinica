import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import {
  usuariosApi,
  type UsuarioClinica,
} from '@/api/modules/usuarios'
import { DataTable, type Columna } from '@/components/data/DataTable'
import { Pagination } from '@/components/data/Pagination'
import { SearchBar } from '@/components/data/SearchBar'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { useAuth } from '@/hooks/useAuth'
import { useListaPaginada } from '@/hooks/useListaPaginada'
import { mensajeDeError } from '@/lib/errorMessages'
import { UsuarioFormModal } from './UsuarioFormModal'
import { UsuarioRolesModal } from './UsuarioRolesModal'

interface CambioEstado {
  usuario: UsuarioClinica
  activar: boolean
}

export function UsuariosPage() {
  const queryClient = useQueryClient()
  const { usuario: sesion, cerrarSesion } = useAuth()

  const {
    page,
    setPage,
    search,
    setSearch,
    query,
  } = useListaPaginada('usuarios', usuariosApi.listar)

  // undefined: cerrado; null: crear; objeto: editar.
  const [formulario, setFormulario] = useState<
    UsuarioClinica | null | undefined
  >(undefined)

  const [usuarioRoles, setUsuarioRoles] = useState<
    UsuarioClinica | null
  >(null)

  const [cambioEstado, setCambioEstado] = useState<
    CambioEstado | null
  >(null)

  const cambiarEstado = useMutation({
    mutationFn: async (datos: CambioEstado): Promise<void> => {
      if (datos.activar) {
        await usuariosApi.reactivar(datos.usuario.id)
      } else {
        await usuariosApi.desactivar(datos.usuario.id)
      }
    },

    onSuccess: async (_, datos) => {
      toast.success(
        datos.activar ? 'Usuario reactivado.' : 'Usuario desactivado.',
      )
      setCambioEstado(null)

      // Al desactivar la propia cuenta, se cierra la sesión local.
      if (!datos.activar && datos.usuario.id === sesion?.id) {
        await cerrarSesion()
        return
      }

      void queryClient.invalidateQueries({
        queryKey: ['usuarios'],
      })
    },

    onError: (error) => {
      toast.error(mensajeDeError(error))
    },
  })

  const columnas: Columna<UsuarioClinica>[] = [
    {
      encabezado: 'Usuario',
      celda: (fila) => (
        <span className="font-medium text-slate-900">
          {fila.username}
          {fila.id === sesion?.id && ' (tú)'}
        </span>
      ),
    },
    {
      encabezado: 'Correo',
      celda: (fila) => fila.email,
    },
    {
      encabezado: 'Roles activos',
      celda: (fila) =>
        fila.roles.length > 0
          ? fila.roles.join(', ')
          : 'Sin roles activos',
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
            disabled={cambiarEstado.isPending}
            onClick={() => setFormulario(fila)}
          >
            Editar
          </Button>

          <Button
            variante="secundario"
            disabled={cambiarEstado.isPending}
            onClick={() => setUsuarioRoles(fila)}
          >
            Roles
          </Button>

          <Button
            variante={fila.estado ? 'peligro' : 'secundario'}
            disabled={cambiarEstado.isPending}
            onClick={() =>
              setCambioEstado({
                usuario: fila,
                activar: !fila.estado,
              })
            }
          >
            {fila.estado ? 'Desactivar' : 'Reactivar'}
          </Button>
        </div>
      ),
    },
  ]

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-900">
          Usuarios
        </h1>

        <Button
          disabled={cambiarEstado.isPending}
          onClick={() => setFormulario(null)}
        >
          Nuevo usuario
        </Button>
      </div>

      <p className="text-sm text-slate-600">
        Administra los usuarios de tu clínica. La creación y
        reactivación respetan el límite del plan. Desactivar un
        usuario conserva su registro.
      </p>

      <SearchBar
        valor={search}
        onBuscar={setSearch}
        placeholder="Buscar por usuario o correo…"
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
            ? 'No se encontraron usuarios.'
            : 'No hay usuarios registrados.'
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
        <UsuarioFormModal
          usuario={formulario}
          onClose={() => setFormulario(undefined)}
        />
      )}

      {usuarioRoles && (
        <UsuarioRolesModal
          usuario={usuarioRoles}
          onClose={() => setUsuarioRoles(null)}
        />
      )}

      {cambioEstado && (
        <ConfirmDialog
          titulo={
            cambioEstado.activar
              ? 'Reactivar usuario'
              : 'Desactivar usuario'
          }
          mensaje={
            cambioEstado.activar
              ? `¿Quieres reactivar a "${cambioEstado.usuario.username}"? Se verificará el límite de usuarios del plan.`
              : cambioEstado.usuario.id === sesion?.id
                ? '¿Quieres desactivar tu propia cuenta? Se cerrará tu sesión y otro administrador tendrá que reactivarla.'
                : `¿Quieres desactivar a "${cambioEstado.usuario.username}"? El usuario perderá el acceso al sistema.`
          }
          textoConfirmar={
            cambioEstado.activar ? 'Reactivar' : 'Desactivar'
          }
          cargando={cambiarEstado.isPending}
          onConfirmar={() => {
            if (!cambiarEstado.isPending) {
              cambiarEstado.mutate(cambioEstado)
            }
          }}
          onCancelar={() => {
            if (!cambiarEstado.isPending) {
              setCambioEstado(null)
            }
          }}
        />
      )}
    </section>
  )
}