from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    language: str = 'fa'
    is_pro: bool = False

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: Optional[str] = None
    is_pro: Optional[bool] = None

class User(UserBase):
    id: int
    created_at: datetime
    api_key: Optional[str] = None

    class Config:
        orm_mode = True

# Filter Schemas
class FilterBase(BaseModel):
    name: str
    params: dict # Example: {'RSI_14_value': '<30', 'VOLUME_24h_usd': '>100000'}
    symbols: Optional[list[str]] = None # List of symbols or None for default
    timeframe: str # e.g., '1h', '4h', '1d'
    active: bool = True

class FilterCreate(FilterBase):
    user_id: int # Required when creating directly via API or for internal linking

class FilterUpdate(BaseModel):
    name: Optional[str] = None
    params: Optional[dict] = None
    symbols: Optional[list[str]] = None
    timeframe: Optional[str] = None
    active: Optional[bool] = None

class Filter(FilterBase):
    id: int
    user_id: int
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Portfolio Schemas
class PortfolioBase(BaseModel):
    exchange: str
    asset: str
    amount: float

class PortfolioCreate(PortfolioBase):
    user_id: int # Required when creating directly

class PortfolioUpdate(BaseModel):
    amount: Optional[float] = None

class Portfolio(PortfolioBase):
    id: int
    user_id: int
    updated_at: datetime

    class Config:
        orm_mode = True

# Calculation Schemas
class CalculationBase(BaseModel):
    type: str
    input_params: dict
    result: dict

class CalculationCreate(CalculationBase):
    user_id: int # Required for creating a calculation linked to a user

class Calculation(CalculationBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True

# News Schemas
class NewsBase(BaseModel):
    source: str
    category: Optional[str] = None
    title: str
    summary: Optional[str] = None
    link: str
    published_at: datetime

class NewsCreate(NewsBase):
    pass

class News(NewsBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
