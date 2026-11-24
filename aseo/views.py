from functools import reduce
from operator import or_

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, models, transaction
from django.db.models import Avg, Count, Q, Sum
from django.db.models.deletion import ProtectedError, RestrictedError
from django.db.models.functions import TruncMonth
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import models as m
from .registro import GRUPOS, TABLAS


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------

def _tabla(nombre):
    try:
        return TABLAS[nombre]
    except KeyError:
        raise Http404("Tabla no encontrada")


def _titulo(modelo, plural=True):
    meta = modelo._meta
    return str(meta.verbose_name_plural if plural else meta.verbose_name).capitalize()


def _celda(obj, campo):
    field = obj._meta.get_field(campo)
    if field.choices:
        return getattr(obj, f"get_{campo}_display")()
    valor = getattr(obj, campo)
    return "" if valor is None else valor


def _encabezado(modelo, campo):
    return str(modelo._meta.get_field(campo).verbose_name).capitalize()


def _siguiente(request, por_defecto):
    url = request.POST.get("next") or request.GET.get("next")
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}):
        return url
    return por_defecto


def formulario_para(modelo):
    """Crea un ModelForm con widgets de Bootstrap para cualquier tabla."""

    class Formulario(forms.ModelForm):
        class Meta:
            model = modelo
            exclude = []
            widgets = {}
            for f in modelo._meta.fields:
                if isinstance(f, models.DateField):
                    widgets[f.name] = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
                elif isinstance(f, models.TimeField):
                    widgets[f.name] = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
                elif isinstance(f, models.TextField):
                    widgets[f.name] = forms.Textarea(attrs={"rows": 3})

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for campo in self.fields.values():
                clase = "form-select" if isinstance(campo.widget, forms.Select) else "form-control"
                campo.widget.attrs.setdefault("class", clase)

    return Formulario


# ---------------------------------------------------------------------
# Inicio
# ---------------------------------------------------------------------

def inicio(request):
    grupos = [
        (grupo, [(clave, _titulo(TABLAS[clave]["modelo"]), TABLAS[clave]["modelo"].objects.count()) for clave in claves])
        for grupo, claves in GRUPOS
    ]
    resumen = {
        "servicios": m.Servicio.objects.count(),
        "pendientes": m.Servicio.objects.filter(estado__in=["pendiente", "confirmado"]).count(),
        "ingresos": m.Pago.objects.aggregate(t=Sum("monto"))["t"] or 0,
        "clientes": m.Cliente.objects.filter(estado="activo").count(),
    }
    return render(request, "aseo/inicio.html", {"grupos": grupos, "resumen": resumen})


# ---------------------------------------------------------------------
# CRUD genérico para las 24 tablas
# ---------------------------------------------------------------------

def lista(request, tabla):
    conf = _tabla(tabla)
    modelo = conf["modelo"]
    qs = modelo.objects.select_related()
    if not qs.ordered:
        qs = qs.order_by("pk")

    # Filtro por cualquier FK (por ejemplo ?servicio=3) para navegar entre tablas
    filtros = {}
    for f in modelo._meta.fields:
        if f.is_relation and request.GET.get(f.name):
            filtros[f.name] = request.GET[f.name]
    if filtros:
        try:
            qs = qs.filter(**filtros)
        except (ValueError, ValidationError):
            messages.warning(request, "El filtro de la dirección no es válido; se muestran todos los registros.")
            filtros = {}

    q = request.GET.get("q", "").strip()
    if q and conf.get("buscar"):
        qs = qs.filter(reduce(or_, (Q(**{f"{c}__icontains": q}) for c in conf["buscar"])))

    pagina = Paginator(qs, 20).get_page(request.GET.get("page"))
    filas = [(obj, [_celda(obj, c) for c in conf["columnas"]]) for obj in pagina]
    return render(request, "aseo/lista.html", {
        "tabla": tabla,
        "titulo": _titulo(modelo),
        "encabezados": [_encabezado(modelo, c) for c in conf["columnas"]],
        "filas": filas,
        "pagina": pagina,
        "q": q,
        "filtros": filtros,
    })


