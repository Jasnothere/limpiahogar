# LimpiaHogar: aplicación Django y guía para publicarla en PythonAnywhere

## Qué incluye

- **Las 24 tablas del modelo UML** como modelos de Django (`aseo/models.py`), con los mismos nombres de tabla y columna del script SQL.
- **CRUD completo:** cualquiera puede ver las tablas. Para agregar, modificar o eliminar registros hay que iniciar sesión.
- **Pantalla de cada servicio:** reúne los tipos de servicio y su alcance, los empleados asignados (con sugerencia de los que cumplen las reglas), las calificaciones, los insumos y el pago.
- **Informes (RF20):** servicios por fecha, zona y barrio; ingresos por mes y por método de pago; empleados y servicios mejor calificados; clientes peor calificados; insumos más usados; y áreas y elementos más limpiados.
- **Calificación de clientes (RF21):** promedio de cada cliente y botón para bloquearlo o desbloquearlo.
- **Datos ficticios:** el comando `python manage.py poblar_datos` llena la base con 30 clientes, 22 empleados y 90 servicios, entre otros datos.
- **Pruebas automáticas:** `python manage.py test aseo` corre 15 pruebas de las reglas y de las vistas.
- **Panel de administración de Django** en `/admin/`, como respaldo.

### Reglas que valida la aplicación

| Regla | Dónde |
|---|---|
| Un solo pago por servicio, y solo si el servicio está finalizado | `Pago` (OneToOne + clean) |
| Solo se califica un servicio finalizado | `Servicio` y `Asignacion` (CheckConstraint + clean) |
| Calificaciones de 1 a 5 | Validadores y CheckConstraint |
| Detalle para toda la vivienda, un área o un elemento (no ambos) | `DetalleServicio` (CheckConstraint) |
| El área o elemento debe ser de la vivienda del servicio | `DetalleServicio.clean` |
| El empleado debe estar activo, tener la especialidad y trabajar en la zona | `Asignacion.clean` |
| Un empleado no puede tener dos servicios a la misma hora | `Asignacion.clean` |
| Un cliente bloqueado no puede pedir servicios | `Servicio.clean` |
| Para confirmar o finalizar, el servicio necesita al menos un detalle y un empleado | `Servicio.clean` |
| Solo los insumos de la empresa se descuentan del stock, y no se puede usar más de lo que hay | `InsumoUsado` |
| Un empleado no puede ser su propio supervisor | `Empleado` |
| No se puede borrar un registro que otros usan (por ejemplo, una zona con barrios) | `on_delete=PROTECT` |

### Diferencias con el script SQL

- **Base de datos.** La aplicación usa SQLite, porque la cuenta gratuita de PythonAnywhere no incluye PostgreSQL. Las tablas, claves y restricciones son las mismas.
- **Tablas intermedias.** Las tablas con clave compuesta (`asignacion`, `empleado_zona`, `empleado_especialidad`, `insumo_requerido`, `insumo_usado`) llevan además una columna `id`, porque los formularios de Django la necesitan. La combinación de las dos claves sigue siendo única gracias a una `UniqueConstraint`, así que la regla es la misma.

---

## Probarla en tu computador (opcional)

```bash
python -m venv venv
venv\Scripts\activate            # en Windows; en Mac o Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py poblar_datos
python manage.py createsuperuser
python manage.py runserver
```

Luego abre http://127.0.0.1:8000.

---

## Publicarla en PythonAnywhere (cuenta gratuita)

En los pasos de abajo, cambia `TU_USUARIO` por tu nombre de usuario de PythonAnywhere.

### 1. Crear la cuenta
Entra a https://www.pythonanywhere.com y crea una cuenta **Beginner (gratis)**. Tu página quedará en `https://TU_USUARIO.pythonanywhere.com`.

### 2. Subir el proyecto
1. Abre la pestaña **Files** y sube el archivo `limpiahogar.zip` a `/home/TU_USUARIO/`.
2. Abre la pestaña **Consoles** y luego **Bash**, y escribe:

```bash
cd ~
unzip limpiahogar.zip
cd limpiahogar
```

### 3. Crear el entorno e instalar Django
En la misma consola:

```bash
mkvirtualenv --python=python3.12 limpiahogar-env
pip install -r requirements.txt
```

Si `python3.12` no existe en tu cuenta, usa `python3.11` o `python3.10`. Más adelante, en el paso 5, elige esa misma versión.

### 4. Crear la base de datos y llenarla
```bash
python manage.py migrate
python manage.py poblar_datos
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

`createsuperuser` crea el usuario con el que se inicia sesión para editar. Puedes crear uno para ti y otro para la profesora.

Después genera una clave secreta y cópiala:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Crear la aplicación web
1. Ve a la pestaña **Web** y pulsa **Add a new web app**. Luego **Next**, elige **Manual configuration** (no "Django") y la misma versión de Python del paso 3.
2. En la sección **Virtualenv**, escribe `/home/TU_USUARIO/.virtualenvs/limpiahogar-env`.
3. En **Code**, en "Source code", escribe `/home/TU_USUARIO/limpiahogar`.
4. Abre el enlace del **WSGI configuration file**. Borra todo su contenido y pega el de `pythonanywhere_wsgi.py`. Cambia `TU_USUARIO` y pega la clave del paso 4 en `DJANGO_SECRET_KEY`. Guarda con **Save**.
5. En **Static files**, agrega URL `/static/` y Directory `/home/TU_USUARIO/limpiahogar/staticfiles`.
6. En **Security**, activa **Force HTTPS**.
7. Pulsa el botón verde **Reload** arriba.

Abre `https://TU_USUARIO.pythonanywhere.com` y debería aparecer la aplicación.

### 6. Si algo falla
- En la pestaña **Web**, el enlace **Error log** muestra el error exacto.
- **"DisallowedHost":** revisa que `USUARIO` en el archivo WSGI sea tu usuario exacto.
- **La página se ve sin estilos:** revisa el paso 5.5 y vuelve a correr `collectstatic`.
- **Cambiaste código:** pulsa **Reload** otra vez.
- **Volver a los datos ficticios iniciales:** corre `python manage.py poblar_datos --borrar`.

### 7. Duración en la cuenta gratuita
PythonAnywhere desactiva las aplicaciones gratuitas después de 3 meses si no las renuevas. Para renovarla, entra a la pestaña **Web** y pulsa "Run until 3 months from today".
