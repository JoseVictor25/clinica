# Código completo por archivo

Las rutas son destinos en el proyecto original. Copia el bloque entero de cada archivo. No elimines archivos.

## REEMPLAZAR: frontend/src/api/client.ts

```ts
import axios from 'axios'
import { authEvents } from './authEvents'
import { ENDPOINTS } from './endpoints'
import { ApiError, normalizarError } from './errors'
import { tokenStorage } from './tokenStorage'

declare module 'axios' {
  interface AxiosRequestConfig {
    skipAuth?: boolean
    _retry?: boolean
  }
}

const baseURL = import.meta.env.VITE_API_URL as string | undefined
if (!baseURL) throw new Error('Falta VITE_API_URL en frontend/.env.')
export const api = axios.create({ baseURL, headers: { 'Content-Type': 'application/json' } })
const plano = axios.create({ baseURL, headers: { 'Content-Type': 'application/json' } })
let refreshPromise: Promise<string> | null = null

function expirar() {
  tokenStorage.clear()
  authEvents.emit('session-expired')
}
async function pedirNuevoAccess(): Promise<string> {
  const refresh = tokenStorage.getRefresh()
  if (!refresh) {
    expirar()
    throw new ApiError({ status: 401, code: 'no_autenticado', message: 'La sesión expiró.' })
  }
  try {
    const { data } = await plano.post<{ access: string; refresh?: string }>(ENDPOINTS.refresh, { refresh })
    if (typeof data.access !== 'string' || !data.access) throw new Error('La respuesta de renovación no contiene un token válido.')
    tokenStorage.set(data.access, data.refresh)
    return data.access
  } catch (fallo) {
    const error = normalizarError(fallo)
    if (error.status === 403 && error.code === 'clinica_inactiva') {
      tokenStorage.clear()
      authEvents.emit('clinica-inactiva')
    } else if ([400, 401, 403].includes(error.status)) {
      expirar()
    }
    throw error
  }
}
export function renovarSesion(): Promise<string> {
  if (!refreshPromise) refreshPromise = pedirNuevoAccess().finally(() => { refreshPromise = null })
  return refreshPromise
}
api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess()
  if (token && !config.skipAuth) config.headers.Authorization = `Bearer ${token}`
  return config
})
api.interceptors.response.use((respuesta) => respuesta, async (fallo: unknown) => {
  const error = normalizarError(fallo)
  const original = axios.isAxiosError(fallo) ? fallo.config : undefined
  if (error.status === 403 && error.code === 'clinica_inactiva') {
    tokenStorage.clear()
    authEvents.emit('clinica-inactiva')
  }
  if (error.status === 403 && error.code === 'suscripcion_vencida') authEvents.emit('suscripcion-vencida')
  if (error.status === 401 && original && !original.skipAuth) {
    if (original._retry) {
      expirar()
      throw error
    }
    original._retry = true
    const nuevo = await renovarSesion()
    original.headers.Authorization = `Bearer ${nuevo}`
    // Los errores del reintento se procesan por el mismo interceptor.
    // Un 400/403 de negocio no debe interpretarse como una sesión expirada.
    return api(original)
  }
  throw error
})
```

## CREAR: frontend/src/api/modules/gestion.ts

```ts
import { api } from '../client'
import type { ListParams, Paginated } from '@/types/api'

export interface Clinica {
  id: number
  nombre: string
  direccion: string
  telefono: string
  email: string
  nit: string
  estado: boolean
}
export interface ClinicaInput {
  nombre: string
  direccion: string
  telefono: string
  email: string
  nit: string
  estado?: boolean
}
export interface ClinicaCreateInput extends Omit<ClinicaInput, 'estado'> {
  admin: { username: string; email: string; password: string }
}
export interface Plan {
  id: number
  nombre: string
  precio: string
  max_usuarios: number
  descripcion: string
  activo: boolean
}
export type PlanInput = Omit<Plan, 'id'>
export interface Medico {
  id: number
  clinica: number
  clinica_nombre: string
  personal: number
  personal_nombre: string
  especialidad: number
  especialidad_nombre: string
  numero_colegiatura: string
  estado: boolean
}
export interface MedicoInput {
  personal: number
  especialidad: number
  numero_colegiatura: string
  estado: boolean
}
export interface Horario {
  id: number
  medico: number
  medico_nombre: string
  dia_semana: number
  hora_inicio: string
  hora_fin: string
}
export interface HorarioInput {
  medico?: number
  dia_semana: number
  hora_inicio: string
  hora_fin: string
}
export interface RecursoApi<T, C, U = Partial<C>> {
  listar: (params?: ListParams) => Promise<Paginated<T>>
  obtener: (id: number) => Promise<T>
  crear: (datos: C) => Promise<T>
  actualizar: (id: number, datos: U) => Promise<T>
  eliminar: (id: number) => Promise<void>
}
function recurso<T, C, U = Partial<C>>(ruta: string): RecursoApi<T, C, U> {
  return {
    listar: async (params = {}) => (await api.get<Paginated<T>>(ruta, { params })).data,
    obtener: async (id) => (await api.get<T>(`${ruta}${id}/`)).data,
    crear: async (datos) => (await api.post<T>(ruta, datos)).data,
    actualizar: async (id, datos) => (await api.patch<T>(`${ruta}${id}/`, datos)).data,
    eliminar: async (id) => { await api.delete(`${ruta}${id}/`) },
  }
}
export const clinicasGestionApi = recurso<Clinica, ClinicaCreateInput, Partial<ClinicaInput>>('/clinicas/')
export const planesGestionApi = recurso<Plan, PlanInput>('/planes/')
export const medicosApi = recurso<Medico, MedicoInput>('/medicos/')
export const horariosApi = recurso<Horario, HorarioInput>('/horarios/')

export async function todasLasPaginas<T>(
  listar: (params?: ListParams) => Promise<Paginated<T>>,
  filtros: ListParams = {},
): Promise<T[]> {
  const filas: T[] = []
  let page = 1
  while (true) {
    const resultado = await listar({ ...filtros, page, page_size: 100 })
    filas.push(...resultado.results)
    if (!resultado.next) return filas
    page += 1
  }
}

export async function cambiarPassword(datos: {
  password_actual: string
  password_nueva: string
}): Promise<{ codigo: string; mensaje: string }> {
  return (await api.post<{ codigo: string; mensaje: string }>('/auth/cambiar-password/', datos)).data
}
```

