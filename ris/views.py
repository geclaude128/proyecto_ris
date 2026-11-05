from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, Count, IntegerField, Q, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import InformeForm, OrdenForm, PacienteForm, ProgramarForm
from .models import Informe, Modalidad, Orden, Paciente

RELACIONES_ORDEN = ("paciente", "procedimiento", "sala", "tecnico")


# --------------------------------------------------------------------- Inicio
@login_required
def dashboard(request):
    hoy = timezone.localdate()
    conteos = dict(Orden.objects.order_by().values_list("estado").annotate(n=Count("id")))
    resumen = [
        {"valor": valor, "etiqueta": etiqueta, "total": conteos.get(valor, 0)}
        for valor, etiqueta in Orden.Estado.choices
    ]
    agenda = (
        Orden.objects.filter(fecha_programada__date=hoy)
        .exclude(estado=Orden.Estado.CANCELADA)
        .select_related(*RELACIONES_ORDEN)
        .order_by("fecha_programada")
    )
    urgentes = Orden.objects.filter(
        prioridad__in=[Orden.Prioridad.URGENTE, Orden.Prioridad.STAT],
        estado__in=[
            Orden.Estado.SOLICITADA,
            Orden.Estado.PROGRAMADA,
            Orden.Estado.EN_CURSO,
            Orden.Estado.REALIZADA,
        ],
    ).select_related(*RELACIONES_ORDEN)
    return render(
        request,
        "ris/dashboard.html",
        {
            "hoy": hoy,
            "resumen": resumen,
            "agenda": agenda,
            "urgentes": urgentes,
            "total_pacientes": Paciente.objects.count(),
        },
    )


# ------------------------------------------------------------------ Pacientes
@login_required
def pacientes_lista(request):
    q = request.GET.get("q", "").strip()
    pacientes = Paciente.objects.annotate(num_ordenes=Count("ordenes"))
    if q:
        pacientes = pacientes.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(documento__icontains=q)
            | Q(historia_clinica__icontains=q)
        )
    return render(request, "ris/pacientes/lista.html", {"pacientes": pacientes, "q": q})


