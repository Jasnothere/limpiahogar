"""Lee las 15 consultas de sql/consultas.sql para mostrarlas y ejecutarlas en la app."""
import re
from functools import lru_cache

from django.conf import settings

ARCHIVO = settings.BASE_DIR / "sql" / "consultas.sql"
PATRON = re.compile(r"^-- Consulta (\d+): (.+)$", re.MULTILINE)


@lru_cache(maxsize=1)
def cargar():
    texto = ARCHIVO.read_text(encoding="utf-8")
    marcas = list(PATRON.finditer(texto))
    consultas = []
    for i, marca in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        bloque = texto[marca.end():fin].strip()
        lineas = bloque.splitlines()
        descripcion = " ".join(l[2:].strip() for l in lineas if l.startswith("--"))
        sql = "\n".join(l for l in lineas if not l.startswith("--")).strip().rstrip(";")
        consultas.append({"numero": int(marca.group(1)), "tipo": marca.group(2).strip(),
                          "descripcion": descripcion, "sql": sql})
    return consultas