## CREAR: frontend/src/components/gestion/GestionRecurso.tsx

```tsx
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
```

## REEMPLAZAR: frontend/src/components/ui/Modal.tsx

```tsx
import { useEffect, useRef, type ReactNode } from 'react'

interface Props {
  titulo: string
  onClose: () => void
  children: ReactNode
}

export function Modal({ titulo, onClose, children }: Props) {
  const contenedor = useRef<HTMLDivElement>(null)
  const cerrar = useRef(onClose)

  useEffect(() => {
    cerrar.current = onClose
  }, [onClose])

  useEffect(() => {
    contenedor.current?.focus()
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key === 'Escape') cerrar.current()
    }
    document.addEventListener('keydown', alTeclear)
    return () => document.removeEventListener('keydown', alTeclear)
  }, [])

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={contenedor}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-lg outline-none"
      >
        <h2 className="mb-4 text-lg font-semibold text-slate-900">{titulo}</h2>
        {children}
      </div>
    </div>
  )
}
```

## REEMPLAZAR: frontend/src/lib/navigation.ts

```ts
import {
  Briefcase, Building2, CalendarCheck, Clock, CreditCard,
  HeartPulse, LayoutDashboard, ShieldCheck, Stethoscope, Users, UserRound,
  type LucideIcon,
} from 'lucide-react'
import type { Usuario } from '@/types/auth'
import { esAdminClinica, esAdminSistema, esMedico } from './roles'

export interface ItemNav {
  etiqueta: string
  ruta: string
  icono: LucideIcon
  visible: (usuario: Usuario) => boolean
}
const completo = (usuario: Usuario) => usuario.esAdminSistema || (!usuario.accesoRestringido && usuario.suscripcionVigente)
const admin = (usuario: Usuario) => esAdminClinica(usuario) && completo(usuario)
const clinico = (usuario: Usuario) => (esAdminClinica(usuario) || esMedico(usuario)) && completo(usuario)

export const ITEMS_NAV: ItemNav[] = [
  { etiqueta: 'Inicio', ruta: '/', icono: LayoutDashboard, visible: completo },
  { etiqueta: 'Mi cuenta', ruta: '/cuenta', icono: UserRound, visible: () => true },
  { etiqueta: 'Clínicas', ruta: '/sistema/clinicas', icono: Building2, visible: esAdminSistema },
  { etiqueta: 'Planes', ruta: '/sistema/planes', icono: CreditCard, visible: esAdminSistema },
  { etiqueta: 'Suscripciones', ruta: '/sistema/suscripciones', icono: CalendarCheck, visible: esAdminSistema },
  { etiqueta: 'Mi clínica', ruta: '/mi-clinica', icono: Building2, visible: admin },
  { etiqueta: 'Mi suscripción', ruta: '/suscripciones', icono: CalendarCheck, visible: esAdminClinica },
  { etiqueta: 'Planes disponibles', ruta: '/planes', icono: CreditCard, visible: esAdminClinica },
  { etiqueta: 'Usuarios', ruta: '/usuarios', icono: Users, visible: admin },
  { etiqueta: 'Roles', ruta: '/roles', icono: ShieldCheck, visible: admin },
  { etiqueta: 'Personal', ruta: '/personal', icono: Briefcase, visible: admin },
  { etiqueta: 'Especialidades', ruta: '/especialidades', icono: Stethoscope, visible: clinico },
  { etiqueta: 'Médicos', ruta: '/medicos', icono: HeartPulse, visible: clinico },
  { etiqueta: 'Horarios', ruta: '/horarios', icono: Clock, visible: clinico },
]
```

## REEMPLAZAR: frontend/src/pages/clinica/especialidades/EspecialidadesPage.tsx

