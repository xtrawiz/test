import os
import ccxt.async_support as ccxt # Use async version for Pyrogram
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Assuming web.models and web.schemas are accessible
# Adjust imports if your project structure is different or PYTHONPATH needs setup
try:
    from web.models import User, Portfolio
    from web.schemas import PortfolioCreate, PortfolioUpdate
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from web.models import User, Portfolio
    from web.schemas import PortfolioCreate, PortfolioUpdate

# Load environment variables from .env in the project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")
EXCHANGE_SECRET_KEY = os.getenv("EXCHANGE_SECRET_KEY")
# Default to Binance if not specified, ensure it's lowercase for ccxt
DEFAULT_EXCHANGE_NAME = os.getenv("DEFAULT_EXCHANGE_NAME", "binance").lower()


async def get_exchange_client(api_key: str, secret_key: str, exchange_name: str = DEFAULT_EXCHANGE_NAME):
    """
    Initializes and returns a CCXT exchange object.
    Handles potential errors during initialization.
    """
    try:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,  # Recommended by CCXT
            # 'options': {'defaultType': 'spot'} # Or 'future', 'margin' as needed
        })
        return exchange
    except AttributeError:
        print(f"خطا: صرافی '{exchange_name}' توسط CCXT پشتیبانی نمی‌شود یا نام آن اشتباه است.")
        return None
    except Exception as e:
        print(f"خطا در هنگام مقداردهی اولیه صرافی {exchange_name}: {e}")
        return None

async def fetch_balances_from_exchange(user_telegram_id: int, db: Session):
    """
    Fetches balances from the exchange using globally configured API keys.
    (Note: For production, per-user API keys are needed).
    Returns a dictionary of asset: amount.
    """
    if not EXCHANGE_API_KEY or not EXCHANGE_SECRET_KEY:
        print("هشدار: کلید API یا کلید مخفی صرافی در فایل .env تنظیم نشده است.")
        # For now, we can return dummy data or raise an error
        # In a real application, this would be a critical configuration issue.
        return {"error": "API_KEY_NOT_SET", "message": "کلید API یا کلید مخفی صرافی تنظیم نشده است."}
        # return {"BTC": 0.05, "ETH": 1.2, "USDT": 150.75} # Example dummy data

    exchange = await get_exchange_client(EXCHANGE_API_KEY, EXCHANGE_SECRET_KEY)
    if not exchange:
        return {"error": "EXCHANGE_INIT_FAILED", "message": "مقداردهی اولیه صرافی با مشکل مواجه شد."}

    try:
        # Test connectivity (optional, but good for early feedback)
        # await exchange.load_markets() # Loads markets, can be slow
        
        balance_data = await exchange.fetch_balance()
        
        # Filter out zero balances and structure the output
        # CCXT fetch_balance returns a complex structure; we need 'free' or 'total' balances
        # For simplicity, let's consider 'total' balances (free + used)
        filtered_balances = {}
        if 'total' in balance_data:
            for asset, amount in balance_data['total'].items():
                if amount > 0: # Only include assets with a positive balance
                    filtered_balances[asset.upper()] = amount
        else: # Fallback for exchanges that might not have 'total' directly structured this way
             for asset, details in balance_data.items():
                if isinstance(details, dict) and 'total' in details and details['total'] > 0:
                    filtered_balances[asset.upper()] = details['total']
                # Some exchanges might list assets directly with their total values
                elif isinstance(details, (float, int)) and details > 0 and asset not in ['info', 'free', 'used', 'total']:
                     filtered_balances[asset.upper()] = details


        if not filtered_balances and 'info' in balance_data and balance_data['info'].get('balances'):
             # Specific handling for Binance-like structures if 'total' is not directly available
            for item in balance_data['info']['balances']:
                asset = item['asset'].upper()
                total_balance = float(item['free']) + float(item['locked'])
                if total_balance > 0:
                    filtered_balances[asset] = total_balance
        
        return filtered_balances

    except ccxt.NetworkError as e:
        print(f"خطای شبکه هنگام دریافت موجودی: {e}")
        return {"error": "NETWORK_ERROR", "message": f"خطای شبکه: {e}"}
    except ccxt.ExchangeError as e: # Covers authentication, rate limits, etc.
        print(f"خطای صرافی هنگام دریافت موجودی: {e}")
        return {"error": "EXCHANGE_ERROR", "message": f"خطای صرافی: {e}"}
    except Exception as e:
        print(f"خطای ناشناخته هنگام دریافت موجودی: {e}")
        return {"error": "UNKNOWN_ERROR", "message": f"خطای ناشناخته: {e}"}
    finally:
        if exchange:
            await exchange.close()


