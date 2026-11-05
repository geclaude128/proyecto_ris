from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Informe, Orden, Paciente, Sala


class BootstrapMixin:
    """Añade las clases CSS de Bootstrap a todos los campos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = "form-select" if isinstance(widget, forms.Select) else "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()


class PacienteForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ["documento", "nombres", "apellidos", "fecha_nacimiento", "sexo", "telefono", "email"]
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data["fecha_nacimiento"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha de nacimiento no puede ser futura.")
        return fecha


class OrdenForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Orden
        fields = ["paciente", "procedimiento", "prioridad", "medico_solicitante", "indicacion_clinica"]
        widgets = {"indicacion_clinica": forms.Textarea(attrs={"rows": 3})}


class ProgramarForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Orden
        fields = ["sala", "fecha_programada"]
        widgets = {
            "fecha_programada": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sala"].required = True
        self.fields["fecha_programada"].required = True
        # Solo salas activas de la misma modalidad que el procedimiento
        self.fields["sala"].queryset = Sala.objects.filter(
            activa=True, modalidad=self.instance.procedimiento.modalidad
        )

    def clean(self):
        cleaned = super().clean()
        sala = cleaned.get("sala")
        inicio = cleaned.get("fecha_programada")
        if sala and inicio:
            fin = inicio + timedelta(minutes=self.instance.procedimiento.duracion_minutos)
            candidatos = (
                Orden.objects.filter(
                    sala=sala,
                    estado__in=[Orden.Estado.PROGRAMADA, Orden.Estado.EN_CURSO],
                    fecha_programada__lt=fin,
                    fecha_programada__gte=inicio - timedelta(hours=4),
                )
                .exclude(pk=self.instance.pk)
                .select_related("procedimiento")
            )
            for otra in candidatos:
                if otra.fin_programado > inicio:
                    desde = timezone.localtime(otra.fecha_programada).strftime("%H:%M")
                    hasta = timezone.localtime(otra.fin_programado).strftime("%H:%M")
                    raise forms.ValidationError(
                        f"{sala.nombre} está ocupada de {desde} a {hasta} (orden {otra.numero_acceso})."
                    )
        return cleaned


class InformeForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Informe
        fields = ["hallazgos", "conclusion"]
        widgets = {
            "hallazgos": forms.Textarea(attrs={"rows": 10}),
            "conclusion": forms.Textarea(attrs={"rows": 4}),
        }