```tsx
import { especialidadesApi, type Especialidad } from '@/api/modules/especialidades'
import { GestionRecurso, type ConfiguracionRecurso } from '@/components/gestion/GestionRecurso'
import { useAuth } from '@/hooks/useAuth'
import { esAdminClinica } from '@/lib/roles'

export function EspecialidadesPage() {
  const { usuario } = useAuth()
  const admin = Boolean(usuario && esAdminClinica(usuario))
  const config: ConfiguracionRecurso<Especialidad> = {
    clave: 'especialidades', titulo: 'Especialidades', nuevo: 'Nueva especialidad',
    gestionar: admin, buscar: true,
    listar: especialidadesApi.listar, obtener: especialidadesApi.obtener,
    campos: () => [
      { nombre: 'nombre', etiqueta: 'Nombre', obligatorio: true, maxLength: 100 },
      { nombre: 'descripcion', etiqueta: 'Descripción', tipo: 'textarea' },
      { nombre: 'estado', etiqueta: 'Especialidad activa', tipo: 'checkbox' },
    ],
    iniciales: (registro) => ({ nombre: registro?.nombre ?? '', descripcion: registro?.descripcion ?? '', estado: registro?.estado ?? true }),
    validar: (valores) => {
      const errores: Record<string, string> = {}
      if (!String(valores.nombre).trim()) errores.nombre = 'El nombre es obligatorio.'
      return errores
    },
    guardar: (valores, registro) => {
      const datos = { nombre: String(valores.nombre).trim(), descripcion: String(valores.descripcion), estado: valores.estado === true }
      return registro ? especialidadesApi.actualizar(registro.id, datos) : especialidadesApi.crear(datos)
    },
    eliminar: especialidadesApi.eliminar,
    mensajeEliminar: (registro) => `¿Eliminar "${registro.nombre}"? No se podrá eliminar si algún médico la utiliza.`,
    invalidar: ['medicos'],
    columnas: [
      { encabezado: 'Nombre', celda: (registro) => registro.nombre },
      { encabezado: 'Descripción', celda: (registro) => registro.descripcion || '—' },
      { encabezado: 'Estado', celda: (registro) => registro.estado ? 'Activa' : 'Inactiva' },
    ],
  }
  return <GestionRecurso config={config} />
}
```

## CREAR: frontend/src/pages/clinica/horarios/HorariosPage.tsx

```tsx
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { horariosApi, medicosApi, todasLasPaginas, type Horario } from '@/api/modules/gestion'
import { GestionRecurso, type ConfiguracionRecurso, type CampoFormulario } from '@/components/gestion/GestionRecurso'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { esAdminClinica } from '@/lib/roles'
import { mensajeDeError } from '@/lib/errorMessages'

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
export function HorariosPage() {
  const { usuario } = useAuth()
  const admin = Boolean(usuario && esAdminClinica(usuario))
  const [params] = useSearchParams()
  const medicoParametro = params.get('medico') ?? ''
  const medicos = useQuery({
    queryKey: ['medicos', 'selector', usuario?.clinicaId, usuario?.id],
    queryFn: () => todasLasPaginas(medicosApi.listar),
  })
  const sinMedico = !admin && medicos.isSuccess && medicos.data.length === 0
  const bloqueo = medicos.isError ? mensajeDeError(medicos.error) : medicos.isPending ? 'Cargando médicos…'
    : sinMedico ? 'Tu cuenta no tiene un médico vinculado. Solicita al administrador que complete la vinculación.'
      : admin && medicos.data?.length === 0 ? 'Registra un médico antes de crear horarios.' : null
  const opciones = medicos.data?.map((medico) => ({ valor: String(medico.id), etiqueta: medico.personal_nombre })) ?? []
  const config: ConfiguracionRecurso<Horario> = {
    clave: 'horarios', titulo: admin ? 'Horarios de atención' : 'Mis horarios', nuevo: 'Crear horario',
    descripcion: 'El horario final debe ser posterior al inicial. El servidor impide superponer horarios del mismo médico.',
    bloqueoFormulario: bloqueo,
    listar: (filtros = {}) => horariosApi.listar({ ...(admin && medicoParametro ? { medico: medicoParametro } : {}), ...filtros }),
    obtener: horariosApi.obtener,
    campos: (registro) => {
      const campos: CampoFormulario[] = []
      if (admin) campos.push({ nombre: 'medico', etiqueta: 'Médico', tipo: 'select', obligatorio: true,
        soloLectura: Boolean(registro), opciones,
        ayuda: registro ? 'Para asignar este intervalo a otro médico, elimina el horario y crea uno nuevo.' : undefined })
      else if (registro) campos.push({ nombre: 'medico_nombre', etiqueta: 'Médico', soloLectura: true })
      campos.push(
        { nombre: 'dia_semana', etiqueta: 'Día', tipo: 'select', obligatorio: true, opciones: DIAS.map((dia, indice) => ({ valor: String(indice), etiqueta: dia })) },
        { nombre: 'hora_inicio', etiqueta: 'Hora de inicio', tipo: 'time', obligatorio: true, step: '1' },
        { nombre: 'hora_fin', etiqueta: 'Hora de fin', tipo: 'time', obligatorio: true, step: '1' },
      )
      return campos
    },
    iniciales: (registro) => ({ medico: registro ? String(registro.medico)
      : opciones.some((opcion) => opcion.valor === medicoParametro) ? medicoParametro : '',
      medico_nombre: registro?.medico_nombre ?? '', dia_semana: String(registro?.dia_semana ?? 0),
      hora_inicio: registro?.hora_inicio ?? '08:00:00', hora_fin: registro?.hora_fin ?? '09:00:00' }),
    validar: (valores) => {
      const errores: Record<string, string> = {}
      const segundos = (hora: string) => { const [h = 0, m = 0, s = 0] = hora.split(':').map(Number); return h * 3600 + m * 60 + s }
      if (segundos(String(valores.hora_inicio)) >= segundos(String(valores.hora_fin))) errores.hora_fin = 'La hora final debe ser posterior al inicio.'
      return errores
    },
    guardar: (valores, registro) => {
      const datos = { dia_semana: Number(valores.dia_semana), hora_inicio: String(valores.hora_inicio), hora_fin: String(valores.hora_fin) }
      if (registro) return horariosApi.actualizar(registro.id, datos)
      return horariosApi.crear({ ...datos, ...(admin ? { medico: Number(valores.medico) } : {}) })
    },
    eliminar: horariosApi.eliminar,
    filtros: [
      ...(admin ? [{ nombre: 'medico', etiqueta: 'Médico', opciones }] : []),
      ...(admin ? [{ nombre: 'dia_semana', etiqueta: 'Día', opciones: DIAS.map((dia, indice) => ({ valor: String(indice), etiqueta: dia })) }] : []),
    ],
    columnas: [
      { encabezado: 'Médico', celda: (registro) => registro.medico_nombre },
      { encabezado: 'Día', celda: (registro) => DIAS[registro.dia_semana] ?? String(registro.dia_semana) },
      { encabezado: 'Inicio', celda: (registro) => registro.hora_inicio },
      { encabezado: 'Fin', celda: (registro) => registro.hora_fin },
    ],
  }
  return <>
    {medicoParametro && admin && <p className="mb-3 text-sm">Lista inicial del médico seleccionado. <a className="text-blue-700 underline" href="/horarios">Ver todos los médicos</a></p>}
    {medicos.isError && <Button variante="secundario" onClick={() => void medicos.refetch()}>Reintentar carga de médicos</Button>}
    <GestionRecurso key={medicoParametro || 'todos'} config={config} />
  </>
}
```

