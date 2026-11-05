from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Modalidad(models.TextChoices):
    RX = "RX", "Rayos X"
    CT = "CT", "Tomografía"
    MR = "MR", "Resonancia magnética"
    US = "US", "Ecografía"
    MG = "MG", "Mamografía"


class Paciente(models.Model):
    class Sexo(models.TextChoices):
        FEMENINO = "F", "Femenino"
        MASCULINO = "M", "Masculino"
        OTRO = "O", "Otro"

    historia_clinica = models.CharField(
        "N.º historia clínica", max_length=20, unique=True, null=True, blank=True, editable=False
    )
    documento = models.CharField("Documento de identidad", max_length=20, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField("Fecha de nacimiento")
    sexo = models.CharField(max_length=1, choices=Sexo.choices)
    telefono = models.CharField("Teléfono", max_length=30, blank=True)
    email = models.EmailField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["apellidos", "nombres"]

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} ({self.historia_clinica})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.historia_clinica:
            self.historia_clinica = f"HC{self.pk:06d}"
            super().save(update_fields=["historia_clinica"])

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    @property
    def edad(self):
        hoy = date.today()
        fn = self.fecha_nacimiento
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))


class Sala(models.Model):
    """Sala o equipo donde se realizan los estudios."""

    nombre = models.CharField(max_length=100, unique=True)
    modalidad = models.CharField(max_length=2, choices=Modalidad.choices)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["modalidad", "nombre"]
        verbose_name_plural = "salas"

    def __str__(self):
        return f"{self.nombre} ({self.modalidad})"


class Procedimiento(models.Model):
    """Catálogo de estudios que se pueden solicitar."""

    codigo = models.CharField("Código", max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    modalidad = models.CharField(max_length=2, choices=Modalidad.choices)
    duracion_minutos = models.PositiveIntegerField("Duración (min)", default=15)

    class Meta:
        ordering = ["modalidad", "nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Orden(models.Model):
    class Prioridad(models.TextChoices):
        RUTINA = "RUTINA", "Rutina"
        URGENTE = "URGENTE", "Urgente"
        STAT = "STAT", "Inmediata (STAT)"

    class Estado(models.TextChoices):
        SOLICITADA = "SOLICITADA", "Solicitada"
        PROGRAMADA = "PROGRAMADA", "Programada"
        EN_CURSO = "EN_CURSO", "En curso"
        REALIZADA = "REALIZADA", "Realizada (pendiente de informe)"
        INFORMADA = "INFORMADA", "Informada"
        CANCELADA = "CANCELADA", "Cancelada"

    numero_acceso = models.CharField(
        "N.º de acceso", max_length=20, unique=True, null=True, blank=True, editable=False
    )
    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name="ordenes")
    procedimiento = models.ForeignKey(Procedimiento, on_delete=models.PROTECT, related_name="ordenes")
    medico_solicitante = models.CharField("Médico solicitante", max_length=150)
    indicacion_clinica = models.TextField("Indicación clínica")
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.RUTINA)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.SOLICITADA)

    sala = models.ForeignKey(Sala, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes")
    fecha_programada = models.DateTimeField("Fecha y hora programada", null=True, blank=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_realizacion = models.DateTimeField("Fecha de realización", null=True, blank=True)
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estudios_realizados",
        verbose_name="Técnico",
    )
    creado = models.DateTimeField("Fecha de solicitud", auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name_plural = "órdenes"

    def __str__(self):
        return f"{self.numero_acceso} - {self.procedimiento.nombre}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.numero_acceso:
            self.numero_acceso = f"ACC{self.pk:07d}"
            super().save(update_fields=["numero_acceso"])

    @property
    def fin_programado(self):
        if self.fecha_programada:
            return self.fecha_programada + timedelta(minutes=self.procedimiento.duracion_minutos)
        return None

    @property
    def puede_programarse(self):
        return self.estado in (self.Estado.SOLICITADA, self.Estado.PROGRAMADA)

    @property
    def puede_cancelarse(self):
        return self.estado in (self.Estado.SOLICITADA, self.Estado.PROGRAMADA, self.Estado.EN_CURSO)

    # --- Flujo de trabajo -------------------------------------------------
    def _transicion(self, desde, hacia):
        if self.estado not in desde:
            raise ValueError(
                f"No se puede pasar de «{self.get_estado_display()}» a «{self.Estado(hacia).label}»."
            )
        self.estado = hacia

    def iniciar(self, usuario):
        self._transicion([self.Estado.PROGRAMADA], self.Estado.EN_CURSO)
        self.fecha_inicio = timezone.now()
        self.tecnico = usuario
        self.save()

    def completar(self, usuario):
        self._transicion([self.Estado.EN_CURSO], self.Estado.REALIZADA)
        self.fecha_realizacion = timezone.now()
        if not self.tecnico:
            self.tecnico = usuario
        self.save()

    def cancelar(self, usuario):
        self._transicion(
            [self.Estado.SOLICITADA, self.Estado.PROGRAMADA, self.Estado.EN_CURSO],
            self.Estado.CANCELADA,
        )
        self.save()


class Informe(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        FIRMADO = "FIRMADO", "Firmado"

    orden = models.OneToOneField(Orden, on_delete=models.CASCADE, related_name="informe")
    hallazgos = models.TextField()
    conclusion = models.TextField("Conclusión / impresión diagnóstica")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.BORRADOR)
    radiologo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="informes_firmados",
        verbose_name="Radiólogo",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    fecha_firma = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Informe {self.orden.numero_acceso} ({self.get_estado_display()})"

    def firmar(self, usuario):
        if self.estado == self.Estado.FIRMADO:
            raise ValueError("El informe ya está firmado.")
        self.estado = self.Estado.FIRMADO
        self.radiologo = usuario
        self.fecha_firma = timezone.now()
        self.save()
        self.orden.estado = Orden.Estado.INFORMADA
        self.orden.save(update_fields=["estado"])
