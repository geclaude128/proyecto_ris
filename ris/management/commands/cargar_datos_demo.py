"""Carga datos ficticios para probar el RIS.

Uso:
    python manage.py cargar_datos_demo           # carga datos si la BD está vacía
    python manage.py cargar_datos_demo --reset   # borra pacientes/órdenes y vuelve a cargar
"""
import random
from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ris.models import Informe, Orden, Paciente, Procedimiento, Sala

USUARIOS = [
    # usuario, contraseña, nombre, apellido, superusuario
    ("admin", "admin123", "Administrador", "Sistema", True),
    ("tecnico", "tecnico123", "Carlos", "Ramírez (Técnico)", False),
    ("radiologo", "radiologo123", "Laura", "Méndez (Radióloga)", False),
]

SALAS = [
    ("Sala RX 1", "RX"),
    ("Sala RX 2", "RX"),
    ("Tomógrafo 1", "CT"),
    ("Resonador 1", "MR"),
    ("Ecografía 1", "US"),
    ("Ecografía 2", "US"),
    ("Mamógrafo 1", "MG"),
]

PROCEDIMIENTOS = [
    ("RX-TOR", "Radiografía de tórax PA y lateral", "RX", 10),
    ("RX-COLL", "Radiografía de columna lumbar", "RX", 15),
    ("RX-MANO", "Radiografía de mano", "RX", 10),
    ("RX-RODI", "Radiografía de rodilla", "RX", 10),
    ("CT-CRA", "TC de cráneo simple", "CT", 20),
    ("CT-TOR", "TC de tórax", "CT", 20),
    ("CT-ABD", "TC de abdomen y pelvis con contraste", "CT", 30),
    ("MR-CER", "RM de cerebro con contraste", "MR", 45),
    ("MR-RODI", "RM de rodilla", "MR", 40),
    ("US-ABD", "Ecografía abdominal", "US", 20),
    ("US-OBS", "Ecografía obstétrica", "US", 30),
    ("US-TIR", "Ecografía de tiroides", "US", 15),
    ("MG-BIL", "Mamografía bilateral", "MG", 20),
]

NOMBRES_F = ["María", "Lucía", "Sofía", "Valentina", "Camila", "Isabel", "Carmen", "Elena", "Paula", "Daniela"]
NOMBRES_M = ["José", "Juan", "Luis", "Carlos", "Miguel", "Andrés", "Jorge", "Diego", "Pedro", "Javier"]
APELLIDOS = [
    "García", "Rodríguez", "Martínez", "López", "González", "Pérez", "Sánchez", "Romero",
    "Torres", "Flores", "Rivera", "Gómez", "Díaz", "Morales", "Vargas", "Castro", "Ortiz", "Silva",
]
MEDICOS = [
    "Dra. Ana Torres (Medicina Interna)",
    "Dr. Luis Herrera (Traumatología)",
    "Dra. Patricia Núñez (Ginecología)",
    "Dr. Roberto Salinas (Urgencias)",
    "Dra. Gabriela Ríos (Neurología)",
]
INDICACIONES = {
    "RX": ["Tos persistente de 3 semanas.", "Dolor tras caída.", "Control post-tratamiento.", "Dolor lumbar crónico."],
    "CT": ["Cefalea intensa de inicio súbito.", "Dolor abdominal agudo en FID.", "Estadificación oncológica."],
    "MR": ["Sospecha de lesión meniscal.", "Crisis convulsiva de reciente comienzo.", "Seguimiento de lesión conocida."],
    "US": ["Dolor en hipocondrio derecho.", "Control de embarazo.", "Nódulo tiroideo palpable."],
    "MG": ["Tamizaje anual.", "Nódulo palpable en mama izquierda."],
}
INFORMES = [
    (
        "Estudio realizado con técnica estándar. No se identifican alteraciones significativas "
        "en las estructuras evaluadas. Partes blandas sin particularidades.",
        "Estudio dentro de límites normales.",
    ),
    (
        "Se identifican cambios degenerativos leves acordes a la edad del paciente. "
        "No se observan lesiones focales agudas.",
        "Cambios degenerativos leves. Sin hallazgos agudos.",
    ),
    (
        "Se observa imagen focal de aspecto benigno, de bordes bien definidos, "
        "sin signos de complicación.",
        "Hallazgo probablemente benigno. Se sugiere control evolutivo en 6 meses.",
    ),
]

# Distribución aproximada de estados de las órdenes generadas
ESTADOS = (
    [Orden.Estado.SOLICITADA] * 6
    + [Orden.Estado.PROGRAMADA] * 12
    + [Orden.Estado.EN_CURSO] * 2
    + [Orden.Estado.REALIZADA] * 8
    + [Orden.Estado.INFORMADA] * 14
    + [Orden.Estado.CANCELADA] * 3
)


