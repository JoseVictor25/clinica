"""Usuario personalizado, roles y asignaciones."""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.managers import TenantBaseMixin, TenantChildModel, TenantModel
from apps.core.tenant import esta_en_bypass, get_clinica_actual


class UsuarioManager(BaseUserManager):
    """
    Manager global por defecto para Usuario.

    NO filtra por clínica. Django lo usa en ModelBackend.authenticate() y
    ModelBackend.get_user() antes de que exista contexto de clínica, por lo que
    filtrarlo aquí rompe el login y la carga de la sesión.

    Para consultas tenant usar explícitamente Usuario.tenant_objects.
    """

    use_in_migrations = True

    def _create_user(
        self,
        username,
        email,
        password,
        evitar_clinica_contexto=False,
        **extra_fields,
    ):
        if not username:
            raise ValueError("El nombre de usuario es obligatorio.")
        if not email:
            raise ValueError("El email es obligatorio.")

        email = self.normalize_email(email)
        usuario = self.model(username=username, email=email, **extra_fields)
        if evitar_clinica_contexto:
            usuario._evitar_clinica_contexto = True
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("estado", True)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("estado", True)
        extra_fields.setdefault("clinica", None)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")

        return self._create_user(
            username,
            email,
            password,
            evitar_clinica_contexto=True,
            **extra_fields,
        )


class UsuarioTenantManager(UsuarioManager):
    """
    Manager explícito para consultas de Usuario dentro de una clínica.

    Falla cerrado: sin contexto de clínica lanza TenantNoConfigurado. No debe
    usarse para autenticación ni para cargar la sesión; para eso está
    Usuario.objects (global).
    """

    use_in_migrations = False

    def get_queryset(self):
        queryset = super().get_queryset()
        if esta_en_bypass():
            return queryset

        clinica = get_clinica_actual()
        if clinica is None:
            return queryset.none()
        return queryset.filter(clinica=clinica)


class Usuario(TenantBaseMixin, AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.BooleanField(default=True)
    clinica = models.ForeignKey(
        "clinicas.Clinica",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="usuarios",
    )
    is_staff = models.BooleanField(default=False)

    # El administrador del sistema no tiene clínica; por eso este modelo permite
    # que la clínica sea nula, pero el CheckConstraint lo restringe a superusuarios.
    tenant_clinica_obligatoria = False

    # objects debe ser el _default_manager global: Django lo usa en
    # ModelBackend.authenticate() y get_user() antes de conocer la clínica.
    objects = UsuarioManager()
    tenant_objects = UsuarioTenantManager()
    all_objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["username"]
        constraints = [
            models.CheckConstraint(
                condition=Q(is_superuser=True) | Q(clinica__isnull=False),
                name="usuario_clinica_o_superuser",
            ),
        ]
        indexes = [
            models.Index(fields=["clinica"], name="usuario_clinica_idx"),
            models.Index(fields=["estado"], name="usuario_estado_idx"),
        ]

    @property
    def is_active(self):
        return self.estado

    @is_active.setter
    def is_active(self, value):
        self.estado = value

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    def __str__(self):
        return self.username


class Rol(TenantModel):
    clinica = models.ForeignKey(
        "clinicas.Clinica",
        on_delete=models.PROTECT,
        related_name="roles",
    )
    nombre = models.CharField(max_length=80)
    descripcion = models.TextField(blank=True)
    estado = models.BooleanField(default=True)

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinica", "nombre"],
                name="uniq_rol_por_clinica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinica", "estado"],
                name="rol_clinica_estado_idx",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.clinica})"


class UsuarioRol(TenantChildModel):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="roles_asignados",
    )
    rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        related_name="asignaciones",
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    tenant_lookup = "usuario__clinica"

    class Meta:
        verbose_name = "asignación de rol"
        verbose_name_plural = "asignaciones de rol"
        ordering = ["-fecha_asignacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "rol"],
                name="uniq_usuario_rol",
            ),
        ]
        indexes = [
            models.Index(fields=["rol"], name="usuario_rol_rol_idx"),
        ]

    def clean(self):
        super().clean()
        if not self.usuario_id or not self.rol_id:
            return
        if self.usuario.clinica_id is None:
            raise ValidationError(
                "El administrador del sistema no puede tener roles de clínica."
            )
        if self.usuario.clinica_id != self.rol.clinica_id:
            raise ValidationError(
                "El usuario y el rol deben pertenecer a la misma clínica."
            )

    def __str__(self):
        return f"{self.usuario} - {self.rol}"
