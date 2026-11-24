"""
Llena la base de datos con datos ficticios que cumplen todas las reglas.

Uso:
    python manage.py poblar_datos            # solo si la base está vacía
    python manage.py poblar_datos --borrar   # borra todo y vuelve a llenar

Cada registro se valida con full_clean() antes de guardarse, así que los
datos de prueba pasan por las mismas reglas que los formularios.
"""
import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from aseo import models as m

NOMBRES = ["Laura", "Andrés", "Camila", "Santiago", "Valentina", "Julián", "Daniela", "Felipe", "Mariana",
           "Sebastián", "Natalia", "Carlos", "Paula", "Diego", "Sofía", "Juan", "Carolina", "Miguel",
           "Isabela", "Alejandro", "Gabriela", "David", "Luisa", "Óscar", "Ana", "Jorge", "Manuela", "Ricardo"]
APELLIDOS = ["Gómez", "Rodríguez", "Martínez", "López", "García", "Hernández", "Ramírez", "Torres", "Díaz",
             "Moreno", "Vargas", "Rojas", "Castro", "Suárez", "Ortiz", "Jiménez", "Pardo", "Cárdenas",
             "Salazar", "Mejía", "Restrepo", "Ospina", "Quintero", "Acosta"]

ZONAS = {
    "Norte": ["Usaquén", "Cedritos", "Chicó", "Santa Bárbara"],
    "Occidente": ["Modelia", "Fontibón", "Salitre", "Castilla"],
    "Sur": ["Kennedy", "Tunal", "Bosa", "Restrepo"],
    "Centro": ["Chapinero", "Teusaquillo", "La Candelaria", "Palermo"],
}
TIPOS_VIVIENDA = ["Casa", "Apartamento", "Apartaestudio", "Finca"]
TIPOS_AREA = ["Cocina", "Baño", "Habitación", "Sala", "Comedor", "Patio", "Jardín", "Piscina", "Terraza",
              "Balcón", "Garaje"]
TIPOS_ELEMENTO = ["Sofá", "Colchón", "Alfombra", "Cortinas", "Nevera", "Horno", "Ventanal"]
ESPECIALIDADES = ["Limpieza general", "Limpieza profunda", "Muebles y tapicería", "Vidrios y alturas",
                  "Mantenimiento de piscinas", "Limpieza de exteriores", "Limpieza post-obra", "Desinfección",
                  "Lavandería y planchado"]
# nombre: (horas, precio, especialidad, alcance) — alcance: None = toda la vivienda,
# ("area", [tipos]) o ("elemento", [tipos])
TIPOS_SERVICIO = {
    "Limpieza general de la vivienda": (4, 120000, "Limpieza general", None),
    "Limpieza profunda de cocina": (3, 95000, "Limpieza profunda", ("area", ["Cocina"])),
    "Limpieza y desinfección de baños": (1.5, 45000, "Desinfección", ("area", ["Baño"])),
    "Lavado de sofá": (2, 80000, "Muebles y tapicería", ("elemento", ["Sofá"])),
    "Lavado de colchón": (1.5, 70000, "Muebles y tapicería", ("elemento", ["Colchón"])),
    "Lavado de alfombra": (1.5, 60000, "Muebles y tapicería", ("elemento", ["Alfombra"])),
    "Lavado de cortinas": (2, 55000, "Lavandería y planchado", ("elemento", ["Cortinas"])),
    "Limpieza de ventanales y vidrios": (2, 65000, "Vidrios y alturas", ("elemento", ["Ventanal"])),
    "Limpieza de piscina": (3, 150000, "Mantenimiento de piscinas", ("area", ["Piscina"])),
    "Limpieza de patio o terraza": (2, 60000, "Limpieza de exteriores", ("area", ["Patio", "Terraza", "Jardín"])),
    "Limpieza post-obra": (6, 280000, "Limpieza post-obra", None),
    "Planchado de ropa": (2, 50000, "Lavandería y planchado", None),
}
PROVEEDORES = [("900123456-1", "Distribuidora Aseo Total S.A.S.", "6015551234"),
               ("901234567-2", "Químicos del Norte Ltda.", "6015552345"),
               ("830345678-3", "Herramientas y Equipos Bogotá", "6015553456"),
               ("860456789-4", "Suministros La Limpieza", "6015554567")]
