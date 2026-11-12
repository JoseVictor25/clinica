import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { rolesApi } from '@/api/modules/roles'
import {
  usuarioRolesApi,
  type UsuarioRol,
} from '@/api/modules/usuarioRoles'
import type { UsuarioClinica } from '@/api/modules/usuarios'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'

interface Props {
  usuario: UsuarioClinica
  onClose: () => void
}

type Operacion =
  | { tipo: 'asignar'; rolId: number }
  | { tipo: 'quitar'; asignacion: UsuarioRol }

export function UsuarioRolesModal({ usuario, onClose }: Props) {
  const queryClient = useQueryClient()
  const {
    usuario: sesion,
    actualizarPerfil,
  } = useAuth()

  const [rolSeleccionado, setRolSeleccionado] = useState('')
  const [aQuitar, setAQuitar] = useState<UsuarioRol | null>(null)
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)

  const roles = useQuery({
    queryKey: ['roles', 'todos'],
    queryFn: () => rolesApi.listarTodos(),
  })

  const asignaciones = useQuery({
    queryKey: ['usuario-roles', usuario.id],
    queryFn: () => usuarioRolesApi.listarDelUsuario(usuario.id),
  })

  const disponibles = roles.data?.filter(
    (rol) =>
      rol.estado &&
      !asignaciones.data?.some(
        (asignacion) => asignacion.rol === rol.id,
      ),
  ) ?? []

  const operacion = useMutation({
    mutationFn: async (datos: Operacion): Promise<void> => {
      if (datos.tipo === 'quitar') {
        await usuarioRolesApi.quitar(datos.asignacion.id)
        return
      }

      await usuarioRolesApi.asignar({
        usuario: usuario.id,
        rol: datos.rolId,
      })
    },

    onSuccess: async (_, datos) => {
      toast.success(
        datos.tipo === 'asignar'
          ? 'Rol asignado.'
          : 'Rol retirado.',
      )

      setRolSeleccionado('')
      setAQuitar(null)
      setErrorGeneral(null)

      void queryClient.invalidateQueries({
        queryKey: ['usuario-roles'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['usuarios'],
      })

      if (usuario.id === sesion?.id) {
        try {
          await actualizarPerfil()
        } catch {
          toast.warning(
            'El cambio se guardó, pero no se pudo actualizar tu perfil. Recarga la página.',
          )
        }
      }
    },

    onError: (error) => {
      setErrorGeneral(mensajeDeError(error))
    },
  })

  const cargando = roles.isPending || asignaciones.isPending
  const errorConsulta = roles.isError
    ? roles.error
    : asignaciones.isError
      ? asignaciones.error
      : null

  function cerrar() {
    if (!operacion.isPending) {
      onClose()
    }
  }

  return (
    <Modal
      titulo={`Roles de ${usuario.username}`}
      onClose={cerrar}
    >
      <div className="space-y-4">
        {errorGeneral && (
          <p
            role="alert"
            className="rounded-md bg-red-50 p-3 text-sm text-red-700"
          >
            {errorGeneral}
          </p>
        )}

        {cargando && (
          <p role="status" className="text-sm text-slate-600">
            Cargando roles y asignaciones…
          </p>
        )}

        {errorConsulta && (
          <div role="alert" className="space-y-2">
            <p className="text-sm text-red-700">
              {mensajeDeError(errorConsulta)}
            </p>
            <Button
              variante="secundario"
              disabled={roles.isFetching || asignaciones.isFetching}
              onClick={() => {
                void roles.refetch()
                void asignaciones.refetch()
              }}
            >
              Reintentar
            </Button>
          </div>
        )}

        {!cargando && !errorConsulta && (
          <>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-900">
                Roles asignados
              </h3>

              {asignaciones.data?.length === 0 && (
                <p className="text-sm text-slate-600">
                  Este usuario no tiene roles asignados.
                </p>
              )}

              <ul className="max-h-48 space-y-2 overflow-y-auto">
                {asignaciones.data?.map((asignacion) => {
                  const rol = roles.data?.find(
                    (item) => item.id === asignacion.rol,
                  )

                  return (
                    <li
                      key={asignacion.id}
                      className="flex items-center justify-between gap-3 rounded-md border border-slate-200 p-3"
                    >
                      <span className="text-sm text-slate-700">
                        {asignacion.rol_nombre}
                        {rol?.estado === false && ' (inactivo)'}
                      </span>

                      <Button
                        variante="peligro"
                        disabled={operacion.isPending}
                        onClick={() => {
                          setErrorGeneral(null)
                          setAQuitar(asignacion)
                        }}
                      >
                        Quitar
                      </Button>
                    </li>
                  )
                })}
              </ul>
            </div>

            {aQuitar && (
              <div className="space-y-3 rounded-md bg-amber-50 p-3">
                <p className="text-sm text-amber-900">
                  ¿Quieres quitar el rol «{aQuitar.rol_nombre}»?
                  El usuario perderá los permisos asociados.
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variante="secundario"
                    disabled={operacion.isPending}
                    onClick={() => setAQuitar(null)}
                  >
                    Mantener rol
                  </Button>
                  <Button
                    variante="peligro"
                    cargando={operacion.isPending}
                    onClick={() => {
                      if (operacion.isPending) return

                      setErrorGeneral(null)
                      operacion.mutate({
                        tipo: 'quitar',
                        asignacion: aQuitar,
                      })
                    }}
                  >
                    Confirmar retiro
                  </Button>
                </div>
              </div>
            )}

            <form
              className="space-y-2 border-t border-slate-200 pt-4"
              onSubmit={(evento) => {
                evento.preventDefault()

                if (operacion.isPending) return

                const rol = disponibles.find(
                  (item) => String(item.id) === rolSeleccionado,
                )

                if (!rol) {
                  setErrorGeneral('Selecciona un rol disponible.')
                  return
                }

                setErrorGeneral(null)
                operacion.mutate({
                  tipo: 'asignar',
                  rolId: rol.id,
                })
              }}
            >
              <label
                htmlFor="rol-nuevo"
                className="block text-sm font-medium text-slate-700"
              >
                Asignar otro rol
              </label>

              <select
                id="rol-nuevo"
                className={inputClass}
                value={rolSeleccionado}
                disabled={operacion.isPending || disponibles.length === 0}
                onChange={(evento) =>
                  setRolSeleccionado(evento.target.value)
                }
              >
                <option value="">Selecciona un rol</option>
                {disponibles.map((rol) => (
                  <option key={rol.id} value={rol.id}>
                    {rol.nombre}
                  </option>
                ))}
              </select>

              {disponibles.length === 0 && (
                <p className="text-sm text-slate-600">
                  No hay otros roles activos disponibles.
                </p>
              )}

              <Button
                type="submit"
                disabled={
                  operacion.isPending ||
                  !rolSeleccionado ||
                  aQuitar !== null
                }
              >
                Asignar rol
              </Button>
            </form>
          </>
        )}

        <p className="text-xs text-slate-500">
          No se puede retirar el rol al último administrador activo
          de la clínica. Los roles inactivos no conceden permisos.
        </p>

        <div className="flex justify-end">
          <Button
            variante="secundario"
            disabled={operacion.isPending}
            onClick={cerrar}
          >
            Cerrar
          </Button>
        </div>
      </div>
    </Modal>
  )
}