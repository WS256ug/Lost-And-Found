"""
WSGI config for lostfound project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lostfound.settings')

application = get_wsgi_application()

should_migrate_on_startup = os.environ.get(
    "RUN_MIGRATIONS_ON_STARTUP",
    "1" if os.environ.get("VERCEL") else "0",
) == "1"

if should_migrate_on_startup:
    call_command("migrate", interactive=False, verbosity=0)

should_seed_demo_data = os.environ.get(
    "SEED_DEMO_DATA",
    "1" if os.environ.get("VERCEL") else "0",
) == "1"

if should_seed_demo_data:
    from items.models import Item

    if not Item.objects.exists():
        call_command("seed_demo_data", verbosity=0)
