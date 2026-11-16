import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { portalPacienteApi } from '@/api/modules/portalPaciente'
import { Pagination } from '@/components/data/Pagination'
import { Button } from '@/components/ui/Button'
import { inputClass } from '@/components/ui/styles'
import { mensajeDeError } from '@/lib/errorMessages'
import { RecetaPacienteModal } from './RecetaPacienteModal'

export function MisConsultasPanel() {
  const [page, setPage] = useState(1); const [desde, setDesde] = useState(''); const [hasta, setHasta] = useState(''); const [ordering, setOrdering] = useState<'fecha' | '-fecha'>('-fecha'); const [recetaId, setRecetaId] = useState<number | null>(null)
  const query = useQuery({ queryKey: ['portal-paciente', 'consultas', { page, desde, hasta, ordering }], queryFn: () => portalPacienteApi.misConsultas({ page, fecha_desde: desde || undefined, fecha_hasta: hasta || undefined, ordering }) })
  return <div className="space-y-4"><div className="grid gap-3 rounded-md border bg-white p-4 md:grid-cols-3"><input aria-label="Fecha desde" type="date" className={inputClass} value={desde} onChange={(e) => { setDesde(e.target.value); setPage(1) }} /><input aria-label="Fecha hasta" type="date" className={inputClass} value={hasta} onChange={(e) => { setHasta(e.target.value); setPage(1) }} /><select aria-label="Orden" className={inputClass} value={ordering} onChange={(e) => { setOrdering(e.target.value as 'fecha' | '-fecha'); setPage(1) }}><option value="-fecha">Más recientes</option><option value="fecha">Más antiguas</option></select></div>
  {query.isLoading && <p>Cargando consultas…</p>}{query.isError && <div><p role="alert" className="text-red-700">{mensajeDeError(query.error)}</p><Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button></div>}{query.data?.results.length === 0 && <p className="rounded-md bg-white p-4 text-sm text-slate-500">No hay consultas para estos filtros.</p>}
  <div className="space-y-4">{query.data?.results.map((c) => <article key={c.id} className="rounded-md border bg-white p-4 text-sm"><div className="flex flex-wrap justify-between gap-2"><strong>Consulta del {new Date(c.fecha).toLocaleString()}</strong><span>{c.medico.nombre} · {c.medico.especialidad}</span></div><dl className="mt-3 grid gap-3 md:grid-cols-2"><div><dt className="text-slate-500">Motivo</dt><dd>{c.motivo}</dd></div><div><dt className="text-slate-500">Diagnóstico</dt><dd>{c.diagnostico}</dd></div><div className="md:col-span-2"><dt className="text-slate-500">Observación</dt><dd>{c.observacion}</dd></div></dl><div className="mt-3 border-t pt-3"><strong>Recetas</strong>{c.recetas.length === 0 ? <p className="text-slate-500">Sin recetas.</p> : <div className="mt-2 flex flex-wrap gap-2">{c.recetas.map((r) => <Button key={r.id} variante="secundario" onClick={() => setRecetaId(r.id)}>Receta #{r.id} ({r.cantidad_medicamentos})</Button>)}</div>}</div></article>)}</div><Pagination pagina={page} total={query.data?.count ?? 0} onCambiar={setPage} />{recetaId !== null && <RecetaPacienteModal id={recetaId} onClose={() => setRecetaId(null)} />}</div>
}
