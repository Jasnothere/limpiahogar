"""Pruebas de las reglas de negocio y de las vistas. Ejecutar: python manage.py test"""
from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from . import models as m
from .registro import TABLAS


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("poblar_datos", verbosity=0)
        cls.usuario = User.objects.create_superuser("profe", "profe@example.com", "clave-segura-123")


class ReglasTest(Base):
    def test_un_solo_pago_por_servicio(self):
        pago = m.Pago.objects.first()
        with self.assertRaises(IntegrityError), transaction.atomic():
            m.Pago.objects.create(servicio=pago.servicio, metodo_pago=pago.metodo_pago, fecha=date.today(), monto=1)

    def test_pago_solo_si_finalizado(self):
        s = m.Servicio.objects.filter(estado="pendiente").first()
        with self.assertRaises(ValidationError):
            m.Pago(servicio=s, metodo_pago=m.MetodoPago.objects.first(), fecha=date.today(), monto=10).full_clean()

    def test_calificar_servicio_no_finalizado(self):
        s = m.Servicio.objects.filter(estado="pendiente").first()
        s.calificacion_servicio = 5
        with self.assertRaises(ValidationError):
            s.full_clean()

    def test_area_y_elemento_a_la_vez(self):
        e = m.Elemento.objects.first()
        s = m.Servicio.objects.filter(vivienda=e.area.vivienda).first() or m.Servicio.objects.create(
            vivienda=e.area.vivienda, fecha=date.today(), hora_inicio=time(9))
        d = m.DetalleServicio(servicio=s, tipo_servicio=m.TipoServicio.objects.first(), area=e.area, elemento=e)
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_area_de_otra_vivienda(self):
        s = m.Servicio.objects.first()
        otra = m.Area.objects.exclude(vivienda=s.vivienda).first()
        d = m.DetalleServicio(servicio=s, tipo_servicio=m.TipoServicio.objects.first(), area=otra)
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_empleado_sin_zona(self):
        s = m.Servicio.objects.filter(estado="pendiente").first()
        e = m.Empleado.objects.filter(estado="activo").exclude(zonas__zona=s.vivienda.barrio.zona).first()
        with self.assertRaises(ValidationError):
            m.Asignacion(servicio=s, empleado=e).full_clean()

    def test_cliente_bloqueado_no_pide_servicios(self):
        c = m.Cliente.objects.filter(estado="bloqueado").first()
        self.assertIsNotNone(c)
        s = m.Servicio(vivienda=c.viviendas.first(), fecha=date.today(), hora_inicio=time(9))
        with self.assertRaises(ValidationError):
            s.full_clean()

    def test_stock_se_descuenta_y_se_devuelve(self):
        s = m.Servicio.objects.filter(estado="finalizado").first()
        insumo = m.Insumo.objects.exclude(insumousado__servicio=s).first()
        antes = insumo.stock
        u = m.InsumoUsado(servicio=s, insumo=insumo, cantidad=Decimal(3), proporcionado_por="empresa")
        u.full_clean()
        u.save()
        insumo.refresh_from_db()
        self.assertEqual(insumo.stock, antes - 3)
        u.delete()
        insumo.refresh_from_db()
        self.assertEqual(insumo.stock, antes)

    def test_insumo_del_cliente_no_descuenta(self):
        s = m.Servicio.objects.filter(estado="finalizado").first()
        insumo = m.Insumo.objects.exclude(insumousado__servicio=s).first()
        antes = insumo.stock
        m.InsumoUsado.objects.create(servicio=s, insumo=insumo, cantidad=5, proporcionado_por="cliente")
        insumo.refresh_from_db()
        self.assertEqual(insumo.stock, antes)

    def test_supervisor_no_es_el_mismo(self):
        e = m.Empleado.objects.first()
        e.supervisor = e
        with self.assertRaises(ValidationError):
            e.full_clean()


class VistasTest(Base):
    def test_paginas_publicas(self):
        for url in [reverse("inicio"), reverse("informes"), reverse("clientes_calificacion"),
                    reverse("servicio_detalle", args=[m.Servicio.objects.first().pk])]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        for tabla in TABLAS:
            self.assertEqual(self.client.get(reverse("lista", args=[tabla])).status_code, 200, tabla)

    def test_editar_requiere_sesion(self):
        r = self.client.get(reverse("crear", args=["zona"]))
        self.assertEqual(r.status_code, 302)

    def test_formularios_de_todas_las_tablas(self):
        self.client.force_login(self.usuario)
        for tabla, conf in TABLAS.items():
            self.assertEqual(self.client.get(reverse("crear", args=[tabla])).status_code, 200, tabla)
            obj = conf["modelo"].objects.first()
            self.assertEqual(self.client.get(reverse("editar", args=[tabla, obj.pk])).status_code, 200, tabla)
            self.assertEqual(self.client.get(reverse("eliminar", args=[tabla, obj.pk])).status_code, 200, tabla)

    def test_crud_zona(self):
        self.client.force_login(self.usuario)
        self.client.post(reverse("crear", args=["zona"]), {"nombre": "Oriente"})
        z = m.Zona.objects.get(nombre="Oriente")
        self.client.post(reverse("editar", args=["zona", z.pk]), {"nombre": "Suroriente"})
        z.refresh_from_db()
        self.assertEqual(z.nombre, "Suroriente")
        self.client.post(reverse("eliminar", args=["zona", z.pk]))
        self.assertFalse(m.Zona.objects.filter(pk=z.pk).exists())

    def test_eliminar_protegido_muestra_mensaje(self):
        self.client.force_login(self.usuario)
        z = m.Zona.objects.first()
        r = self.client.post(reverse("eliminar", args=["zona", z.pk]), follow=True)
        self.assertTrue(m.Zona.objects.filter(pk=z.pk).exists())
        self.assertContains(r, "No se puede eliminar")
