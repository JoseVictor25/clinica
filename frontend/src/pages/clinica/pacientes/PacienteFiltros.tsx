import { SEXOS, type SexoPaciente } from '@/api/modules/pacientes'
import { inputClass } from '@/components/ui/styles'

interface Props { estado: string; sexo: string; onEstado: (v: string) => void; onSexo: (v: string) => void }
export function PacienteFiltros({ estado, sexo, onEstado, onSexo }: Props) {
  return <div className="grid gap-3 sm:grid-cols-2">
    <select aria-label="Filtrar por estado" className={inputClass} value={estado} onChange={(e) => onEstado(e.target.value)}>
      <option value="">Todos los estados</option><option value="true">Activos</option><option value="false">Inactivos</option>
    </select>
    <select aria-label="Filtrar por sexo" className={inputClass} value={sexo} onChange={(e) => onSexo(e.target.value as SexoPaciente | '')}>
      <option value="">Todos</option>{SEXOS.map((s) => <option key={s.valor} value={s.valor}>{s.etiqueta}</option>)}
    </select>
  </div>
}
