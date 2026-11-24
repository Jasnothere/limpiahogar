"""
Modelos del sistema de servicios de aseo en viviendas.

Cada clase corresponde a una tabla del modelo lógico UML (24 tablas). Los
nombres de tabla y de columna son los mismos del script SQL (db_table y
db_column). Las reglas de negocio de los supuestos se validan en clean(),
que Django ejecuta automáticamente en todos los formularios.
"""
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Avg, F, Q, Sum
from django.db.models.signals import pre_delete
from django.dispatch import receiver

CALIFICACION = [MinValueValidator(1), MaxValueValidator(5)]


# =====================================================================
# Catálogos y ubicación
# =====================================================================

class Zona(models.Model):
    id_zona = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "zona"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Barrio(models.Model):
    id_barrio = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=60)
    zona = models.ForeignKey(Zona, on_delete=models.PROTECT, db_column="id_zona", related_name="barrios")

    class Meta:
        db_table = "barrio"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["nombre", "zona"], name="uq_barrio_nombre_zona"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.zona})"


class TipoVivienda(models.Model):
    id_tipo_vivienda = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "tipo_vivienda"
        verbose_name = "tipo de vivienda"
        verbose_name_plural = "tipos de vivienda"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class TipoArea(models.Model):
    id_tipo_area = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "tipo_area"
        verbose_name = "tipo de área"
        verbose_name_plural = "tipos de área"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class TipoElemento(models.Model):
    id_tipo_elemento = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "tipo_elemento"
        verbose_name = "tipo de elemento"
        verbose_name_plural = "tipos de elemento"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# =====================================================================
# Clientes y viviendas
# =====================================================================

class Cliente(models.Model):
    ESTADOS = [("activo", "Activo"), ("bloqueado", "Bloqueado")]

    id_cliente = models.AutoField(primary_key=True)
    documento = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=60)
    apellido = models.CharField(max_length=60)
    telefono = models.CharField(max_length=15)
    correo = models.EmailField(max_length=100, unique=True, null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="activo")

    class Meta:
        db_table = "cliente"
        ordering = ["apellido", "nombre"]
        constraints = [
            models.CheckConstraint(condition=Q(estado__in=["activo", "bloqueado"]), name="ck_cliente_estado"),
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    @property
    def promedio_calificacion(self):
        """Promedio de las calificaciones que los empleados le dieron (supuesto 15)."""
        return Asignacion.objects.filter(servicio__vivienda__cliente=self).aggregate(
            p=Avg("calificacion_cliente")
        )["p"]


class Vivienda(models.Model):
    id_vivienda = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, db_column="id_cliente", related_name="viviendas")
    barrio = models.ForeignKey(Barrio, on_delete=models.PROTECT, db_column="id_barrio", related_name="viviendas")
    tipo_vivienda = models.ForeignKey(TipoVivienda, on_delete=models.PROTECT, db_column="id_tipo_vivienda")
    direccion = models.CharField("dirección", max_length=120)

    class Meta:
        db_table = "vivienda"
        ordering = ["direccion"]

    def __str__(self):
        return f"{self.direccion} - {self.barrio.nombre}"


class Area(models.Model):
    id_area = models.AutoField(primary_key=True)
    vivienda = models.ForeignKey(Vivienda, on_delete=models.CASCADE, db_column="id_vivienda", related_name="areas")
    tipo_area = models.ForeignKey(TipoArea, on_delete=models.PROTECT, db_column="id_tipo_area")
    descripcion = models.CharField("descripción", max_length=100, blank=True, null=True)

    class Meta:
        db_table = "area"
        verbose_name = "área"
        ordering = ["vivienda", "tipo_area"]

    def __str__(self):
        nombre = self.descripcion or self.tipo_area.nombre
        return f"{nombre} ({self.vivienda.direccion})"

    def clean(self):
        # Un área que ya se usó en un servicio no puede pasar a otra vivienda
        if self.pk and self.vivienda_id:
            antes = Area.objects.filter(pk=self.pk).values_list("vivienda_id", flat=True).first()
            if antes and antes != self.vivienda_id and DetalleServicio.objects.filter(
                    Q(area_id=self.pk) | Q(elemento__area_id=self.pk)).exists():
                raise ValidationError({"vivienda": "Esta área ya se usó en servicios; no se puede mover a otra vivienda."})


