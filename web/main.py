from fastapi import FastAPI, Depends, HTTPException, status, Request # Added Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any # Added Dict, Any
from contextlib import asynccontextmanager
import logging # For logging webhook calls

import os # For path joining and env vars
from passlib.context import CryptContext
from fastapi_admin.app import app as admin_app # FastAPI-Admin app instance
from fastapi_admin.providers.login import UsernamePasswordProvider
from fastapi_admin.models import AbstractAdmin # For custom admin user model if needed
from fastapi_admin.resources import Link, Field
from fastapi_admin.widgets import displays

from . import models, schemas, database, admin_models # Import admin_models
from .models import User as WebUser # Explicit import for clarity in webhook
from .database import engine as db_engine # Import the SQLAlchemy engine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI-Admin Setup ---
# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory storage for a single admin user for simplicity, as per UsernamePasswordProvider
# For DB-backed admins, you'd create an SQLAlchemy Admin model and register it.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = pwd_context.hash(os.getenv("ADMIN_PASSWORD", "admin")) # Hash the default/env password

# This is a simplified Admin model for the UsernamePasswordProvider.
# It doesn't store admins in the DB but provides the structure FastAPI-Admin expects.
class Admin(AbstractAdmin):
    # These fields are not used for DB storage in this simple setup
    # but are part of the AbstractAdmin interface.
    id: int
    username: str
    password: str # This would be the hashed password if loaded from DB
    # Add other fields if your AbstractAdmin or provider needs them.

    # For this simple provider, only username and password check matters.
    # The provider itself will handle checking against env vars or a fixed list.

    @classmethod
    async def get_by_username(cls, username: str):
        if username == ADMIN_USERNAME:
            # Create a dummy Admin instance with the expected hashed password
            # This is what UsernamePasswordProvider will compare against
            return Admin(id=1, username=ADMIN_USERNAME, password=ADMIN_PASSWORD_HASH)
        return None

    @classmethod
    async def create_admin(cls, obj_in): # Not used in this simple setup
        pass


login_provider = UsernamePasswordProvider(
    admin_model=Admin, # Use our simplified Admin class
    login_logo_url="https://preview.tabler.io/static/logo.svg" # Optional
)

@asynccontextmanager
async def lifespan(app: FastAPI): # app here is the main FastAPI app instance
    # Startup
    database.create_tables()
    
    # Configure and initialize FastAPI-Admin
    # Note: `admin_app` is the FastAPI-Admin's own FastAPI instance.
    # We are configuring it here, then mounting it to our main `app`.
    await admin_app.configure(
        logo_url="https://preview.tabler.io/static/logo-white.svg",
        template_folders=[os.path.join(os.path.dirname(__file__), "templates")], # If you have custom templates
        providers=[login_provider], # Register the login provider
        db_engine=db_engine, # Provide the SQLAlchemy engine
        redis=None, # No Redis for admin panel for now, unless explicitly needed by a feature
        admin_path="/admin", # Base path for admin panel
        secret=os.getenv("SECRET_KEY", "a_very_default_secret_key_please_change") # JWT Secret
    )
    
    # Register resources
    admin_app.add_resource(admin_models.UserResource)
    admin_app.add_resource(admin_models.NewsResource)
    admin_app.add_resource(admin_models.FilterResource)
    admin_app.add_resource(admin_models.CalculationResource)
    admin_app.add_resource(admin_models.PortfolioResource)

    # Add placeholder links for complex features
    admin_app.add_link(Link(name="مانیتورینگ وظایف Celery", icon="fas fa-circle-nodes", url="/admin/celery-dashboard-placeholder"))
    admin_app.add_link(Link(name="گزارشات و نمودارها", icon="fas fa-chart-line", url="/admin/reports-placeholder"))

    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)

# Mount the admin app to the main FastAPI application
app.mount("/admin", admin_app)


# Placeholder routes for complex features (to avoid 404 on link click)
@app.get("/admin/celery-dashboard-placeholder")
async def celery_dashboard_placeholder():
    # In a real scenario, this would render a page or proxy to Flower
    return {"message": "صفحه مانیتورینگ وظایف Celery در اینجا پیاده‌سازی خواهد شد."}

