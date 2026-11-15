const REFRESH_KEY = 'clinicas.refresh'

// El access vive solo en memoria; el refresh se persiste para restaurar la sesión.
let accessToken: string | null = null

export const tokenStorage = {
  getAccess: () => accessToken,
  getRefresh(): string | null {
    try {
      return localStorage.getItem(REFRESH_KEY)
    } catch {
      return null
    }
  },
  set(access: string, refresh?: string) {
    accessToken = access
    if (refresh) {
      try {
        localStorage.setItem(REFRESH_KEY, refresh)
      } catch {
        /* almacenamiento no disponible */
      }
    }
  },
  clear() {
    accessToken = null
    try {
      localStorage.removeItem(REFRESH_KEY)
    } catch {
      /* almacenamiento no disponible */
    }
  },
}