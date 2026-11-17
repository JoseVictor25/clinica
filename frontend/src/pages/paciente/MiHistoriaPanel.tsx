import { useQuery } from '@tanstack/react-query'
import { portalPacienteApi } from '@/api/modules/portalPaciente'
import { Button } from '@/components/ui/Button'
import { mensajeDeError } from '@/lib/errorMessages'

export function MiHistoriaPanel() {
  const query = useQuery({ queryKey: ['portal-paciente', 'historia'], queryFn: portalPacienteApi.miHistoria, retry: false })
  if (query.isLoading) return <p className="text-sm text-slate-600">Cargando tu historia…</p>
  if (query.isError) return <div className="space-y-3 rounded-md bg-amber-50 p-4"><p role="alert" className="text-amber-800">{mensajeDeError(query.error)}</p><Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button></div>
  const h = query.data!
  return <div className="space-y-4">
    <div className="rounded-md border bg-white p-4 text-sm"><p><strong>Abierta:</strong> {h.fecha_apertura}</p><p><strong>Grupo sanguíneo:</strong> {h.grupo_sanguineo}</p><p className="mt-2 whitespace-pre-wrap"><strong>Observaciones:</strong> {h.observaciones_generales || 'Sin observaciones'}</p></div>
    <section className="rounded-md border bg-white p-4"><h2 className="font-semibold">Enfermedades</h2>{h.enfermedades.length === 0 ? <p className="mt-2 text-sm text-slate-500">Sin enfermedades registradas.</p> : <ul className="mt-2 space-y-2 text-sm">{h.enfermedades.map((e) => <li key={e.id}><strong>{e.nombre}</strong> · {e.tipo} · {e.severidad} · {e.fecha_deteccion}</li>)}</ul>}</section>
    <section className="rounded-md border bg-white p-4"><h2 className="font-semibold">Alergias</h2>{h.alergias.length === 0 ? <p className="mt-2 text-sm text-slate-500">Sin alergias registradas.</p> : <ul className="mt-2 space-y-2 text-sm">{h.alergias.map((a) => <li key={a.id}><strong>{a.nombre}</strong> · {a.tipo} · {a.severidad}{a.descripcion ? ` · ${a.descripcion}` : ''}</li>)}</ul>}</section>
  </div>
}
