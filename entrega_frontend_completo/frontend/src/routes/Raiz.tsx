import { Outlet } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthProvider'

export function Raiz() {
  return <AuthProvider><Outlet /></AuthProvider>
}