## CREAR: frontend/src/pages/clinica/medicos/MedicosPage.tsx

```tsx
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { medicosApi, todasLasPaginas, type Medico } from '@/api/modules/gestion'
import { personalApi } from '@/api/modules/personal'
import { especialidadesApi } from '@/api/modules/especialidades'
import { GestionRecurso, type ConfiguracionRecurso } from '@/components/gestion/GestionRecurso'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { esAdminClinica } from '@/lib/roles'
import { mensajeDeError } from '@/lib/errorMessages'

export function MedicosPage() {
  const { usuario } = useAuth()
  const admin = Boolean(usuario && esAdminClinica(usuario))
  const referencias = useQuery({
    queryKey: ['medicos', 'referencias', usuario?.clinicaId],
    queryFn: async () => {
      const [personal, especialidades, medicos] = await Promise.all([
        personalApi.listarTodos(), todasLasPaginas(especialidadesApi.listar), todasLasPaginas(medicosApi.listar),
      ])
      return { personal, especialidades, medicos }
    },
    enabled: admin,
  })
  const bloqueo = !admin ? null : referencias.isError ? mensajeDeError(referencias.error)
    : referencias.isPending ? 'Cargando personal y especialidades…' : null
  const config: ConfiguracionRecurso<Medico> = {
    clave: 'medicos', titulo: admin ? 'Médicos' : 'Mi registro de médico', nuevo: 'Registrar médico',
    descripcion: admin ? 'Relaciona un registro de personal con su especialidad y colegiatura. El rol Médico se asigna desde Usuarios.'
      : 'Consulta tu registro profesional y accede a tus horarios. Si no aparece, solicita que vinculen tu cuenta a Personal y creen su registro de médico.',
    gestionar: admin, bloqueoFormulario: bloqueo,
    listar: medicosApi.listar, obtener: medicosApi.obtener, buscar: true,
    campos: (registro) => [
      { nombre: 'personal', etiqueta: 'Personal', tipo: 'select', obligatorio: true,
        opciones: referencias.data?.personal.filter((persona) => persona.id === registro?.personal ||
          !referencias.data.medicos.some((medico) => medico.personal === persona.id)).map((persona) => ({
            valor: String(persona.id), etiqueta: `${persona.apellido}, ${persona.nombre} — ${persona.ci}${persona.estado ? '' : ' (inactivo)'}`,
          })) ?? (registro ? [{ valor: String(registro.personal), etiqueta: registro.personal_nombre }] : []) },
      { nombre: 'especialidad', etiqueta: 'Especialidad', tipo: 'select', obligatorio: true,
        opciones: referencias.data?.especialidades.map((especialidad) => ({ valor: String(especialidad.id), etiqueta: `${especialidad.nombre}${especialidad.estado ? '' : ' (inactiva)'}` }))
          ?? (registro ? [{ valor: String(registro.especialidad), etiqueta: registro.especialidad_nombre }] : []) },
      { nombre: 'numero_colegiatura', etiqueta: 'Número de colegiatura', obligatorio: true, maxLength: 30 },
      { nombre: 'estado', etiqueta: 'Médico activo', tipo: 'checkbox' },
    ],
    iniciales: (registro) => ({ personal: registro ? String(registro.personal) : '', especialidad: registro ? String(registro.especialidad) : '',
      numero_colegiatura: registro?.numero_colegiatura ?? '', estado: registro?.estado ?? true }),
    validar: (valores) => {
      const errores: Record<string, string> = {}
      if (!String(valores.numero_colegiatura).trim()) errores.numero_colegiatura = 'La colegiatura es obligatoria.'
      return errores
    },
    guardar: (valores, registro) => {
      const datos = { personal: Number(valores.personal), especialidad: Number(valores.especialidad),
        numero_colegiatura: String(valores.numero_colegiatura).trim(), estado: valores.estado === true }
      return registro ? medicosApi.actualizar(registro.id, datos) : medicosApi.crear(datos)
    },
    eliminar: medicosApi.eliminar,
    mensajeEliminar: (registro) => `¿Eliminar el registro médico de "${registro.personal_nombre}"? Sus horarios se eliminarán. Si tiene relaciones protegidas, no se podrá eliminar. El registro de personal se conserva.`,
    invalidar: ['horarios', 'personal'],
    filtros: admin ? [{ nombre: 'especialidad', etiqueta: 'Especialidad', opciones: referencias.data?.especialidades.map((especialidad) => ({ valor: String(especialidad.id), etiqueta: especialidad.nombre })) ?? [] }] : [],
    columnas: [
      { encabezado: 'Médico', celda: (registro) => registro.personal_nombre },
      { encabezado: 'Especialidad', celda: (registro) => registro.especialidad_nombre },
      { encabezado: 'Colegiatura', celda: (registro) => registro.numero_colegiatura },
      { encabezado: 'Estado', celda: (registro) => registro.estado ? 'Activo' : 'Inactivo' },
    ],
    acciones: (registro) => <Link className="rounded-md border border-slate-300 px-3 py-2 text-sm text-blue-700" to={`/horarios?medico=${registro.id}`}>Horarios</Link>,
  }
  return <>
    {admin && referencias.isError && <Button variante="secundario" onClick={() => void referencias.refetch()}>Reintentar carga de personal y especialidades</Button>}
    <GestionRecurso config={config} />
  </>
}
```

