from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from sqlalchemy import Text, JSON, ForeignKey, Float, UniqueConstraint # Import Text, JSON, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import relationship # Import relationship
import uuid
from datetime import datetime # Import datetime for default value

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    language = Column(String(10), default='fa')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_pro = Column(Boolean, default=False)
    api_key = Column(String(255), unique=True, nullable=True, default=lambda: str(uuid.uuid4()))
    calculations = relationship("Calculation", back_populates="user")
    portfolios = relationship("Portfolio", back_populates="user")
    filters = relationship("Filter", back_populates="user") # Added filter relationship

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source = Column(String(255), nullable=False)
    category = Column(String(255), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    link = Column(String(500), unique=True, nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<News(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"

class Calculation(Base):
    __tablename__ = "calculations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False, index=True) # e.g., 'profit', 'convert', 'margin', 'whatif'
    input_params = Column(JSON, nullable=False)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="calculations")

    def __repr__(self):
        return f"<Calculation(id={self.id}, type='{self.type}', user_id={self.user_id})>"

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exchange = Column(String(100), nullable=False)
    asset = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="portfolios")

    __table_args__ = (UniqueConstraint('user_id', 'exchange', 'asset', name='_user_exchange_asset_uc'),)

    def __repr__(self):
        return f"<Portfolio(id={self.id}, user_id={self.user_id}, exchange='{self.exchange}', asset='{self.asset}', amount={self.amount})>"

class Filter(Base):
    __tablename__ = "filters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    params = Column(JSON, nullable=False) # e.g., {'RSI_14_value': '<30', 'VOLUME_24h_usd': '>100000'}
    symbols = Column(JSON, nullable=True) # List of symbols or null for default (e.g., top N)
    timeframe = Column(String(10), nullable=False) # e.g., '1h', '4h', '1d'
    active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


    user = relationship("User", back_populates="filters")

    def __repr__(self):
        return f"<Filter(id={self.id}, name='{self.name}', user_id={self.user_id}, active={self.active})>"