class Elemento(models.Model):
    id_elemento = models.AutoField(primary_key=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, db_column="id_area", related_name="elementos")
    tipo_elemento = models.ForeignKey(TipoElemento, on_delete=models.PROTECT, db_column="id_tipo_elemento")
    descripcion = models.CharField("descripción", max_length=100, blank=True, null=True)

    class Meta:
        db_table = "elemento"
        ordering = ["area", "tipo_elemento"]

    def __str__(self):
        nombre = self.descripcion or self.tipo_elemento.nombre
        return f"{nombre} - {self.area}"

    def clean(self):
        # Un elemento usado en un servicio no puede pasar a un área de otra vivienda
        if self.pk and self.area_id:
            antes = Elemento.objects.filter(pk=self.pk).values_list("area__vivienda_id", flat=True).first()
            nueva = Area.objects.filter(pk=self.area_id).values_list("vivienda_id", flat=True).first()
            if antes and antes != nueva and DetalleServicio.objects.filter(elemento_id=self.pk).exists():
                raise ValidationError({"area": "Este elemento ya se usó en servicios; no se puede mover a otra vivienda."})


# =====================================================================
# Empleados
# =====================================================================

class Especialidad(models.Model):
    id_especialidad = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=60, unique=True)

    class Meta:
        db_table = "especialidad"
        verbose_name_plural = "especialidades"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Empleado(models.Model):
    ESTADOS = [("activo", "Activo"), ("inactivo", "Inactivo")]

    id_empleado = models.AutoField(primary_key=True)
    documento = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=60)
    apellido = models.CharField(max_length=60)
    telefono = models.CharField(max_length=15)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="activo")
    supervisor = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        db_column="id_supervisor", related_name="supervisados",
    )

    class Meta:
        db_table = "empleado"
        ordering = ["apellido", "nombre"]
        constraints = [
            models.CheckConstraint(condition=Q(estado__in=["activo", "inactivo"]), name="ck_empleado_estado"),
            models.CheckConstraint(
                condition=Q(supervisor__isnull=True) | ~Q(supervisor=F("id_empleado")),
                name="ck_empleado_supervisor",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    def clean(self):
        if self.pk and self.supervisor_id == self.pk:
            raise ValidationError({"supervisor": "Un empleado no puede ser su propio supervisor."})
        # Evita ciclos: A supervisa a B y B supervisa a A (directa o indirectamente)
        visto, actual = set(), self.supervisor_id
        while actual and self.pk:
            if actual == self.pk:
                raise ValidationError({"supervisor": "Esa asignación crea un ciclo de supervisores."})
            if actual in visto:
                break
            visto.add(actual)
            actual = Empleado.objects.filter(pk=actual).values_list("supervisor_id", flat=True).first()

    @property
    def promedio_calificacion(self):
        return self.asignaciones.aggregate(p=Avg("calificacion_empleado"))["p"]


class EmpleadoEspecialidad(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column="id_empleado", related_name="especialidades")
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT, db_column="id_especialidad")

    class Meta:
        db_table = "empleado_especialidad"
        verbose_name = "especialidad de empleado"
        verbose_name_plural = "especialidades de empleados"
        constraints = [
            models.UniqueConstraint(fields=["empleado", "especialidad"], name="pk_empleado_especialidad"),
        ]

    def __str__(self):
        return f"{self.empleado} - {self.especialidad}"


class EmpleadoZona(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column="id_empleado", related_name="zonas")
    zona = models.ForeignKey(Zona, on_delete=models.PROTECT, db_column="id_zona")

    class Meta:
        db_table = "empleado_zona"
        verbose_name = "zona de empleado"
        verbose_name_plural = "zonas de empleados"
        constraints = [
            models.UniqueConstraint(fields=["empleado", "zona"], name="pk_empleado_zona"),
        ]

    def __str__(self):
        return f"{self.empleado} - {self.zona}"


# =====================================================================
# Servicios
# =====================================================================

class TipoServicio(models.Model):
    id_tipo_servicio = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=80, unique=True)
    duracion_horas = models.DecimalField("duración (horas)", max_digits=4, decimal_places=1,
                                         validators=[MinValueValidator(0.5)])
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT, db_column="id_especialidad",
                                     related_name="tipos_servicio")

    class Meta:
        db_table = "tipo_servicio"
        verbose_name = "tipo de servicio"
        verbose_name_plural = "tipos de servicio"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(condition=Q(duracion_horas__gt=0), name="ck_tipo_servicio_duracion"),
            models.CheckConstraint(condition=Q(precio__gte=0), name="ck_tipo_servicio_precio"),
        ]

    def __str__(self):
        return self.nombre


