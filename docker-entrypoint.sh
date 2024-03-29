#!/usr/bin/env bash
set -e

cd /workspace
service mysql restart
sh run_migration.sh
python3 -c "import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'CrackSite.settings'
import django
django.setup()
from django.contrib.auth.management.commands.createsuperuser import get_user_model
if not get_user_model().objects.filter(username='$DJANGO_SUPERUSER_USERNAME'): 
    get_user_model()._default_manager.db_manager().create_superuser(username='$DJANGO_SUPERUSER_USERNAME', email='$DJANGO_SUPERUSER_EMAIL', password='$DJANGO_SUPERUSER_PASSWORD')"
sh server_start.sh

trap 'sh server_shutdown.sh' EXIT

tail -f django.log

exec "$@"
