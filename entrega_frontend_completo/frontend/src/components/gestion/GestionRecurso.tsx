import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type ReactNode, type ChangeEvent } from 'react'
import { toast } from 'sonner'
import { normalizarError } from '@/api/errors'
import type { ListParams, Paginated } from '@/types/api'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Field } from '@/components/ui/Field'
import { inputClass } from '@/components/ui/styles'
import { DataTable, type Columna } from '@/components/data/DataTable'

export type ValoresFormulario = Record<string, string | boolean>
export interface Opcion { valor: string; etiqueta: string }
export interface CampoFormulario {
  nombre: string
  etiqueta: string
  tipo?: 'text' | 'email' | 'password' | 'number' | 'date' | 'time' | 'tel' | 'textarea' | 'select' | 'checkbox'
  obligatorio?: boolean
  maxLength?: number
  min?: number | string
  max?: number | string
  step?: string
  patron?: string
  opciones?: Opcion[]
  soloLectura?: boolean
  ayuda?: string
}
export interface ConfiguracionRecurso<T extends { id: number }> {
  clave: string
  titulo: string
  nuevo: string
  descripcion?: string
  listar: (params?: ListParams) => Promise<Paginated<T>>
  obtener: (id: number) => Promise<T>
  guardar: (valores: ValoresFormulario, registro: T | null) => Promise<unknown>
  eliminar?: (id: number) => Promise<void>
  textoEliminar?: string
  mensajeEliminar?: (registro: T) => string
  puedeEliminar?: (registro: T) => boolean
  campos: (registro: T | null) => CampoFormulario[]
  iniciales: (registro: T | null) => ValoresFormulario
  columnas: Columna<T>[]
  buscar?: boolean
  filtros?: { nombre: string; etiqueta: string; opciones: Opcion[] }[]
  gestionar?: boolean
  bloqueoFormulario?: string | null
  validar?: (valores: ValoresFormulario, registro: T | null) => Record<string, string>
  invalidar?: string[]
  despuesGuardar?: () => Promise<unknown>
  acciones?: (registro: T) => ReactNode
}

function erroresAnidados(valor: unknown, prefijo = ''): Record<string, string> {
  if (typeof valor === 'string') return prefijo ? { [prefijo]: valor } : {}
  if (Array.isArray(valor)) {
    return prefijo ? { [prefijo]: valor.map(String).join(' ') } : {}
  }
  if (!valor || typeof valor !== 'object') return {}
  return Object.assign({}, ...Object.entries(valor).map(([clave, contenido]) =>
    erroresAnidados(contenido, prefijo ? `${prefijo}.${clave}` : clave),
  )) as Record<string, string>
}

