"""
Exporta los datos actuales de la app como un script SQL de INSERT para pgAdmin.

Uso:
    python manage.py exportar_datos_sql > sql/datos-prueba.sql

El script resultante se ejecuta después de aseo-viviendas.sql (que crea las
tablas) y antes de consultas.sql.
"""
from datetime import date, time
from decimal import Decimal

from django.core.management.base import BaseCommand

from aseo import models as m

# Orden en que se insertan para respetar las claves foráneas
ORDEN = [m.Zona, m.Barrio, m.TipoVivienda, m.TipoArea, m.TipoElemento, m.Cliente, m.Vivienda, m.Area,
         m.Elemento, m.Especialidad, m.Empleado, m.EmpleadoEspecialidad, m.EmpleadoZona, m.TipoServicio,
         m.Servicio, m.DetalleServicio, m.Asignacion, m.CategoriaInsumo, m.Proveedor, m.Insumo,
         m.InsumoRequerido, m.InsumoUsado, m.MetodoPago, m.Pago]


def literal(valor):
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, (int, Decimal)):
        return str(valor)
    if isinstance(valor, date):
        return f"'{valor.isoformat()}'"
    if isinstance(valor, time):
        return f"'{valor.strftime('%H:%M:%S')}'"
    return "'" + str(valor).replace("'", "''") + "'"


class Command(BaseCommand):
    help = "Genera un script SQL con los datos actuales para cargarlos en pgAdmin."

    def handle(self, *args, **opts):
        salida = [
            "-- =====================================================================",
            "-- PROYECTO : Sistema de servicios de aseo en viviendas (LimpiaHogar)",
            "-- ARCHIVO  : Datos de prueba (ficticios) para PostgreSQL / pgAdmin 4",
            "-- Ejecutar DESPUÉS de aseo-viviendas.sql y ANTES de consultas.sql.",
            f"-- Generado el {date.today().isoformat()} desde la aplicación web.",
            "-- =====================================================================",
            "",
            "BEGIN;",
            "",
        ]
        supervisores = []
        for modelo in ORDEN:
            meta = modelo._meta
            # Las tablas intermedias del script SQL no tienen la columna 'id' de Django
            campos = [f for f in meta.concrete_fields if not (f.primary_key and f.column == "id")]
            identidad = meta.pk.column != "id"
            columnas = ", ".join(f.column for f in campos)
            salida.append(f"-- {meta.db_table}")
            for obj in modelo.objects.order_by("pk"):
                valores = []
                for f in campos:
                    valor = getattr(obj, f.attname)
                    if modelo is m.Empleado and f.column == "id_supervisor":
                        if valor:
                            supervisores.append((obj.pk, valor))
                        valor = None
                    valores.append(literal(valor))
                overriding = " OVERRIDING SYSTEM VALUE" if identidad else ""
                salida.append(f"INSERT INTO {meta.db_table} ({columnas}){overriding} VALUES ({', '.join(valores)});")
            salida.append("")

        salida.append("-- Supervisores (se asignan después porque es una auto-relación)")
        for emp, sup in supervisores:
            salida.append(f"UPDATE empleado SET id_supervisor = {sup} WHERE id_empleado = {emp};")
        salida.append("")
        salida.append("-- Ajusta los contadores de las claves autoincrementales")
        for modelo in ORDEN:
            pk = modelo._meta.pk.column
            tabla = modelo._meta.db_table
            if pk != "id":
                salida.append(f"SELECT setval(pg_get_serial_sequence('{tabla}', '{pk}'), "
                              f"COALESCE((SELECT MAX({pk}) FROM {tabla}), 0) + 1, false);")
        salida += ["", "COMMIT;", ""]
        self.stdout.write("\n".join(salida))
