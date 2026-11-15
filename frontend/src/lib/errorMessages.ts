import { normalizarError } from '@/api/errors'

// Código de error del backend -> mensaje en español (catálogo de INFORME_SPRINT1.md).
export const MENSAJES_POR_CODIGO: Record<string, string> = {
  credenciales_invalidas: 'Usuario o contraseña incorrectos.',
  no_autenticado: 'Tu sesión no es válida. Inicia sesión nuevamente.',
  permiso_denegado: 'No tienes permiso para realizar esta acción.',
  suscripcion_vencida: 'La clínica no tiene una suscripción vigente. Renueva o contrata un plan.',
  clinica_inactiva: 'La clínica está desactivada. Contacta al administrador de la plataforma.',
  sin_clinica: 'Tu usuario no está asociado a ninguna clínica.',
  medico_no_vinculado: 'Tu usuario no está vinculado a un registro de médico.',
  datos_invalidos: 'Revisa los datos ingresados.',
  password_invalida: 'La contraseña no cumple los requisitos de seguridad.',
  password_actual_invalida: 'La contraseña actual no es correcta.',
  password_repetida: 'La nueva contraseña debe ser distinta de la actual.',
  refresh_invalido: 'Tu sesión expiró. Inicia sesión nuevamente.',
  nit_duplicado: 'Ya existe una clínica con ese NIT.',
  usuario_duplicado: 'Ese nombre de usuario no está disponible.',
  email_duplicado: 'Ese correo electrónico no está disponible.',
  clinica_duplicada: 'Ya existe una clínica con esos datos.',
  limite_usuarios: 'La clínica alcanzó el máximo de usuarios activos de su plan.',
  plan_inactivo: 'El plan seleccionado no está activo.',
  suscripcion_activa: 'La clínica ya tiene una suscripción activa.',
  suscripcion_no_vigente: 'La suscripción no está vigente, no se puede renovar.',
  suscripcion_no_activa: 'La suscripción no está activa.',
  fechas_invalidas: 'La fecha de fin no puede ser anterior a la de inicio.',
  fecha_fin_invalida: 'La nueva fecha de fin debe ser posterior a la actual.',
  ultimo_administrador: 'No puedes dejar la clínica sin un administrador activo.',
  rol_base_protegido: 'Los roles base no se pueden renombrar, desactivar ni eliminar.',
  rol_duplicado: 'Ya existe un rol con ese nombre.',
  rol_con_asignaciones: 'El rol tiene usuarios asignados y no se puede eliminar.',
  rol_ya_asignado: 'El usuario ya tiene ese rol.',
  rol_ajeno: 'El rol no pertenece a esta clínica.',
  rol_inactivo: 'El rol está inactivo.',
  ci_duplicada: 'Ya existe personal con esa cédula en la clínica.',
  personal_ya_es_medico: 'Esta persona ya está registrada como médico.',
  colegiatura_duplicada: 'Ese número de colegiatura ya está registrado.',
  especialidad_duplicada: 'Ya existe una especialidad con ese nombre.',
  especialidad_en_uso: 'La especialidad tiene médicos asociados y no se puede eliminar.',
  horario_solapado: 'El horario se solapa con otro del mismo médico.',
  horario_invalido: 'La hora de inicio debe ser anterior a la hora de fin.',
  medico_requerido: 'Debes seleccionar un médico.',
  personal_con_medico: 'No se puede eliminar personal que ya es médico.',
  usuario_ya_vinculado: 'El usuario ya está vinculado a otro registro de personal.',
  no_encontrado: 'El recurso no existe.',
  demasiados_intentos: 'Demasiados intentos. Espera un minuto e inténtalo de nuevo.',
}

const MENSAJES_POR_ESTADO: Record<number, string> = {
  0: 'No se pudo conectar con el servidor.',
  400: 'Revisa los datos ingresados.',
  401: 'Tu sesión no es válida. Inicia sesión nuevamente.',
  403: 'No tienes permiso para realizar esta acción.',
  404: 'El recurso solicitado no existe.',
  409: 'La operación entra en conflicto con el estado actual de los datos.',
  429: 'Demasiados intentos. Espera un momento.',
  500: 'Error interno del servidor. Intenta más tarde.',
}

/** Prioridad: código conocido > mensaje del servidor > mensaje por estado HTTP. */
export function mensajeDeError(error: unknown): string {
  const e = normalizarError(error)

  if (e.code === 'limite_usuarios') {
    const activos = e.details.usuarios_activos
    const max = e.details.max_usuarios
    if (typeof activos === 'number' && typeof max === 'number') {
      return `Tu plan permite ${max} usuarios activos y ya tienes ${activos}. Cambia de plan o desactiva usuarios.`
    }
  }

  if (e.code && MENSAJES_POR_CODIGO[e.code]) return MENSAJES_POR_CODIGO[e.code]
  if (e.status !== 0 && e.message && e.message !== 'Ocurrió un error inesperado.') return e.message
  return MENSAJES_POR_ESTADO[e.status] ?? 'Ocurrió un error inesperado.'
}