export function FormularioRecurso<T extends { id: number }>({
  config, registro, lectura = false, onClose,
}: {
  config: ConfiguracionRecurso<T>
  registro: T | null
  lectura?: boolean
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [valores, setValores] = useState(() => config.iniciales(registro))
  const [errores, setErrores] = useState<Record<string, string>>({})
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null)
  const campos = config.campos(registro)
  const guardar = useMutation({
    mutationFn: () => config.guardar(valores, registro),
    onSuccess: async () => {
      toast.success('Cambios guardados.')
      for (const clave of new Set([config.clave, ...(config.invalidar ?? [])])) {
        void queryClient.invalidateQueries({ queryKey: [clave] })
      }
      try { await config.despuesGuardar?.() }
      catch { toast.warning('El cambio se guardó. Recarga la página para actualizar tu perfil.') }
      onClose()
    },
    onError: (error) => {
      const normalizado = normalizarError(error)
      setErrores(erroresAnidados(normalizado.details))
      setErrorGeneral(mensajeDeError(error))
    },
  })
  function cerrar() { if (!guardar.isPending) onClose() }
  return (
    <Modal titulo={`${lectura ? 'Consultar' : registro ? 'Editar' : 'Registrar'}: ${config.titulo}`} onClose={cerrar}>
      <form className="max-h-[75vh] space-y-4 overflow-y-auto pr-1" onSubmit={(evento) => {
        evento.preventDefault()
        if (lectura || guardar.isPending || config.bloqueoFormulario) return
        const validacion = config.validar?.(valores, registro) ?? {}
        setErrores(validacion)
        setErrorGeneral(null)
        if (Object.keys(validacion).length === 0) guardar.mutate()
      }}>
        {errorGeneral && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{errorGeneral}</p>}
        {!lectura && config.bloqueoFormulario && <p role="alert">{config.bloqueoFormulario}</p>}
        {campos.map((campo) => {
          const id = `campo-${campo.nombre.replaceAll('.', '-')}`
          const valor = valores[campo.nombre] ?? ''
          const soloLectura = lectura || campo.soloLectura
          if (campo.tipo === 'checkbox') return (
            <div key={campo.nombre}>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={valor === true} disabled={soloLectura || guardar.isPending}
                  onChange={(e) => setValores((actual) => ({ ...actual, [campo.nombre]: e.target.checked }))} />
                {campo.etiqueta}
              </label>
              {errores[campo.nombre] && <p role="alert" className="text-sm text-red-600">{errores[campo.nombre]}</p>}
            </div>
          )
          if (lectura) {
            const texto = campo.opciones?.find((opcion) => opcion.valor === String(valor))?.etiqueta ?? String(valor)
            return <div key={campo.nombre}><p className="text-sm font-medium text-slate-700">{campo.etiqueta}</p><p className="whitespace-pre-wrap break-words text-sm">{texto || '—'}</p></div>
          }
          const comunes = {
            id, className: inputClass, value: String(valor), required: campo.obligatorio,
            disabled: guardar.isPending, 'aria-invalid': Boolean(errores[campo.nombre]),
            'aria-describedby': errores[campo.nombre] ? `${id}-error` : undefined,
            onChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
              setValores((actual) => ({ ...actual, [campo.nombre]: e.target.value })),
          }
          return (
            <Field key={campo.nombre} id={id} label={campo.etiqueta} error={errores[campo.nombre]}>
              {campo.tipo === 'select' ? (
                <select {...comunes} disabled={guardar.isPending || soloLectura}>
                  <option value="">Selecciona una opción</option>
                  {valor !== '' && !campo.opciones?.some((opcion) => opcion.valor === String(valor)) &&
                    <option value={String(valor)}>{String(valor)}</option>}
                  {campo.opciones?.map((opcion) => <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>)}
                </select>
              ) : campo.tipo === 'textarea' ? (
                <textarea {...comunes} rows={3} readOnly={soloLectura} maxLength={campo.maxLength} />
              ) : (
                <input {...comunes} type={campo.tipo ?? 'text'} readOnly={soloLectura}
                  maxLength={campo.maxLength} min={campo.min} max={campo.max} step={campo.step}
                  pattern={campo.patron} autoComplete={campo.tipo === 'password' ? 'new-password' : undefined} />
              )}
              {campo.ayuda && <p className="text-xs text-slate-500">{campo.ayuda}</p>}
            </Field>
          )
        })}
        <div className="flex justify-end gap-2 pt-2">
          <Button variante="secundario" disabled={guardar.isPending} onClick={cerrar}>{lectura ? 'Cerrar' : 'Cancelar'}</Button>
          {!lectura && <Button type="submit" cargando={guardar.isPending} disabled={Boolean(config.bloqueoFormulario)}>Guardar</Button>}
        </div>
      </form>
    </Modal>
  )
}

