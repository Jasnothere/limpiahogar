"""
Pruebas de entrega: requerimientos funcionales (RF), restricciones y posibles fallos.

Ejecutar:  python manage.py test aseo.tests_entrega -v 2

Cada prueba describe el comportamiento CORRECTO esperado. Si una prueba falla,
es porque la aplicación no cumple ese comportamiento.
"""
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from . import models as m

HOY = date.today()


class Escenario(TestCase):
    """Datos pequeños y controlados para cada prueba."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("profesora", "p@example.com", "Clave-segura-2026")
        cls.norte = m.Zona.objects.create(nombre="Norte")
        cls.sur = m.Zona.objects.create(nombre="Sur")
        cls.usaquen = m.Barrio.objects.create(nombre="Usaquén", zona=cls.norte)
        cls.kennedy = m.Barrio.objects.create(nombre="Kennedy", zona=cls.sur)
        cls.casa = m.TipoVivienda.objects.create(nombre="Casa")
        cls.ta_cocina = m.TipoArea.objects.create(nombre="Cocina")
        cls.ta_sala = m.TipoArea.objects.create(nombre="Sala")
        cls.ta_piscina = m.TipoArea.objects.create(nombre="Piscina")
        cls.te_sofa = m.TipoElemento.objects.create(nombre="Sofá")
        cls.esp_general = m.Especialidad.objects.create(nombre="Limpieza general")
        cls.esp_tapiceria = m.Especialidad.objects.create(nombre="Muebles y tapicería")
        cls.esp_piscina = m.Especialidad.objects.create(nombre="Piscinas")
        cls.ts_general = m.TipoServicio.objects.create(nombre="Limpieza general", duracion_horas=4,
                                                       precio=100000, especialidad=cls.esp_general)
        cls.ts_sofa = m.TipoServicio.objects.create(nombre="Lavado de sofá", duracion_horas=2,
                                                    precio=80000, especialidad=cls.esp_tapiceria)
        cls.ts_piscina = m.TipoServicio.objects.create(nombre="Limpieza de piscina", duracion_horas=3,
                                                       precio=150000, especialidad=cls.esp_piscina)

        cls.c1 = m.Cliente.objects.create(documento="100", nombre="Ana", apellido="Ruiz", telefono="300",
                                          correo="ana@x.com")
        cls.c2 = m.Cliente.objects.create(documento="200", nombre="Luis", apellido="Mora", telefono="301",
                                          correo="luis@x.com")
        cls.v1 = m.Vivienda.objects.create(cliente=cls.c1, barrio=cls.usaquen, tipo_vivienda=cls.casa,
                                           direccion="Calle 1 # 2-3")
        cls.v2 = m.Vivienda.objects.create(cliente=cls.c2, barrio=cls.kennedy, tipo_vivienda=cls.casa,
                                           direccion="Calle 9 # 8-7")
        cls.cocina1 = m.Area.objects.create(vivienda=cls.v1, tipo_area=cls.ta_cocina)
        cls.sala1 = m.Area.objects.create(vivienda=cls.v1, tipo_area=cls.ta_sala)
        cls.piscina1 = m.Area.objects.create(vivienda=cls.v1, tipo_area=cls.ta_piscina)
        cls.sofa1 = m.Elemento.objects.create(area=cls.sala1, tipo_elemento=cls.te_sofa)
        cls.cocina2 = m.Area.objects.create(vivienda=cls.v2, tipo_area=cls.ta_cocina)
        cls.sala2 = m.Area.objects.create(vivienda=cls.v2, tipo_area=cls.ta_sala)
        cls.sofa2 = m.Elemento.objects.create(area=cls.sala2, tipo_elemento=cls.te_sofa)

        def empleado(doc, nombre, zonas, esps, estado="activo"):
            e = m.Empleado.objects.create(documento=doc, nombre=nombre, apellido="X", telefono="310",
                                          estado=estado)
            for z in zonas:
                m.EmpleadoZona.objects.create(empleado=e, zona=z)
            for es in esps:
                m.EmpleadoEspecialidad.objects.create(empleado=e, especialidad=es)
            return e

        cls.e_norte = empleado("1", "Norte", [cls.norte], [cls.esp_general, cls.esp_tapiceria])
        cls.e_sur = empleado("2", "Sur", [cls.sur], [cls.esp_general, cls.esp_tapiceria])
        cls.e_inactivo = empleado("3", "Inactivo", [cls.norte], [cls.esp_general], estado="inactivo")
        cls.e_piscina = empleado("4", "Piscina", [cls.norte], [cls.esp_general, cls.esp_piscina])

        cls.producto = m.CategoriaInsumo.objects.create(nombre="producto")
        cls.prov = m.Proveedor.objects.create(nit="900", nombre="Prov")
        cls.jabon = m.Insumo.objects.create(nombre="Jabón", categoria=cls.producto, proveedor=cls.prov, stock=10)
        cls.nequi = m.MetodoPago.objects.create(nombre="Nequi")

    def setUp(self):
        self.client.force_login(self.admin)

    # ---- utilidades ----
    def servicio(self, vivienda=None, fecha=None, hora=time(8), tipos=None):
        s = m.Servicio.objects.create(vivienda=vivienda or self.v1, fecha=fecha or HOY + timedelta(days=3),
                                      hora_inicio=hora)
        for t in tipos or [self.ts_general]:
            m.DetalleServicio.objects.create(servicio=s, tipo_servicio=t)
        return s

    def finalizado(self, empleado=None):
        s = self.servicio()
        m.Asignacion.objects.create(servicio=s, empleado=empleado or self.e_norte)
        s.estado = "finalizado"
        s.save()
        return s

    def post(self, nombre, *args, datos=None, **kw):
        return self.client.post(reverse(nombre, args=args), datos or {}, **kw)

    def assertGuardado(self, r):
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context.get("form").errors)

    def assertRechazado(self, r, texto=None):
        self.assertEqual(r.status_code, 200, "Se esperaba que el formulario rechazara los datos")
        if texto:
            self.assertContains(r, texto)


# =====================================================================
# 1. REQUERIMIENTOS FUNCIONALES
# =====================================================================

class RequerimientosFuncionales(Escenario):

    def test_rf01_zonas_y_barrios(self):
        self.assertGuardado(self.post("crear", "zona", datos={"nombre": "Centro"}))
        centro = m.Zona.objects.get(nombre="Centro")
        self.assertGuardado(self.post("crear", "barrio", datos={"nombre": "Chapinero", "zona": centro.pk}))
        self.assertGuardado(self.post("editar", "zona", centro.pk, datos={"nombre": "Centro histórico"}))
        b = m.Barrio.objects.get(nombre="Chapinero")
        self.assertGuardado(self.post("eliminar", "barrio", b.pk))
        self.assertGuardado(self.post("eliminar", "zona", centro.pk))
        self.assertFalse(m.Zona.objects.filter(pk=centro.pk).exists())

    def test_rf02_crud_clientes(self):
        datos = {"documento": "555", "nombre": "Eva", "apellido": "Gil", "telefono": "320",
                 "correo": "eva@x.com", "estado": "activo"}
        self.assertGuardado(self.post("crear", "cliente", datos=datos))
        c = m.Cliente.objects.get(documento="555")
        self.assertContains(self.client.get(reverse("lista", args=["cliente"]) + "?q=Eva"), "Eva")
        datos["telefono"] = "399"
        self.assertGuardado(self.post("editar", "cliente", c.pk, datos=datos))
        c.refresh_from_db()
        self.assertEqual(c.telefono, "399")
        self.assertGuardado(self.post("eliminar", "cliente", c.pk))
        self.assertFalse(m.Cliente.objects.filter(pk=c.pk).exists())

    def test_rf03_varias_viviendas_por_cliente(self):
        datos = {"cliente": self.c1.pk, "barrio": self.kennedy.pk, "tipo_vivienda": self.casa.pk,
                 "direccion": "Carrera 50 # 1-1"}
        self.assertGuardado(self.post("crear", "vivienda", datos=datos))
        self.assertEqual(self.c1.viviendas.count(), 2)

    def test_rf04_areas(self):
        self.assertGuardado(self.post("crear", "area", datos={"vivienda": self.v1.pk,
                                                              "tipo_area": self.ta_cocina.pk,
                                                              "descripcion": "Cocina auxiliar"}))
        self.assertEqual(self.v1.areas.filter(tipo_area=self.ta_cocina).count(), 2)

    def test_rf05_elementos(self):
        self.assertGuardado(self.post("crear", "elemento", datos={"area": self.cocina1.pk,
                                                                  "tipo_elemento": self.te_sofa.pk}))

    def test_rf06_empleados_y_estado(self):
        datos = {"documento": "77", "nombre": "Raúl", "apellido": "Paz", "telefono": "311", "estado": "activo"}
        self.assertGuardado(self.post("crear", "empleado", datos=datos))
        e = m.Empleado.objects.get(documento="77")
        datos["estado"] = "inactivo"
        self.assertGuardado(self.post("editar", "empleado", e.pk, datos=datos))
        e.refresh_from_db()
        self.assertEqual(e.estado, "inactivo")

    def test_rf07_zonas_del_empleado(self):
        self.assertGuardado(self.post("crear", "empleado_zona", datos={"empleado": self.e_norte.pk,
                                                                       "zona": self.sur.pk}))
        self.assertEqual(self.e_norte.zonas.count(), 2)

    def test_rf08_supervisor(self):
        datos = {"documento": self.e_sur.documento, "nombre": "Sur", "apellido": "X", "telefono": "310",
                 "estado": "activo", "supervisor": self.e_norte.pk}
        self.assertGuardado(self.post("editar", "empleado", self.e_sur.pk, datos=datos))
        self.assertEqual(list(self.e_norte.supervisados.all()), [self.e_sur])

    def test_rf09_especialidades(self):
        self.assertGuardado(self.post("crear", "especialidad", datos={"nombre": "Desinfección"}))
        esp = m.Especialidad.objects.get(nombre="Desinfección")
        self.assertGuardado(self.post("crear", "empleado_especialidad",
                                      datos={"empleado": self.e_sur.pk, "especialidad": esp.pk}))

    def test_rf10_tipos_de_servicio(self):
        datos = {"nombre": "Planchado", "duracion_horas": "2", "precio": "50000",
                 "especialidad": self.esp_general.pk}
        self.assertGuardado(self.post("crear", "tipo_servicio", datos=datos))

    def test_rf11_solicitar_servicio(self):
        datos = {"vivienda": self.v1.pk, "fecha": str(HOY + timedelta(days=5)), "hora_inicio": "09:00",
                 "estado": "pendiente", "observaciones": "Hay perro"}
        self.assertGuardado(self.post("crear", "servicio", datos=datos))

    def test_rf12_detalle_toda_vivienda_area_o_elemento(self):
        s = m.Servicio.objects.create(vivienda=self.v1, fecha=HOY, hora_inicio=time(8))
        for extra in [{}, {"area": self.piscina1.pk}, {"elemento": self.sofa1.pk}]:
            datos = {"servicio": s.pk, "tipo_servicio": self.ts_general.pk, **extra}
            self.assertGuardado(self.post("crear", "detalle_servicio", datos=datos))
        self.assertEqual(s.detalles.count(), 3)
        # Si no se escribe precio, toma el del tipo de servicio
        self.assertEqual(s.detalles.first().precio_aplicado, Decimal("100000"))

    def test_rf13_asignar_empleado_valido(self):
        s = self.servicio(tipos=[self.ts_general, self.ts_sofa])
        self.assertGuardado(self.post("crear", "asignacion", datos={"servicio": s.pk, "empleado": self.e_norte.pk}))
        # La pantalla del servicio sugiere empleados que cumplen (el de piscina no tiene tapicería)
        r = self.client.get(reverse("servicio_detalle", args=[s.pk]))
        self.assertEqual(r.status_code, 200)

    def test_rf14_insumos_y_proveedores(self):
        self.assertGuardado(self.post("crear", "proveedor", datos={"nit": "901", "nombre": "Otro"}))
        p = m.Proveedor.objects.get(nit="901")
        self.assertGuardado(self.post("crear", "insumo", datos={"nombre": "Cloro", "categoria": self.producto.pk,
                                                                "proveedor": p.pk, "stock": 5}))

    def test_rf15_insumos_requeridos(self):
        self.assertGuardado(self.post("crear", "insumo_requerido",
                                      datos={"tipo_servicio": self.ts_general.pk, "insumo": self.jabon.pk,
                                             "cantidad_sugerida": "1"}))

    def test_rf16_insumo_usado_empresa_y_cliente(self):
        s = self.finalizado()
        self.assertGuardado(self.post("crear", "insumo_usado", datos={
            "servicio": s.pk, "insumo": self.jabon.pk, "cantidad": "3", "proporcionado_por": "empresa"}))
        self.jabon.refresh_from_db()
        self.assertEqual(self.jabon.stock, 7)
        s2 = self.finalizado(self.e_piscina)
        self.assertGuardado(self.post("crear", "insumo_usado", datos={
            "servicio": s2.pk, "insumo": self.jabon.pk, "cantidad": "4", "proporcionado_por": "cliente"}))
        self.jabon.refresh_from_db()
        self.assertEqual(self.jabon.stock, 7)  # lo del cliente no se descuenta

    def test_rf17_calificar_servicio_y_empleado(self):
        s = self.finalizado()
        datos = {"vivienda": s.vivienda_id, "fecha": str(s.fecha), "hora_inicio": "08:00", "estado": "finalizado",
                 "calificacion_servicio": "5", "comentario_servicio": "Muy bien"}
        self.assertGuardado(self.post("editar", "servicio", s.pk, datos=datos))
        a = s.asignaciones.get()
        self.assertGuardado(self.post("editar", "asignacion", a.pk, datos={
            "servicio": s.pk, "empleado": a.empleado_id, "calificacion_empleado": "4", "comentario_empleado": "Bien"}))
        a.refresh_from_db()
        self.assertEqual(a.calificacion_empleado, 4)

    def test_rf18_empleado_califica_cliente(self):
        s = self.finalizado()
        a = s.asignaciones.get()
        self.assertGuardado(self.post("editar", "asignacion", a.pk, datos={
            "servicio": s.pk, "empleado": a.empleado_id, "calificacion_cliente": "2",
            "comentario_cliente": "No estaba"}))
        self.assertEqual(self.c1.promedio_calificacion, 2)

    def test_rf19_pago_con_metodo(self):
        s = self.finalizado()
        self.assertGuardado(self.post("crear", "pago", datos={"servicio": s.pk, "metodo_pago": self.nequi.pk,
                                                              "fecha": str(HOY), "monto": "100000"}))

    def test_rf20_informes(self):
        s = self.finalizado()
        a = s.asignaciones.get()
        a.calificacion_empleado, a.calificacion_cliente = 5, 2
        a.save()
        m.Pago.objects.create(servicio=s, metodo_pago=self.nequi, fecha=HOY, monto=100000)
        m.DetalleServicio.objects.create(servicio=s, tipo_servicio=self.ts_sofa, elemento=self.sofa1)
        r = self.client.get(reverse("informes"))
        self.assertEqual(r.status_code, 200)
        for texto in ["Norte", "Usaquén", "Nequi", str(self.e_norte), str(self.c1), "Sofá"]:
            self.assertContains(r, texto)

    def test_rf21_bloquear_cliente(self):
        r = self.post("cambiar_estado_cliente", self.c1.pk)
        self.assertEqual(r.status_code, 302)
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.estado, "bloqueado")
        r = self.post("crear", "servicio", datos={"vivienda": self.v1.pk, "fecha": str(HOY), "hora_inicio": "09:00",
                                                  "estado": "pendiente"})
        self.assertRechazado(r, "bloqueado")
        self.post("cambiar_estado_cliente", self.c1.pk)  # desbloquear
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.estado, "activo")


# =====================================================================
# 2. RESTRICCIONES
# =====================================================================

class Restricciones(Escenario):

    def test_documento_y_correo_unicos(self):
        r = self.post("crear", "cliente", datos={"documento": "100", "nombre": "Z", "apellido": "Z",
                                                 "telefono": "1", "estado": "activo"})
        self.assertRechazado(r)
        r = self.post("crear", "cliente", datos={"documento": "999", "nombre": "Z", "apellido": "Z",
                                                 "telefono": "1", "correo": "ana@x.com", "estado": "activo"})
        self.assertRechazado(r)

    def test_estado_invalido(self):
        r = self.post("crear", "cliente", datos={"documento": "999", "nombre": "Z", "apellido": "Z",
                                                 "telefono": "1", "estado": "vip"})
        self.assertRechazado(r)

    def test_calificaciones_fuera_de_rango(self):
        s = self.finalizado()
        a = s.asignaciones.get()
        for valor in ["0", "6", "-1"]:
            r = self.post("editar", "asignacion", a.pk, datos={"servicio": s.pk, "empleado": a.empleado_id,
                                                               "calificacion_empleado": valor})
            self.assertRechazado(r)

    def test_calificar_servicio_no_finalizado(self):
        s = self.servicio()
        r = self.post("editar", "servicio", s.pk, datos={"vivienda": s.vivienda_id, "fecha": str(s.fecha),
                                                         "hora_inicio": "08:00", "estado": "pendiente",
                                                         "calificacion_servicio": "5"})
        self.assertRechazado(r, "finalizado")

    def test_calificar_empleado_servicio_no_finalizado(self):
        s = self.servicio()
        r = self.post("crear", "asignacion", datos={"servicio": s.pk, "empleado": self.e_norte.pk,
                                                    "calificacion_empleado": "5"})
        self.assertRechazado(r, "finalizado")

    def test_un_solo_pago(self):
        s = self.finalizado()
        m.Pago.objects.create(servicio=s, metodo_pago=self.nequi, fecha=HOY, monto=1)
        r = self.post("crear", "pago", datos={"servicio": s.pk, "metodo_pago": self.nequi.pk, "fecha": str(HOY),
                                              "monto": "5"})
        self.assertRechazado(r)
        self.assertEqual(m.Pago.objects.filter(servicio=s).count(), 1)

    def test_pago_monto_cero_o_negativo(self):
        s = self.finalizado()
        for monto in ["0", "-100"]:
            r = self.post("crear", "pago", datos={"servicio": s.pk, "metodo_pago": self.nequi.pk,
                                                  "fecha": str(HOY), "monto": monto})
            self.assertRechazado(r)

    def test_pago_servicio_no_finalizado(self):
        s = self.servicio()
        r = self.post("crear", "pago", datos={"servicio": s.pk, "metodo_pago": self.nequi.pk, "fecha": str(HOY),
                                              "monto": "5"})
        self.assertRechazado(r, "finalizado")

    def test_detalle_area_y_elemento_a_la_vez(self):
        s = self.servicio()
        r = self.post("crear", "detalle_servicio", datos={"servicio": s.pk, "tipo_servicio": self.ts_general.pk,
                                                          "area": self.sala1.pk, "elemento": self.sofa1.pk})
        self.assertRechazado(r)

    def test_detalle_area_o_elemento_de_otra_vivienda(self):
        s = self.servicio()
        for extra in [{"area": self.cocina2.pk}, {"elemento": self.sofa2.pk}]:
            r = self.post("crear", "detalle_servicio",
                          datos={"servicio": s.pk, "tipo_servicio": self.ts_general.pk, **extra})
            self.assertRechazado(r, "no pertenece")

    def test_empleado_de_otra_zona(self):
        s = self.servicio()
        r = self.post("crear", "asignacion", datos={"servicio": s.pk, "empleado": self.e_sur.pk})
        self.assertRechazado(r, "zona")

    def test_empleado_sin_especialidad(self):
        s = self.servicio(tipos=[self.ts_piscina])
        r = self.post("crear", "asignacion", datos={"servicio": s.pk, "empleado": self.e_norte.pk})
        self.assertRechazado(r, "especialidad")

    def test_empleado_inactivo(self):
        s = self.servicio()
        r = self.post("crear", "asignacion", datos={"servicio": s.pk, "empleado": self.e_inactivo.pk})
        self.assertRechazado(r, "inactivo")

    def test_empleado_en_dos_servicios_a_la_vez(self):
        f = HOY + timedelta(days=10)
        s1 = self.servicio(fecha=f, hora=time(8))           # 8:00 a 12:00
        m.Asignacion.objects.create(servicio=s1, empleado=self.e_norte)
        s2 = self.servicio(fecha=f, hora=time(10))          # se cruza
        r = self.post("crear", "asignacion", datos={"servicio": s2.pk, "empleado": self.e_norte.pk})
        self.assertRechazado(r, "horario")
        s3 = self.servicio(fecha=f, hora=time(13))          # no se cruza
        self.assertGuardado(self.post("crear", "asignacion", datos={"servicio": s3.pk, "empleado": self.e_norte.pk}))

    def test_servicio_cancelado_no_ocupa_horario(self):
        f = HOY + timedelta(days=11)
        s1 = self.servicio(fecha=f, hora=time(8))
        m.Asignacion.objects.create(servicio=s1, empleado=self.e_norte)
        s1.estado = "cancelado"
        s1.save()
        s2 = self.servicio(fecha=f, hora=time(9))
        self.assertGuardado(self.post("crear", "asignacion", datos={"servicio": s2.pk, "empleado": self.e_norte.pk}))

    def test_asignar_sin_detalles(self):
        s = m.Servicio.objects.create(vivienda=self.v1, fecha=HOY, hora_inicio=time(8))
        r = self.post("crear", "asignacion", datos={"servicio": s.pk, "empleado": self.e_norte.pk})
        self.assertRechazado(r, "tipos de servicio")

    def test_finalizar_sin_detalles_o_empleados(self):
        s = self.servicio()
        r = self.post("editar", "servicio", s.pk, datos={"vivienda": s.vivienda_id, "fecha": str(s.fecha),
                                                         "hora_inicio": "08:00", "estado": "finalizado"})
        self.assertRechazado(r, "empleado")

    def test_stock_insuficiente(self):
        s = self.finalizado()
        r = self.post("crear", "insumo_usado", datos={"servicio": s.pk, "insumo": self.jabon.pk,
                                                      "cantidad": "11", "proporcionado_por": "empresa"})
        self.assertRechazado(r, "stock")

    def test_empleado_propio_supervisor(self):
        r = self.post("editar", "empleado", self.e_norte.pk, datos={
            "documento": "1", "nombre": "Norte", "apellido": "X", "telefono": "310", "estado": "activo",
            "supervisor": self.e_norte.pk})
        self.assertRechazado(r, "supervisor")

    def test_no_borrar_registros_en_uso(self):
        casos = [("zona", self.norte), ("cliente", self.c1), ("tipo_servicio", self.ts_general),
                 ("especialidad", self.esp_general), ("metodo_pago", self.nequi)]
        s = self.finalizado()
        m.Pago.objects.create(servicio=s, metodo_pago=self.nequi, fecha=HOY, monto=1)
        casos.append(("servicio", s))
        for tabla, obj in casos:
            r = self.post("eliminar", tabla, obj.pk, follow=True)
            self.assertContains(r, "No se puede eliminar", msg_prefix=tabla)
            self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists(), tabla)

    def test_borrar_vivienda_sin_servicios_borra_areas_y_elementos(self):
        self.post("eliminar", "vivienda", self.v2.pk)
        self.assertFalse(m.Area.objects.filter(vivienda_id=self.v2.pk).exists())
        self.assertFalse(m.Elemento.objects.filter(pk=self.sofa2.pk).exists())

    def test_borrar_supervisor_deja_empleados_sin_supervisor(self):
        jefe = m.Empleado.objects.create(documento="99", nombre="Jefe", apellido="X", telefono="1")
        self.e_sur.supervisor = jefe
        self.e_sur.save()
        self.post("eliminar", "empleado", jefe.pk)
        self.e_sur.refresh_from_db()
        self.assertIsNone(self.e_sur.supervisor)

    def test_editar_requiere_sesion(self):
        self.client.logout()
        for nombre, args in [("crear", ["zona"]), ("editar", ["zona", self.norte.pk]),
                             ("eliminar", ["zona", self.norte.pk])]:
            self.assertEqual(self.client.get(reverse(nombre, args=args)).status_code, 302)
        self.client.post(reverse("cambiar_estado_cliente", args=[self.c1.pk]))
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.estado, "activo")
        # Pero sí se puede ver
        self.assertEqual(self.client.get(reverse("lista", args=["zona"])).status_code, 200)

    def test_textos_demasiado_largos(self):
        r = self.post("crear", "zona", datos={"nombre": "x" * 51})
        self.assertRechazado(r)


# =====================================================================
# 3. POSIBLES FALLOS (casos raros, ediciones y borrados)
# =====================================================================

class PosiblesFallos(Escenario):

    # ---------- URLs y entradas raras ----------
    def test_filtro_con_valor_invalido_no_rompe(self):
        r = self.client.get(reverse("lista", args=["detalle_servicio"]) + "?servicio=abc")
        self.assertLess(r.status_code, 500)

    def test_tabla_o_registro_inexistente_da_404(self):
        self.assertEqual(self.client.get("/tabla/no_existe/").status_code, 404)
        self.assertEqual(self.client.get(reverse("editar", args=["zona", 99999])).status_code, 404)
        self.assertEqual(self.client.get(reverse("servicio_detalle", args=[99999])).status_code, 404)

    def test_pagina_invalida(self):
        for p in ["999", "abc", "-1"]:
            self.assertEqual(self.client.get(reverse("lista", args=["zona"]) + f"?page={p}").status_code, 200)

    def test_html_en_los_datos_se_escapa(self):
        m.Cliente.objects.create(documento="666", nombre="<script>alert(1)</script>", apellido="X", telefono="1")
        r = self.client.get(reverse("lista", args=["cliente"]))
        self.assertNotContains(r, "<script>alert(1)</script>")

    def test_redireccion_externa_ignorada(self):
        r = self.post("crear", "zona", datos={"nombre": "Oeste", "next": "https://sitio-malo.com/"})
        self.assertFalse(r["Location"].startswith("https://sitio-malo.com"))

    def test_login_incorrecto(self):
        self.client.logout()
        r = self.client.post(reverse("login"), {"username": "profesora", "password": "mala"})
        self.assertContains(r, "incorrectos")

    def test_eliminar_por_get_no_borra(self):
        self.client.get(reverse("eliminar", args=["zona", self.sur.pk]))
        self.assertTrue(m.Zona.objects.filter(pk=self.sur.pk).exists())

    # ---------- inventario ----------
    def test_cambiar_insumo_usado_mueve_el_stock(self):
        cloro = m.Insumo.objects.create(nombre="Cloro", categoria=self.producto, proveedor=self.prov, stock=10)
        s = self.finalizado()
        u = m.InsumoUsado.objects.create(servicio=s, insumo=self.jabon, cantidad=3)
        self.assertGuardado(self.post("editar", "insumo_usado", u.pk, datos={
            "servicio": s.pk, "insumo": cloro.pk, "cantidad": "2", "proporcionado_por": "empresa"}))
        self.jabon.refresh_from_db()
        cloro.refresh_from_db()
        self.assertEqual((self.jabon.stock, cloro.stock), (10, 8))

    def test_cambiar_insumo_usado_a_cliente_devuelve_stock(self):
        s = self.finalizado()
        u = m.InsumoUsado.objects.create(servicio=s, insumo=self.jabon, cantidad=3)
        self.post("editar", "insumo_usado", u.pk, datos={"servicio": s.pk, "insumo": self.jabon.pk,
                                                          "cantidad": "3", "proporcionado_por": "cliente"})
        self.jabon.refresh_from_db()
        self.assertEqual(self.jabon.stock, 10)

    def test_borrar_servicio_devuelve_insumos_al_stock(self):
        s = self.servicio()
        m.InsumoUsado.objects.create(servicio=s, insumo=self.jabon, cantidad=4)
        self.jabon.refresh_from_db()
        self.assertEqual(self.jabon.stock, 6)
        self.post("eliminar", "servicio", s.pk)
        self.assertFalse(m.Servicio.objects.filter(pk=s.pk).exists())
        self.jabon.refresh_from_db()
        self.assertEqual(self.jabon.stock, 10, "Al borrar el servicio el stock no volvió")

    # ---------- ediciones que dejan datos incoherentes ----------
    def test_devolver_a_pendiente_un_servicio_pagado(self):
        s = self.finalizado()
        m.Pago.objects.create(servicio=s, metodo_pago=self.nequi, fecha=HOY, monto=1)
        r = self.post("editar", "servicio", s.pk, datos={"vivienda": s.vivienda_id, "fecha": str(s.fecha),
                                                         "hora_inicio": "08:00", "estado": "pendiente"})
        self.assertRechazado(r)

    def test_devolver_a_pendiente_con_calificaciones_de_empleado(self):
        s = self.finalizado()
        a = s.asignaciones.get()
        a.calificacion_empleado = 5
        a.save()
        r = self.post("editar", "servicio", s.pk, datos={"vivienda": s.vivienda_id, "fecha": str(s.fecha),
                                                         "hora_inicio": "08:00", "estado": "pendiente"})
        self.assertRechazado(r)

    def test_cambiar_hora_del_servicio_cruza_horario_del_empleado(self):
        f = HOY + timedelta(days=12)
        s1 = self.servicio(fecha=f, hora=time(8))
        m.Asignacion.objects.create(servicio=s1, empleado=self.e_norte)
        s2 = self.servicio(fecha=f, hora=time(14))
        m.Asignacion.objects.create(servicio=s2, empleado=self.e_norte)
        r = self.post("editar", "servicio", s2.pk, datos={"vivienda": s2.vivienda_id, "fecha": str(f),
                                                          "hora_inicio": "09:00", "estado": "confirmado"})
        self.assertRechazado(r)

    def test_cambiar_vivienda_del_servicio_con_areas_de_la_anterior(self):
        s = self.servicio()
        m.DetalleServicio.objects.create(servicio=s, tipo_servicio=self.ts_sofa, elemento=self.sofa1)
        m.Asignacion.objects.create(servicio=s, empleado=self.e_norte)
        r = self.post("editar", "servicio", s.pk, datos={"vivienda": self.v2.pk, "fecha": str(s.fecha),
                                                         "hora_inicio": "08:00", "estado": "pendiente"})
        self.assertRechazado(r)

    def test_agregar_tipo_de_servicio_que_el_empleado_asignado_no_sabe(self):
        s = self.servicio()
        m.Asignacion.objects.create(servicio=s, empleado=self.e_norte)
        r = self.post("crear", "detalle_servicio", datos={"servicio": s.pk, "tipo_servicio": self.ts_piscina.pk,
                                                          "area": self.piscina1.pk})
        self.assertRechazado(r)

    def test_mover_area_usada_a_otra_vivienda(self):
        s = self.servicio()
        m.DetalleServicio.objects.create(servicio=s, tipo_servicio=self.ts_piscina, area=self.piscina1)
        r = self.post("editar", "area", self.piscina1.pk, datos={"vivienda": self.v2.pk,
                                                                 "tipo_area": self.ta_piscina.pk})
        self.assertRechazado(r)

    def test_ciclo_de_supervisores(self):
        self.e_sur.supervisor = self.e_norte
        self.e_sur.save()
        r = self.post("editar", "empleado", self.e_norte.pk, datos={
            "documento": "1", "nombre": "Norte", "apellido": "X", "telefono": "310", "estado": "activo",
            "supervisor": self.e_sur.pk})
        self.assertRechazado(r)

    def test_mover_servicio_de_cliente_activo_a_vivienda_de_cliente_bloqueado(self):
        self.c2.estado = "bloqueado"
        self.c2.save()
        s = m.Servicio.objects.create(vivienda=self.v1, fecha=HOY, hora_inicio=time(8))
        r = self.post("editar", "servicio", s.pk, datos={"vivienda": self.v2.pk, "fecha": str(HOY),
                                                         "hora_inicio": "08:00", "estado": "pendiente"})
        self.assertRechazado(r)


class BaseVaciaYDatosDePrueba(TestCase):
    def test_paginas_con_base_vacia(self):
        for url in ["/", "/informes/", "/clientes/calificacion/", "/tabla/servicio/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_poblar_datos_dos_veces_no_duplica(self):
        call_command("poblar_datos", verbosity=0)
        n = m.Servicio.objects.count()
        call_command("poblar_datos", verbosity=0)
        self.assertEqual(m.Servicio.objects.count(), n)
        call_command("poblar_datos", "--borrar", verbosity=0)
        self.assertEqual(m.Servicio.objects.count(), n)

    def test_datos_ficticios_cumplen_todas_las_reglas(self):
        call_command("poblar_datos", verbosity=0)
        errores = []
        for modelo in [m.Servicio, m.DetalleServicio, m.Asignacion, m.InsumoUsado, m.Pago, m.Empleado]:
            for obj in modelo.objects.all():
                try:
                    obj.full_clean()
                except ValidationError as e:
                    errores.append(f"{modelo.__name__} {obj.pk}: {e.messages}")
        self.assertEqual(errores, [])


class ConsultasSQL(TestCase):
    def test_archivo_tiene_15_consultas(self):
        from .consultas import cargar
        consultas = cargar()
        self.assertEqual([c["numero"] for c in consultas], list(range(1, 16)))
        self.assertTrue(all(c["sql"].upper().lstrip().startswith(("SELECT", "WITH")) for c in consultas))

    def test_pagina_de_consultas(self):
        call_command("poblar_datos", verbosity=0)
        r = self.client.get(reverse("consultas_sql"))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "alert-danger")
        self.assertContains(r, "Función de ventana")