@login_required
def paciente_detalle(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    ordenes = paciente.ordenes.select_related("procedimiento", "sala")
    return render(request, "ris/pacientes/detalle.html", {"paciente": paciente, "ordenes": ordenes})


@login_required
def paciente_form(request, pk=None):
    paciente = get_object_or_404(Paciente, pk=pk) if pk else None
    form = PacienteForm(request.POST or None, instance=paciente)
    if request.method == "POST" and form.is_valid():
        paciente = form.save()
        messages.success(request, f"Paciente {paciente.nombre_completo} guardado.")
        return redirect("ris:paciente_detalle", pk=paciente.pk)
    return render(request, "ris/pacientes/form.html", {"form": form, "paciente": paciente})


# -------------------------------------------------------------------- Órdenes
@login_required
def ordenes_lista(request):
    estado = request.GET.get("estado", "")
    modalidad = request.GET.get("modalidad", "")
    q = request.GET.get("q", "").strip()
    ordenes = Orden.objects.select_related(*RELACIONES_ORDEN)
    if estado:
        ordenes = ordenes.filter(estado=estado)
    if modalidad:
        ordenes = ordenes.filter(procedimiento__modalidad=modalidad)
    if q:
        ordenes = ordenes.filter(
            Q(numero_acceso__icontains=q)
            | Q(paciente__apellidos__icontains=q)
            | Q(paciente__nombres__icontains=q)
            | Q(paciente__historia_clinica__icontains=q)
        )
    return render(
        request,
        "ris/ordenes/lista.html",
        {
            "ordenes": ordenes,
            "estados": Orden.Estado.choices,
            "modalidades": Modalidad.choices,
            "filtro": {"estado": estado, "modalidad": modalidad, "q": q},
        },
    )


@login_required
def orden_crear(request):
    initial = {}
    if request.GET.get("paciente"):
        initial["paciente"] = request.GET["paciente"]
    form = OrdenForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        orden = form.save()
        messages.success(request, f"Orden {orden.numero_acceso} creada. Ahora puedes programarla.")
        return redirect("ris:orden_detalle", pk=orden.pk)
    return render(request, "ris/ordenes/form.html", {"form": form})


def _contexto_detalle(orden, programar_form=None):
    if programar_form is None and orden.puede_programarse:
        programar_form = ProgramarForm(instance=orden)
    return {
        "orden": orden,
        "programar_form": programar_form,
        "informe": getattr(orden, "informe", None),
    }


@login_required
def orden_detalle(request, pk):
    orden = get_object_or_404(Orden.objects.select_related(*RELACIONES_ORDEN), pk=pk)
    return render(request, "ris/ordenes/detalle.html", _contexto_detalle(orden))


@login_required
@require_POST
def orden_programar(request, pk):
    orden = get_object_or_404(Orden.objects.select_related("procedimiento"), pk=pk)
    if not orden.puede_programarse:
        messages.error(request, "Esta orden ya no se puede programar.")
        return redirect("ris:orden_detalle", pk=pk)
    form = ProgramarForm(request.POST, instance=orden)
    if form.is_valid():
        orden = form.save(commit=False)
        orden.estado = Orden.Estado.PROGRAMADA
        orden.save()
        messages.success(request, f"Orden {orden.numero_acceso} programada.")
        return redirect("ris:orden_detalle", pk=pk)
    # Recargar la orden sin los cambios inválidos para mostrarla
    orden = Orden.objects.select_related(*RELACIONES_ORDEN).get(pk=pk)
    return render(request, "ris/ordenes/detalle.html", _contexto_detalle(orden, form))


@login_required
@require_POST
def orden_accion(request, pk, accion):
    orden = get_object_or_404(Orden, pk=pk)
    acciones = {"iniciar": orden.iniciar, "completar": orden.completar, "cancelar": orden.cancelar}
    if accion not in acciones:
        raise Http404("Acción no válida")
    try:
        acciones[accion](request.user)
        messages.success(request, f"Orden {orden.numero_acceso}: {orden.get_estado_display()}.")
    except ValueError as error:
        messages.error(request, str(error))
    siguiente = request.POST.get("next")
    if siguiente and url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
        return redirect(siguiente)
    return redirect("ris:orden_detalle", pk=pk)


# ------------------------------------------------------- Lista de trabajo
@login_required
def worklist(request):
    try:
        fecha = date.fromisoformat(request.GET.get("fecha", ""))
    except ValueError:
        fecha = timezone.localdate()
    modalidad = request.GET.get("modalidad", "")
    ordenes = (
        Orden.objects.filter(
            fecha_programada__date=fecha,
            estado__in=[Orden.Estado.PROGRAMADA, Orden.Estado.EN_CURSO, Orden.Estado.REALIZADA],
        )
        .select_related(*RELACIONES_ORDEN)
        .order_by("fecha_programada")
    )
    if modalidad:
        ordenes = ordenes.filter(procedimiento__modalidad=modalidad)
    return render(
        request,
        "ris/worklist.html",
        {
            "ordenes": ordenes,
            "fecha": fecha,
            "anterior": fecha - timedelta(days=1),
            "siguiente": fecha + timedelta(days=1),
            "modalidad": modalidad,
            "modalidades": Modalidad.choices,
        },
    )


# ------------------------------------------------------------------ Informes
@login_required
def informes_pendientes(request):
    rango_prioridad = Case(
        When(prioridad=Orden.Prioridad.STAT, then=0),
        When(prioridad=Orden.Prioridad.URGENTE, then=1),
        default=2,
        output_field=IntegerField(),
    )
    ordenes = (
        Orden.objects.filter(estado=Orden.Estado.REALIZADA)
        .select_related(*RELACIONES_ORDEN)
        .annotate(rango=rango_prioridad)
        .order_by("rango", "fecha_realizacion")
    )
    borradores = set(
        Informe.objects.filter(orden__in=ordenes, estado=Informe.Estado.BORRADOR).values_list(
            "orden_id", flat=True
        )
    )
    return render(
        request, "ris/informes/pendientes.html", {"ordenes": ordenes, "borradores": borradores}
    )


@login_required
def informe_editar(request, orden_pk):
    orden = get_object_or_404(Orden.objects.select_related(*RELACIONES_ORDEN), pk=orden_pk)
    informe = getattr(orden, "informe", None)
    if informe and informe.estado == Informe.Estado.FIRMADO:
        messages.info(request, "El informe ya está firmado y no puede modificarse.")
        return redirect("ris:orden_detalle", pk=orden.pk)
    if orden.estado != Orden.Estado.REALIZADA:
        messages.error(request, "Solo se pueden informar estudios realizados.")
        return redirect("ris:orden_detalle", pk=orden.pk)

    form = InformeForm(request.POST or None, instance=informe)
    if request.method == "POST" and form.is_valid():
        informe = form.save(commit=False)
        informe.orden = orden
        informe.save()
        if "firmar" in request.POST:
            informe.firmar(request.user)
            messages.success(request, f"Informe de {orden.numero_acceso} firmado.")
            return redirect("ris:orden_detalle", pk=orden.pk)
        messages.success(request, "Borrador guardado.")
        return redirect("ris:informe_editar", orden_pk=orden.pk)

    previos = (
        orden.paciente.ordenes.filter(estado=Orden.Estado.INFORMADA)
        .exclude(pk=orden.pk)
        .select_related("procedimiento", "informe")[:5]
    )
    return render(
        request,
        "ris/informes/editar.html",
        {"orden": orden, "form": form, "informe": informe, "previos": previos},
    )
