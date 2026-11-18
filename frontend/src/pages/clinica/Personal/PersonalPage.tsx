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
import { inputClass } from '@/components/ui/styles'
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
  const [estado, setEstado] = useState<'true' | 'false' | ''>('true')

  const {
    page,
    setPage,
    search,
    setSearch,
    query,
  } = useListaPaginada('personal', personalApi.listar, {
    estado: estado || undefined,
  })

  // undefined: cerrado; null: crear; objeto: editar.
  const [formulario, setFormulario] = useState<
    Personal | null | undefined
  >(undefined)

  const [aVincular, setAVincular] = useState<Personal | null>(null)
  const [aFinalizar, setAFinalizar] = useState<Personal | null>(null)

  const finalizar = useMutation({
    mutationFn: (id: number) => personalApi.finalizarRelacion(id),

    onSuccess: () => {
      toast.success('Relación laboral finalizada. El historial fue conservado.')
      setAFinalizar(null)

      void queryClient.invalidateQueries({
        queryKey: ['personal'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['usuarios'],
      })
      void queryClient.invalidateQueries({ queryKey: ['medicos'] })
    },

    onError: (error) => {
      toast.error(mensajeDeError(error))
    },
  })

  const reactivar = useMutation({
    mutationFn: (id: number) => personalApi.reactivar(id),
    onSuccess: () => {
      toast.success('Relación laboral reactivada.')
      void queryClient.invalidateQueries({ queryKey: ['personal'] })
      void queryClient.invalidateQueries({ queryKey: ['usuarios'] })
      void queryClient.invalidateQueries({ queryKey: ['medicos'] })
    },
    onError: (error) => toast.error(mensajeDeError(error)),
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
          : fila.cuenta?.username ?? `Vinculada (ID ${fila.usuario})`,
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
            disabled={finalizar.isPending || reactivar.isPending}
            onClick={() => setFormulario(fila)}
          >
            Editar
          </Button>

          <Button
            variante="secundario"
            disabled={finalizar.isPending || reactivar.isPending}
            onClick={() => setAVincular(fila)}
          >
            Cuenta
          </Button>

          {fila.estado ? (
            <Button
              variante="peligro"
              disabled={finalizar.isPending || reactivar.isPending}
              onClick={() => setAFinalizar(fila)}
            >
              Finalizar relación
            </Button>
          ) : (
            <Button
              variante="secundario"
              cargando={reactivar.isPending}
              disabled={finalizar.isPending}
              onClick={() => reactivar.mutate(fila.id)}
            >
              Reactivar
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
          Personal
        </h1>

        <Button
          disabled={finalizar.isPending || reactivar.isPending}
          onClick={() => setFormulario(null)}
        >
          Registrar personal
        </Button>
      </div>

      <p className="text-sm text-slate-600">
        Registra al personal de la clínica y vincula sus cuentas de acceso.
        Finalizar una relación bloquea el acceso laboral y conserva el
        historial, la identidad y cualquier acceso como paciente.
      </p>

      <div className="grid gap-3 sm:grid-cols-[minmax(0,20rem)_14rem]">
        <SearchBar
          valor={search}
          onBuscar={setSearch}
          placeholder="Buscar por CI, nombre, apellido o teléfono…"
        />

        <select
          aria-label="Filtrar personal por estado"
          className={inputClass}
          value={estado}
          onChange={(event) => {
            setEstado(event.target.value as 'true' | 'false' | '')
            setPage(1)
          }}
        >
          <option value="true">Personal activo</option>
          <option value="false">Relaciones finalizadas</option>
          <option value="">Todo el personal</option>
        </select>
      </div>

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
          onCreated={(creado) => setAVincular(creado)}
        />
      )}

      {aVincular && (
        <VincularUsuarioModal
          personal={aVincular}
          onClose={() => setAVincular(null)}
        />
      )}

      {aFinalizar && (
        <ConfirmDialog
          titulo="Finalizar relación laboral"
          mensaje={`¿Quieres finalizar la relación laboral de "${aFinalizar.nombre} ${aFinalizar.apellido}"? Se desactivará su acceso laboral y su perfil médico, si existe. Su cuenta, vínculo e historial permanecerán registrados; si también es paciente conservará ese acceso.`}
          textoConfirmar="Finalizar relación"
          cargando={finalizar.isPending}
          onConfirmar={() => {
            if (!finalizar.isPending) {
              finalizar.mutate(aFinalizar.id)
            }
          }}
          onCancelar={() => {
            if (!finalizar.isPending) {
              setAFinalizar(null)
            }
          }}
        />
      )}
    </section>
  )
}
