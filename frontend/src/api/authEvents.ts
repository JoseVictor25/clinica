export type EventoAuth = 'session-expired' | 'clinica-inactiva' | 'suscripcion-vencida'

const listeners: Record<EventoAuth, Set<() => void>> = {
  'session-expired': new Set(),
  'clinica-inactiva': new Set(),
  'suscripcion-vencida': new Set(),
}

export const authEvents = {
  on(evento: EventoAuth, fn: () => void) {
    listeners[evento].add(fn)
    return () => {
      listeners[evento].delete(fn)
    }
  },
  emit(evento: EventoAuth) {
    listeners[evento].forEach((fn) => fn())
  },
}