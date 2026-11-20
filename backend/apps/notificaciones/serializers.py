from rest_framework import serializers

from .models import PlataformaDispositivo


from rest_framework import serializers

from .models import Notificacion


class NotificacionSerializer(serializers.ModelSerializer):
    leida = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = ("id", "titulo", "cuerpo", "datos", "creada_en", "leida")

    def get_leida(self, obj):
        return obj.leida_en is not None


class DispositivoPushSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=4096, trim_whitespace=True)
    plataforma = serializers.ChoiceField(choices=PlataformaDispositivo.choices)