## CREAR: frontend/src/pages/clinica/MiClinicaPage.tsx

```tsx
import { useQuery } from '@tanstack/react-query'
import { clinicasGestionApi } from '@/api/modules/gestion'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'

export function MiClinicaPage() {
  const { usuario } = useAuth()
  const clinica = useQuery({
    queryKey: ['clinicas', 'propia', usuario?.clinicaId],
    queryFn: () => clinicasGestionApi.obtener(usuario!.clinicaId!),
    enabled: usuario?.clinicaId != null,
  })
  return <section className="max-w-xl space-y-4">
    <h1 className="text-2xl font-semibold">Mi clínica</h1>
    <p className="text-sm text-slate-600">El administrador del sistema puede modificar estos datos.</p>
    {clinica.isPending && <p role="status">Cargando…</p>}
    {clinica.isError && <p role="alert">{mensajeDeError(clinica.error)}</p>}
    {clinica.data && <dl className="space-y-2 rounded-xl border border-slate-200 bg-white p-5 text-sm">
      <dt className="font-semibold">Nombre</dt><dd>{clinica.data.nombre}</dd>
      <dt className="font-semibold">NIT</dt><dd>{clinica.data.nit}</dd>
      <dt className="font-semibold">Dirección</dt><dd>{clinica.data.direccion}</dd>
      <dt className="font-semibold">Teléfono</dt><dd>{clinica.data.telefono}</dd>
      <dt className="font-semibold">Correo</dt><dd>{clinica.data.email}</dd>
      <dt className="font-semibold">Estado</dt><dd>{clinica.data.estado ? 'Activa' : 'Inactiva'}</dd>
    </dl>}
    <Button variante="secundario" disabled={clinica.isFetching} onClick={() => void clinica.refetch()}>Actualizar</Button>
  </section>
}
```

## CREAR: frontend/src/pages/clinica/suscripciones/SuscripcionDetalleModal.tsx

```tsx
import { useQuery } from '@tanstack/react-query'
import { suscripcionesApi } from '@/api/modules/suscripciones'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { mensajeDeError } from '@/lib/errorMessages'

export function SuscripcionDetalleModal({ id, onClose }: { id: number; onClose: () => void }) {
  const detalle = useQuery({ queryKey: ['suscripciones', 'detalle', id], queryFn: () => suscripcionesApi.obtener(id) })
  return <Modal titulo="Detalle de suscripción" onClose={onClose}>
    {detalle.isPending && <p role="status">Cargando…</p>}
    {detalle.isError && <div role="alert"><p>{mensajeDeError(detalle.error)}</p><Button onClick={() => void detalle.refetch()}>Reintentar</Button></div>}
    {detalle.data && <dl className="space-y-2 text-sm">
      <dt className="font-semibold">Clínica</dt><dd>{detalle.data.clinica_nombre}</dd>
      <dt className="font-semibold">Plan</dt><dd>{detalle.data.plan_nombre}</dd>
      <dt className="font-semibold">Inicio</dt><dd>{detalle.data.fecha_inicio}</dd>
      <dt className="font-semibold">Fin</dt><dd>{detalle.data.fecha_fin}</dd>
      <dt className="font-semibold">Estado registrado</dt><dd>{detalle.data.estado}</dd>
    </dl>}
    <div className="mt-4 flex justify-end"><Button variante="secundario" onClick={onClose}>Cerrar</Button></div>
  </Modal>
}
```

## REEMPLAZAR: frontend/src/pages/clinica/suscripciones/SuscripcionesPage.tsx

```tsx
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
```

## CREAR: frontend/src/pages/cuenta/CuentaPage.tsx