def cruce_horario(empleado_id, servicio):
    """Devuelve otro servicio activo del empleado que se cruce con 'servicio', o None (supuesto 8)."""
    if servicio.estado == "cancelado":
        return None
    inicio, fin = servicio.rango_horario()
    otros = (Asignacion.objects.filter(empleado_id=empleado_id, servicio__fecha=servicio.fecha)
             .exclude(servicio_id=servicio.pk).exclude(servicio__estado="cancelado")
             .select_related("servicio"))
    for otra in otros:
        o_ini, o_fin = otra.servicio.rango_horario()
        if inicio < o_fin and o_ini < fin:
            return otra.servicio
    return None


class Servicio(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("confirmado", "Confirmado"),
        ("finalizado", "Finalizado"),
        ("cancelado", "Cancelado"),
    ]

    id_servicio = models.AutoField(primary_key=True)
    vivienda = models.ForeignKey(Vivienda, on_delete=models.PROTECT, db_column="id_vivienda", related_name="servicios")
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    estado = models.CharField(max_length=12, choices=ESTADOS, default="pendiente")
    observaciones = models.TextField(blank=True, null=True)
    calificacion_servicio = models.PositiveSmallIntegerField("calificación del servicio", blank=True, null=True,
                                                             validators=CALIFICACION)
    comentario_servicio = models.TextField("comentario del servicio", blank=True, null=True)

    class Meta:
        db_table = "servicio"
        ordering = ["-fecha", "-hora_inicio"]
        constraints = [
            models.CheckConstraint(
                condition=Q(estado__in=["pendiente", "confirmado", "finalizado", "cancelado"]),
                name="ck_servicio_estado",
            ),
            models.CheckConstraint(
                condition=Q(calificacion_servicio__isnull=True)
                | Q(calificacion_servicio__gte=1, calificacion_servicio__lte=5),
                name="ck_servicio_calificacion",
            ),
            # Supuesto 12: solo se califica un servicio finalizado
            models.CheckConstraint(
                condition=Q(calificacion_servicio__isnull=True) | Q(estado="finalizado"),
                name="ck_servicio_calif_final",
            ),
        ]

    def __str__(self):
        return f"#{self.pk} {self.fecha} {self.hora_inicio:%H:%M} - {self.vivienda.direccion}"

    # ---- utilidades ----
    @property
    def duracion_total(self):
        total = self.detalles.aggregate(t=Sum("tipo_servicio__duracion_horas"))["t"]
        return total or 0

    @property
    def total(self):
        return self.detalles.aggregate(t=Sum("precio_aplicado"))["t"] or 0

    def rango_horario(self):
        inicio = datetime.combine(self.fecha, self.hora_inicio)
        horas = float(self.duracion_total) or 1
        return inicio, inicio + timedelta(hours=horas)

    def clean(self):
        errores = {}
        # Supuesto 15: un cliente bloqueado no puede solicitar nuevos servicios
        if self._state.adding and self.vivienda_id:
            if Vivienda.objects.get(pk=self.vivienda_id).cliente.estado == "bloqueado":
                errores["vivienda"] = "El cliente de esta vivienda está bloqueado y no puede solicitar servicios."
        # Supuesto 12: solo se califica un servicio finalizado
        if self.calificacion_servicio is not None and self.estado != "finalizado":
            errores["calificacion_servicio"] = "Solo se puede calificar un servicio finalizado."
        # Para finalizar el servicio debe tener al menos un detalle y un empleado (1..*)
        if self.pk and self.estado in ("confirmado", "finalizado"):
            if not self.detalles.exists():
                errores["estado"] = "Agregue al menos un tipo de servicio antes de confirmar o finalizar."
            elif not self.asignaciones.exists():
                errores["estado"] = "Asigne al menos un empleado antes de confirmar o finalizar."
        if self.pk and self.vivienda_id:
            errores.update(self._validar_edicion())
        if errores:
            raise ValidationError(errores)

    def _validar_edicion(self):
        """Reglas que solo aplican al editar un servicio que ya existe."""
        errores = {}
        anterior = Servicio.objects.get(pk=self.pk)
        asignaciones = list(self.asignaciones.select_related("empleado"))

        # Un servicio pagado o con calificaciones debe seguir finalizado (supuestos 10 y 12)
        if self.estado != "finalizado":
            if Pago.objects.filter(servicio_id=self.pk).exists():
                errores["estado"] = "El servicio ya tiene un pago registrado; debe seguir finalizado."
            elif any(a.calificacion_empleado is not None or a.calificacion_cliente is not None
                     for a in asignaciones):
                errores["estado"] = "El servicio ya tiene calificaciones; debe seguir finalizado."

        # Cambio de vivienda: cliente bloqueado, áreas y elementos, zona de los empleados
        if self.vivienda_id != anterior.vivienda_id:
            nueva = Vivienda.objects.select_related("cliente", "barrio").get(pk=self.vivienda_id)
            problemas = []
            if nueva.cliente.estado == "bloqueado":
                problemas.append("El cliente de esa vivienda está bloqueado.")
            if self.detalles.filter(Q(area__isnull=False) & ~Q(area__vivienda_id=self.vivienda_id)).exists() or \
                    self.detalles.filter(Q(elemento__isnull=False)
                                         & ~Q(elemento__area__vivienda_id=self.vivienda_id)).exists():
                problemas.append("Hay tipos de servicio con áreas o elementos de la vivienda anterior.")
            fuera = [a.empleado for a in asignaciones
                     if not a.empleado.zonas.filter(zona_id=nueva.barrio.zona_id).exists()]
            if fuera:
                problemas.append("No trabajan en la zona de la nueva vivienda: "
                                 + ", ".join(str(e) for e in fuera) + ".")
            if problemas:
                errores["vivienda"] = " ".join(problemas)

        # Cambio de fecha, hora o reactivación: revisar cruces de horario (supuesto 8)
        if (self.fecha, self.hora_inicio, self.estado == "cancelado") != \
                (anterior.fecha, anterior.hora_inicio, anterior.estado == "cancelado"):
            for a in asignaciones:
                otro = cruce_horario(a.empleado_id, self)
                if otro:
                    errores["hora_inicio"] = f"{a.empleado} ya tiene el servicio #{otro.pk} en ese horario."
                    break
        return errores


