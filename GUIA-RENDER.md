# Publicar LimpiaHogar gratis en Render

En Render, la aplicación usa una base **PostgreSQL** gratuita, el mismo motor del script SQL. El archivo `render.yaml` crea la base y la aplicación de una vez, y en el primer despliegue la base se llena con los datos ficticios.

Render tiene dos límites en el plan gratuito:
- **La app "se duerme" tras 15 minutos sin visitas.** La primera visita después de eso tarda unos 50 segundos en cargar. Ábrela un minuto antes de mostrársela a la profesora.
- **La base de datos gratuita dura 30 días.** Alcanza de sobra para la entrega.

## 1. Subir el proyecto a GitHub

1. Entra a https://github.com y crea un repositorio nuevo con **New repository**. Ponle de nombre `limpiahogar` y elige **Public**. No marques "Add a README".
2. Sube el código al repositorio. Hay dos formas:
   - **Yo lo subo:** me dices el nombre del repositorio y lo hago.
   - **Lo subes tú:** en la página del repositorio vacío pulsa **uploading an existing file**. Descomprime `limpiahogar-render.zip` en tu computador, entra a la carpeta `limpiahogar` y arrastra **todo su contenido** (las carpetas `aseo`, `limpiahogar` y los archivos `manage.py`, `render.yaml`, `build.sh`, `requirements.txt`...). Pulsa **Commit changes**.

   El archivo `render.yaml` tiene que quedar en la raíz del repositorio, no dentro de otra carpeta.

## 2. Crear la app en Render

1. Entra a https://render.com y pulsa **Get Started**. Regístrate con **GitHub**, así no hay que esperar ningún correo de verificación.
2. En el panel pulsa **New +** y luego **Blueprint**.
3. Conecta tu cuenta de GitHub si lo pide y elige el repositorio `limpiahogar`.
4. Render lee el `render.yaml` y muestra la base `limpiahogar-db` y el servicio web `limpiahogar`. Te pide un valor para **DJANGO_SUPERUSER_PASSWORD**: escribe la contraseña que usará la profesora para entrar a editar. El usuario es `profesora`.
5. Pulsa **Apply** y espera de 5 a 10 minutos mientras instala, crea las tablas y carga los datos.
6. Cuando el servicio diga **Live**, abre el enlace que aparece arriba, parecido a `https://limpiahogar-xxxx.onrender.com`.

## 3. Entrar a editar

En la app pulsa **Ingresar para editar** y usa:
- **Usuario:** `profesora`
- **Contraseña:** la que pusiste en el paso 2.4

Con esa cuenta también funciona el panel de Django en `/admin/`.

## Si algo falla

- En Render, entra al servicio `limpiahogar` y abre la pestaña **Logs**. Ahí aparece el error exacto; cópialo y me lo mandas.
- **Si cambias el código en GitHub,** Render vuelve a desplegar solo. Los datos no se borran.
