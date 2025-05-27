import os
import sys
from celery import Celery

# This is to ensure 'core' is in sys.path when Celery worker starts
# Adjust if your project structure or PYTHONPATH setup is different
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from core.settings.config import settings
except ModuleNotFoundError as e:
    print(f"Error: Could not import settings. Ensure 'core' module is in PYTHONPATH.")
    print(f"Current sys.path: {sys.path}")
    # If running in Docker, this might indicate a volume mapping issue or incorrect WORKDIR.
    # If running locally, ensure PYTHONPATH is set or this script is run from a location
    # where 'core' is discoverable.
    raise e


celery_app = Celery(
    "crypto_bot_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["celery_worker.tasks"]  # List of modules to import when the worker starts
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True, # Ensure Redis is available before worker starts
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
)

# Example: To automatically discover tasks in all 'tasks.py' files within your apps
# if you had a more Django-like structure:
# celery_app.autodiscover_tasks()

if __name__ == '__main__':
    # This is for direct execution testing, not how Celery usually runs.
    # For Celery, you'd use the CLI: celery -A celery_worker.celery_app worker -l info
    print("Celery app configured. To run worker: celery -A celery_worker.celery_app worker -l INFO")
    # You might want to set dummy env vars for testing direct execution if settings relies on them
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "False")
    # Re-initialize settings if needed for direct script test.
    # settings = settings.__class__() # Be careful with side effects if settings is already used.
    print(f"Broker: {celery_app.conf.broker_url}")
    print(f"Task always eager: {settings.CELERY_TASK_ALWAYS_EAGER}")