@login_required
def crear(request, tabla):
    modelo = _tabla(tabla)["modelo"]
    Formulario = formulario_para(modelo)
    if request.method == "POST":
        form = Formulario(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    obj = form.save()
            except IntegrityError as e:
                form.add_error(None, f"La base de datos rechazó el registro: {e}")
            else:
                messages.success(request, f"Se creó «{obj}».")
                return redirect(_siguiente(request, reverse("lista", args=[tabla])))
    else:
        iniciales = {k: v for k, v in request.GET.items() if k in form_fields(modelo)}
        form = Formulario(initial=iniciales)
    return render(request, "aseo/formulario.html", {
        "form": form, "tabla": tabla, "titulo": f"Nuevo registro: {_titulo(modelo, False)}",
        "next": request.GET.get("next", ""),
    })


def form_fields(modelo):
    return {f.name for f in modelo._meta.fields}


@login_required
def editar(request, tabla, pk):
    modelo = _tabla(tabla)["modelo"]
    obj = get_object_or_404(modelo, pk=pk)
    Formulario = formulario_para(modelo)
    form = Formulario(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                obj = form.save()
        except IntegrityError as e:
            form.add_error(None, f"La base de datos rechazó el cambio: {e}")
        else:
            messages.success(request, f"Se actualizó «{obj}».")
            return redirect(_siguiente(request, reverse("lista", args=[tabla])))
    return render(request, "aseo/formulario.html", {
        "form": form, "tabla": tabla, "titulo": f"Editar {_titulo(modelo, False).lower()}: {obj}",
        "next": request.GET.get("next", ""),
    })


@login_required
def eliminar(request, tabla, pk):
    modelo = _tabla(tabla)["modelo"]
    obj = get_object_or_404(modelo, pk=pk)
    if request.method == "POST":
        texto = str(obj)
        try:
            with transaction.atomic():
                obj.delete()
        except (ProtectedError, RestrictedError) as e:
            relacionados = sorted({_titulo(o.__class__, False) for o in e.protected_objects
                                   } if isinstance(e, ProtectedError) else set())
            messages.error(request, f"No se puede eliminar «{texto}» porque tiene registros relacionados"
                                    + (f" en: {', '.join(relacionados)}." if relacionados else "."))
            return redirect(_siguiente(request, reverse("lista", args=[tabla])))
        messages.success(request, f"Se eliminó «{texto}».")
        return redirect(_siguiente(request, reverse("lista", args=[tabla])))
    return render(request, "aseo/eliminar.html", {
        "obj": obj, "tabla": tabla, "titulo": _titulo(modelo, False), "next": request.GET.get("next", ""),
    })


# ---------------------------------------------------------------------
# Detalle de un servicio (RF11 a RF19 en una sola pantalla)
# ---------------------------------------------------------------------

def servicio_detalle(request, pk):
    servicio = get_object_or_404(
        m.Servicio.objects.select_related("vivienda__cliente", "vivienda__barrio__zona"), pk=pk)
    requeridas = set(servicio.detalles.values_list("tipo_servicio__especialidad_id", flat=True))

    # Empleados que cumplen zona y especialidades (supuesto 7)
    candidatos = m.Empleado.objects.filter(estado="activo", zonas__zona=servicio.vivienda.barrio.zona).distinct()
    for esp in requeridas:
        candidatos = candidatos.filter(especialidades__especialidad_id=esp)
    candidatos = candidatos.exclude(asignaciones__servicio=servicio)

    return render(request, "aseo/servicio_detalle.html", {
        "s": servicio,
        "detalles": servicio.detalles.select_related("tipo_servicio", "area__tipo_area", "elemento__tipo_elemento"),
        "asignaciones": servicio.asignaciones.select_related("empleado"),
        "insumos": servicio.insumos_usados.select_related("insumo"),
        "pago": getattr(servicio, "pago", None),
        "candidatos": candidatos if requeridas else [],
        "volver": reverse("servicio_detalle", args=[pk]),
    })


# ---------------------------------------------------------------------
# Calificación de clientes y bloqueo (RF18, RF21, supuesto 15)
# ---------------------------------------------------------------------

def clientes_calificacion(request):
    clientes = (m.Cliente.objects
                .annotate(promedio=Avg("viviendas__servicios__asignaciones__calificacion_cliente"),
                          servicios=Count("viviendas__servicios", distinct=True))
                .order_by("promedio"))
    return render(request, "aseo/clientes_calificacion.html", {"clientes": clientes, "limite": 3})


@login_required
@require_POST
def cambiar_estado_cliente(request, pk):
    cliente = get_object_or_404(m.Cliente, pk=pk)
    cliente.estado = "activo" if cliente.estado == "bloqueado" else "bloqueado"
    cliente.save(update_fields=["estado"])
    messages.success(request, f"{cliente} ahora está {cliente.get_estado_display().lower()}.")
    return redirect("clientes_calificacion")


# ---------------------------------------------------------------------
# Informes (RF20)
# ---------------------------------------------------------------------

def informes(request):
    ctx = {
        "por_fecha": (m.Servicio.objects.values("fecha").annotate(n=Count("pk")).order_by("-fecha")[:15]),
        "por_zona": (m.Servicio.objects.values("vivienda__barrio__zona__nombre")
                     .annotate(n=Count("pk")).order_by("-n")),
        "por_barrio": (m.Servicio.objects.values("vivienda__barrio__nombre", "vivienda__barrio__zona__nombre")
                       .annotate(n=Count("pk")).order_by("-n")[:10]),
        "ingresos_mes": (m.Pago.objects.annotate(mes=TruncMonth("fecha")).values("mes")
                         .annotate(total=Sum("monto"), n=Count("pk")).order_by("-mes")),
        "ingresos_metodo": (m.Pago.objects.values("metodo_pago__nombre")
                            .annotate(total=Sum("monto"), n=Count("pk")).order_by("-total")),
        "mejores_empleados": (m.Empleado.objects.annotate(promedio=Avg("asignaciones__calificacion_empleado"),
                                                          n=Count("asignaciones__calificacion_empleado"))
                              .filter(n__gt=0).order_by("-promedio", "-n")[:10]),
        "mejores_servicios": (m.TipoServicio.objects
                              .annotate(promedio=Avg("detalleservicio__servicio__calificacion_servicio"),
                                        n=Count("detalleservicio__servicio__calificacion_servicio"))
                              .filter(n__gt=0).order_by("-promedio")[:10]),
        "peores_clientes": (m.Cliente.objects
                            .annotate(promedio=Avg("viviendas__servicios__asignaciones__calificacion_cliente"),
                                      n=Count("viviendas__servicios__asignaciones__calificacion_cliente"))
                            .filter(n__gt=0).order_by("promedio")[:10]),
        "insumos_usados": (m.InsumoUsado.objects.values("insumo__nombre", "insumo__categoria__nombre")
                           .annotate(total=Sum("cantidad"), n=Count("pk")).order_by("-total")[:10]),
        "areas": (m.DetalleServicio.objects.filter(area__isnull=False).values("area__tipo_area__nombre")
                  .annotate(n=Count("pk")).order_by("-n")),
        "elementos": (m.DetalleServicio.objects.filter(elemento__isnull=False)
                      .values("elemento__tipo_elemento__nombre").annotate(n=Count("pk")).order_by("-n")),
    }
    return render(request, "aseo/informes.html", ctx)
