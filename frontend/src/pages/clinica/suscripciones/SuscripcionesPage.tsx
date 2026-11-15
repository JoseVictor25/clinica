import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import {
  suscripcionesApi,
  type EstadoSuscripcion,
  type Suscripcion,
} from '@/api/modules/suscripciones'
import { DataTable, type Columna } from '@/components/data/DataTable'
import { Pagination } from '@/components/data/Pagination'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { inputClass } from '@/components/ui/styles'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'
import { esAdminClinica } from '@/lib/roles'
import { SuscripcionFormModal } from './SuscripcionFormModal'
import { SuscripcionDetalleModal } from './SuscripcionDetalleModal'

type Formulario =
  | { modo: 'contratar' }
  | {
      modo: 'renovar' | 'cambiar-plan'
      suscripcion: Suscripcion
    }
  | null

const ESTADOS: EstadoSuscripcion[] = [
  'ACTIVA',
  'VENCIDA',
  'CANCELADA',
  'SUSPENDIDA',
]

function fechaActual(): string {
  const partes = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/La_Paz',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date())

  const obtener = (tipo: Intl.DateTimeFormatPartTypes) =>
    partes.find((parte) => parte.type === tipo)?.value ?? ''

  return `${obtener('year')}-${obtener('month')}-${obtener('day')}`
}

function mostrarFecha(fecha: string): string {
  const [anio, mes, dia] = fecha.split('-')
  return `${dia}/${mes}/${anio}`
}

function describirEstado(
  suscripcion: Suscripcion,
  hoy: string,
): string {
  if (suscripcion.estado === 'ACTIVA') {
    if (suscripcion.fecha_fin < hoy) return 'Vencida'
    if (suscripcion.fecha_inicio > hoy) return 'Programada'
    return 'Vigente'
  }

  const etiquetas: Record<EstadoSuscripcion, string> = {
    ACTIVA: 'Activa',
    VENCIDA: 'Vencida',
    CANCELADA: 'Cancelada',
    SUSPENDIDA: 'Suspendida',
  }

  return etiquetas[suscripcion.estado]
}