def update_user_portfolio(db: Session, user_telegram_id: int, balances: dict, exchange_name: str = DEFAULT_EXCHANGE_NAME):
    """
    Updates the user's portfolio in the database with the fetched balances.
    """
    db_user = db.query(User).filter(User.telegram_id == user_telegram_id).first()
    if not db_user:
        print(f"کاربر با شناسه تلگرام {user_telegram_id} برای بروزرسانی پرتفوی یافت نشد.")
        return False # User not found

    exchange_name_upper = exchange_name.upper() # Store exchange name consistently

    try:
        current_db_assets = {
            p.asset: p for p in db.query(Portfolio).filter_by(user_id=db_user.id, exchange=exchange_name_upper).all()
        }
        
        updated_or_created_count = 0

        for asset_symbol, amount in balances.items():
            asset_symbol_upper = asset_symbol.upper()
            if asset_symbol_upper in current_db_assets:
                # Update existing asset
                portfolio_entry = current_db_assets[asset_symbol_upper]
                if portfolio_entry.amount != amount: # Only update if amount changed
                    portfolio_entry.amount = amount
                    # updated_at is handled by SQLAlchemy's default/onupdate
                    db.add(portfolio_entry)
                    updated_or_created_count +=1
            else:
                # Add new asset
                new_portfolio_entry = Portfolio(
                    user_id=db_user.id,
                    exchange=exchange_name_upper,
                    asset=asset_symbol_upper,
                    amount=amount
                )
                db.add(new_portfolio_entry)
                updated_or_created_count +=1
        
        # Optional: Mark assets no longer in balances but present in DB as amount 0
        # This might be desired to keep a record vs. deleting them
        assets_in_fetched_balances = {s.upper() for s in balances.keys()}
        for asset_in_db, entry in current_db_assets.items():
            if asset_in_db not in assets_in_fetched_balances:
                if entry.amount != 0: # Only update if it's not already zero
                    entry.amount = 0 
                    db.add(entry)
                    updated_or_created_count +=1
                    print(f"دارایی {asset_in_db} در صرافی {exchange_name_upper} برای کاربر {user_telegram_id} به صفر تغییر یافت.")

        if updated_or_created_count > 0:
            db.commit()
        print(f"پرتفوی کاربر {user_telegram_id} برای صرافی {exchange_name_upper} بروزرسانی شد. {updated_or_created_count} رکورد تغییر کرد.")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"خطا در بروزرسانی پرتفوی کاربر در پایگاه داده: {e}")
        return False

async def get_asset_price_in_usd(exchange, asset_symbol: str) -> float:
    """
    Fetches the current price of an asset in USD.
    Tries common quote currencies like USDT, USDC, BUSD.
    """
    if not exchange: return 0.0
    
    common_usd_quotes = ['USDT', 'USDC', 'BUSD', 'TUSD', 'DAI', 'USD']
    asset_symbol_upper = asset_symbol.upper()

    if asset_symbol_upper in common_usd_quotes: # Asset itself is a stablecoin
        return 1.0

    for quote in common_usd_quotes:
        try:
            ticker = f"{asset_symbol_upper}/{quote}"
            data = await exchange.fetch_ticker(ticker)
            if data and 'last' in data and data['last'] is not None:
                return float(data['last'])
        except ccxt.BadSymbol: # Pair doesn't exist
            continue
        except ccxt.NetworkError:
            print(f"خطای شبکه هنگام دریافت قیمت برای {ticker}")
            return 0.0 # Or raise, or retry
        except ccxt.ExchangeError:
            print(f"خطای صرافی هنگام دریافت قیمت برای {ticker}")
            return 0.0 # Or raise
        except Exception as e:
            print(f"خطای ناشناخته هنگام دریافت قیمت برای {ticker}: {e}")
            return 0.0 # Or raise
    
    print(f"قیمت USD برای {asset_symbol_upper} یافت نشد.")
    return 0.0 # Could not find price against any common USD quote

# Example usage (for testing, can be removed or put under if __name__ == "__main__":)
async def main_test():
    # This is a placeholder for testing; direct execution would require a DB session
    # and proper async handling if called from a synchronous context.
    print("برای تست مستقیم این ماژول، به یک session دیتابیس و اجرای async نیاز است.")
    # client = await get_exchange_client(EXCHANGE_API_KEY, EXCHANGE_SECRET_KEY)
    # if client:
    #     balances = await fetch_balances_from_exchange(12345) # Dummy telegram_id
    #     print("Balances:", balances)
    #     # In a real scenario, you'd get a db session here
    #     # update_user_portfolio(db_session, 12345, balances)
    #     await client.close()

# if __name__ == "__main__":
# import asyncio
# asyncio.run(main_test())
