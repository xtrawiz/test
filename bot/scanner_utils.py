import os
import ccxt.async_support as ccxt
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

# Assuming web.models and chart_utils are accessible
try:
    from web.models import Filter as DBFilter, User as DBUser # Renamed to avoid conflict
    from bot.chart_utils import fetch_historical_data, add_indicators, get_ccxt_exchange_client
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from web.models import Filter as DBFilter, User as DBUser
    from bot.chart_utils import fetch_historical_data, add_indicators, get_ccxt_exchange_client


load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DEFAULT_EXCHANGE_NAME = os.getenv("DEFAULT_EXCHANGE_NAME", "binance").lower()
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY") # For fetching markets if needed
EXCHANGE_SECRET_KEY = os.getenv("EXCHANGE_SECRET_KEY")

# --- Symbol Fetching ---
async def get_symbols_to_scan(filter_obj: DBFilter, exchange_name: str = DEFAULT_EXCHANGE_NAME) -> tuple[list[str] | None, str | None]:
    """
    Determines the list of symbols to scan.
    If filter_obj.symbols is set, use that.
    Otherwise, fetch top N (e.g., 20) USDT markets by volume from the exchange.
    Returns (list_of_symbols, error_message_if_any)
    """
    if filter_obj.symbols and isinstance(filter_obj.symbols, list) and len(filter_obj.symbols) > 0:
        return filter_obj.symbols, None

    # Fetch top N symbols (e.g., top 20 by volume with USDT as quote)
    exchange = await get_ccxt_exchange_client(exchange_name, EXCHANGE_API_KEY, EXCHANGE_SECRET_KEY)
    if not exchange:
        return None, f"خطا در اتصال به صرافی {exchange_name} برای دریافت لیست نمادها."
    
    try:
        markets = await exchange.load_markets()
        usdt_pairs = []
        for symbol, market_data in markets.items():
            if market_data.get('quote', '').upper() == 'USDT' and market_data.get('active', True):
                # CCXT often provides 'quoteVolume' or 'info' field for 24h volume
                volume = market_data.get('quoteVolume', 0)
                if not volume and market_data.get('info') and isinstance(market_data['info'], dict):
                    # Example for Binance-like structure, may need adjustment for others
                    volume = float(market_data['info'].get('quoteVolume', 0)) 
                usdt_pairs.append({'symbol': symbol, 'volume': volume})
        
        # Sort by volume in descending order and take top 20
        sorted_pairs = sorted(usdt_pairs, key=lambda x: x['volume'], reverse=True)
        top_symbols = [pair['symbol'] for pair in sorted_pairs[:20]] # Get top 20 symbols

        if not top_symbols:
            return None, "نمادی برای اسکن یافت نشد (لیست پیشفرض خالی است)."
        
        print(f"اسکن بر روی {len(top_symbols)} نماد برتر انجام می‌شود: {top_symbols}")
        return top_symbols, None

    except Exception as e:
        return None, f"خطا در دریافت لیست نمادهای پیشفرض از صرافی: {e}"
    finally:
        if exchange:
            await exchange.close()


# --- Condition Evaluation ---
def evaluate_condition(value, operator, condition_value_str) -> bool:
    """
    Evaluates a single condition.
    Example: value=25, operator='<', condition_value_str='30' -> True
    """
    try:
        condition_value = float(condition_value_str)
        if operator == '<':
            return value < condition_value
        elif operator == '<=':
            return value <= condition_value
        elif operator == '>':
            return value > condition_value
        elif operator == '>=':
            return value >= condition_value
        elif operator == '=' or operator == '==':
            # Using a small epsilon for float comparison might be better in some cases
            return value == condition_value 
        # Potentially add 'crosses', 'crosses_above', 'crosses_below' for two series later
        else:
            print(f"عملگر نامعتبر: {operator}")
            return False
    except ValueError:
        print(f"مقدار شرط نامعتبر: {condition_value_str}")
        return False

