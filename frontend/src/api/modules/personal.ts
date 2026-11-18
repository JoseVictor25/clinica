import type { ListParams, Paginated } from '@/types/api'
import type { IdentidadCompartida } from '@/types/identidad'
import { api } from '../client'
import type { CuentaResumen, UsuarioClinica } from './usuarios'

export type CargoPersonal =
  | 'MEDICO'
  | 'ENFERMERIA'
  | 'RECEPCION'
  | 'CONDUCTOR'
  | 'OTRO'

export const CARGOS_PERSONAL: {
  valor: CargoPersonal
  etiqueta: string
}[] = [
  { valor: 'MEDICO', etiqueta: 'Médico' },
  { valor: 'ENFERMERIA', etiqueta: 'Enfermería' },
  { valor: 'RECEPCION', etiqueta: 'Recepción' },
  { valor: 'CONDUCTOR', etiqueta: 'Conductor' },
  { valor: 'OTRO', etiqueta: 'Otro' },
]

export interface Personal {
  id: number
  clinica: number
  clinica_nombre: string
  usuario: number | null
  cuenta: CuentaResumen | null
  ci: string
  nombre: string
  apellido: string
  telefono: string
  cargo: CargoPersonal
  /** Fecha YYYY-MM-DD. */
  fecha_ingreso: string
  estado: boolean
}

export interface PersonalInput {
  ci: string
  nombre: string
  apellido: string
  telefono: string
  cargo: CargoPersonal
  fecha_ingreso: string
  estado: boolean
}

export interface CrearCuentaPersonalInput {
  username: string
  email: string
  password: string
  roles: number[]
}

export const personalApi = {
  async identidadPorCi(ci: string): Promise<IdentidadCompartida> {
    const { data } = await api.get<IdentidadCompartida>(
      '/personal/identidad-por-ci/',
      { params: { ci } },
    )
    return data
  },

  async listar(
    params: ListParams = {},
  ): Promise<Paginated<Personal>> {
    const { data } = await api.get<Paginated<Personal>>(
      '/personal/',
      { params },
    )

    return data
  },

  async obtener(id: number): Promise<Personal> {
    const { data } = await api.get<Personal>(
      `/personal/${id}/`,
    )

    return data
  },

  async crear(datos: PersonalInput): Promise<Personal> {
    const { data } = await api.post<Personal>(
      '/personal/',
      datos,
    )

    return data
  },

  async actualizar(
    id: number,
    datos: Partial<PersonalInput>,
  ): Promise<Personal> {
    const { data } = await api.patch<Personal>(
      `/personal/${id}/`,
      datos,
    )

    return data
  },

  /** Finaliza la relación laboral sin eliminar identidad ni historial. */
  async finalizarRelacion(id: number): Promise<void> {
    await api.delete(`/personal/${id}/`)
  },

  async reactivar(id: number): Promise<Personal> {
    return personalApi.actualizar(id, { estado: true })
  },

  /** Enviar null corrige un vínculo erróneo sin actividad profesional. */
  async vincularUsuario(
    personalId: number,
    usuarioId: number | null,
  ): Promise<Personal> {
    const { data } = await api.post<Personal>(
      `/personal/${personalId}/vincular-usuario/`,
      { usuario_id: usuarioId },
    )

    return data
  },

  async crearCuenta(
    personalId: number,
    datos: CrearCuentaPersonalInput,
  ): Promise<Personal> {
    const { data } = await api.post<Personal>(
      `/personal/${personalId}/crear-cuenta/`,
      datos,
    )
    return data
  },

  async cuentasElegibles(
    personalId: number,
    params: ListParams = {},
  ): Promise<Paginated<UsuarioClinica>> {
    const { data } = await api.get<Paginated<UsuarioClinica>>(
      `/personal/${personalId}/cuentas-elegibles/`,
      { params },
    )
    return data
  },

  /** Obtiene todas las páginas para los selectores de personal. */
  async listarTodos(): Promise<Personal[]> {
    const registros: Personal[] = []
    let page = 1

    while (true) {
      const { data } = await api.get<Paginated<Personal>>(
        '/personal/',
        {
          params: {
            page,
            page_size: 100,
          },
        },
      )

      registros.push(...data.results)

      if (!data.next) {
        return registros
      }

      page += 1
    }
  },
}