INSUMOS = {  # nombre: (categoría, índice de proveedor)
    "Desengrasante": ("producto", 1), "Cloro": ("producto", 1), "Ambientador": ("producto", 0),
    "Limpiavidrios": ("producto", 1), "Jabón multiusos": ("producto", 0), "Shampoo para tapicería": ("producto", 3),
    "Desinfectante": ("producto", 1), "Trapeador": ("utensilio", 0), "Escoba": ("utensilio", 0),
    "Paños de microfibra": ("utensilio", 3), "Cepillo de cerdas duras": ("utensilio", 3),
    "Aspiradora": ("herramienta", 2), "Hidrolavadora": ("herramienta", 2), "Escalera": ("herramienta", 2),
    "Máquina lavatapetes": ("herramienta", 2), "Aspiradora de piscina": ("herramienta", 2), "Plancha": ("herramienta", 2),
}
REQUERIDOS = {
    "Limpieza general de la vivienda": [("Jabón multiusos", 1), ("Trapeador", 1), ("Escoba", 1), ("Paños de microfibra", 2), ("Ambientador", 1)],
    "Limpieza profunda de cocina": [("Desengrasante", 1), ("Paños de microfibra", 2), ("Cepillo de cerdas duras", 1)],
    "Limpieza y desinfección de baños": [("Cloro", 1), ("Desinfectante", 1), ("Cepillo de cerdas duras", 1)],
    "Lavado de sofá": [("Shampoo para tapicería", 1), ("Máquina lavatapetes", 1)],
    "Lavado de colchón": [("Shampoo para tapicería", 1), ("Aspiradora", 1)],
    "Lavado de alfombra": [("Shampoo para tapicería", 1), ("Máquina lavatapetes", 1)],
    "Lavado de cortinas": [("Jabón multiusos", 1), ("Plancha", 1)],
    "Limpieza de ventanales y vidrios": [("Limpiavidrios", 1), ("Paños de microfibra", 2), ("Escalera", 1)],
    "Limpieza de piscina": [("Cloro", 3), ("Cepillo de cerdas duras", 1), ("Aspiradora de piscina", 1)],
    "Limpieza de patio o terraza": [("Hidrolavadora", 1), ("Escoba", 1), ("Jabón multiusos", 1)],
    "Limpieza post-obra": [("Aspiradora", 1), ("Desengrasante", 2), ("Trapeador", 1), ("Paños de microfibra", 4)],
    "Planchado de ropa": [("Plancha", 1)],
}
METODOS_PAGO = ["Efectivo", "Tarjeta débito", "Tarjeta crédito", "Transferencia bancaria", "Llave Bre-B",
                "Código QR", "Nequi", "Daviplata"]
COMENTARIOS_BUENOS = ["Excelente trabajo", "Muy puntual y amable", "Quedó impecable", "Muy recomendado", ""]
COMENTARIOS_MALOS = ["Llegó tarde", "Faltaron cosas por limpiar", "No respetó las indicaciones", ""]
COMENTARIOS_CLIENTE_MALO = ["No estaba en casa a la hora acordada", "Trato irrespetuoso", "Cambió el servicio sin avisar"]


def guardar(obj):
    """Valida con las mismas reglas de los formularios y guarda."""
    obj.full_clean()
    obj.save()
    return obj


