#!/usr/bin/env bash
# Script de construcción para Render: se ejecuta en cada despliegue.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Llena la base con datos ficticios solo la primera vez (si está vacía)
python manage.py poblar_datos

# Crea el usuario administrador con las variables DJANGO_SUPERUSER_*
# (si ya existe, no hace nada)
python manage.py createsuperuser --noinput || true
