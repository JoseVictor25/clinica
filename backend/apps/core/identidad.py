"""Datos de identidad compartidos entre Personal y Paciente."""

from rest_framework import serializers


CAMPOS_IDENTIDAD = ("nombre", "apellido", "telefono")


class ConsultaIdentidadSerializer(serializers.Serializer):
    ci = serializers.CharField(max_length=20, trim_whitespace=True)


class IdentidadCompartidaSerializer(serializers.Serializer):
    encontrado = serializers.BooleanField()
    ci = serializers.CharField(allow_blank=True)
    nombre = serializers.CharField(allow_blank=True)
    apellido = serializers.CharField(allow_blank=True)
    telefono = serializers.CharField(allow_blank=True)
    email = serializers.EmailField(allow_blank=True)
    origen = serializers.ChoiceField(
        choices=("PERSONAL", "PACIENTE"), allow_null=True
    )


def respuesta_identidad(objeto, origen):
    if objeto is None:
        return {
            "encontrado": False,
            "ci": "",
            "nombre": "",
            "apellido": "",
            "telefono": "",
            "email": "",
            "origen": None,
        }
    usuario = getattr(objeto, "usuario", None)
    email = usuario.email if usuario is not None else getattr(objeto, "email", "")
    return {
        "encontrado": True,
        "ci": objeto.ci,
        "nombre": objeto.nombre,
        "apellido": objeto.apellido,
        "telefono": objeto.telefono,
        "email": email,
        "origen": origen,
    }


def copiar_identidad(datos, origen):
    """Fuerza en ``datos`` la identidad ya verificada por el otro perfil."""
    for campo in CAMPOS_IDENTIDAD:
        datos[campo] = getattr(origen, campo)
    return datos
