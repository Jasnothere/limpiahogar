from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("informes/", views.informes, name="informes"),
    path("clientes/calificacion/", views.clientes_calificacion, name="clientes_calificacion"),
    path("clientes/<int:pk>/estado/", views.cambiar_estado_cliente, name="cambiar_estado_cliente"),
    path("servicios/<int:pk>/", views.servicio_detalle, name="servicio_detalle"),
    path("tabla/<str:tabla>/", views.lista, name="lista"),
    path("tabla/<str:tabla>/nuevo/", views.crear, name="crear"),
    path("tabla/<str:tabla>/<int:pk>/editar/", views.editar, name="editar"),
    path("tabla/<str:tabla>/<int:pk>/eliminar/", views.eliminar, name="eliminar"),
]