```tsx
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { normalizarError } from '@/api/errors'
import { cambiarPassword } from '@/api/modules/gestion'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { inputClass } from '@/components/ui/styles'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'

export function CuentaPage() {
  const { usuario, actualizarPerfil } = useAuth()
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [confirmacion, setConfirmacion] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [errores, setErrores] = useState<Record<string, string>>({})
  const refrescar = useMutation({ mutationFn: actualizarPerfil, onError: (fallo) => toast.error(mensajeDeError(fallo)) })
  const guardar = useMutation({
    mutationFn: () => cambiarPassword({ password_actual: actual, password_nueva: nueva }),
    onSuccess: () => { toast.success('Contraseña actualizada.'); setActual(''); setNueva(''); setConfirmacion(''); setErrores({}); setError(null) },
    onError: (fallo) => {
      const normalizado = normalizarError(fallo)
      const campos: Record<string, string> = {}
      for (const [campo, mensajes] of Object.entries(normalizado.fieldErrors)) campos[campo] = mensajes.join(' ')
      if (campos.password) campos.password_nueva = campos.password
      if (normalizado.code === 'password_actual_invalida') campos.password_actual = mensajeDeError(fallo)
      setErrores(campos); setError(mensajeDeError(fallo))
    },
  })
  if (!usuario) return null
  return <section className="max-w-xl space-y-6">
    <h1 className="text-2xl font-semibold">Mi cuenta</h1>
    <dl className="space-y-2 rounded-xl border border-slate-200 bg-white p-5 text-sm">
      <dt className="font-semibold">Usuario</dt><dd>{usuario.username}</dd>
      <dt className="font-semibold">Correo</dt><dd>{usuario.email}</dd>
      <dt className="font-semibold">Clínica</dt><dd>{usuario.clinicaNombre ?? 'Administración del sistema'}</dd>
      <dt className="font-semibold">Roles</dt><dd>{usuario.esAdminSistema ? 'Administrador del sistema' : usuario.roles.join(', ') || 'Sin roles activos'}</dd>
      {usuario.clinicaId !== null && <><dt className="font-semibold">Suscripción</dt><dd>{usuario.suscripcionVigente ? `Vigente hasta ${usuario.suscripcionFin}` : 'Sin suscripción vigente'}</dd></>}
    </dl>
    <Button variante="secundario" cargando={refrescar.isPending} onClick={() => refrescar.mutate()}>Actualizar perfil</Button>
    <form className="space-y-4 rounded-xl border border-slate-200 bg-white p-5" onSubmit={(evento) => {
      evento.preventDefault()
      if (guardar.isPending) return
      setError(null); setErrores({})
      if (nueva !== confirmacion) { setErrores({ confirmacion: 'Las contraseñas no coinciden.' }); return }
      if (actual === nueva) { setErrores({ password_nueva: 'La nueva contraseña debe ser diferente de la actual.' }); return }
      guardar.mutate()
    }}>
      <h2 className="text-lg font-semibold">Cambiar contraseña</h2>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <Field id="password-actual" label="Contraseña actual" error={errores.password_actual}>
        <input id="password-actual" type="password" autoComplete="current-password" className={inputClass} required value={actual} onChange={(e) => setActual(e.target.value)} />
      </Field>
      <Field id="password-nueva" label="Nueva contraseña" error={errores.password_nueva}>
        <input id="password-nueva" type="password" autoComplete="new-password" className={inputClass} required value={nueva} onChange={(e) => setNueva(e.target.value)} />
      </Field>
      <Field id="password-confirmacion" label="Confirmar nueva contraseña" error={errores.confirmacion}>
        <input id="password-confirmacion" type="password" autoComplete="new-password" className={inputClass} required value={confirmacion} onChange={(e) => setConfirmacion(e.target.value)} />
      </Field>
      <Button type="submit" cargando={guardar.isPending}>Actualizar contraseña</Button>
    </form>
  </section>
}
```

## CREAR: frontend/src/pages/sistema/ClinicasPage.tsx