class DetalleServicio(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, db_column="id_servicio", related_name="detalles")
    tipo_servicio = models.ForeignKey(TipoServicio, on_delete=models.PROTECT, db_column="id_tipo_servicio")
    area = models.ForeignKey(Area, on_delete=models.PROTECT, null=True, blank=True, db_column="id_area",
                             help_text="Déjelo vacío si el servicio es para toda la vivienda.")
    elemento = models.ForeignKey(Elemento, on_delete=models.PROTECT, null=True, blank=True, db_column="id_elemento",
                                 help_text="Solo si el servicio es para un elemento puntual (sofá, colchón...).")
    precio_aplicado = models.DecimalField(max_digits=10, decimal_places=2, blank=True,
                                          validators=[MinValueValidator(0)],
                                          help_text="Si lo deja vacío se usa el precio del tipo de servicio.")

    class Meta:
        db_table = "detalle_servicio"
        verbose_name = "detalle de servicio"
        verbose_name_plural = "detalles de servicio"
        constraints = [
            models.CheckConstraint(condition=Q(precio_aplicado__gte=0), name="ck_detalle_servicio_precio"),
            # Supuesto 5: toda la vivienda, un área o un elemento (no ambos)
            models.CheckConstraint(
                condition=Q(area__isnull=True) | Q(elemento__isnull=True),
                name="ck_detalle_servicio_alcance",
            ),
        ]

    def __str__(self):
        return f"{self.tipo_servicio} en {self.alcance}"

    @property
    def alcance(self):
        if self.elemento_id:
            return str(self.elemento)
        if self.area_id:
            return str(self.area)
        return "toda la vivienda"

    def clean(self):
        errores = {}
        if self.area_id and self.elemento_id:
            errores["elemento"] = "Elija un área o un elemento, no ambos."
        if self.servicio_id:
            vivienda_id = Servicio.objects.values_list("vivienda_id", flat=True).get(pk=self.servicio_id)
            if self.area_id and Area.objects.get(pk=self.area_id).vivienda_id != vivienda_id:
                errores["area"] = "El área no pertenece a la vivienda del servicio."
            if self.elemento_id and Elemento.objects.get(pk=self.elemento_id).area.vivienda_id != vivienda_id:
                errores["elemento"] = "El elemento no pertenece a la vivienda del servicio."
        # Los empleados ya asignados deben tener la especialidad de este tipo de servicio
        if self.servicio_id and self.tipo_servicio_id:
            esp = TipoServicio.objects.get(pk=self.tipo_servicio_id).especialidad_id
            sin = Empleado.objects.filter(asignaciones__servicio_id=self.servicio_id).exclude(
                especialidades__especialidad_id=esp)
            if sin.exists():
                errores["tipo_servicio"] = ("Estos empleados asignados no tienen la especialidad requerida: "
                                            + ", ".join(str(e) for e in sin) + ".")
        if self.precio_aplicado is None and self.tipo_servicio_id:
            self.precio_aplicado = TipoServicio.objects.get(pk=self.tipo_servicio_id).precio
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if self.precio_aplicado is None:
            self.precio_aplicado = self.tipo_servicio.precio
        super().save(*args, **kwargs)


