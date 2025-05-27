from sqlalchemy.orm import Session
from web.models import News # Assuming web.models is accessible
from web.schemas import NewsCreate # Assuming web.schemas is accessible
from typing import List, Optional
from datetime import datetime

def add_news_item_if_not_exists(db: Session, news_item: NewsCreate) -> Optional[News]:
    """
    Adds a news item to the database if it doesn't already exist (based on link).
    Returns the created News object or None if it already exists or an error occurs.
    """
    existing_news = db.query(News).filter(News.link == news_item.link).first()
    if existing_news:
        return None  # Already exists

    db_news = News(
        source=news_item.source,
        category=news_item.category,
        title=news_item.title,
        summary=news_item.summary,
        link=news_item.link,
        published_at=news_item.published_at
    )
    try:
        db.add(db_news)
        db.commit()
        db.refresh(db_news)
        return db_news
    except Exception as e:
        db.rollback()
        print(f"Error adding news item: {e}") # Basic error logging
        return None

def get_latest_news(db: Session, category: Optional[str] = None, limit: int = 5) -> List[News]:
    """
    Fetches the latest news items, optionally filtered by category.
    """
    query = db.query(News)
    if category:
        query = query.filter(News.category == category)
    
    return query.order_by(News.published_at.desc()).limit(limit).all()

def get_news_sources_from_env():
    """
    Placeholder function to get RSS feed URLs.
    In a real app, this would parse from os.getenv("RSS_FEEDS")
    """
    # Replace with actual environment variable parsing
    # For now, returning a fixed list for development
    return [
        {"url": "http://feeds.bbci.co.uk/news/technology/rss.xml", "category": "Technology", "source": "BBC Technology"},
        {"url": "https://feeds.reuters.com/reuters/technologyNews", "category": "Technology", "source": "Reuters Technology"},
        {"url": "http://www.varzesh3.com/rss/all", "category": "Sport", "source": "Varzesh3"},
    ]