```tsx
import { clinicasGestionApi, type Clinica } from '@/api/modules/gestion'
import { GestionRecurso, type ConfiguracionRecurso, type CampoFormulario } from '@/components/gestion/GestionRecurso'

const campos: CampoFormulario[] = [
  { nombre: 'nombre', etiqueta: 'Nombre', obligatorio: true, maxLength: 150 },
  { nombre: 'direccion', etiqueta: 'Dirección', obligatorio: true, maxLength: 255 },
  { nombre: 'telefono', etiqueta: 'Teléfono', tipo: 'tel', obligatorio: true, maxLength: 30 },
  { nombre: 'email', etiqueta: 'Correo de la clínica', tipo: 'email', obligatorio: true, maxLength: 254 },
  { nombre: 'nit', etiqueta: 'NIT', obligatorio: true, maxLength: 20 },
]
const config: ConfiguracionRecurso<Clinica> = {
  clave: 'clinicas', titulo: 'Clínicas', nuevo: 'Registrar clínica',
  descripcion: 'El registro crea los roles base, las especialidades iniciales y el primer administrador de la clínica.',
  listar: clinicasGestionApi.listar, obtener: clinicasGestionApi.obtener,
  campos: (registro) => registro ? [...campos, { nombre: 'estado', etiqueta: 'Clínica activa', tipo: 'checkbox' }] : [
    ...campos,
    { nombre: 'admin.username', etiqueta: 'Usuario del primer administrador', obligatorio: true, maxLength: 150 },
    { nombre: 'admin.email', etiqueta: 'Correo del primer administrador', tipo: 'email', obligatorio: true, maxLength: 254 },
    { nombre: 'admin.password', etiqueta: 'Contraseña del primer administrador', tipo: 'password', obligatorio: true },
    { nombre: 'confirmacion', etiqueta: 'Confirmar contraseña', tipo: 'password', obligatorio: true },
  ],
  iniciales: (registro) => ({
    nombre: registro?.nombre ?? '', direccion: registro?.direccion ?? '',
    telefono: registro?.telefono ?? '', email: registro?.email ?? '', nit: registro?.nit ?? '',
    estado: registro?.estado ?? true,
    'admin.username': '', 'admin.email': '', 'admin.password': '', confirmacion: '',
  }),
  validar: (valores, registro) => {
    const errores: Record<string, string> = {}
    if (!registro && valores['admin.password'] !== valores.confirmacion) errores.confirmacion = 'Las contraseñas no coinciden.'
    for (const campo of ['nombre', 'direccion', 'telefono', 'email', 'nit']) {
      if (!String(valores[campo]).trim()) errores[campo] = 'Este campo es obligatorio.'
    }
    return errores
  },
  guardar: (valores, registro) => {
    const datos = {
      nombre: String(valores.nombre).trim(), direccion: String(valores.direccion).trim(),
      telefono: String(valores.telefono).trim(), email: String(valores.email).trim(), nit: String(valores.nit).trim(),
    }
    if (registro) return clinicasGestionApi.actualizar(registro.id, { ...datos, estado: valores.estado === true })
    return clinicasGestionApi.crear({ ...datos, admin: {
      username: String(valores['admin.username']).trim(), email: String(valores['admin.email']).trim(),
      password: String(valores['admin.password']),
    } })
  },
  eliminar: clinicasGestionApi.eliminar,
  textoEliminar: 'Desactivar', puedeEliminar: (registro) => registro.estado,
  mensajeEliminar: (registro) => `¿Desactivar la clínica "${registro.nombre}"? Sus usuarios perderán el acceso. Puedes reactivarla desde Editar.`,
  invalidar: ['suscripciones'],
  columnas: [
    { encabezado: 'Nombre', celda: (registro) => registro.nombre },
    { encabezado: 'NIT', celda: (registro) => registro.nit },
    { encabezado: 'Correo', celda: (registro) => registro.email },
    { encabezado: 'Teléfono', celda: (registro) => registro.telefono },
    { encabezado: 'Estado', celda: (registro) => registro.estado ? 'Activa' : 'Inactiva' },
  ],
}
export function ClinicasPage() { return <GestionRecurso config={config} /> }
```

## CREAR: frontend/src/pages/sistema/PlanesPage.tsx

```tsx
import { planesGestionApi, type Plan } from '@/api/modules/gestion'
import { GestionRecurso, type ConfiguracionRecurso } from '@/components/gestion/GestionRecurso'
import { useAuth } from '@/hooks/useAuth'
import { esAdminSistema } from '@/lib/roles'

const config: ConfiguracionRecurso<Plan> = {
  clave: 'planes', titulo: 'Planes de suscripción', nuevo: 'Crear plan',
  listar: planesGestionApi.listar, obtener: planesGestionApi.obtener,
  campos: () => [
    { nombre: 'nombre', etiqueta: 'Nombre', obligatorio: true, maxLength: 80 },
    { nombre: 'precio', etiqueta: 'Precio', tipo: 'number', obligatorio: true, min: 0, max: 99999999.99, step: '0.01' },
    { nombre: 'max_usuarios', etiqueta: 'Máximo de usuarios activos', tipo: 'number', obligatorio: true, min: 1, step: '1' },
    { nombre: 'descripcion', etiqueta: 'Descripción', tipo: 'textarea' },
    { nombre: 'activo', etiqueta: 'Plan activo', tipo: 'checkbox' },
  ],
  iniciales: (registro) => ({
    nombre: registro?.nombre ?? '', precio: registro?.precio ?? '0.00',
    max_usuarios: String(registro?.max_usuarios ?? 1), descripcion: registro?.descripcion ?? '', activo: registro?.activo ?? true,
  }),
  validar: (valores) => {
    const errores: Record<string, string> = {}
    if (!String(valores.nombre).trim()) errores.nombre = 'El nombre es obligatorio.'
    if (!Number.isInteger(Number(valores.max_usuarios)) || Number(valores.max_usuarios) < 1) errores.max_usuarios = 'Introduce un entero mayor a cero.'
    if (!/^\d{1,8}(\.\d{1,2})?$/.test(String(valores.precio))) errores.precio = 'Introduce un precio no negativo con hasta dos decimales.'
    return errores
  },
  guardar: (valores, registro) => {
    const datos = { nombre: String(valores.nombre).trim(), precio: String(valores.precio),
      max_usuarios: Number(valores.max_usuarios), descripcion: String(valores.descripcion), activo: valores.activo === true }
    return registro ? planesGestionApi.actualizar(registro.id, datos) : planesGestionApi.crear(datos)
  },
  eliminar: planesGestionApi.eliminar, textoEliminar: 'Desactivar', puedeEliminar: (registro) => registro.activo,
  mensajeEliminar: (registro) => `¿Desactivar el plan "${registro.nombre}"? No podrá contratarse mientras esté inactivo. Las suscripciones existentes se conservan.`,
  filtros: [{ nombre: 'activo', etiqueta: 'Estado', opciones: [{ valor: 'true', etiqueta: 'Activo' }, { valor: 'false', etiqueta: 'Inactivo' }] }],
  columnas: [
    { encabezado: 'Plan', celda: (registro) => registro.nombre },
    { encabezado: 'Precio', celda: (registro) => registro.precio },
    { encabezado: 'Usuarios', celda: (registro) => registro.max_usuarios },
    { encabezado: 'Estado', celda: (registro) => registro.activo ? 'Activo' : 'Inactivo' },
  ],
}
export function PlanesPage() {
  const { usuario } = useAuth()
  const admin = Boolean(usuario && esAdminSistema(usuario))
  return <GestionRecurso config={{ ...config, gestionar: admin,
    descripcion: admin ? 'Administra los planes ofrecidos por la plataforma.'
      : 'Consulta los planes y sus límites. La contratación se realiza desde Mi suscripción.' }} />
}
```

