import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

app = Celery("backend")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Force override for Windows cases
app.conf.broker_url = "redis://127.0.0.1:6379/0"
app.conf.result_backend = "redis://127.0.0.1:6379/0"

app.autodiscover_tasks()