export function SuscripcionesPage() {
  const { usuario, actualizarPerfil, suscripcionVencida } = useAuth()
  const queryClient = useQueryClient()

  const [pagina, setPagina] = useState(1)
  const [estado, setEstado] = useState<EstadoSuscripcion | ''>('')
  const [formulario, setFormulario] = useState<Formulario>(null)
  const [aCancelar, setACancelar] = useState<Suscripcion | null>(null)
  const [detalleId, setDetalleId] = useState<number | null>(null)

  const puedeGestionar = usuario !== null && esAdminClinica(usuario)
  const identificador = usuario?.clinicaId ?? 'sistema'
  const hoy = fechaActual()

  const historial = useQuery({
    queryKey: [
      'suscripciones',
      'historial',
      identificador,
      pagina,
      estado,
    ],
    queryFn: () =>
      suscripcionesApi.listar({
        page: pagina,
        page_size: 20,
        estado: estado || undefined,
      }),
  })

  // Esta consulta es independiente del filtro y página del historial.
  // La base de datos permite una sola suscripción ACTIVA por clínica.
  const activa = useQuery({
    queryKey: ['suscripciones', 'activa', identificador],
    queryFn: () =>
      suscripcionesApi.listar({
        estado: 'ACTIVA',
        page_size: 1,
      }),
    enabled: puedeGestionar,
  })

  const actual = activa.data?.results[0]

  // Una fila puede seguir marcada ACTIVA aunque su fecha ya haya pasado.
  // Al contratar, el backend marca esas filas como VENCIDAS.
  const puedeContratar =
    puedeGestionar &&
    activa.isSuccess &&
    (!actual || actual.fecha_fin < hoy)

  const actualizar = useMutation({
    mutationFn: actualizarPerfil,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ['suscripciones'],
      })
      toast.success('Estado de suscripción actualizado.')
    },
    onError: (error) => toast.error(mensajeDeError(error)),
  })

  const cancelar = useMutation({
    mutationFn: (id: number) => suscripcionesApi.cancelar(id),

    onSuccess: async () => {
      toast.success('Suscripción cancelada.')

      try {
        await actualizarPerfil()
      } catch {
        toast.warning(
          'La cancelación se guardó, pero no se pudo actualizar el perfil. Recarga la página.',
        )
      }

      setACancelar(null)

      void queryClient.invalidateQueries({
        queryKey: ['suscripciones'],
      })
    },

    onError: (error) => {
      toast.error(mensajeDeError(error))
    },
  })

  const columnas: Columna<Suscripcion>[] = [
    {
      encabezado: 'Plan',
      celda: (fila) => fila.plan_nombre,
    },
    {
      encabezado: 'Inicio',
      celda: (fila) => mostrarFecha(fila.fecha_inicio),
    },
    {
      encabezado: 'Fin',
      celda: (fila) => mostrarFecha(fila.fecha_fin),
    },
    {
      encabezado: 'Estado',
      celda: (fila) => describirEstado(fila, hoy),
    },
    {
      encabezado: 'Detalle',
      celda: (fila) => <Button variante="secundario" onClick={() => setDetalleId(fila.id)}>Consultar</Button>,
    },
  ]

  if (usuario?.esAdminSistema) {
    columnas.unshift({
      encabezado: 'Clínica',
      celda: (fila) => fila.clinica_nombre,
    })
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-900">
          {puedeGestionar ? 'Mi suscripción' : 'Suscripciones'}
        </h1>

        <Button
          variante="secundario"
          cargando={actualizar.isPending}
          disabled={cancelar.isPending || formulario !== null}
          onClick={() => actualizar.mutate()}
        >
          Actualizar estado
        </Button>
      </div>

      {usuario?.esAdminSistema && (
        <p className="text-sm text-slate-600">
          Consulta las suscripciones de las clínicas. La contratación,
          renovación, cambio de plan y cancelación corresponden al
          administrador de cada clínica.
        </p>
      )}

      {puedeGestionar && (
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold text-slate-900">
            {usuario?.clinicaNombre ?? 'Tu clínica'}
          </h2>

          <p
            className={
              suscripcionVencida
                ? 'text-sm text-amber-800'
                : 'text-sm text-green-700'
            }
          >
            {suscripcionVencida
              ? 'Acceso restringido: no hay una suscripción vigente.'
              : 'La clínica tiene acceso habilitado.'}
          </p>

          {activa.isPending && (
            <p role="status" className="text-sm text-slate-600">
              Consultando suscripción…
            </p>
          )}

          {activa.isError && (
            <div role="alert" className="space-y-2">
              <p className="text-sm text-red-700">
                {mensajeDeError(activa.error)}
              </p>
              <Button
                variante="secundario"
                disabled={activa.isFetching}
                onClick={() => void activa.refetch()}
              >
                Reintentar
              </Button>
            </div>
          )}

          {activa.isSuccess && actual && (
            <div className="space-y-2 text-sm text-slate-700">
              <p>
                Plan: <strong>{actual.plan_nombre}</strong>
              </p>
              <p>
                Período: {mostrarFecha(actual.fecha_inicio)} al{' '}
                {mostrarFecha(actual.fecha_fin)}.
              </p>
              <p>Estado: {describirEstado(actual, hoy)}.</p>

              {actual.fecha_inicio > hoy && (
                <p className="text-amber-800">
                  El acceso se habilitará en la fecha de inicio.
                  Puedes cambiar el plan y sus fechas, o cancelar
                  esta suscripción.
                </p>
              )}

              {actual.fecha_fin < hoy && (
                <p className="text-amber-800">
                  El período terminó. Para recuperar el acceso,
                  contrata una nueva suscripción.
                </p>
              )}
            </div>
          )}

          {activa.isSuccess && !actual && (
            <p className="text-sm text-slate-600">
              No hay una suscripción activa. Selecciona un plan
              para contratar.
            </p>
          )}

          <div className="flex flex-wrap gap-2">
            {puedeContratar && (
              <Button
                disabled={cancelar.isPending}
                onClick={() => setFormulario({ modo: 'contratar' })}
              >
                Contratar plan
              </Button>
            )}

            {activa.isSuccess && actual && actual.fecha_fin >= hoy && (
              <>
                <Button
                  disabled={cancelar.isPending}
                  onClick={() =>
                    setFormulario({
                      modo: 'renovar',
                      suscripcion: actual,
                    })
                  }
                >
                  Renovar
                </Button>

                <Button
                  variante="secundario"
                  disabled={cancelar.isPending}
                  onClick={() =>
                    setFormulario({
                      modo: 'cambiar-plan',
                      suscripcion: actual,
                    })
                  }
                >
                  Cambiar plan
                </Button>
              </>
            )}

            {activa.isSuccess && actual && (
              <Button
                variante="peligro"
                disabled={cancelar.isPending}
                onClick={() => setACancelar(actual)}
              >
                Cancelar suscripción
              </Button>
            )}
          </div>
        </div>
      )}

      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">
          Historial de suscripciones
        </h2>

        <div className="max-w-xs space-y-1">
          <label
            htmlFor="filtro-estado"
            className="block text-sm font-medium text-slate-700"
          >
            Estado registrado
          </label>
          <select
            id="filtro-estado"
            className={inputClass}
            value={estado}
            onChange={(evento) => {
              const valor = evento.target.value

              setEstado(
                ESTADOS.includes(valor as EstadoSuscripcion)
                  ? (valor as EstadoSuscripcion)
                  : '',
              )
              setPagina(1)
            }}
          >
            <option value="">Todos</option>
            {ESTADOS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>

        <p className="text-xs text-slate-500">
          El filtro usa el estado almacenado. La tabla también comprueba
          las fechas para distinguir suscripciones vigentes, programadas
          y vencidas.
        </p>

        <DataTable
          filas={historial.data?.results}
          columnas={columnas}
          claveFila={(fila) => fila.id}
          cargando={historial.isPending}
          error={
            historial.isError ? mensajeDeError(historial.error) : null
          }
          textoVacio="No hay suscripciones para mostrar."
        />

        {historial.isError && (
          <Button
            variante="secundario"
            disabled={historial.isFetching}
            onClick={() => void historial.refetch()}
          >
            Reintentar historial
          </Button>
        )}

        <Pagination
          pagina={pagina}
          total={historial.data?.count ?? 0}
          tamano={20}
          onCambiar={setPagina}
        />
      </div>

      {formulario?.modo === 'contratar' && (
        <SuscripcionFormModal
          modo="contratar"
          onClose={() => setFormulario(null)}
        />
      )}

      {formulario && formulario.modo !== 'contratar' && (
        <SuscripcionFormModal
          modo={formulario.modo}
          suscripcion={formulario.suscripcion}
          onClose={() => setFormulario(null)}
        />
      )}

      {detalleId !== null && <SuscripcionDetalleModal id={detalleId} onClose={() => setDetalleId(null)} />}

      {aCancelar && (
        <ConfirmDialog
          titulo="Cancelar suscripción"
          mensaje={`¿Quieres cancelar la suscripción al plan "${aCancelar.plan_nombre}"? Si está vigente, la clínica perderá el acceso a los módulos de negocio.`}
          textoConfirmar="Confirmar cancelación"
          cargando={cancelar.isPending}
          onConfirmar={() => {
            if (!cancelar.isPending) {
              cancelar.mutate(aCancelar.id)
            }
          }}
          onCancelar={() => {
            if (!cancelar.isPending) {
              setACancelar(null)
            }
          }}
        />
      )}
    </section>
  )
}