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
