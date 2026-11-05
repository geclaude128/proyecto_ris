from django.contrib import admin

from .models import Informe, Orden, Paciente, Procedimiento, Sala


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("historia_clinica", "apellidos", "nombres", "documento", "fecha_nacimiento", "sexo")
    search_fields = ("historia_clinica", "apellidos", "nombres", "documento")
    list_filter = ("sexo",)


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "modalidad", "activa")
    list_filter = ("modalidad", "activa")


@admin.register(Procedimiento)
class ProcedimientoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "modalidad", "duracion_minutos")
    list_filter = ("modalidad",)
    search_fields = ("codigo", "nombre")


class InformeInline(admin.StackedInline):
    model = Informe
    extra = 0


@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ("numero_acceso", "paciente", "procedimiento", "prioridad", "estado", "sala", "fecha_programada")
    list_filter = ("estado", "prioridad", "procedimiento__modalidad", "sala")
    search_fields = ("numero_acceso", "paciente__apellidos", "paciente__historia_clinica")
    autocomplete_fields = ("paciente", "procedimiento")
    date_hierarchy = "fecha_programada"
    inlines = [InformeInline]


@admin.register(Informe)
class InformeAdmin(admin.ModelAdmin):
    list_display = ("orden", "estado", "radiologo", "fecha_firma")
    list_filter = ("estado",)
