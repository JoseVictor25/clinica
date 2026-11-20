import { api } from '../client'

export interface AsistenteRespuesta {
  explicacion: string
  pasos: string[]
  id_accion: string | null
  id_menu: string | null
  ruta_objetivo: string | null
}

export const asistenteApi = {
  async consultar(consulta: string, rutaActual: string): Promise<AsistenteRespuesta> {
    return (
      await api.post<AsistenteRespuesta>(
        '/asistente/consultar/',
        {
          consulta,
          ruta_actual: rutaActual,
        },
        { timeout: 185000 },
      )
    ).data
  },
}
