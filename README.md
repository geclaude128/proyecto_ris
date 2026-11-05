# RIS Demo: Sistema de Información Radiológica (proyecto de prueba)

Proyecto de práctica en **Django + SQLite** que simula el flujo básico de un servicio de radiología.
Todos los datos son ficticios. **No apto para uso clínico real.**

## Funcionalidades

| Módulo | Qué hace |
|---|---|
| **Pacientes** | Alta, edición, búsqueda e historial de estudios. La historia clínica se genera sola (`HC000001`). |
| **Órdenes** | Solicitud de estudios con prioridad (rutina, urgente, STAT) y número de acceso automático (`ACC0000001`). |
| **Programación** | Asignación de sala y horario. Valida que la sala sea de la modalidad correcta y que no haya choques de horario. |
| **Lista de trabajo** | Agenda diaria por modalidad para el técnico: *Iniciar* → *Completar*. |
| **Informes** | Lista priorizada de estudios pendientes; el radiólogo guarda un borrador y luego firma (el informe firmado ya no se puede editar). |
| **Panel** | Contadores por estado, agenda del día y urgentes pendientes. |
| **Admin** | Administración de Django para catálogos (salas, procedimientos) y usuarios. |

### Flujo de estados de una orden

```
SOLICITADA → PROGRAMADA → EN_CURSO → REALIZADA → INFORMADA
     └───────────┴───────────┴──→ CANCELADA
```

## Estructura

```
proyecto_ris/
├── config/                 # settings, urls
├── ris/
│   ├── models.py           # Paciente, Sala, Procedimiento, Orden, Informe
│   ├── forms.py            # Formularios + validación de agenda
│   ├── views.py            # Vistas (funciones)
│   ├── admin.py
│   ├── management/commands/cargar_datos_demo.py
│   └── templates/ris/      # Plantillas con Bootstrap 5
├── manage.py
└── requirements.txt
```

## Instalación (Windows / PowerShell)

1. Instala Python 3.12 o superior (si no lo tienes):
   ```powershell
   winget install Python.Python.3.12
   ```
   Cierra y vuelve a abrir la terminal.

2. Crea el entorno virtual e instala las dependencias:
   ```powershell
   cd C:\Users\Claude\proyecto_ris
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Crea la base de datos y carga los datos de prueba:
   ```powershell
   python manage.py makemigrations ris
   python manage.py migrate
   python manage.py cargar_datos_demo
   ```

4. Arranca el servidor:
   ```powershell
   python manage.py runserver
   ```
   Abre <http://127.0.0.1:8000/>.

### Usuarios de prueba

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Superusuario |
| `tecnico` | `tecnico123` | Técnico radiólogo |
| `radiologo` | `radiologo123` | Médico radiólogo |

Para regenerar los datos: `python manage.py cargar_datos_demo --reset`

## Ideas para ampliar

- Permisos por rol (que solo los radiólogos puedan firmar informes) con grupos de Django.
- Exportar el informe a PDF.
- API REST con Django REST Framework.
- Mensajes HL7 (ORM/ORU) o integración DICOM Modality Worklist con un PACS de prueba como Orthanc.
- Pruebas automatizadas (`python manage.py test`).
