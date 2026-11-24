from django.contrib import admin

from .registro import TABLAS

# El panel de administración de Django queda como respaldo: registra las 24 tablas.
for conf in TABLAS.values():
    admin.site.register(conf["modelo"], list_display=conf["columnas"], search_fields=conf["buscar"])

admin.site.site_header = "LimpiaHogar - Administración"
