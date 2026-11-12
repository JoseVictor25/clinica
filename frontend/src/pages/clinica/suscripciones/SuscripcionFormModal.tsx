import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { planesApi } from '@/api/modules/planes'
import {
    suscripcionesApi,
    type Suscripcion,
} from '@/api/modules/suscripciones'
import { Button } from '@/components/ui/Button'
import { Field } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { inputClass } from '@/components/ui/styles'
import { useAuth } from '@/hooks/useAuth'
import { mensajeDeError } from '@/lib/errorMessages'
import { aplicarErroresDeApi } from '@/lib/formErrors'
import { normalizarError } from '@/api/errors'

type Props = {
    onClose: () => void
} & (
        | {
            modo: 'contratar'
            suscripcion?: never
        }
        | {
            modo: 'renovar' | 'cambiar-plan'
            suscripcion: Suscripcion
        }
    )

interface Valores {
    plan_id: string
    fecha_inicio: string
    fecha_fin: string
}

const TITULOS = {
    contratar: 'Contratar suscripción',
    renovar: 'Renovar suscripción',
    'cambiar-plan': 'Cambiar de plan',
} as const

const BOTONES = {
    contratar: 'Contratar',
    renovar: 'Renovar',
    'cambiar-plan': 'Cambiar plan',
} as const

const CAMPOS = ['plan_id', 'fecha_inicio', 'fecha_fin'] as const

function fechaActual(): string {
    const partes = new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/La_Paz',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    }).formatToParts(new Date())

    const obtener = (tipo: Intl.DateTimeFormatPartTypes) =>
        partes.find((parte) => parte.type === tipo)?.value ?? ''

    return `${obtener('year')}-${obtener('month')}-${obtener('day')}`
}