class Asignacion(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, db_column="id_servicio", related_name="asignaciones")
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, db_column="id_empleado", related_name="asignaciones")
    calificacion_empleado = models.PositiveSmallIntegerField(
        "calificación al empleado", blank=True, null=True, validators=CALIFICACION,
        help_text="La que el cliente le da al empleado (1 a 5).")
    comentario_empleado = models.TextField("comentario al empleado", blank=True, null=True)
    calificacion_cliente = models.PositiveSmallIntegerField(
        "calificación al cliente", blank=True, null=True, validators=CALIFICACION,
        help_text="La que el empleado le da al cliente (1 a 5).")
    comentario_cliente = models.TextField("comentario al cliente", blank=True, null=True)

    class Meta:
        db_table = "asignacion"
        verbose_name = "asignación"
        verbose_name_plural = "asignaciones"
        constraints = [
            models.UniqueConstraint(fields=["servicio", "empleado"], name="pk_asignacion"),
            models.CheckConstraint(
                condition=Q(calificacion_empleado__isnull=True)
                | Q(calificacion_empleado__gte=1, calificacion_empleado__lte=5),
                name="ck_asignacion_calif_empl",
            ),
            models.CheckConstraint(
                condition=Q(calificacion_cliente__isnull=True)
                | Q(calificacion_cliente__gte=1, calificacion_cliente__lte=5),
                name="ck_asignacion_calif_client",
            ),
        ]

    def __str__(self):
        return f"{self.empleado} en servicio #{self.servicio_id}"

    def clean(self):
        if not (self.servicio_id and self.empleado_id):
            return
        errores = []
        servicio = Servicio.objects.select_related("vivienda__barrio").get(pk=self.servicio_id)
        empleado = Empleado.objects.get(pk=self.empleado_id)

        if empleado.estado != "activo":
            errores.append("El empleado está inactivo.")

        # Supuesto 7: debe trabajar en la zona de la vivienda
        zona = servicio.vivienda.barrio.zona_id
        if not empleado.zonas.filter(zona_id=zona).exists():
            errores.append("El empleado no trabaja en la zona de la vivienda.")

        # Supuesto 7: debe tener la especialidad de cada tipo de servicio
        requeridas = set(servicio.detalles.values_list("tipo_servicio__especialidad_id", flat=True))
        if not requeridas:
            errores.append("Agregue primero los tipos de servicio (detalles) a este servicio.")
        tiene = set(empleado.especialidades.values_list("especialidad_id", flat=True))
        faltan = Especialidad.objects.filter(pk__in=requeridas - tiene)
        if faltan:
            errores.append("Al empleado le falta la especialidad: " + ", ".join(e.nombre for e in faltan) + ".")

        # Supuesto 8: no puede tener dos servicios a la misma hora
        otro = cruce_horario(self.empleado_id, servicio)
        if otro:
            errores.append(f"El empleado ya tiene el servicio #{otro.pk} en ese horario.")

        # Supuestos 12 a 14: solo se califica cuando el servicio termina
        if (self.calificacion_empleado is not None or self.calificacion_cliente is not None) \
                and servicio.estado != "finalizado":
            errores.append("Las calificaciones solo se registran cuando el servicio está finalizado.")

        if errores:
            raise ValidationError(errores)


