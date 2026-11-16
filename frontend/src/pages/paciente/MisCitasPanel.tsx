import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { portalPacienteApi } from '@/api/modules/portalPaciente'
import { Pagination } from '@/components/data/Pagination'
import { Button } from '@/components/ui/Button'
import { inputClass } from '@/components/ui/styles'
import { mensajeDeError } from '@/lib/errorMessages'

export function MisCitasPanel() {
  const [page, setPage] = useState(1); const [desde, setDesde] = useState(''); const [hasta, setHasta] = useState(''); const [estado, setEstado] = useState(''); const [ordering, setOrdering] = useState<'fecha' | '-fecha'>('-fecha')
  const query = useQuery({ queryKey: ['portal-paciente', 'citas', { page, desde, hasta, estado, ordering }], queryFn: () => portalPacienteApi.misCitas({ page, fecha_desde: desde || undefined, fecha_hasta: hasta || undefined, estado: estado || undefined, ordering }) })
  return <div className="space-y-4"><div className="grid gap-3 rounded-md border bg-white p-4 md:grid-cols-4">
    <input aria-label="Fecha desde" type="date" className={inputClass} value={desde} onChange={(e) => { setDesde(e.target.value); setPage(1) }} /><input aria-label="Fecha hasta" type="date" className={inputClass} value={hasta} onChange={(e) => { setHasta(e.target.value); setPage(1) }} />
    <select aria-label="Estado" className={inputClass} value={estado} onChange={(e) => { setEstado(e.target.value); setPage(1) }}><option value="">Todos los estados</option>{['PROGRAMADA','CONFIRMADA','ATENDIDA','CANCELADA','NO_ASISTIO'].map((v) => <option key={v} value={v}>{v}</option>)}</select>
    <select aria-label="Orden" className={inputClass} value={ordering} onChange={(e) => { setOrdering(e.target.value as 'fecha' | '-fecha'); setPage(1) }}><option value="-fecha">Más recientes</option><option value="fecha">Más antiguas</option></select>
  </div>{query.isLoading && <p>Cargando citas…</p>}{query.isError && <div><p role="alert" className="text-red-700">{mensajeDeError(query.error)}</p><Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button></div>}
  {query.data?.results.length === 0 && <p className="rounded-md bg-white p-4 text-sm text-slate-500">No hay citas para estos filtros.</p>}
  <div className="space-y-3">{query.data?.results.map((c) => <article key={c.id} className="rounded-md border bg-white p-4 text-sm"><div className="flex justify-between"><strong>{c.fecha} · {c.hora.slice(0,5)}</strong><span>{c.estado}</span></div><p className="mt-2">{c.motivo}</p><p className="text-slate-600">{c.medico.nombre} · {c.medico.especialidad}</p></article>)}</div><Pagination pagina={page} total={query.data?.count ?? 0} onCambiar={setPage} /></div>
}
