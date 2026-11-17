import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { MiDatosPanel } from './MiDatosPanel'
import { MiHistoriaPanel } from './MiHistoriaPanel'
import { MisCitasPanel } from './MisCitasPanel'
import { MisConsultasPanel } from './MisConsultasPanel'

type Seccion = 'datos' | 'historia' | 'citas' | 'consultas'
const OPCIONES: { id: Seccion; texto: string }[] = [{ id: 'datos', texto: 'Mis datos' }, { id: 'historia', texto: 'Mi historia clínica' }, { id: 'citas', texto: 'Mis citas' }, { id: 'consultas', texto: 'Mis consultas y recetas' }]

export function PortalPacientePage() {
  const [seccion, setSeccion] = useState<Seccion>('datos')
  return <section className="space-y-5"><div><h1 className="text-2xl font-semibold">Mi información</h1><p className="mt-1 text-sm text-slate-600">Consulta tus datos clínicos. Este portal es de solo lectura.</p></div><nav className="flex flex-wrap gap-2">{OPCIONES.map((o) => <Button key={o.id} variante={seccion === o.id ? 'primario' : 'secundario'} onClick={() => setSeccion(o.id)}>{o.texto}</Button>)}</nav>{seccion === 'datos' && <MiDatosPanel />}{seccion === 'historia' && <MiHistoriaPanel />}{seccion === 'citas' && <MisCitasPanel />}{seccion === 'consultas' && <MisConsultasPanel />}</section>
}
