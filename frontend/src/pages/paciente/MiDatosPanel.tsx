import { useQuery } from '@tanstack/react-query'
import { portalPacienteApi } from '@/api/modules/portalPaciente'
import { Button } from '@/components/ui/Button'
import { mensajeDeError } from '@/lib/errorMessages'

export function MiDatosPanel() {
  const query = useQuery({ queryKey: ['portal-paciente', 'informacion'], queryFn: portalPacienteApi.miInformacion })
  if (query.isLoading) return <p className="text-sm text-slate-600">Cargando tus datos…</p>
  if (query.isError) return <div className="space-y-3"><p role="alert" className="text-red-700">{mensajeDeError(query.error)}</p><Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button></div>
  const p = query.data!
  return <dl className="grid gap-4 rounded-md border bg-white p-5 text-sm md:grid-cols-2">
    <div><dt className="text-slate-500">Nombre</dt><dd>{p.nombre} {p.apellido}</dd></div><div><dt className="text-slate-500">CI</dt><dd>{p.ci}</dd></div>
    <div><dt className="text-slate-500">Fecha de nacimiento</dt><dd>{p.fecha_nacimiento}</dd></div><div><dt className="text-slate-500">Sexo</dt><dd>{p.sexo}</dd></div>
    <div><dt className="text-slate-500">Teléfono</dt><dd>{p.telefono}</dd></div><div><dt className="text-slate-500">Correo</dt><dd>{p.email || 'Sin correo registrado'}</dd></div>
  </dl>
}
