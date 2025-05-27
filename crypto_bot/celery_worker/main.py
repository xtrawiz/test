import os
import sys

# This is to ensure 'core' is in sys.path when Celery worker starts
# Adjust if your project structure or PYTHONPATH setup is different
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from celery_worker.celery_app import celery_app
except ModuleNotFoundError as e:
    print(f"Error: Could not import celery_app. Ensure 'celery_worker.celery_app' is accessible.")
    print(f"Current sys.path: {sys.path}")
    # This might indicate an issue with how the worker is being started or project structure.
    raise e
except ImportError as e:
    print(f"Error importing something from celery_app, possibly settings: {e}")
    # This could be due to 'core.settings.config' not being found from within celery_app.py
    raise e


# This line makes `celery -A main.app worker ...` work,
# where `main` is this file and `app` is the celery_app instance.
app = celery_app

# For debugging purposes if run directly, though not its primary execution path
if __name__ == '__main__':
    print("Celery worker main.py executed. 'app' is now an alias to 'celery_app'.")
    print(f"Celery app name: {app.main}")
    # Set dummy env vars if needed for settings during this direct test
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    # You might need to re-initialize settings if celery_app.py relies on them being set before import
    # from core.settings.config import settings
    # settings = settings.__class__()
    print(f"Broker: {app.conf.broker_url}")
