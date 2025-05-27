import os
import ccxt.async_support as ccxt
import pandas as pd
import talib
import io
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
import matplotlib.pyplot as plt # For style and some date functionalities
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from .env in the project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")
EXCHANGE_SECRET_KEY = os.getenv("EXCHANGE_SECRET_KEY")
DEFAULT_EXCHANGE_NAME = os.getenv("DEFAULT_EXCHANGE_NAME", "binance").lower()

# --- Exchange Client ---
async def get_ccxt_exchange_client(exchange_name: str = DEFAULT_EXCHANGE_NAME, api_key: str = None, secret_key: str = None):
    """
    Initializes and returns a CCXT exchange object.
    Uses provided API keys or global ones if available and exchange requires them for OHLCV.
    Many exchanges provide OHLCV data without API keys.
    """
    try:
        exchange_class = getattr(ccxt, exchange_name)
        params = {'enableRateLimit': True}
        if api_key and secret_key: # Use keys if provided (and exchange supports/requires them for endpoint)
            params['apiKey'] = api_key
            params['secret'] = secret_key
        
        exchange = exchange_class(params)
        return exchange
    except AttributeError:
        print(f"Error: Exchange '{exchange_name}' is not supported by CCXT or name is incorrect.")
        return None
    except Exception as e:
        print(f"Error initializing exchange {exchange_name}: {e}")
        return None

# --- Historical Data Fetching ---
async def fetch_historical_data(symbol: str, timeframe: str = '1d', limit: int = 100, exchange_name: str = DEFAULT_EXCHANGE_NAME):
    """
    Fetches OHLCV data and converts it to a Pandas DataFrame.
    """
    exchange = await get_ccxt_exchange_client(exchange_name, EXCHANGE_API_KEY, EXCHANGE_SECRET_KEY) # Pass global keys
    if not exchange:
        return None, f"خطا در اتصال به صرافی {exchange_name}."

    try:
        if not exchange.has['fetchOHLCV']:
            await exchange.close()
            return None, f"صرافی {exchange_name} از دریافت اطلاعات OHLCV پشتیبانی نمی‌کند."

        # Fetch OHLCV data
        # CCXT returns: [timestamp, open, high, low, close, volume]
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if not ohlcv:
            await exchange.close()
            return None, f"اطلاعاتی برای نماد {symbol} با تایم‌فریم {timeframe} یافت نشد."

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True) # Convert to datetime
        df.set_index('timestamp', inplace=True) # Set timestamp as index for easier plotting
        
        # Ensure data types are correct for TA-Lib
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(inplace=True) # Drop rows with NaN values that might result from coercion
        
        if df.empty:
             return None, f"پس از پردازش، اطلاعات معتبری برای نماد {symbol} یافت نشد."

        return df, None # Return DataFrame and no error message

    except ccxt.BadSymbol:
        return None, f"نماد '{symbol}' در صرافی {exchange_name} یافت نشد."
    except ccxt.NetworkError as e:
        return None, f"خطای شبکه هنگام دریافت اطلاعات: {e}"
    except ccxt.ExchangeError as e:
        return None, f"خطای صرافی هنگام دریافت اطلاعات: {e}"
    except Exception as e:
        return None, f"خطای ناشناخته: {e}"
    finally:
        if exchange:
            await exchange.close()

