import uvicorn # Typically used by CMD in Dockerfile, but good for linters/IDEs
from fastapi import FastAPI

# Assuming crypto_bot is in PYTHONPATH or installed
# For Docker, this should work as /app will be the working directory
try:
    from core.settings.config import settings
except ModuleNotFoundError:
    # Fallback for direct execution if 'core' is not in sys.path
    import sys
    import os
    # Add the parent directory of 'web/app' twice to get to 'crypto_bot'
    # This ensures that 'core' (for settings) can be found.
    # It also helps if static/templates are referenced relative to project root.
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_dir = os.path.abspath(os.path.join(current_script_dir, '..', '..'))
    if project_root_dir not in sys.path:
        sys.path.insert(0, project_root_dir)
    from core.settings.config import settings

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.responses import HTMLResponse


app = FastAPI(title="Crypto Bot API", version="0.1.0")

# Mount static files - relative to the CWD.
# In Docker, WORKDIR is /app. crypto_bot/static is copied to /app/static.
# docker-compose.yml volume mounts ./static to /app/static.
# So, "static" should resolve to /app/static in the container.
# For local execution, if running from project root `crypto_bot/`, "static" is correct.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates - relative to the CWD.
# Similar logic as StaticFiles: "templates" should resolve to /app/templates in container
# or crypto_bot/templates if running locally from project root.
templates = Jinja2Templates(directory="templates")

# Integrate Babel translations with Jinja2
try:
    from core.translations import gettext_provider, ngettext_provider
    templates.env.globals['gettext'] = gettext_provider
    templates.env.globals['_'] = gettext_provider # common alias
    templates.env.globals['ngettext'] = ngettext_provider
except ImportError as e:
    print(f"Could not import translations for FastAPI Jinja2: {e}")
    # Fallback or raise error, depending on desired behavior
    pass


@app.get("/")
async def root():
    return {"message": "FastAPI server is running"}

@app.get("/test-template", response_class=HTMLResponse)
async def test_template(request: Request):
    return templates.TemplateResponse("test_page.html", {"request": request, "message": "Hello from FastAPI with Jinja2!"})

if __name__ == "__main__":
    # This block is for local development convenience, outside Docker.
    # The Docker container uses the CMD in the Dockerfile.

    # Set default environment variables for local development if not already set
    # These would typically be in a .env file loaded by pydantic-settings or set in the shell
    import os
    os.environ.setdefault("DATABASE_URL", "mysql+aiomysql://user:pass@localhost:3306/db_name")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("FASTAPI_SECRET_KEY", "local_dev_secret_key_should_be_overridden")
    os.environ.setdefault("LOG_LEVEL", "debug")
    
    # Re-import settings to ensure they pick up any environment variables set above for local run
    # This is a bit of a workaround for direct script execution without a .env file properly configured
    # or without environment variables pre-set in the shell.
    # In a more complex setup, you might use python-dotenv explicitly here.
    current_settings = settings
    if hasattr(settings, '_env_file'): # Check if settings was loaded from Pydantic's BaseSettings
        current_settings = settings.__class__() # Re-instantiate to load .env or env vars

    uvicorn.run(
        "main:app", # Points to the 'app' instance in this 'main.py' file
        host="0.0.0.0", 
        port=8001, # Different port for local dev to avoid conflict with Docker
        log_level=current_settings.LOG_LEVEL.lower(),
        reload=True # Enable auto-reload for development
    )