export function SuscripcionFormModal(props: Props) {
    const { modo, onClose } = props
    const suscripcion = props.suscripcion
    const esRenovacion = modo === 'renovar'

    const queryClient = useQueryClient()
    const { actualizarPerfil } = useAuth()
    const [errorGeneral, setErrorGeneral] = useState<string | null>(null)

    const {
        register,
        handleSubmit,
        getValues,
        watch,
        setError,
        clearErrors,
        formState: { errors },
    } = useForm<Valores>({
        defaultValues: {
            plan_id: '',
            fecha_inicio: fechaActual(),
            fecha_fin: '',
        },
    })

    const planes = useQuery({
        queryKey: ['planes', 'activos'],
        queryFn: planesApi.listarActivos,
        enabled: !esRenovacion,
    })

    const planSeleccionado = planes.data?.find(
        (plan) => String(plan.id) === watch('plan_id'),
    )

    const guardar = useMutation({
        mutationFn: async (valores: Valores): Promise<Suscripcion> => {
            if (modo === 'renovar') {
                if (!suscripcion) {
                    throw new Error('No se seleccionó la suscripción a renovar.')
                }

                return suscripcionesApi.renovar(suscripcion.id, {
                    nueva_fecha_fin: valores.fecha_fin,
                })
            }

            const datos = {
                plan_id: Number(valores.plan_id),
                fecha_inicio: valores.fecha_inicio,
                fecha_fin: valores.fecha_fin,
            }

            if (modo === 'cambiar-plan') {
                if (!suscripcion) {
                    throw new Error('No se seleccionó la suscripción a modificar.')
                }

                return suscripcionesApi.cambiarPlan(suscripcion.id, datos)
            }

            return suscripcionesApi.contratar(datos)
        },

        onSuccess: async () => {
            toast.success(
                modo === 'contratar'
                    ? 'Suscripción contratada.'
                    : modo === 'renovar'
                        ? 'Suscripción renovada.'
                        : 'Plan actualizado.',
            )

            // Una operación exitosa no debe mostrarse como fallida
            // si la consulta posterior del perfil tiene un problema.
            try {
                await actualizarPerfil()
            } catch {
                toast.warning(
                    'El cambio se guardó, pero no se pudo actualizar el perfil. Recarga la página para consultar el estado actual.',
                )
            }

            void queryClient.invalidateQueries({
                queryKey: ['suscripciones'],
            })

            onClose()
        },

        onError: (error) => {
            if (esRenovacion) {
                const errorApi = normalizarError(error)

                const mensajesFecha =
                    errorApi.fieldErrors.nueva_fecha_fin ??
                    errorApi.fieldErrors.fecha_fin

                if (errorApi.code === 'fecha_fin_invalida') {
                    setError('fecha_fin', {
                        type: 'server',
                        message: mensajeDeError(errorApi),
                    })
                } else if (mensajesFecha?.length) {
                    setError('fecha_fin', {
                        type: 'server',
                        message: mensajesFecha.join(' '),
                    })
                }

                // Conserva también el mensaje general del error.
                setErrorGeneral(mensajeDeError(errorApi))
                return
            }

            setErrorGeneral(
                aplicarErroresDeApi(error, setError, CAMPOS, {
                    plan_inactivo: 'plan_id',
                    fechas_invalidas: 'fecha_fin',
                }),
            )
        },
    })

    const bloquearGuardado =
        !esRenovacion &&
        (planes.isPending || planes.isError || !planes.data?.length)

    function cerrar() {
        if (!guardar.isPending) {
            onClose()
        }
    }

    return (
        <Modal titulo={TITULOS[modo]} onClose={cerrar}>
            <form
                className="space-y-4"
                noValidate
                onSubmit={handleSubmit((valores) => {
                    if (guardar.isPending) return

                    clearErrors()
                    setErrorGeneral(null)
                    guardar.mutate(valores)
                })}
            >
                {errorGeneral && (
                    <p
                        role="alert"
                        className="rounded-md bg-red-50 p-3 text-sm text-red-700"
                    >
                        {errorGeneral}
                    </p>
                )}

                {suscripcion && (
                    <p className="text-sm text-slate-600">
                        Plan actual: <strong>{suscripcion.plan_nombre}</strong>.
                        {' '}Fecha de fin: {suscripcion.fecha_fin}.
                    </p>
                )}

                {!esRenovacion && (
                    <>
                        {planes.isPending && (
                            <p role="status" className="text-sm text-slate-600">
                                Cargando planes…
                            </p>
                        )}

                        {planes.isError && (
                            <div role="alert" className="space-y-2">
                                <p className="text-sm text-red-700">
                                    {mensajeDeError(planes.error)}
                                </p>
                                <Button
                                    variante="secundario"
                                    onClick={() => void planes.refetch()}
                                    disabled={planes.isFetching}
                                >
                                    Reintentar
                                </Button>
                            </div>
                        )}

                        {planes.isSuccess && planes.data.length === 0 && (
                            <p role="status" className="text-sm text-amber-800">
                                No hay planes activos disponibles.
                            </p>
                        )}

                        <Field
                            id="plan_id"
                            label="Plan"
                            error={errors.plan_id?.message}
                        >
                            <select
                                id="plan_id"
                                className={inputClass}
                                disabled={guardar.isPending || bloquearGuardado}
                                aria-invalid={Boolean(errors.plan_id)}
                                aria-describedby={
                                    errors.plan_id ? 'plan_id-error' : undefined
                                }
                                {...register('plan_id', {
                                    required: 'Selecciona un plan.',
                                    validate: (valor) => {
                                        const plan = planes.data?.find(
                                            (item) => String(item.id) === valor,
                                        )

                                        if (!plan) return 'Selecciona un plan disponible.'

                                        if (
                                            modo === 'cambiar-plan' &&
                                            plan.id === suscripcion?.plan
                                        ) {
                                            return 'Selecciona un plan diferente al actual.'
                                        }

                                        return true
                                    },
                                })}
                            >
                                <option value="">Selecciona un plan</option>
                                {planes.data?.map((plan) => (
                                    <option
                                        key={plan.id}
                                        value={plan.id}
                                        disabled={
                                            modo === 'cambiar-plan' &&
                                            plan.id === suscripcion?.plan
                                        }
                                    >
                                        {plan.nombre} — {plan.precio} — hasta{' '}
                                        {plan.max_usuarios} usuarios
                                    </option>
                                ))}
                            </select>
                        </Field>

                        {planSeleccionado?.descripcion && (
                            <p className="text-sm text-slate-600">
                                {planSeleccionado.descripcion}
                            </p>
                        )}

                        <Field
                            id="fecha_inicio"
                            label="Fecha de inicio"
                            error={errors.fecha_inicio?.message}
                        >
                            <input
                                id="fecha_inicio"
                                type="date"
                                className={inputClass}
                                disabled={guardar.isPending}
                                aria-invalid={Boolean(errors.fecha_inicio)}
                                aria-describedby={
                                    errors.fecha_inicio ? 'fecha_inicio-error' : undefined
                                }
                                {...register('fecha_inicio', {
                                    required: 'Indica la fecha de inicio.',
                                })}
                            />
                        </Field>
                    </>
                )}

                <Field
                    id="fecha_fin"
                    label={esRenovacion ? 'Nueva fecha de fin' : 'Fecha de fin'}
                    error={errors.fecha_fin?.message}
                >
                    <input
                        id="fecha_fin"
                        type="date"
                        className={inputClass}
                        disabled={guardar.isPending}
                        aria-invalid={Boolean(errors.fecha_fin)}
                        aria-describedby={
                            errors.fecha_fin ? 'fecha_fin-error' : undefined
                        }
                        {...register('fecha_fin', {
                            required: 'Indica la fecha de fin.',
                            validate: (valor) => {
                                if (esRenovacion) {
                                    return (
                                        (suscripcion !== undefined &&
                                            valor > suscripcion.fecha_fin) ||
                                        'La nueva fecha debe ser posterior a la fecha de fin actual.'
                                    )
                                }

                                const inicio = getValues('fecha_inicio')

                                return (
                                    !inicio ||
                                    valor >= inicio ||
                                    'La fecha de fin no puede ser anterior a la de inicio.'
                                )
                            },
                        })}
                    />
                </Field>

                {!esRenovacion && (
                    <p className="text-sm text-slate-600">
                        El acceso se habilita cuando la suscripción está activa
                        y la fecha actual está dentro del período contratado.
                    </p>
                )}

                {modo === 'cambiar-plan' && (
                    <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                        Al confirmar, se cancelará la suscripción actual y se creará
                        una nueva con el plan y las fechas seleccionadas.
                    </p>
                )}

                <div className="flex justify-end gap-2 pt-2">
                    <Button
                        variante="secundario"
                        onClick={cerrar}
                        disabled={guardar.isPending}
                    >
                        Cancelar
                    </Button>
                    <Button
                        type="submit"
                        cargando={guardar.isPending}
                        disabled={bloquearGuardado}
                    >
                        {BOTONES[modo]}
                    </Button>
                </div>
            </form>
        </Modal>
    )
}
