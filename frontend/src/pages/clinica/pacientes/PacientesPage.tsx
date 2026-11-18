import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { pacientesApi, SEXOS, type Paciente } from '@/api/modules/pacientes'
import { DataTable, type Columna } from '@/components/data/DataTable'
import { Pagination } from '@/components/data/Pagination'
import { SearchBar } from '@/components/data/SearchBar'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'
import { esAdminClinica, esMedico, puedeGestionarPacientes } from '@/lib/roles'
import { PacienteDetalleModal } from './PacienteDetalleModal'
import { PacienteFiltros } from './PacienteFiltros'
import { PacienteFormModal } from './PacienteFormModal'
import { VincularPacienteUsuarioModal } from './VincularPacienteUsuarioModal'

export function PacientesPage() {
  const navigate = useNavigate()
  const { usuario } = useAuth(); const puedeGestionar = Boolean(usuario && puedeGestionarPacientes(usuario)); const qc = useQueryClient()
  const puedeVerHistorial = Boolean(usuario && esMedico(usuario))
  const puedeVincular = Boolean(usuario && esAdminClinica(usuario))
  const [page, setPage] = useState(1); const [search, setSearch] = useState(''); const [estado, setEstado] = useState(''); const [sexo, setSexo] = useState('')
  const [form, setForm] = useState<Paciente | null | undefined>(); const [detalle, setDetalle] = useState<number | null>(null); const [aCambiar, setACambiar] = useState<Paciente | null>(null)
  const [aVincular, setAVincular] = useState<Paciente | null>(null)
  const query = useQuery({ queryKey: ['pacientes', { page, search, estado, sexo }], queryFn: () => pacientesApi.listar({ page, search: search || undefined, estado: estado || undefined, sexo: sexo || undefined }) })
  const cambiarEstado = useMutation({ mutationFn: async (p: Paciente) => p.estado ? pacientesApi.desactivar(p.id) : pacientesApi.actualizar(p.id, { estado: true }), onSuccess: () => { toast.success(aCambiar?.estado ? 'Paciente desactivado.' : 'Paciente reactivado.'); setACambiar(null); void qc.invalidateQueries({ queryKey: ['pacientes'] }) }, onError: (e) => toast.error(mensajeDeError(e)) })
  const columnas: Columna<Paciente>[] = [
    { encabezado: 'Paciente', celda: (p) => <span className="font-medium">{p.apellido}, {p.nombre}</span> }, { encabezado: 'CI', celda: (p) => p.ci }, { encabezado: 'Sexo', celda: (p) => SEXOS.find((s) => s.valor === p.sexo)?.etiqueta }, { encabezado: 'Teléfono', celda: (p) => p.telefono },
    { encabezado: 'Estado', celda: (p) => <span className={`rounded-full px-2 py-1 text-xs ${p.estado ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}`}>{p.estado ? 'Activo' : 'Inactivo'}</span> },
    { encabezado: 'Acciones', className: 'text-right', celda: (p) => <div className="flex flex-wrap justify-end gap-2"><Button variante="secundario" onClick={() => setDetalle(p.id)}>Ver</Button>{puedeVincular && p.estado && <Button variante="secundario" onClick={() => setAVincular(p)}>Cuenta</Button>}{puedeVerHistorial && p.estado && <Button variante="secundario" onClick={() => navigate(`/pacientes/${p.id}/historial`)}>Historial</Button>}{puedeGestionar && <><Button variante="secundario" onClick={() => setForm(p)}>Editar</Button><Button variante={p.estado ? 'peligro' : 'secundario'} onClick={() => setACambiar(p)}>{p.estado ? 'Desactivar' : 'Reactivar'}</Button></>}</div> },
  ]
  return <section className="space-y-4"><div className="flex items-center justify-between"><h1 className="text-2xl font-semibold">Pacientes</h1>{puedeGestionar && <Button onClick={() => setForm(null)}>Registrar paciente</Button>}</div>
    <p className="text-sm text-slate-600">Consulta y administra los datos generales de los pacientes de tu clínica.</p>
    <SearchBar valor={search} onBuscar={(v) => { setSearch(v); setPage(1) }} placeholder="Buscar por CI, nombre, apellido, teléfono o correo…" />
    <PacienteFiltros estado={estado} sexo={sexo} onEstado={(v) => { setEstado(v); setPage(1) }} onSexo={(v) => { setSexo(v); setPage(1) }} />
    <DataTable filas={query.data?.results} columnas={columnas} claveFila={(p) => p.id} cargando={query.isLoading} error={query.isError ? mensajeDeError(query.error) : null} textoVacio={search || estado || sexo ? 'No se encontraron pacientes.' : 'Todavía no hay pacientes registrados.'} />
    {query.isError && <Button variante="secundario" onClick={() => void query.refetch()}>Reintentar</Button>}<Pagination pagina={page} total={query.data?.count ?? 0} onCambiar={setPage} />
    {form !== undefined && <PacienteFormModal paciente={form} onClose={() => setForm(undefined)} onCreated={puedeVincular ? (creado) => setAVincular(creado) : undefined} />}{detalle !== null && <PacienteDetalleModal id={detalle} onClose={() => setDetalle(null)} />}
    {aVincular && <VincularPacienteUsuarioModal paciente={aVincular} onClose={() => setAVincular(null)} />}
    {aCambiar && <ConfirmDialog titulo={aCambiar.estado ? 'Desactivar paciente' : 'Reactivar paciente'} mensaje={aCambiar.estado ? `¿Quieres desactivar a ${aCambiar.nombre} ${aCambiar.apellido}? Su registro se conservará.` : `¿Quieres reactivar a ${aCambiar.nombre} ${aCambiar.apellido}?`} textoConfirmar={aCambiar.estado ? 'Desactivar' : 'Reactivar'} cargando={cambiarEstado.isPending} onConfirmar={() => cambiarEstado.mutate(aCambiar)} onCancelar={() => setACambiar(null)} />}
  </section>
}
