from .registro import GRUPOS, TABLAS


def menu(request):
    """Menú lateral con las tablas agrupadas, disponible en todas las plantillas."""
    return {
        "menu_grupos": [
            (grupo, [(clave, str(TABLAS[clave]["modelo"]._meta.verbose_name_plural).capitalize())
                     for clave in claves])
            for grupo, claves in GRUPOS
        ]
    }