class Command(BaseCommand):
    help = "Carga datos ficticios (usuarios, salas, procedimientos, pacientes, órdenes e informes)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Borra pacientes y órdenes existentes antes de cargar.")
        parser.add_argument("--pacientes", type=int, default=30)

    @transaction.atomic
    def handle(self, *args, **opts):
        rng = random.Random(42)

        usuarios = {}
        for username, password, nombre, apellido, es_super in USUARIOS:
            user, creado = User.objects.get_or_create(
                username=username,
                defaults={"first_name": nombre, "last_name": apellido, "is_staff": True, "is_superuser": es_super},
            )
            if creado:
                user.set_password(password)
                user.save()
            usuarios[username] = user

        salas = {}
        for nombre, modalidad in SALAS:
            sala, _ = Sala.objects.get_or_create(nombre=nombre, defaults={"modalidad": modalidad})
            salas.setdefault(sala.modalidad, []).append(sala)

        procedimientos = []
        for codigo, nombre, modalidad, duracion in PROCEDIMIENTOS:
            proc, _ = Procedimiento.objects.get_or_create(
                codigo=codigo,
                defaults={"nombre": nombre, "modalidad": modalidad, "duracion_minutos": duracion},
            )
            procedimientos.append(proc)

        if opts["reset"]:
            Informe.objects.all().delete()
            Orden.objects.all().delete()
            Paciente.objects.all().delete()
        elif Paciente.objects.exists():
            self.stdout.write(self.style.WARNING("Ya hay pacientes cargados. Usa --reset para regenerarlos."))
            return

        # --- Pacientes
        pacientes = []
        for i in range(opts["pacientes"]):
            sexo = rng.choice(["F", "M"])
            nombre = rng.choice(NOMBRES_F if sexo == "F" else NOMBRES_M)
            pacientes.append(
                Paciente.objects.create(
                    documento=f"{rng.randint(10_000_000, 99_999_999)}",
                    nombres=nombre,
                    apellidos=f"{rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}",
                    fecha_nacimiento=date(rng.randint(1940, 2015), rng.randint(1, 12), rng.randint(1, 28)),
                    sexo=sexo,
                    telefono=f"55 {rng.randint(1000, 9999)} {rng.randint(1000, 9999)}",
                    email=f"{nombre.lower()}.{i}@ejemplo.com".replace("í", "i").replace("é", "e").replace("á", "a"),
                )
            )

        # --- Órdenes
        hoy = timezone.localdate()
        siguiente_hueco = {}  # (sala_id, fecha) -> datetime libre

        def reservar(sala, dia, duracion):
            clave = (sala.pk, dia)
            inicio = siguiente_hueco.get(clave) or timezone.make_aware(datetime.combine(dia, time(8, 0)))
            siguiente_hueco[clave] = inicio + timedelta(minutes=duracion + 5)
            return inicio

        total_informes = 0
        for estado in ESTADOS:
            proc = rng.choice(procedimientos)
            if proc.modalidad == "MG" or proc.codigo == "US-OBS":
                candidatas = [p for p in pacientes if p.sexo == "F"]
            else:
                candidatas = pacientes
            orden = Orden(
                paciente=rng.choice(candidatas),
                procedimiento=proc,
                medico_solicitante=rng.choice(MEDICOS),
                indicacion_clinica=rng.choice(INDICACIONES[proc.modalidad]),
                prioridad=rng.choices(
                    [Orden.Prioridad.RUTINA, Orden.Prioridad.URGENTE, Orden.Prioridad.STAT], weights=[75, 20, 5]
                )[0],
                estado=estado,
            )

            if estado in (Orden.Estado.PROGRAMADA, Orden.Estado.EN_CURSO, Orden.Estado.REALIZADA, Orden.Estado.INFORMADA):
                if estado == Orden.Estado.PROGRAMADA:
                    dia = hoy + timedelta(days=rng.randint(0, 3))
                elif estado == Orden.Estado.EN_CURSO:
                    dia = hoy
                else:
                    dia = hoy - timedelta(days=rng.randint(1, 10))
                orden.sala = rng.choice(salas[proc.modalidad])
                orden.fecha_programada = reservar(orden.sala, dia, proc.duracion_minutos)

            if estado in (Orden.Estado.EN_CURSO, Orden.Estado.REALIZADA, Orden.Estado.INFORMADA):
                orden.fecha_inicio = orden.fecha_programada
                orden.tecnico = usuarios["tecnico"]
            if estado in (Orden.Estado.REALIZADA, Orden.Estado.INFORMADA):
                orden.fecha_realizacion = orden.fecha_programada + timedelta(minutes=proc.duracion_minutos)

            orden.save()

            hallazgos, conclusion = rng.choice(INFORMES)
            if estado == Orden.Estado.INFORMADA:
                Informe.objects.create(
                    orden=orden,
                    hallazgos=hallazgos,
                    conclusion=conclusion,
                    estado=Informe.Estado.FIRMADO,
                    radiologo=usuarios["radiologo"],
                    fecha_firma=orden.fecha_realizacion + timedelta(hours=rng.randint(1, 24)),
                )
                total_informes += 1
            elif estado == Orden.Estado.REALIZADA and rng.random() < 0.3:
                Informe.objects.create(orden=orden, hallazgos=hallazgos, conclusion="(pendiente)")
                total_informes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Datos cargados: {len(pacientes)} pacientes, {len(ESTADOS)} órdenes, {total_informes} informes."
            )
        )
        self.stdout.write("Usuarios: admin/admin123 · tecnico/tecnico123 · radiologo/radiologo123")
