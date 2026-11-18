export const usuarioObligatorio = (valor: string) =>
  valor.trim().length > 0 || 'El nombre de usuario es obligatorio.'

export const correoValido = (valor: string) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valor.trim()) ||
  'Introduce un correo electrónico válido.'

export const passwordsCoinciden = (confirmacion: string, password: string) =>
  confirmacion === password || 'Las contraseñas no coinciden.'