## REEMPLAZAR: frontend/src/routes/ProtectedRoute.tsx

```tsx
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { PantallaCarga } from '@/components/ui/PantallaCarga'
import { useAuth } from '@/hooks/useAuth'
import { esAdminClinica } from '@/lib/roles'

export function ProtectedRoute() {
  const { usuario, cargando, suscripcionVencida } = useAuth()
  const location = useLocation()
  if (cargando) return <PantallaCarga />
  if (!usuario) return <Navigate to="/login" replace state={{ from: location }} />
  if (suscripcionVencida) {
    const administrador = esAdminClinica(usuario)
    // Perfil y contraseña están disponibles con sesión; planes y suscripción
    // también están permitidos al administrador con acceso restringido.
    const permitidas = administrador ? ['/suscripciones', '/planes', '/cuenta', '/sin-permiso'] : ['/cuenta', '/sin-permiso']
    if (!permitidas.includes(location.pathname)) {
      return <Navigate to={administrador ? '/suscripciones' : '/sin-permiso'} replace />
    }
  }
  return <Outlet />
}
```

## REEMPLAZAR: frontend/src/routes/Raiz.tsx

```tsx
import { Outlet } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthProvider'

export function Raiz() {
  return <AuthProvider><Outlet /></AuthProvider>
}
```

## REEMPLAZAR: frontend/src/routes/router.tsx

```tsx
import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { esAdminClinica, esAdminSistema, esMedico } from '@/lib/roles'
import { LoginPage } from '@/pages/auth/LoginPage'
import { EspecialidadesPage } from '@/pages/clinica/especialidades/EspecialidadesPage'
import { PersonalPage } from '@/pages/clinica/Personal/PersonalPage'
import { RolesPage } from '@/pages/clinica/roles/RolesPage'
import { SuscripcionesPage } from '@/pages/clinica/suscripciones/SuscripcionesPage'
import { UsuariosPage } from '@/pages/clinica/usuarios/UsuariosPage'
import { MedicosPage } from '@/pages/clinica/medicos/MedicosPage'
import { HorariosPage } from '@/pages/clinica/horarios/HorariosPage'
import { MiClinicaPage } from '@/pages/clinica/MiClinicaPage'
import { CuentaPage } from '@/pages/cuenta/CuentaPage'
import { ClinicasPage } from '@/pages/sistema/ClinicasPage'
import { PlanesPage } from '@/pages/sistema/PlanesPage'
import { ClinicaInactivaPage } from '@/pages/errors/ClinicaInactivaPage'
import { NotFoundPage } from '@/pages/errors/NotFoundPage'
import { SinPermisoPage } from '@/pages/errors/SinPermisoPage'
import { InicioPage } from '@/pages/InicioPage'
import { ProtectedRoute } from './ProtectedRoute'
import { Raiz } from './Raiz'
import { RoleRoute } from './RoleRoute'

const adminOMedico = (usuario: Parameters<typeof esAdminClinica>[0]) => esAdminClinica(usuario) || esMedico(usuario)

export const router = createBrowserRouter([
  {
    element: <Raiz />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/clinica-inactiva', element: <ClinicaInactivaPage /> },
      {
        element: <ProtectedRoute />,
        children: [{
          element: <AppLayout />,
          children: [
            { index: true, element: <InicioPage /> },
            { path: 'cuenta', element: <CuentaPage /> },
            { path: 'sin-permiso', element: <SinPermisoPage /> },
            {
              element: <RoleRoute permitir={esAdminSistema} />,
              children: [
                { path: 'sistema/clinicas', element: <ClinicasPage /> },
                { path: 'sistema/planes', element: <PlanesPage /> },
                { path: 'sistema/suscripciones', element: <SuscripcionesPage /> },
              ],
            },
            {
              element: <RoleRoute permitir={esAdminClinica} />,
              children: [
                { path: 'suscripciones', element: <SuscripcionesPage /> },
                { path: 'planes', element: <PlanesPage /> },
                { path: 'mi-clinica', element: <MiClinicaPage /> },
                { path: 'usuarios', element: <UsuariosPage /> },
                { path: 'roles', element: <RolesPage /> },
                { path: 'personal', element: <PersonalPage /> },
              ],
            },
            {
              element: <RoleRoute permitir={adminOMedico} />,
              children: [
                { path: 'especialidades', element: <EspecialidadesPage /> },
                { path: 'medicos', element: <MedicosPage /> },
                { path: 'horarios', element: <HorariosPage /> },
              ],
            },
            { path: '*', element: <NotFoundPage /> },
          ],
        }],
      },
    ],
  },
])
```