# --- Main Scanner Logic ---
async def run_single_filter(db_session, filter_obj: DBFilter, bot_client=None, user_telegram_id_override=None) -> tuple[list[str], str | None, str | None]:
    """
    Runs a single filter, evaluates conditions, and returns triggered symbols and a message.
    bot_client is the Pyrogram client, passed if a direct message needs to be sent.
    user_telegram_id_override is used by manual /scan run <id>
    Returns (triggered_symbols, formatted_message, error_message)
    """
    print(f"درحال اجرای اسکنر: {filter_obj.name} (ID: {filter_obj.id}) برای کاربر ID: {filter_obj.user_id}")
    
    symbols_to_scan, error_msg = await get_symbols_to_scan(filter_obj)
    if error_msg:
        return [], None, error_msg
    if not symbols_to_scan:
        return [], None, "هیچ نمادی برای اسکن مشخص نشده یا یافت نشد."

    triggered_symbols_details = []
    
    # Extract all unique indicator types and periods needed for this filter
    # Example param: {'indicator': 'RSI', 'period': 14, 'condition': '<', 'value': 30, 'output_key': 'rsi'}
    # Example param from UI: {'type': 'RSI', 'period': '14', 'condition': '<', 'value': '30'}
    
    indicators_needed_for_chart_utils = set()
    for cond_name, cond_details in filter_obj.params.items():
        # Assuming params structure is like: "RSI_14_<": 30 or a more structured dict
        # Let's assume a structured dict from our new UI:
        # params = { "condition_1": {'type': 'RSI', 'period': 14, 'operator': '<', 'value': 30}, ... }
        if isinstance(cond_details, dict) and 'type' in cond_details:
             indicators_needed_for_chart_utils.add(cond_details['type'].upper())


    for symbol in symbols_to_scan:
        print(f"  درحال بررسی نماد: {symbol} برای اسکنر {filter_obj.name}...")
        ohlcv_df, fetch_err = await fetch_historical_data(symbol, timeframe=filter_obj.timeframe, limit=150) # Fetch enough data for indicators
        if fetch_err:
            print(f"    خطا در دریافت اطلاعات OHLCV برای {symbol}: {fetch_err}")
            continue
        if ohlcv_df is None or ohlcv_df.empty:
            print(f"    اطلاعات OHLCV برای {symbol} خالی است.")
            continue

        # Calculate indicators based on what's defined in filter_obj.params
        # The add_indicators function expects a list like ['RSI', 'EMA']
        df_with_indicators = add_indicators(ohlcv_df, list(indicators_needed_for_chart_utils))
        if df_with_indicators.empty:
            print(f"    داده‌ای پس از افزودن اندیکاتورها برای {symbol} باقی نماند.")
            continue
        
        latest_data = df_with_indicators.iloc[-1] # Get the most recent row with indicators
        
        all_conditions_met = True
        symbol_trigger_reasons = []

        for cond_name, condition in filter_obj.params.items():
            # condition = {'type': 'RSI', 'period': 14, 'operator': '<', 'value': 30}
            indicator_type = condition.get('type', '').upper()
            period = int(condition.get('period', 0)) # Ensure period is int
            operator = condition.get('operator')
            target_value_str = str(condition.get('value')) # Ensure value is str for evaluate_condition

            current_indicator_value = None
            indicator_key_in_df = ""

            if indicator_type == 'RSI':
                indicator_key_in_df = 'rsi' # As defined in add_indicators
            elif indicator_type == 'EMA': # Assuming we care about a specific EMA, e.g., ema20
                # For simplicity, let's assume filter params will specify which EMA, e.g. 'EMA_20'
                # Or our add_indicators always adds 'ema20' if 'EMA' is requested.
                indicator_key_in_df = f'ema{period}' if period > 0 else 'ema20' # Default to ema20 if period not specified for EMA
                if indicator_key_in_df not in latest_data.index and 'ema20' in latest_data.index: # Fallback
                    indicator_key_in_df = 'ema20'

            # Add more indicator key mappings here (MACD, BBANDS etc.) if they are supported by filter params
            # e.g. if indicator_type == 'MACD': indicator_key_in_df = 'macd' (or 'macdsignal', 'macdhist')

            if indicator_key_in_df and indicator_key_in_df in latest_data:
                current_indicator_value = latest_data[indicator_key_in_df]
            else:
                print(f"    اندیکاتور {indicator_type} (کلید: {indicator_key_in_df}) برای {symbol} محاسبه نشده یا یافت نشد.")
                all_conditions_met = False
                break 

            if current_indicator_value is None: # Should be caught by above, but as a safeguard
                all_conditions_met = False
                break

            condition_met = evaluate_condition(current_indicator_value, operator, target_value_str)
            
            reason = f"{indicator_type}({period if period else ''})={current_indicator_value:.2f} {operator} {target_value_str}"
            if condition_met:
                symbol_trigger_reasons.append(f"✅ {reason}")
            else:
                symbol_trigger_reasons.append(f"❌ {reason}")
                all_conditions_met = False
                break # One condition failed, no need to check others for this symbol
        
        if all_conditions_met:
            print(f"    >>> نماد {symbol} با شرایط اسکنر {filter_obj.name} مطابقت دارد!")
            triggered_symbols_details.append({
                "symbol": symbol,
                "reasons": symbol_trigger_reasons,
                "latest_close": latest_data['close']
            })

    if not triggered_symbols_details:
        print(f"هیچ نمادی با شرایط اسکنر {filter_obj.name} مطابقت نداشت.")
        return [], None, None # No error, but no symbols triggered

    # Format message
    message_lines = [f"🔔 **نتایج اسکنر: {filter_obj.name}** (تایم فریم: {filter_obj.timeframe})\n"]
    for item in triggered_symbols_details:
        message_lines.append(f"📈 **نماد: {item['symbol']}** (قیمت فعلی: ${item['latest_close']:.2f})")
        for reason in item['reasons']:
            message_lines.append(f"   {reason}")
        message_lines.append("") # Add a blank line for readability

    formatted_message = "\n".join(message_lines)
    
    # Update last_triggered_at in DB
    try:
        filter_obj.last_triggered_at = datetime.now(timezone.utc)
        db_session.add(filter_obj)
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        print(f"خطا در بروزرسانی last_triggered_at برای اسکنر {filter_obj.id}: {e}")
        # Non-fatal, proceed with sending notification

    # Send notification via bot if client is provided
    if bot_client:
        # Fetch the user's telegram_id from the User model via filter_obj.user_id (which is User PK)
        user_to_notify = db_session.query(DBUser).filter(DBUser.id == filter_obj.user_id).first()
        if user_to_notify and user_to_notify.telegram_id:
            target_telegram_id = user_to_notify.telegram_id
            if user_telegram_id_override: # If manual run, send to the person who ran it
                target_telegram_id = user_telegram_id_override
            try:
                await bot_client.send_message(chat_id=target_telegram_id, text=formatted_message)
                print(f"پیام نتایج اسکنر {filter_obj.name} برای کاربر تلگرام {target_telegram_id} ارسال شد.")
            except Exception as e:
                print(f"خطا در ارسال پیام نتایج اسکنر برای کاربر تلگرام {target_telegram_id}: {e}")
        else:
            print(f"کاربر برای ارسال پیام نتایج اسکنر {filter_obj.name} یافت نشد (user_id: {filter_obj.user_id}).")


    return [item['symbol'] for item in triggered_symbols_details], formatted_message, None


