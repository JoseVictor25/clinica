import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  enfermedadesApi,
  SEVERIDADES_ENFERMEDAD,
  TIPOS_ENFERMEDAD,
  type Enfermedad,
  type SeveridadEnfermedad,
  type TipoEnfermedad,
} from '@/api/modules/enfermedades'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'
import { puedeGestionarEnfermedades } from '@/lib/roles'
import { EnfermedadFormModal } from './EnfermedadFormModal'

const etiquetaTipo = (valor: TipoEnfermedad) => TIPOS_ENFERMEDAD.find((item) => item.valor === valor)?.etiqueta ?? valor
const etiquetaSeveridad = (valor: SeveridadEnfermedad) => SEVERIDADES_ENFERMEDAD.find((item) => item.valor === valor)?.etiqueta ?? valor

export function EnfermedadesPanel({ pacienteId }: { pacienteId: number }) {
  const { usuario } = useAuth()
  const puedeGestionar = Boolean(usuario && puedeGestionarEnfermedades(usuario))
  const [page, setPage] = useState(1)
  const [tipo, setTipo] = useState<TipoEnfermedad | ''>('')
  const [severidad, setSeveridad] = useState<SeveridadEnfermedad | ''>('')
  const [formulario, setFormulario] = useState<Enfermedad | null | undefined>()
  const consulta = useQuery({
    queryKey: ['enfermedades', pacienteId, { page, tipo, severidad }],
    queryFn: () => enfermedadesApi.listar(pacienteId, {
      page,
      tipo: tipo || undefined,
      severidad: severidad || undefined,
      ordering: '-fecha_deteccion',
    }),
  })

  return <section className="mt-6 space-y-3 border-t border-slate-200 pt-5">
    <div className="flex items-center justify-between gap-3">
      <div>
        <h3 className="font-semibold text-slate-900">Enfermedades</h3>
        <p className="text-xs text-slate-500">Antecedentes registrados en la historia clínica.</p>
      </div>
      {puedeGestionar && <Button onClick={() => setFormulario(null)}>Registrar</Button>}
    </div>
    <div className="grid grid-cols-2 gap-2">
      <select aria-label="Filtrar por tipo" className="rounded-md border border-slate-300 px-3 py-2 text-sm" value={tipo} onChange={(evento) => { setTipo(evento.target.value as TipoEnfermedad | ''); setPage(1) }}>
        <option value="">Todos los tipos</option>
        {TIPOS_ENFERMEDAD.map((opcion) => <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>)}
      </select>
      <select aria-label="Filtrar por severidad" className="rounded-md border border-slate-300 px-3 py-2 text-sm" value={severidad} onChange={(evento) => { setSeveridad(evento.target.value as SeveridadEnfermedad | ''); setPage(1) }}>
        <option value="">Todas las severidades</option>
        {SEVERIDADES_ENFERMEDAD.map((opcion) => <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>)}
      </select>
    </div>
    {consulta.isLoading && <p role="status" className="py-4 text-center text-sm text-slate-500">Cargando enfermedades…</p>}
    {consulta.isError && <div className="space-y-2 rounded-md bg-red-50 p-3 text-sm text-red-700"><p role="alert">{mensajeDeError(consulta.error)}</p><Button variante="secundario" onClick={() => void consulta.refetch()}>Reintentar</Button></div>}
    {consulta.data?.results.length === 0 && <p className="py-4 text-center text-sm text-slate-500">No hay enfermedades registradas.</p>}
    {consulta.data?.results.map((enfermedad) => <article key={enfermedad.id} className="rounded-md border border-slate-200 p-3 text-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-900">{enfermedad.nombre}</p>
          <p className="text-slate-600">{etiquetaTipo(enfermedad.tipo)} · {etiquetaSeveridad(enfermedad.severidad)}</p>
          <p className="text-xs text-slate-500">Detectada: {enfermedad.fecha_deteccion}</p>
        </div>
        {puedeGestionar && <Button variante="secundario" onClick={() => setFormulario(enfermedad)}>Editar</Button>}
      </div>
    </article>)}
    {(consulta.data?.count ?? 0) > 20 && <div className="flex items-center justify-between text-sm text-slate-600"><span>Página {page}</span><div className="flex gap-2"><Button variante="secundario" disabled={!consulta.data?.previous} onClick={() => setPage((actual) => actual - 1)}>Anterior</Button><Button variante="secundario" disabled={!consulta.data?.next} onClick={() => setPage((actual) => actual + 1)}>Siguiente</Button></div></div>}
    {formulario !== undefined && <EnfermedadFormModal pacienteId={pacienteId} enfermedad={formulario} onClose={() => setFormulario(undefined)} />}
  </section>
}