# =====================================================================
# Insumos
# =====================================================================

class CategoriaInsumo(models.Model):
    CATEGORIAS = [("producto", "Producto"), ("utensilio", "Utensilio"), ("herramienta", "Herramienta")]

    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=30, unique=True, choices=CATEGORIAS)

    class Meta:
        db_table = "categoria_insumo"
        verbose_name = "categoría de insumo"
        verbose_name_plural = "categorías de insumo"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(condition=Q(nombre__in=["producto", "utensilio", "herramienta"]),
                                   name="ck_categoria_insumo_nom"),
        ]

    def __str__(self):
        return self.get_nombre_display()


class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    nit = models.CharField("NIT", max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField("teléfono", max_length=15, blank=True, null=True)

    class Meta:
        db_table = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Insumo(models.Model):
    id_insumo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=80, unique=True)
    categoria = models.ForeignKey(CategoriaInsumo, on_delete=models.PROTECT, db_column="id_categoria",
                                  verbose_name="categoría")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, db_column="id_proveedor", related_name="insumos")
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "insumo"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(condition=Q(stock__gte=0), name="ck_insumo_stock"),
        ]

    def __str__(self):
        return self.nombre


class InsumoRequerido(models.Model):
    tipo_servicio = models.ForeignKey(TipoServicio, on_delete=models.CASCADE, db_column="id_tipo_servicio",
                                      related_name="insumos_requeridos")
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, db_column="id_insumo")
    cantidad_sugerida = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0.01)])

    class Meta:
        db_table = "insumo_requerido"
        verbose_name = "insumo requerido"
        verbose_name_plural = "insumos requeridos"
        constraints = [
            models.UniqueConstraint(fields=["tipo_servicio", "insumo"], name="pk_insumo_requerido"),
            models.CheckConstraint(condition=Q(cantidad_sugerida__gt=0), name="ck_insumo_requerido_cantidad"),
        ]

    def __str__(self):
        return f"{self.insumo} para {self.tipo_servicio}"