@app.get("/admin/reports-placeholder")
async def reports_placeholder():
    # In a real scenario, this would render a page with reports/charts
    return {"message": "صفحه گزارشات و نمودارها در اینجا پیاده‌سازی خواهد شد."}


# Dependency to get DB session (already exists)

# Dependency to get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.telegram_id == user.telegram_id).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Telegram ID already registered")
    
    new_user_data = user.dict()
    # Ensure api_key is generated if not provided, using the model's default
    if "api_key" not in new_user_data or new_user_data["api_key"] is None:
        # This relies on the default lambda in the model for api_key
        db_user = models.User(**{k: v for k, v in new_user_data.items() if k != "api_key"})
    else:
        db_user = models.User(**new_user_data)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{telegram_id}", response_model=schemas.User)
def read_user(telegram_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@app.put("/users/{telegram_id}", response_model=schemas.User)
def update_user(telegram_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Placeholder for a root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the User API"}

# --- Telegram Payment Webhook ---
# This is an alternative/additional way Telegram can notify about payments.
# Pyrogram's SuccessfulPayment handler is often sufficient for direct bot-user interaction.

@app.post("/webhook/telegram_payment/{secret_token}") # Added a {secret_token} path parameter for basic security
async def telegram_payment_webhook(
    update: Dict[Any, Any], # Telegram sends an Update object
    secret_token: str,
    db: Session = Depends(get_db)
):
    # Basic security: Check if the secret_token matches one you've configured
    # This should be a securely generated and stored token, e.g., in .env
    EXPECTED_SECRET_TOKEN = "YOUR_VERY_SECRET_WEBHOOK_TOKEN" # Replace with a real secret from .env
    if secret_token != EXPECTED_SECRET_TOKEN:
        logger.warning("Invalid secret token received for payment webhook.")
        raise HTTPException(status_code=403, detail="Invalid secret token")

    logger.info(f"Received payment webhook update: {update}")

    if "message" in update and "successful_payment" in update["message"]:
        message_data = update["message"]
        payment_info = message_data["successful_payment"]
        
        # Extract user_id from the payload if possible, or from message.from.id
        # The payload was defined as `pro_sub_user_{user_id}_{timestamp}`
        telegram_user_id = None
        if "from" in message_data and "id" in message_data["from"]:
            telegram_user_id = message_data["from"]["id"]
        
        # Attempt to parse user_id more reliably from payload if this webhook is primary
        # For now, we'll assume `message_data["from"]["id"]` is the user who paid.
        
        if not telegram_user_id:
            logger.error("Could not determine user_id from payment webhook.")
            # Return 200 to Telegram to acknowledge receipt, but log error.
            return {"status": "error", "detail": "User ID not found in webhook"}

        logger.info(f"Processing successful payment for user {telegram_user_id} via webhook.")
        logger.info(f"  Currency: {payment_info.get('currency')}")
        logger.info(f"  Total Amount: {payment_info.get('total_amount')}")
        logger.info(f"  Invoice Payload: {payment_info.get('invoice_payload')}")

        try:
            db_user = db.query(WebUser).filter(WebUser.telegram_id == telegram_user_id).first()
            if db_user:
                db_user.is_pro = True
                # Add subscription start/end date logic here if needed in future
                db.commit()
                logger.info(f"User {telegram_user_id} status updated to PRO via webhook.")
                # Optionally, send a message back to the user via the bot if this is the primary confirmation method
                # This would require having the bot client instance available here or an API call to the bot.
            else:
                logger.error(f"User {telegram_user_id} not found in DB after webhook payment.")
                # Still return 200 to Telegram, but this is an issue to investigate.
                return {"status": "error", "detail": "User not found in DB"}
        
        except Exception as e:
            db.rollback()
            logger.error(f"DB Error updating user {telegram_user_id} to PRO via webhook: {e}")
            # Consider raising HTTPException for server errors if Telegram should retry (not typical for this)
            return {"status": "error", "detail": "Database error"}
            
        return {"status": "ok", "message": "Payment processed"}
    
    logger.info("Webhook called with non-payment update or malformed data.")
    return {"status": "ignored", "detail": "Not a successful payment update"}