export function GestionRecurso<T extends { id: number }>({ config }: { config: ConfiguracionRecurso<T> }) {
  const { usuario } = useAuth()
  const queryClient = useQueryClient()
  const [pagina, setPagina] = useState(1)
  const [busqueda, setBusqueda] = useState('')
  const [buscar, setBuscar] = useState('')
  const [filtros, setFiltros] = useState<Record<string, string>>({})
  const [editor, setEditor] = useState<{ modo: 'crear' | 'editar' | 'ver'; id?: number } | null>(null)
  const [aEliminar, setAEliminar] = useState<T | null>(null)
  const gestionar = config.gestionar !== false
  const lista = useQuery({
    queryKey: [config.clave, 'lista', usuario?.clinicaId ?? 'sistema', pagina, buscar, filtros],
    queryFn: () => config.listar({
      page: pagina, page_size: 20,
      ...(config.buscar && buscar ? { search: buscar } : {}),
      ...Object.fromEntries(Object.entries(filtros).filter(([, valor]) => valor !== '')),
    }),
  })
  const detalle = useQuery({
    queryKey: [config.clave, 'detalle', editor?.id],
    queryFn: () => config.obtener(editor!.id!),
    enabled: editor?.id !== undefined,
  })
  const eliminar = useMutation({
    mutationFn: (id: number) => config.eliminar!(id),
    onSuccess: () => {
      toast.success('Operación completada.')
      setAEliminar(null)
      if (lista.data?.results.length === 1 && pagina > 1) setPagina((actual) => actual - 1)
      for (const clave of new Set([config.clave, ...(config.invalidar ?? [])])) {
        void queryClient.invalidateQueries({ queryKey: [clave] })
      }
    },
    onError: (error) => toast.error(mensajeDeError(error)),
  })
  const columnas: Columna<T>[] = [...config.columnas, {
    encabezado: 'Acciones',
    celda: (fila) => <div className="flex flex-wrap gap-2">
      <Button variante="secundario" onClick={() => setEditor({ modo: 'ver', id: fila.id })}>Consultar</Button>
      {gestionar && <Button variante="secundario" disabled={Boolean(config.bloqueoFormulario) || eliminar.isPending} onClick={() => setEditor({ modo: 'editar', id: fila.id })}>Editar</Button>}
      {gestionar && config.eliminar && (config.puedeEliminar?.(fila) ?? true) &&
        <Button variante="peligro" disabled={eliminar.isPending} onClick={() => setAEliminar(fila)}>{config.textoEliminar ?? 'Eliminar'}</Button>}
      {config.acciones?.(fila)}
    </div>,
  }]
  return <section className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-2xl font-semibold text-slate-900">{config.titulo}</h1>
      <div className="flex gap-2">
        <Button variante="secundario" disabled={lista.isFetching} onClick={() => void lista.refetch()}>Actualizar</Button>
        {gestionar && <Button disabled={Boolean(config.bloqueoFormulario)} onClick={() => setEditor({ modo: 'crear' })}>{config.nuevo}</Button>}
      </div>
    </div>
    {config.descripcion && <p className="text-sm text-slate-600">{config.descripcion}</p>}
    {config.bloqueoFormulario && gestionar && <p role="status" className="text-sm text-amber-800">{config.bloqueoFormulario}</p>}
    <div className="flex flex-wrap items-end gap-3">
      {config.buscar && <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setBuscar(busqueda.trim()); setPagina(1) }}>
        <input type="search" className={inputClass} aria-label="Buscar" placeholder="Buscar…" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
        <Button type="submit" variante="secundario">Buscar</Button>
      </form>}
      {config.filtros?.map((filtro) => <label key={filtro.nombre} className="text-sm">
        {filtro.etiqueta}
        <select className={inputClass} value={filtros[filtro.nombre] ?? ''} onChange={(e) => { setFiltros((actual) => ({ ...actual, [filtro.nombre]: e.target.value })); setPagina(1) }}>
          <option value="">Todos</option>
          {filtro.opciones.map((opcion) => <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>)}
        </select>
      </label>)}
    </div>
    <DataTable filas={lista.data?.results} columnas={columnas} claveFila={(fila) => fila.id}
      cargando={lista.isPending} error={lista.isError ? mensajeDeError(lista.error) : null} textoVacio="No hay registros para mostrar." />
    <nav aria-label="Paginación" className="flex items-center justify-between gap-3 text-sm">
      <span>Página {pagina} · {lista.data?.count ?? 0} registros</span>
      <div className="flex gap-2">
        <Button variante="secundario" disabled={pagina <= 1 || lista.isFetching} onClick={() => setPagina((actual) => actual - 1)}>Anterior</Button>
        <Button variante="secundario" disabled={!lista.data?.next || lista.isFetching} onClick={() => setPagina((actual) => actual + 1)}>Siguiente</Button>
      </div>
    </nav>
    {editor?.modo === 'crear' && <FormularioRecurso config={config} registro={null} onClose={() => setEditor(null)} />}
    {editor && editor.modo !== 'crear' && (detalle.isPending || detalle.isError) &&
      <Modal titulo="Consultar registro" onClose={() => setEditor(null)}>
        <p role="status">{detalle.isError ? mensajeDeError(detalle.error) : 'Cargando…'}</p>
        {detalle.isError && <Button onClick={() => void detalle.refetch()}>Reintentar</Button>}
        <Button variante="secundario" onClick={() => setEditor(null)}>Cerrar</Button>
      </Modal>}
    {editor && editor.modo !== 'crear' && detalle.isSuccess &&
      <FormularioRecurso key={`${editor.modo}-${detalle.data.id}`} config={config} registro={detalle.data} lectura={editor.modo === 'ver'} onClose={() => setEditor(null)} />}
    {aEliminar && <ConfirmDialog titulo={config.textoEliminar ?? 'Eliminar registro'}
      mensaje={config.mensajeEliminar?.(aEliminar) ?? '¿Confirmas la eliminación? Esta acción es permanente.'}
      textoConfirmar={config.textoEliminar ?? 'Eliminar'} cargando={eliminar.isPending}
      onConfirmar={() => { if (!eliminar.isPending) eliminar.mutate(aEliminar.id) }}
      onCancelar={() => { if (!eliminar.isPending) setAEliminar(null) }} />}
  </section>
}
