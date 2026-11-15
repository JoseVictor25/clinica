import { Button } from './Button'
import { Modal } from './Modal'

interface Props {
  titulo: string
  mensaje: string
  textoConfirmar?: string
  cargando?: boolean
  onConfirmar: () => void
  onCancelar: () => void
}

export function ConfirmDialog({
  titulo,
  mensaje,
  textoConfirmar = 'Eliminar',
  cargando = false,
  onConfirmar,
  onCancelar,
}: Props) {
  return (
    <Modal titulo={titulo} onClose={onCancelar}>
      <p className="text-sm text-slate-600">{mensaje}</p>
      <div className="mt-6 flex justify-end gap-2">
        <Button variante="secundario" onClick={onCancelar} disabled={cargando}>
          Cancelar
        </Button>
        <Button variante="peligro" onClick={onConfirmar} cargando={cargando}>
          {textoConfirmar}
        </Button>
      </div>
    </Modal>
  )
}