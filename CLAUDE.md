# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

RIS Demo: Sistema de Información Radiológica de práctica hecho con Django 5 + SQLite y plantillas Bootstrap 5 cargadas desde un CDN. Todos los datos son ficticios y el proyecto no es apto para uso clínico. El usuario se comunica en **español**: el código, los nombres de variables, los textos de la interfaz y los mensajes van en español.

## Comandos

Usa Windows y PowerShell. El entorno virtual está en `.venv`.

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py makemigrations ris      # todavía no hay migraciones versionadas en ris/migrations/
python manage.py migrate
python manage.py cargar_datos_demo       # --reset para borrar y regenerar; --pacientes N
python manage.py runserver               # http://127.0.0.1:8000/
python manage.py test ris                # todas las pruebas
python manage.py test ris.tests.MiClase.test_metodo   # una sola prueba
```

Aún no hay pruebas ni linter configurados. Usuarios de demo: `admin/admin123` (superusuario), `tecnico/tecnico123` y `radiologo/radiologo123`. Los tres son `is_staff`, porque el inicio de sesión usa el formulario del admin (`LOGIN_URL = "admin:login"`).

## Arquitectura

Toda la lógica de negocio está en una sola app, `ris`; `config/` solo contiene los settings y las URLs raíz.

**Flujo de estados de `Orden`**, que es el núcleo del sistema:
`SOLICITADA → PROGRAMADA → EN_CURSO → REALIZADA → INFORMADA`, con `CANCELADA` posible desde los tres primeros estados.
- Las transiciones viven en los métodos del modelo (`Orden.iniciar/completar/cancelar`, `Informe.firmar`). Pasan por `_transicion()`, que lanza `ValueError` si la transición no es válida.
- `views.orden_accion` despacha las acciones a partir de la URL `ordenes/<pk>/<accion>/` (solo POST), convierte el `ValueError` en un mensaje de error y acepta un `next` para volver a la página anterior; la lista de trabajo lo usa. Si añades una acción, regístrala en el diccionario `acciones` de esa vista.
- Las dos transiciones que no pasan por esos métodos son: programar (`views.orden_programar` pone `PROGRAMADA` tras validar `ProgramarForm`) y firmar el informe (`Informe.firmar` pone la orden en `INFORMADA`).
- El comando `cargar_datos_demo` asigna los estados y las fechas directamente, sin pasar por esos métodos.

**Reglas de negocio repartidas en otros archivos:**
- `ProgramarForm` (`forms.py`) limita las salas a las de la misma modalidad que el procedimiento y detecta choques de horario en la sala. La duración de cada estudio sale de `Procedimiento.duracion_minutos`.
- `informe_editar` solo permite informar órdenes en estado `REALIZADA`. Un informe `FIRMADO` ya no se puede editar.
- `historia_clinica` (`HC000001`) y `numero_acceso` (`ACC0000001`) se generan en `save()` después del primer guardado, a partir del `pk`. Por eso son `null=True` y `editable=False`.

**Plantillas** (`ris/templates/ris/`): todas extienden `base.html`. Los formularios se pintan con el parcial `_form.html`, que espera `form` en el contexto, y las tablas de órdenes con `_tabla_ordenes.html` (opción `ocultar_paciente`). Los colores de estado y prioridad usan las clases CSS `estado-<ESTADO>` y `prio-<PRIORIDAD>` definidas en `base.html`. Si añades un estado nuevo, agrega también su clase. `BootstrapMixin` (`forms.py`) añade las clases `form-control` y `form-select` a todos los campos.

**Zona horaria:** `USE_TZ=True` con `TIME_ZONE="America/Mexico_City"`. Las consultas de agenda usan `fecha_programada__date` y `timezone.localdate()`.
