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
