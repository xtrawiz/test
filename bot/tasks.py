import os
import feedparser
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone # Ensure timezone is imported
from dotenv import load_dotenv

# Assuming web.models and web.schemas are in the parent directory of bot,
# or the PYTHONPATH is set up accordingly for Celery to find them.
# Adjust these imports if your project structure is different.
try:
    from web.models import News, Base as WebBase
    from web.schemas import NewsCreate
except ImportError:
    # This is a fallback for local execution if PYTHONPATH isn't set
    # You might need to adjust this based on your exact execution environment for Celery
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from web.models import News, Base as WebBase
    from web.schemas import NewsCreate

from bot.news_utils import add_news_item_if_not_exists, get_news_sources_from_env

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env')) # Ensure .env is loaded from project root

# Celery Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

celery_app = Celery(
    "tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['bot.tasks'] # Crucial for Celery to find the tasks module
)

# Database Setup
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")
if not DB_CONNECTION_STRING:
    raise ValueError("DB_CONNECTION_STRING environment variable not set for Celery tasks")

engine = create_engine(DB_CONNECTION_STRING)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist
# This is important for Celery workers that might start independently of the web app
WebBase.metadata.create_all(bind=engine)


@celery_app.task(name='bot.tasks.fetch_news_task')
def fetch_news_task():
    db = SessionLocal()
    rss_feeds = get_news_sources_from_env() # Using the function from news_utils
    new_items_count = 0
    processed_links = set()

    for feed_info in rss_feeds:
        feed_url = feed_info["url"]
        category = feed_info.get("category", "General")
        source_name = feed_info.get("source", feed_url)

        print(f"Fetching news from: {feed_url} for category: {category}")
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                if entry.link in processed_links:
                    continue

                published_dt = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published_dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                else:
                    published_dt = datetime.now(timezone.utc)

                summary = entry.summary if hasattr(entry, 'summary') else ''
                if hasattr(entry, 'description') and not summary: # Some feeds use description instead of summary
                    summary = entry.description


                news_data = NewsCreate(
                    source=source_name,
                    category=category,
                    title=entry.title,
                    summary=summary,
                    link=entry.link,
                    published_at=published_dt
                )
                
                added_news = add_news_item_if_not_exists(db, news_data)
                if added_news:
                    new_items_count += 1
                    processed_links.add(entry.link)

        except Exception as e:
            print(f"Error fetching or processing feed {feed_url}: {e}")
    
    db.close()
    summary_message = f"Fetched {new_items_count} new news items."
    print(summary_message)
    return summary_message

celery_app.conf.beat_schedule = {
    'fetch-news-every-30-minutes': {
        'task': 'bot.tasks.fetch_news_task',
        'schedule': 1800.0,  # 30 minutes
    },
}
celery_app.conf.timezone = 'UTC'

# For running worker directly (development/testing)
if __name__ == '__main__':
    # This allows running the worker directly for development/testing
    # For production, use the celery command through docker-compose
    # Example: celery -A bot.tasks worker -l info -B (to run beat scheduler within the same process for dev)
    celery_app.worker_main(argv=['worker', '-l', 'info'])