# --- Indicator Calculation ---
def add_indicators(df: pd.DataFrame, indicators_requested: list = None):
    """
    Calculates requested technical indicators and adds them to the DataFrame.
    """
    if indicators_requested is None:
        indicators_requested = ['RSI', 'EMA'] # Default indicators

    df_with_indicators = df.copy()

    if 'RSI' in indicators_requested:
        df_with_indicators['rsi'] = talib.RSI(df_with_indicators['close'], timeperiod=14)
    
    if 'EMA' in indicators_requested: # Example: EMA20
        df_with_indicators['ema20'] = talib.EMA(df_with_indicators['close'], timeperiod=20)
        # You can add more EMAs, e.g., EMA50
        # df_with_indicators['ema50'] = talib.EMA(df_with_indicators['close'], timeperiod=50)

    if 'MACD' in indicators_requested:
        # MACD returns macd, macdsignal, macdhist
        macd, macdsignal, macdhist = talib.MACD(df_with_indicators['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        df_with_indicators['macd'] = macd
        df_with_indicators['macdsignal'] = macdsignal
        # df_with_indicators['macdhist'] = macdhist # Usually plotted as histogram

    if 'BBANDS' in indicators_requested:
        upper, middle, lower = talib.BBANDS(df_with_indicators['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df_with_indicators['bb_upper'] = upper
        df_with_indicators['bb_middle'] = middle
        df_with_indicators['bb_lower'] = lower
        
    df_with_indicators.dropna(inplace=True) # Indicators might create NaNs at the beginning
    return df_with_indicators

# --- SVG Chart Generation ---
def generate_price_chart_svg(df: pd.DataFrame, symbol: str, indicators_to_plot: list = None):
    """
    Generates an SVG price chart with specified indicators.
    """
    if indicators_to_plot is None:
        indicators_to_plot = ['RSI', 'EMA']

    plt.style.use('seaborn-v0_8-darkgrid') # Using a seaborn style for better aesthetics

    num_subplots = 1
    if 'RSI' in indicators_to_plot and 'rsi' in df.columns:
        num_subplots += 1
    if 'MACD' in indicators_to_plot and 'macd' in df.columns and 'macdsignal' in df.columns:
        num_subplots +=1

    fig = Figure(figsize=(12, 2 * num_subplots + 4), dpi=100) # Adjust size based on subplots
    # fig.patch.set_facecolor('#f0f0f0') # Light gray background for the figure
    
    current_subplot_index = 0
    gs_rows = num_subplots * 2 # Define grid spec rows, e.g. 2 for price, 1 for RSI, 1 for MACD
    
    # Main Price Plot
    current_subplot_index +=1
    ax_price = fig.add_subplot(num_subplots, 1, current_subplot_index) # Price chart takes more space
    
    ax_price.plot(df.index, df['close'], label=f'{symbol} قیمت', color='cyan', linewidth=1.5)
    
    if 'EMA' in indicators_to_plot and 'ema20' in df.columns:
        ax_price.plot(df.index, df['ema20'], label='EMA (20)', color='orange', linestyle='--', linewidth=1)
    if 'BBANDS' in indicators_to_plot and 'bb_upper' in df.columns:
        ax_price.plot(df.index, df['bb_upper'], label='باند بالایی بولینگر', color='lightgray', linestyle=':', linewidth=0.8)
        ax_price.plot(df.index, df['bb_middle'], label='باند میانی بولینگر', color='lightgray', linestyle='-.', linewidth=0.8)
        ax_price.plot(df.index, df['bb_lower'], label='باند پایینی بولینگر', color='lightgray', linestyle=':', linewidth=0.8)
        ax_price.fill_between(df.index, df['bb_upper'], df['bb_lower'], color='silver', alpha=0.1)


    ax_price.set_title(f"نمودار قیمت و اندیکاتورها برای {symbol}", fontsize=14, color='white')
    ax_price.set_ylabel("قیمت", fontsize=10, color='white')
    ax_price.legend(loc='upper left', fontsize=8)
    ax_price.tick_params(axis='x', colors='lightgray', labelsize=8)
    ax_price.tick_params(axis='y', colors='lightgray', labelsize=8)
    ax_price.grid(True, linestyle='--', alpha=0.5)
    ax_price.set_facecolor('#1e1e1e') # Dark background for price chart

    # RSI Subplot
    if 'RSI' in indicators_to_plot and 'rsi' in df.columns:
        current_subplot_index +=1
        ax_rsi = fig.add_subplot(num_subplots, 1, current_subplot_index, sharex=ax_price) # Share X-axis with price
        ax_rsi.plot(df.index, df['rsi'], label='RSI (14)', color='magenta', linewidth=1)
        ax_rsi.axhline(70, color='red', linestyle='--', linewidth=0.7, label='اشباع خرید (70)')
        ax_rsi.axhline(30, color='green', linestyle='--', linewidth=0.7, label='اشباع فروش (30)')
        ax_rsi.set_ylabel("RSI", fontsize=10, color='white')
        ax_rsi.legend(loc='lower left', fontsize=8)
        ax_rsi.tick_params(axis='x', colors='lightgray', labelsize=8)
        ax_rsi.tick_params(axis='y', colors='lightgray', labelsize=8)
        ax_rsi.grid(True, linestyle='--', alpha=0.3)
        ax_rsi.set_facecolor('#2a2a2a') # Slightly different dark background

    # MACD Subplot
    if 'MACD' in indicators_to_plot and 'macd' in df.columns and 'macdsignal' in df.columns:
        current_subplot_index +=1
        ax_macd = fig.add_subplot(num_subplots, 1, current_subplot_index, sharex=ax_price) # Share X-axis
        ax_macd.plot(df.index, df['macd'], label='MACD', color='blue', linewidth=1)
        ax_macd.plot(df.index, df['macdsignal'], label='Signal Line', color='red', linestyle='--', linewidth=1)
        # Optional: Plot MACD histogram if you have df['macdhist']
        # ax_macd.bar(df.index, df['macdhist'], label='Histogram', color='gray', alpha=0.5, width=0.05) # Adjust width
        ax_macd.set_ylabel("MACD", fontsize=10, color='white')
        ax_macd.legend(loc='lower left', fontsize=8)
        ax_macd.tick_params(axis='x', colors='lightgray', labelsize=8)
        ax_macd.tick_params(axis='y', colors='lightgray', labelsize=8)
        ax_macd.grid(True, linestyle='--', alpha=0.3)
        ax_macd.set_facecolor('#2a2a2a')

    fig.autofmt_xdate() # Auto-format date labels for better readability
    fig.tight_layout(pad=1.5) # Adjust layout to prevent overlap
    fig.patch.set_facecolor('#121212') # Overall figure background

    # Save to SVG
    svg_io = io.BytesIO()
    canvas = FigureCanvasSVG(fig)
    canvas.print_svg(svg_io)
    plt.close(fig) # Close the figure to free up memory
    return svg_io.getvalue()

# Example usage (for testing)
async def _test_chart_generation():
    symbol = 'BTC/USDT'
    print(f"Fetching data for {symbol}...")
    df, error = await fetch_historical_data(symbol, timeframe='1d', limit=100)
    if error:
        print(f"Error fetching data: {error}")
        return
    if df is None or df.empty:
        print("No data fetched.")
        return
        
    print("Data fetched. Adding indicators...")
    # df_with_indicators = add_indicators(df, indicators_requested=['RSI', 'EMA', 'MACD', 'BBANDS'])
    df_with_indicators = add_indicators(df, indicators_requested=['RSI', 'EMA'])
    print("Indicators added. Generating chart...")
    print(df_with_indicators.tail())
    
    svg_bytes = generate_price_chart_svg(df_with_indicators, symbol, indicators_to_plot=['RSI', 'EMA'])
    
    with open(f"{symbol.replace('/', '_')}_chart.svg", "wb") as f:
        f.write(svg_bytes)
    print(f"Chart saved as {symbol.replace('/', '_')}_chart.svg")

# if __name__ == "__main__":
# import asyncio
# asyncio.run(_test_chart_generation())
