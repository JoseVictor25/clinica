import { useQueryClient } from '@tanstack/react-query'
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { authEvents } from '@/api/authEvents'
import { renovarSesion } from '@/api/client'
import { login, logout, obtenerPerfil } from '@/api/modules/auth'
import { tokenStorage } from '@/api/tokenStorage'
import type { Usuario } from '@/types/auth'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [cargando, setCargando] = useState(true)

  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // El modo restringido se deriva del perfil del usuario.
  const suscripcionVencida =
    usuario !== null &&
    usuario.clinicaId !== null &&
    !usuario.esAdminSistema &&
    (usuario.accesoRestringido || !usuario.suscripcionVigente)

  // Escuchar los cambios de autenticación detectados por el cliente HTTP.
  useEffect(() => {
    const offExpirada = authEvents.on('session-expired', () => {
      setUsuario(null)
      queryClient.clear()
      toast.error('Tu sesión expiró. Inicia sesión nuevamente.')
      navigate('/login', { replace: true })
    })

    const offInactiva = authEvents.on('clinica-inactiva', () => {
      setUsuario(null)
      queryClient.clear()
      navigate('/clinica-inactiva', { replace: true })
    })

    const offVencida = authEvents.on('suscripcion-vencida', () => {
      setUsuario((actual) => {
        if (
          !actual ||
          actual.esAdminSistema ||
          actual.clinicaId === null
        ) {
          return actual
        }

        return {
          ...actual,
          suscripcionVigente: false,
          suscripcionFin: null,
          accesoRestringido: true,
        }
      })
    })

    return () => {
      offExpirada()
      offInactiva()
      offVencida()
    }
  }, [navigate, queryClient])

  // Restaurar la sesión y consultar el estado actual de la suscripción.
  useEffect(() => {
    let activo = true

    async function restaurar() {
      if (!tokenStorage.getRefresh()) {
        if (activo) setCargando(false)
        return
      }

      try {
        await renovarSesion()
        const perfil = await obtenerPerfil()

        if (activo) {
          setUsuario(perfil)
        }
      } catch {
        if (activo) {
          tokenStorage.clear()
          setUsuario(null)
          queryClient.clear()
        }
      } finally {
        if (activo) {
          setCargando(false)
        }
      }
    }

    void restaurar()

    return () => {
      activo = false
    }
  }, [queryClient])

  const iniciarSesion = useCallback(
    async (username: string, password: string): Promise<Usuario> => {
      const perfil = await login(username, password)

      queryClient.clear()
      setUsuario(perfil)

      return perfil
    },
    [queryClient],
  )

  const cerrarSesion = useCallback(async (): Promise<void> => {
    await logout()

    setUsuario(null)
    queryClient.clear()
    navigate('/login', { replace: true })
  }, [navigate, queryClient])

  const actualizarPerfil = useCallback(async (): Promise<Usuario> => {
    const perfil = await obtenerPerfil()

    setUsuario((actual) => {
      // Evita restaurar un usuario que cerró sesión mientras se consultaba.
      if (!actual || actual.id !== perfil.id) {
        return actual
      }

      return perfil
    })

    return perfil
  }, [])

  const valor = useMemo(
    () => ({
      usuario,
      cargando,
      suscripcionVencida,
      iniciarSesion,
      cerrarSesion,
      actualizarPerfil,
    }),
    [
      usuario,
      cargando,
      suscripcionVencida,
      iniciarSesion,
      cerrarSesion,
      actualizarPerfil,
    ],
  )

  return (
    <AuthContext.Provider value={valor}>
      {children}
    </AuthContext.Provider>
  )
}