class Command(BaseCommand):
    help = "Llena la base de datos con datos ficticios de prueba."

    def add_arguments(self, parser):
        parser.add_argument("--borrar", action="store_true", help="Borra los datos existentes antes de llenar.")
        parser.add_argument("--semilla", type=int, default=2026)

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(opts["semilla"])
        if opts["borrar"]:
            self.borrar()
        elif m.Servicio.objects.exists():
            self.stdout.write(self.style.WARNING("La base ya tiene datos. Use --borrar para reemplazarlos."))
            return

        # ---------- catálogos ----------
        zonas = {}
        barrios = []
        for z, bs in ZONAS.items():
            zonas[z] = guardar(m.Zona(nombre=z))
            barrios += [guardar(m.Barrio(nombre=b, zona=zonas[z])) for b in bs]
        tv = {n: guardar(m.TipoVivienda(nombre=n)) for n in TIPOS_VIVIENDA}
        ta = {n: guardar(m.TipoArea(nombre=n)) for n in TIPOS_AREA}
        te = {n: guardar(m.TipoElemento(nombre=n)) for n in TIPOS_ELEMENTO}
        esp = {n: guardar(m.Especialidad(nombre=n)) for n in ESPECIALIDADES}
        ts = {n: guardar(m.TipoServicio(nombre=n, duracion_horas=Decimal(str(h)), precio=Decimal(p),
                                        especialidad=esp[e]))
              for n, (h, p, e, _) in TIPOS_SERVICIO.items()}
        cat = {c: guardar(m.CategoriaInsumo(nombre=c)) for c in ["producto", "utensilio", "herramienta"]}
        prov = [guardar(m.Proveedor(nit=n, nombre=nom, telefono=t)) for n, nom, t in PROVEEDORES]
        ins = {n: guardar(m.Insumo(nombre=n, categoria=cat[c], proveedor=prov[p], stock=rnd.randint(300, 600)))
               for n, (c, p) in INSUMOS.items()}
        for t, lista in REQUERIDOS.items():
            for n, cant in lista:
                guardar(m.InsumoRequerido(tipo_servicio=ts[t], insumo=ins[n], cantidad_sugerida=Decimal(cant)))
        metodos = [guardar(m.MetodoPago(nombre=n)) for n in METODOS_PAGO]

        # ---------- clientes, viviendas, áreas y elementos ----------
        usados = set()

        def persona():
            while True:
                n, a = rnd.choice(NOMBRES), f"{rnd.choice(APELLIDOS)} {rnd.choice(APELLIDOS)}"
                if (n, a) not in usados:
                    usados.add((n, a))
                    return n, a

        clientes, viviendas = [], []
        for i in range(30):
            n, a = persona()
            correo = f"{n}.{a.split()[0]}{i}@correo.com".lower()
            for x, y in zip("áéíóúñ", "aeioun"):
                correo = correo.replace(x, y)
            c = guardar(m.Cliente(documento=str(1010200300 + i * 137), nombre=n, apellido=a,
                                  telefono=f"3{rnd.randint(100000000, 209999999)}", correo=correo))
            clientes.append(c)
            for _ in range(rnd.choice([1, 1, 1, 2])):
                tipo = rnd.choice(["Apartamento", "Apartamento", "Casa", "Casa", "Apartaestudio", "Finca"])
                v = guardar(m.Vivienda(
                    cliente=c, barrio=rnd.choice(barrios), tipo_vivienda=tv[tipo],
                    direccion=f"{rnd.choice(['Calle', 'Carrera', 'Avenida', 'Transversal', 'Diagonal'])} "
                              f"{rnd.randint(1, 170)} # {rnd.randint(1, 120)}-{rnd.randint(1, 99)}"
                              + (f" apto {rnd.randint(101, 1204)}" if tipo.startswith("Apart") else "")))
                viviendas.append(v)
                self.crear_areas(rnd, v, tipo, ta, te)

        # ---------- empleados ----------
        empleados = []
        supervisores = []
        for i in range(22):
            n, a = persona()
            sup = None if i < 4 else rnd.choice(supervisores)
            e = guardar(m.Empleado(documento=str(52100200 + i * 311), nombre=n, apellido=a,
                                   telefono=f"3{rnd.randint(100000000, 209999999)}",
                                   estado="inactivo" if i in (20, 21) else "activo", supervisor=sup))
            if i < 4:
                supervisores.append(e)
            empleados.append(e)
            for z in rnd.sample(list(zonas.values()), rnd.randint(1, 3)):
                guardar(m.EmpleadoZona(empleado=e, zona=z))
            base = ["Limpieza general"] + rnd.sample(ESPECIALIDADES[1:], rnd.randint(1, 4))
            for nombre in base:
                guardar(m.EmpleadoEspecialidad(empleado=e, especialidad=esp[nombre]))

        # ---------- servicios ----------
        hoy = date.today()
        malos = set(rnd.sample(clientes, 3))  # clientes que los empleados califican mal
        creados = 0
        intentos = 0
        while creados < 90 and intentos < 600:
            intentos += 1
            v = rnd.choice(viviendas)
            dias = rnd.randint(-120, 20)
            s = m.Servicio(vivienda=v, fecha=hoy + timedelta(days=dias),
                           hora_inicio=time(rnd.choice([7, 8, 9, 10, 11, 13, 14]), rnd.choice([0, 30])),
                           observaciones=rnd.choice(["", "", "Dejar las llaves en portería",
                                                     "Hay mascotas en casa", "Traer productos sin olor"]) or None)
            try:
                guardar(s)
            except ValidationError:
                continue
            if not self.agregar_detalles(rnd, s, v, ts) or not self.asignar(rnd, s, empleados):
                s.delete()
                continue
            creados += 1
            if dias < 0:
                s.estado = "cancelado" if rnd.random() < 0.08 else "finalizado"
            else:
                s.estado = rnd.choice(["pendiente", "confirmado"])
            if s.estado == "finalizado":
                s.calificacion_servicio = rnd.choice([3, 4, 4, 5, 5, 5])
                s.comentario_servicio = rnd.choice(COMENTARIOS_BUENOS) or None
            guardar(s)
            if s.estado == "finalizado":
                self.cerrar(rnd, s, v.cliente in malos, metodos)

        # Supuesto 15: se bloquea a un cliente con promedio menor a 3
        for c in malos:
            if (c.promedio_calificacion or 5) < 3:
                c.estado = "bloqueado"
                guardar(c)
                break

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {m.Cliente.objects.count()} clientes, {m.Vivienda.objects.count()} viviendas, "
            f"{m.Empleado.objects.count()} empleados, {m.Servicio.objects.count()} servicios, "
            f"{m.Pago.objects.count()} pagos."))

    # -----------------------------------------------------------------
    def borrar(self):
        for modelo in [m.Pago, m.InsumoUsado, m.Asignacion, m.DetalleServicio, m.Servicio, m.Elemento, m.Area,
                       m.Vivienda, m.Cliente, m.EmpleadoZona, m.EmpleadoEspecialidad]:
            modelo.objects.all().delete()
        m.Empleado.objects.update(supervisor=None)
        for modelo in [m.Empleado, m.InsumoRequerido, m.Insumo, m.Proveedor, m.CategoriaInsumo, m.MetodoPago,
                       m.TipoServicio, m.Especialidad, m.TipoElemento, m.TipoArea, m.TipoVivienda, m.Barrio, m.Zona]:
            modelo.objects.all().delete()

    def crear_areas(self, rnd, v, tipo, ta, te):
        def area(nombre, desc=None):
            return guardar(m.Area(vivienda=v, tipo_area=ta[nombre], descripcion=desc))

        def elem(a, nombre, desc=None):
            guardar(m.Elemento(area=a, tipo_elemento=te[nombre], descripcion=desc))

        cocina = area("Cocina")
        elem(cocina, "Nevera")
        elem(cocina, "Horno")
        sala = area("Sala")
        elem(sala, "Sofá", rnd.choice(["Sofá de tela gris", "Sofá en L", "Sofá de cuero"]))
        if rnd.random() < 0.6:
            elem(sala, "Alfombra")
        elem(sala, "Cortinas", "Cortinas de la sala")
        if rnd.random() < 0.5:
            elem(sala, "Ventanal", "Ventanal de la sala")
        if tipo != "Apartaestudio":
            area("Comedor")
        habitaciones = 1 if tipo == "Apartaestudio" else rnd.randint(2, 4)
        for i in range(habitaciones):
            h = area("Habitación", "Habitación principal" if i == 0 else f"Habitación {i + 1}")
            elem(h, "Colchón")
            if rnd.random() < 0.5:
                elem(h, "Cortinas")
        for i in range(1 if tipo == "Apartaestudio" else rnd.randint(1, 3)):
            area("Baño", "Baño principal" if i == 0 else ("Baño social" if i == 1 else "Baño de servicio"))
        if tipo in ("Casa", "Finca"):
            area("Patio")
            if rnd.random() < 0.5:
                area("Garaje")
        if tipo == "Finca" or (tipo == "Casa" and rnd.random() < 0.3):
            area("Piscina")
            area("Jardín")
        if tipo == "Apartamento" and rnd.random() < 0.5:
            area(rnd.choice(["Balcón", "Terraza"]))

    def agregar_detalles(self, rnd, s, v, ts):
        nombres = rnd.sample(list(TIPOS_SERVICIO), rnd.choice([1, 1, 2, 2, 3]))
        agregados = 0
        for nombre in nombres:
            alcance = TIPOS_SERVICIO[nombre][3]
            d = m.DetalleServicio(servicio=s, tipo_servicio=ts[nombre])
            if alcance and alcance[0] == "area":
                opciones = list(v.areas.filter(tipo_area__nombre__in=alcance[1]))
                if not opciones:
                    continue
                d.area = rnd.choice(opciones)
            elif alcance and alcance[0] == "elemento":
                opciones = list(m.Elemento.objects.filter(area__vivienda=v, tipo_elemento__nombre__in=alcance[1]))
                if not opciones:
                    continue
                d.elemento = rnd.choice(opciones)
            guardar(d)
            agregados += 1
        return agregados > 0

    def asignar(self, rnd, s, empleados):
        necesarios = 2 if s.duracion_total >= 5 else 1
        asignados = 0
        for e in rnd.sample(empleados, len(empleados)):
            try:
                guardar(m.Asignacion(servicio=s, empleado=e))
                asignados += 1
            except ValidationError:
                continue
            if asignados == necesarios:
                break
        return asignados > 0

    def cerrar(self, rnd, s, cliente_malo, metodos):
        for a in s.asignaciones.all():
            a.calificacion_empleado = rnd.choice([3, 4, 4, 5, 5, 5, 2])
            a.comentario_empleado = (rnd.choice(COMENTARIOS_BUENOS) if a.calificacion_empleado >= 4
                                     else rnd.choice(COMENTARIOS_MALOS)) or None
            if cliente_malo:
                a.calificacion_cliente = rnd.choice([1, 2, 2])
                a.comentario_cliente = rnd.choice(COMENTARIOS_CLIENTE_MALO)
            else:
                a.calificacion_cliente = rnd.choice([4, 5, 5])
            guardar(a)
        cliente_pone = rnd.random() < 0.2
        for d in s.detalles.all():
            for req in d.tipo_servicio.insumos_requeridos.all():
                if s.insumos_usados.filter(insumo=req.insumo).exists():
                    continue
                es_producto = req.insumo.categoria.nombre == "producto"
                guardar(m.InsumoUsado(servicio=s, insumo=req.insumo, cantidad=req.cantidad_sugerida,
                                      proporcionado_por="cliente" if cliente_pone and es_producto else "empresa"))
        guardar(m.Pago(servicio=s, metodo_pago=rnd.choice(metodos), fecha=s.fecha, monto=s.total))
