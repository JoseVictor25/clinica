import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import {
  personalApi,
  type Personal,
} from '@/api/modules/personal'
import {
  usuariosApi,
  type UsuarioClinica,
} from '@/api/modules/usuarios'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { mensajeDeError } from '@/lib/errorMessages'

interface Props {
  personal: Personal
  onClose: () => void
}

async function listarUsuarios(): Promise<UsuarioClinica[]> {
  const usuarios: UsuarioClinica[] = []
  let page = 1

  while (true) {
    const respuesta = await usuariosApi.listar({
      page,
      page_size: 100,
    })

    usuarios.push(...respuesta.results)

    if (!respuesta.next) {
      return usuarios
    }

    page += 1
  }
}

export function VincularUsuarioModal({ personal, onClose }: Props) {
  const queryClient = useQueryClient()

  const [seleccionado, setSeleccionado] = useState(
    personal.usuario === null ? '' : String(personal.usuario),
  )
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)

  const usuarios = useQuery({
    queryKey: ['usuarios', 'vinculacion'],
    queryFn: listarUsuarios,
  })

  const registros = useQuery({
    queryKey: ['personal', 'todos'],
    queryFn: personalApi.listarTodos,
  })

  const ocupados = new Set(
    registros.data
      ?.filter(
        (registro) =>
          registro.id !== personal.id &&
          registro.usuario !== null,
      )
      .map((registro) => registro.usuario),
  )

  const disponibles = usuarios.data?.filter(
    (usuario) => !ocupados.has(usuario.id),
  ) ?? []

  const cuentaActual = usuarios.data?.find(
    (usuario) => usuario.id === personal.usuario,
  )

  const guardar = useMutation({
    mutationFn: (usuarioId: number | null) =>
      personalApi.vincularUsuario(personal.id, usuarioId),

    onSuccess: (actualizado) => {
      toast.success(
        actualizado.usuario === null
          ? 'Cuenta desvinculada.'
          : 'Cuenta vinculada.',
      )

      void queryClient.invalidateQueries({
        queryKey: ['personal'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['usuarios'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['medicos'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['horarios'],
      })

      onClose()
    },

    onError: (error) => {
      setErrorGeneral(mensajeDeError(error))
    },
  })

  const cargando = usuarios.isPending || registros.isPending
  const errorConsulta = usuarios.isError
    ? usuarios.error
    : registros.isError
      ? registros.error
      : null

  const sinCambios =
    seleccionado === (
      personal.usuario === null ? '' : String(personal.usuario)
    )

  function cerrar() {
    if (!guardar.isPending) {
      onClose()
    }
  }

  return (
    <Modal titulo="Cuenta de acceso" onClose={cerrar}>
      <form
        className="space-y-4"
        onSubmit={(evento) => {
          evento.preventDefault()

          if (
            guardar.isPending ||
            cargando ||
            errorConsulta ||
            sinCambios
          ) {
            return
          }

          if (seleccionado !== '') {
            const existe = disponibles.some(
              (usuario) => String(usuario.id) === seleccionado,
            )

            if (!existe) {
              setErrorGeneral('Selecciona una cuenta disponible.')
              return
            }
          }

          setErrorGeneral(null)
          guardar.mutate(
            seleccionado === '' ? null : Number(seleccionado),
          )
        }}
      >
        <p className="text-sm text-slate-700">
          Personal: <strong>{personal.nombre} {personal.apellido}</strong>.
        </p>

        <p className="text-sm text-slate-600">
          Cuenta actual:{' '}
          {personal.usuario === null
            ? 'Sin cuenta vinculada'
            : cuentaActual?.username ?? `Usuario #${personal.usuario}`}.
        </p>

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
            Consultando cuentas disponibles…
          </p>
        )}

        {errorConsulta && (
          <div role="alert" className="space-y-2">
            <p className="text-sm text-red-700">
              {mensajeDeError(errorConsulta)}
            </p>
            <Button
              variante="secundario"
              disabled={usuarios.isFetching || registros.isFetching}
              onClick={() => {
                void usuarios.refetch()
                void registros.refetch()
              }}
            >
              Reintentar
            </Button>
          </div>
        )}

        {!cargando && !errorConsulta && (
          <div className="space-y-1">
            <label
              htmlFor="cuenta-personal"
              className="block text-sm font-medium text-slate-700"
            >
              Cuenta de usuario
            </label>

            <select
              id="cuenta-personal"
              className={inputClass}
              value={seleccionado}
              disabled={guardar.isPending}
              onChange={(evento) =>
                setSeleccionado(evento.target.value)
              }
            >
              <option value="">Sin cuenta vinculada</option>
              {disponibles.map((usuario) => (
                <option key={usuario.id} value={usuario.id}>
                  {usuario.username} — {usuario.email}
                  {!usuario.estado && ' (inactivo)'}
                </option>
              ))}
            </select>

            <p className="text-xs text-slate-500">
              Solo aparecen cuentas de esta clínica que no están
              vinculadas a otra persona. Una cuenta inactiva seguirá
              sin poder iniciar sesión.
            </p>
          </div>
        )}

        {personal.usuario !== null && seleccionado === '' && (
          <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
            Al guardar se desvinculará la cuenta actual. Si esta persona
            tiene un registro médico, esa cuenta dejará de acceder a él.
          </p>
        )}

        <p className="text-xs text-slate-500">
          Vincular una cuenta no crea usuarios ni modifica sus roles.
        </p>

        <div className="flex justify-end gap-2 pt-2">
          <Button
            variante="secundario"
            disabled={guardar.isPending}
            onClick={cerrar}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            cargando={guardar.isPending}
            disabled={
              cargando ||
              Boolean(errorConsulta) ||
              sinCambios
            }
          >
            Guardar vínculo
          </Button>
        </div>
      </form>
    </Modal>
  )
}