# Placeholder for testing
# async def main_test():
#     from sqlalchemy import create_engine
#     from sqlalchemy.orm import sessionmaker
#     from web.models import Base
#     DATABASE_URL = os.getenv("DB_CONNECTION_STRING")
#     engine = create_engine(DATABASE_URL)
#     SessionLocalTest = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#     Base.metadata.create_all(bind=engine) # Ensure tables are created
#     db = SessionLocalTest()
    
#     # Create a dummy filter for testing
#     test_user = db.query(DBUser).first()
#     if not test_user:
#         print("No user found for testing, please create one.")
#         return

#     test_filter = DBFilter(
#         user_id=test_user.id,
#         name="Test RSI Low",
#         params={"condition_1": {"type": "RSI", "period": 14, "operator": "<", "value": 45}},
#         symbols=["BTC/USDT", "ETH/USDT"], # Small list for testing
#         # symbols=None, # To test default list fetching
#         timeframe='1h',
#         active=True
#     )
#     db.add(test_filter)
#     db.commit()
#     db.refresh(test_filter)
    
#     triggered, msg, err = await run_single_filter(db, test_filter)
#     if err:
#         print(f"Error running filter: {err}")
#     elif triggered:
#         print("Filter triggered for symbols:", triggered)
#         print("Message:\n", msg)
#     else:
#         print("Filter did not trigger for any symbols.")
    
#     db.delete(test_filter) # Clean up
#     db.commit()
#     db.close()

# if __name__ == "__main__":
# import asyncio
# asyncio.run(main_test())
