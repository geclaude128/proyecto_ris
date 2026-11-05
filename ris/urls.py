from django.urls import path

from . import views

app_name = "ris"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("pacientes/", views.pacientes_lista, name="pacientes"),
    path("pacientes/nuevo/", views.paciente_form, name="paciente_nuevo"),
    path("pacientes/<int:pk>/", views.paciente_detalle, name="paciente_detalle"),
    path("pacientes/<int:pk>/editar/", views.paciente_form, name="paciente_editar"),
    path("ordenes/", views.ordenes_lista, name="ordenes"),
    path("ordenes/nueva/", views.orden_crear, name="orden_nueva"),
    path("ordenes/<int:pk>/", views.orden_detalle, name="orden_detalle"),
    path("ordenes/<int:pk>/programar/", views.orden_programar, name="orden_programar"),
    path("ordenes/<int:pk>/<str:accion>/", views.orden_accion, name="orden_accion"),
    path("worklist/", views.worklist, name="worklist"),
    path("informes/", views.informes_pendientes, name="informes"),
    path("informes/<int:orden_pk>/", views.informe_editar, name="informe_editar"),
]
