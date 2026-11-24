# =====================================================================
# Contenido para el archivo WSGI de PythonAnywhere
# (pestaña Web -> "WSGI configuration file"). Borre todo lo que tenga
# ese archivo y pegue esto. Cambie TU_USUARIO y la clave secreta.
# =====================================================================
import os
import sys

USUARIO = "TU_USUARIO"
ruta = f"/home/{USUARIO}/limpiahogar"
if ruta not in sys.path:
    sys.path.insert(0, ruta)

os.environ["DJANGO_SETTINGS_MODULE"] = "limpiahogar.settings"
os.environ["DJANGO_DEBUG"] = "0"
os.environ["DJANGO_ALLOWED_HOSTS"] = f"{USUARIO}.pythonanywhere.com"
os.environ["DJANGO_SECRET_KEY"] = "PEGUE_AQUI_LA_CLAVE_GENERADA"

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
