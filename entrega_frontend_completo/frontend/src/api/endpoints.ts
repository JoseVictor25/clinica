// Rutas relativas a VITE_API_URL (que ya incluye /api/v1). Confirmadas en INFORME_SPRINT1.md.
export const ENDPOINTS = {
  login: '/auth/login/',
  refresh: '/auth/refresh/',
  logout: '/auth/logout/',
  me: '/auth/me/',
} as const