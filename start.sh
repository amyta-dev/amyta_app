#!/bin/sh
set -e

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings.prod}

python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-3}