class InsumoUsado(models.Model):
    ORIGEN = [("empresa", "Empresa"), ("cliente", "Cliente")]

    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, db_column="id_servicio", related_name="insumos_usados")
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, db_column="id_insumo")
    cantidad = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0.01)])
    proporcionado_por = models.CharField(max_length=10, choices=ORIGEN, default="empresa")

    class Meta:
        db_table = "insumo_usado"
        verbose_name = "insumo usado"
        verbose_name_plural = "insumos usados"
        constraints = [
            models.UniqueConstraint(fields=["servicio", "insumo"], name="pk_insumo_usado"),
            models.CheckConstraint(condition=Q(cantidad__gt=0), name="ck_insumo_usado_cantidad"),
            models.CheckConstraint(condition=Q(proporcionado_por__in=["empresa", "cliente"]),
                                   name="ck_insumo_usado_proveedor"),
        ]

    def __str__(self):
        return f"{self.cantidad} de {self.insumo} ({self.proporcionado_por})"

    # Supuesto 11: solo lo que pone la empresa se descuenta del inventario.
    def _consumo(self):
        return int(self.cantidad) if self.proporcionado_por == "empresa" and self.cantidad else 0

    def _anterior(self):
        if self.pk:
            return InsumoUsado.objects.filter(pk=self.pk).first()
        return None

    def clean(self):
        if not self.insumo_id or self.cantidad is None:
            return
        disponible = Insumo.objects.get(pk=self.insumo_id).stock
        anterior = self._anterior()
        if anterior and anterior.insumo_id == self.insumo_id:
            disponible += anterior._consumo()
        if self._consumo() > disponible:
            raise ValidationError({"cantidad": f"No hay suficiente stock. Disponible: {disponible}."})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            anterior = self._anterior()
            if anterior and anterior._consumo():
                Insumo.objects.filter(pk=anterior.insumo_id).update(stock=F("stock") + anterior._consumo())
            super().save(*args, **kwargs)
            if self._consumo():
                Insumo.objects.filter(pk=self.insumo_id).update(stock=F("stock") - self._consumo())



@receiver(pre_delete, sender=InsumoUsado)
def devolver_stock(sender, instance, **kwargs):
    """Devuelve al inventario lo que puso la empresa, también cuando se borra el servicio completo."""
    if instance._consumo():
        Insumo.objects.filter(pk=instance.insumo_id).update(stock=F("stock") + instance._consumo())


# =====================================================================
# Pagos
# =====================================================================

class MetodoPago(models.Model):
    id_metodo_pago = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=40, unique=True)

    class Meta:
        db_table = "metodo_pago"
        verbose_name = "método de pago"
        verbose_name_plural = "métodos de pago"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    # OneToOneField = FK + UNIQUE: un solo pago por servicio (supuesto 10)
    servicio = models.OneToOneField(Servicio, on_delete=models.PROTECT, db_column="id_servicio", related_name="pago")
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, db_column="id_metodo_pago",
                                    verbose_name="método de pago")
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])

    class Meta:
        db_table = "pago"
        ordering = ["-fecha"]
        constraints = [
            models.CheckConstraint(condition=Q(monto__gt=0), name="ck_pago_monto"),
        ]

    def __str__(self):
        return f"Pago #{self.pk} - servicio #{self.servicio_id}"

    def clean(self):
        # Supuesto 10: el pago se registra cuando el servicio termina
        if self.servicio_id and Servicio.objects.get(pk=self.servicio_id).estado != "finalizado":
            raise ValidationError({"servicio": "Solo se puede pagar un servicio finalizado."})
