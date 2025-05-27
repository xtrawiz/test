import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

# Assuming crypto_bot is in PYTHONPATH or installed
# If running directly, sys.path manipulation might be needed for imports from core
# For Docker, this should work as /app will be the working directory
try:
    from core.settings.config import settings
except ModuleNotFoundError:
    # This is a fallback if 'core' is not in sys.path,
    # which can happen if you run 'python bot/main.py' directly without installing the package.
    # For dockerized execution where WORKDIR is /app, 'from core...' should work.
    import sys
    import os
    # Add the parent directory of 'bot' to sys.path, which should be 'crypto_bot'
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from core.settings.config import settings


# Configure basic logging
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create a Pyrogram Client instance
app = Client(
    name="crypto_bot",
    api_id=settings.API_ID,
    api_hash=settings.API_HASH,
    bot_token=settings.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)

# Simple health check handler for /start command (will be overridden by plugin)
@app.on_message(filters.command("health"))
async def health_check(client: Client, message: Message):
    await message.reply_text("Bot is running healthily!")

async def main():
    logger.info("Starting bot...")
    await app.start()
    logger.info("Bot started. Idling...")
    await asyncio.Event().wait()  # Keep the bot running until interrupted
    logger.info("Stopping bot...")
    await app.stop()
    logger.info("Bot stopped.")

if __name__ == "__main__":
    # Example environment variables (replace with your actual values or use a .env file)
    # These are usually set in the docker-compose.yml or environment for production
    import os
    os.environ.setdefault("API_ID", "12345") # Replace with your API_ID
    os.environ.setdefault("API_HASH", "your_api_hash") # Replace with your API_HASH
    os.environ.setdefault("BOT_TOKEN", "your_bot_token") # Replace with your BOT_TOKEN
    os.environ.setdefault("DATABASE_URL", "mysql+aiomysql://user:pass@host:port/db_name")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("LOG_LEVEL", "INFO")

    # Re-initialize settings if environment variables were set after initial import
    # This is more of a safeguard for direct script execution outside Docker
    settings.API_ID = int(os.environ["API_ID"])
    settings.API_HASH = os.environ["API_HASH"]
    settings.BOT_TOKEN = os.environ["BOT_TOKEN"]
    settings.DATABASE_URL = os.environ["DATABASE_URL"]
    settings.REDIS_URL = os.environ["REDIS_URL"]
    settings.LOG_LEVEL = os.environ["LOG_LEVEL"]
    
    # Update logger level based on potentially updated settings
    logging.getLogger().setLevel(settings.LOG_LEVEL.upper())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
