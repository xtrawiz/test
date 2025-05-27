import os
from pyrogram import Client, filters
from pyrogram.types import Message
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")

if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, DB_CONNECTION_STRING]):
    raise ValueError("One or more environment variables are not set. Please check your .env file or environment.")

# SQLAlchemy User Model (consistent with web/models.py)
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

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"

# Database setup for the bot
engine = create_engine(DB_CONNECTION_STRING)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    return SessionLocal()

from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton # Added CallbackQuery
from bot.news_utils import get_latest_news
from web.models import News as WebNews, User as WebUser, Calculation as WebCalculation # Added User and Calculation models
from web.schemas import CalculationCreate # Added CalculationCreate schema
from bot.keyboards import get_calculator_menu_keyboard, get_currency_selection_keyboard, get_position_type_keyboard
from bot.calculators import (
    calculate_profit_loss,
    convert_currency,
    calculate_margin,
    calculate_whatif,
    get_supported_currencies
)
from pyrogram.errors import TimeoutError
from bot.portfolio_utils import (
    fetch_balances_from_exchange, 
    update_user_portfolio, 
    get_asset_price_in_usd,
    get_exchange_client as get_portfolio_exchange_client # Renamed to avoid conflict
)
from bot.chart_utils import (
    fetch_historical_data,
    add_indicators,
    generate_price_chart_svg
)
import io # For BytesIO
from bot.scheduler import (
    start_scheduler, 
    shutdown_scheduler, 
    schedule_filter_job, 
    remove_filter_job,
    load_active_filters_on_startup
)
from bot.keyboards import (
    get_scanner_main_menu_keyboard,
    get_scanner_timeframe_keyboard,
    get_scanner_symbols_type_keyboard,
    get_scanner_condition_indicator_keyboard,
    get_scanner_condition_operator_keyboard,
    get_scanner_add_another_condition_keyboard,
    get_user_filters_list_keyboard,
    get_single_filter_manage_keyboard
)
from web.models import Filter as DBFilter # Import the DB model
from web.schemas import FilterCreate as SchemaFilterCreate # For creating filter instances
from sqlalchemy.exc import IntegrityError
from bot.scanner_utils import run_single_filter as run_manual_scan # For manual runs

from pyrogram.types import LabeledPrice, PreCheckoutQuery # Added for payments

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
USD_TOMAN_RATE = float(os.getenv("USD_TOMAN_RATE", "50000.0"))
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")
EXCHANGE_SECRET_KEY = os.getenv("EXCHANGE_SECRET_KEY")
DEFAULT_EXCHANGE_NAME = os.getenv("DEFAULT_EXCHANGE_NAME", "binance").lower()
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBotUsername") # Used for payload

# Payment Specific Environment Variables
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
PRO_SUBSCRIPTION_PRICE_CENTS = int(os.getenv("PRO_SUBSCRIPTION_PRICE_USD", "1000")) # e.g., 1000 for $10.00
PRO_SUBSCRIPTION_CURRENCY = os.getenv("PRO_SUBSCRIPTION_CURRENCY", "USD")


# Initialize Pyrogram Client
app = Client("my_bot", api_id=int(TELEGRAM_API_ID), api_hash=TELEGRAM_API_HASH, bot_token=TELEGRAM_BOT_TOKEN)

# In-memory store for conversation state (simple approach)
# For production, consider a more robust solution like Redis
conversation_state = {}

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user = message.from_user
    telegram_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    db = get_db_session()
    try:
        db_user = db.query(User).filter(User.telegram_id == telegram_id).first()

        if db_user:
            welcome_message = f"سلام {first_name}! خوش آمدید، به ربات کریپتو بازگشتید."
        else:
            new_user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
                # api_key will be generated by default
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            welcome_message = f"سلام {first_name}! به ربات کریپتو خوش آمدید!"
        
        await message.reply_text(welcome_message)

    except Exception as e:
        # Log error
        print(f"Error in /start command: {e}")
        await message.reply_text("متاسفانه مشکلی پیش آمده است. لطفا بعدا دوباره تلاش کنید.")
    finally:
        db.close()

@app.on_message(filters.command("news"))
async def news_command(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    category = args[1] if len(args) > 1 else None

    db = get_db_session()
    try:
        if category:
            latest_news_items = get_latest_news(db, category=category, limit=5)
        else:
            latest_news_items = get_latest_news(db, limit=5)

        if not latest_news_items:
            await message.reply_text("در حال حاضر خبری برای نمایش در این دسته بندی وجود ندارد." if category else "در حال حاضر خبری برای نمایش وجود ندارد.")
            return

        response_message = "آخرین اخبار:\n\n"
        for item in latest_news_items:
            response_message += f"**{item.title}**\n"
            if item.summary:
                summary_snippet = item.summary[:100] + "..." if len(item.summary) > 100 else item.summary
                response_message += f"{summary_snippet}\n"
            response_message += f"*منبع: {item.source}*\n"
            response_message += f"[لینک خبر]({item.link})\n\n"
        
        await message.reply_text(response_message, disable_web_page_preview=True)

    except Exception as e:
        print(f"Error in /news command: {e}")
        await message.reply_text("متاسفانه مشکلی در دریافت اخبار پیش آمده است. لطفا بعدا دوباره تلاش کنید.")
    finally:
        db.close()

# --- Helper function to save calculation ---
def save_calculation_to_db(user_id: int, calc_type: str, inputs: dict, outputs: dict):
    db = get_db_session()
    try:
        # Get the main User ID from telegram_id
        db_user = db.query(WebUser).filter(WebUser.telegram_id == user_id).first()
        if not db_user:
            print(f"User with telegram_id {user_id} not found in DB for saving calculation.")
            # Optionally create the user if they somehow don't exist yet, or handle error
            return

        calculation_entry = WebCalculation(
            user_id=db_user.id, # Use the User table's primary key
            type=calc_type,
            input_params=inputs,
            result=outputs
        )
        db.add(calculation_entry)
        db.commit()
        print(f"Calculation saved for user_id {db_user.id}, type {calc_type}")
    except Exception as e:
        db.rollback()
        print(f"Error saving calculation to DB: {e}")
    finally:
        db.close()

# --- Calculator Command and Callbacks ---
@app.on_message(filters.command("calc"))
async def calc_command_handler(client: Client, message: Message):
    await message.reply_text(
        "کدام ماشین حساب را نیاز دارید؟",
        reply_markup=get_calculator_menu_keyboard()
    )

# Generic input prompt function
async def ask_for_input(client: Client, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup = None, state_key_suffix: str = "") -> Message:
    question_message = await client.send_message(chat_id, text, reply_markup=reply_markup)
    try:
        response = await client.listen(chat_id=chat_id, user_id=chat_id, timeout=300) # 5 minutes timeout
        # Store message IDs for potential cleanup
        conversation_state[chat_id] = conversation_state.get(chat_id, {})
        conversation_state[chat_id][f'question_msg_id_{state_key_suffix}'] = question_message.id
        conversation_state[chat_id][f'response_msg_id_{state_key_suffix}'] = response.id
        return response
    except TimeoutError:
        await client.send_message(chat_id, "زمان پاسخگویی به پایان رسید. لطفا دوباره تلاش کنید.")
        return None

async def cleanup_conversation_messages(client: Client, chat_id: int):
    if chat_id in conversation_state:
        messages_to_delete = []
        for key, msg_id in conversation_state[chat_id].items():
            if key.startswith('question_msg_id_') or key.startswith('response_msg_id_'):
                messages_to_delete.append(msg_id)
        
        if messages_to_delete:
            try:
                await client.delete_messages(chat_id, messages_to_delete)
            except Exception as e:
                print(f"Error deleting conversation messages: {e}")
        del conversation_state[chat_id]


@app.on_callback_query(filters.regex("^calc_"))
async def calculator_callback_handler(client: Client, callback_query: CallbackQuery):
    action = callback_query.data
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id # This is telegram_id

    await callback_query.answer() # Acknowledge callback

    if action == "calc_profit":
        try:
            buy_price_msg = await ask_for_input(client, chat_id, "لطفا قیمت خرید را وارد کنید:", state_key_suffix="buyprice")
            if not buy_price_msg: return
            buy_price = float(buy_price_msg.text)

            sell_price_msg = await ask_for_input(client, chat_id, "لطفا قیمت فروش را وارد کنید:", state_key_suffix="sellprice")
            if not sell_price_msg: return
            sell_price = float(sell_price_msg.text)

            quantity_msg = await ask_for_input(client, chat_id, "لطفا مقدار را وارد کنید:", state_key_suffix="quantity")
            if not quantity_msg: return
            quantity = float(quantity_msg.text)

            inputs = {"buy_price": buy_price, "sell_price": sell_price, "quantity": quantity}
            result = calculate_profit_loss(**inputs)
            
            response_text = (
                f"ماشین حساب سود/زیان:\n\n"
                f"سود/زیان: {result['profit_or_loss_amount']:.2f}\n"
                f"درصد سود/زیان: {result['profit_or_loss_percentage']:.2f}%\n\n"
                f"جزئیات:\n"
                f"قیمت خرید: {buy_price}\n"
                f"قیمت فروش: {sell_price}\n"
                f"مقدار: {quantity}"
            )
            await client.send_message(chat_id, response_text)
            save_calculation_to_db(user_id, "profit_loss", inputs, result)
            await cleanup_conversation_messages(client, chat_id)

        except ValueError:
            await client.send_message(chat_id, "ورودی نامعتبر است. لطفا فقط عدد وارد کنید.")
        except Exception as e:
            await client.send_message(chat_id, f"خطایی رخ داد: {e}")
            print(f"Error in calc_profit: {e}")

    elif action == "calc_convert":
        conversation_state[chat_id] = {"type": "convert"}
        await client.send_message(chat_id, "واحد پولی مبدا را انتخاب کنید:", reply_markup=get_currency_selection_keyboard(get_supported_currencies(), "from"))
    
    elif action == "calc_convert_help":
        currencies = get_supported_currencies()
        help_text = "جفت ارزهای پشتیبانی شده برای تبدیل:\n\n"
        for code, name in currencies.items():
            help_text += f"- {name} ({code.replace('_', ' به ')})\n"
        await client.send_message(chat_id, help_text)


    elif action == "calc_margin":
        conversation_state[chat_id] = {"type": "margin"}
        entry_price_msg = await ask_for_input(client, chat_id, "لطفا قیمت ورود را وارد کنید:", state_key_suffix="entryprice_margin")
        if not entry_price_msg: return
        try:
            conversation_state[chat_id]['entry_price'] = float(entry_price_msg.text)
        except ValueError:
            await client.send_message(chat_id, "قیمت ورود نامعتبر است. لطفا عدد وارد کنید.")
            return
        
        exit_price_msg = await ask_for_input(client, chat_id, "لطفا قیمت خروج را وارد کنید:", state_key_suffix="exitprice_margin")
        if not exit_price_msg: return
        try:
            conversation_state[chat_id]['exit_price'] = float(exit_price_msg.text)
        except ValueError:
            await client.send_message(chat_id, "قیمت خروج نامعتبر است. لطفا عدد وارد کنید.")
            return

        quantity_msg = await ask_for_input(client, chat_id, "لطفا مقدار را وارد کنید:", state_key_suffix="quantity_margin")
        if not quantity_msg: return
        try:
            conversation_state[chat_id]['quantity'] = float(quantity_msg.text)
        except ValueError:
            await client.send_message(chat_id, "مقدار نامعتبر است. لطفا عدد وارد کنید.")
            return
        
        leverage_msg = await ask_for_input(client, chat_id, "لطفا اهرم (leverage) را وارد کنید (مثلا 5، 10):", state_key_suffix="leverage_margin")
        if not leverage_msg: return
        try:
            conversation_state[chat_id]['leverage'] = float(leverage_msg.text)
        except ValueError:
            await client.send_message(chat_id, "اهرم نامعتبر است. لطفا عدد وارد کنید.")
            return

        await client.send_message(chat_id, "نوع پوزیشن خود را انتخاب کنید (لانگ یا شورت):", reply_markup=get_position_type_keyboard())


    elif action == "calc_whatif":
        try:
            initial_investment_msg = await ask_for_input(client, chat_id, "لطفا مبلغ سرمایه‌گذاری اولیه را وارد کنید:", state_key_suffix="invest_whatif")
            if not initial_investment_msg: return
            initial_investment = float(initial_investment_msg.text)

            current_price_msg = await ask_for_input(client, chat_id, "لطفا قیمت فعلی دارایی را وارد کنید:", state_key_suffix="current_whatif")
            if not current_price_msg: return
            current_price = float(current_price_msg.text)

            target_price_msg = await ask_for_input(client, chat_id, "لطفا قیمت هدف دارایی را وارد کنید:", state_key_suffix="target_whatif")
            if not target_price_msg: return
            target_price = float(target_price_msg.text)
            
            # asset_symbol is not used in the current calculator logic but kept for potential future use
            inputs = {"initial_investment": initial_investment, "current_price": current_price, "target_price": target_price}
            result = calculate_whatif(**inputs)

            response_text = (
                f"ماشین حساب 'چه می‌شد اگر؟':\n\n"
                f"با سرمایه اولیه: {initial_investment:,.2f}\n"
                f"و قیمت فعلی: {current_price:,.2f}\n"
                f"می‌توانید تعداد واحد: {result['units_purchasable']:.6f} خریداری کنید.\n\n"
                f"اگر قیمت به {target_price:,.2f} برسد:\n"
                f"سود بالقوه شما: {result['potential_profit_at_target']:,.2f}"
            )
            await client.send_message(chat_id, response_text)
            save_calculation_to_db(user_id, "whatif", inputs, result)
            await cleanup_conversation_messages(client, chat_id)

        except ValueError:
            await client.send_message(chat_id, "ورودی نامعتبر است. لطفا فقط عدد وارد کنید.")
        except Exception as e:
            await client.send_message(chat_id, f"خطایی رخ داد: {e}")
            print(f"Error in calc_whatif: {e}")


@app.on_callback_query(filters.regex("^select_currency_"))
async def currency_selection_handler(client: Client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    action_parts = callback_query.data.split("_")
    direction = action_parts[2] # 'from' or 'to'
    currency_code = action_parts[3]

    await callback_query.answer()
    await callback_query.message.delete() # Remove the currency selection keyboard

    if direction == "from":
        conversation_state[chat_id]["from_currency"] = currency_code
        await client.send_message(chat_id, f"واحد پولی مبدا: {currency_code}. حالا واحد پولی مقصد را انتخاب کنید:", reply_markup=get_currency_selection_keyboard(get_supported_currencies(), "to"))
    elif direction == "to":
        conversation_state[chat_id]["to_currency"] = currency_code
        from_currency = conversation_state[chat_id].get("from_currency")
        if not from_currency:
            await client.send_message(chat_id, "خطا: واحد پولی مبدا یافت نشد. لطفا دوباره از /calc شروع کنید.")
            return

        amount_msg = await ask_for_input(client, chat_id, f"لطفا مقدار را برای تبدیل از {from_currency} به {currency_code} وارد کنید:", state_key_suffix="amount_convert")
        if not amount_msg: return
        
        try:
            amount = float(amount_msg.text)
            inputs = {"amount": amount, "from_currency": from_currency, "to_currency": currency_code}
            result = convert_currency(**inputs)

            response_text = (
                f"ماشین حساب تبدیل ارز:\n\n"
                f"{amount} {from_currency} = {result['converted_amount']:.6f} {currency_code}\n"
                f"(نرخ تبدیل استفاده شده: {result['rate_used']})"
            )
            await client.send_message(chat_id, response_text)
            save_calculation_to_db(user_id, "convert", inputs, result)
            await cleanup_conversation_messages(client, chat_id)
            del conversation_state[chat_id] # Clear state
        except ValueError:
            await client.send_message(chat_id, "مقدار نامعتبر است. لطفا فقط عدد وارد کنید.")
        except Exception as e:
            await client.send_message(chat_id, f"خطایی در تبدیل ارز رخ داد: {e}")
            print(f"Error in currency conversion processing: {e}")


@app.on_callback_query(filters.regex("^select_pos_"))
async def margin_position_selection_handler(client: Client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    position_type = callback_query.data.split("_")[2] # 'long' or 'short'

    await callback_query.answer()
    await callback_query.message.delete() # Remove the position type keyboard

    state = conversation_state.get(chat_id, {})
    if not all(k in state for k in ['entry_price', 'exit_price', 'quantity', 'leverage']):
        await client.send_message(chat_id, "خطا: اطلاعات مورد نیاز برای محاسبه مارجین کامل نیست. لطفا دوباره از /calc شروع کنید.")
        return

    try:
        inputs = {
            "entry_price": state['entry_price'],
            "exit_price": state['exit_price'],
            "quantity": state['quantity'],
            "leverage": state['leverage'],
            "position_type": position_type
        }
        result = calculate_margin(**inputs)

        response_text = (
            f"ماشین حساب مارجین ({'لانگ' if position_type == 'long' else 'شورت'}):\n\n"
            f"سود/زیان (PnL): {result['pnl']:.2f}\n"
            f"بازده درصدی (ROE): {result['roe_percentage']:.2f}%\n\n"
            f"جزئیات:\n"
            f"قیمت ورود: {inputs['entry_price']}\n"
            f"قیمت خروج: {inputs['exit_price']}\n"
            f"مقدار: {inputs['quantity']}\n"
            f"اهرم: {inputs['leverage']}x\n"
            f"مارجین اولیه: {result['initial_margin']:.2f}"
        )
        await client.send_message(chat_id, response_text)
        save_calculation_to_db(user_id, "margin", inputs, result)
        await cleanup_conversation_messages(client, chat_id)
        if chat_id in conversation_state: del conversation_state[chat_id] # Clear state

    except ValueError as e:
        await client.send_message(chat_id, f"خطای محاسباتی: {e}")
    except Exception as e:
        await client.send_message(chat_id, f"خطایی در محاسبه مارجین رخ داد: {e}")
        print(f"Error in margin calculation processing: {e}")

@app.on_callback_query(filters.regex("^(cancel_conversion|cancel_margin_calc)$"))
async def cancel_calculation_handler(client: Client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    await callback_query.answer("عملیات لغو شد.", show_alert=False)
    await callback_query.message.delete() # Remove the keyboard message
    if chat_id in conversation_state:
        await cleanup_conversation_messages(client, chat_id) # Also cleanup previous q/a messages
        if chat_id in conversation_state: # Check again as cleanup might delete it
            del conversation_state[chat_id]
    await client.send_message(chat_id, "عملیات لغو شد. برای شروع مجدد از /calc استفاده کنید.")

# --- Portfolio Command ---
@app.on_message(filters.command("portfolio"))
async def portfolio_command_handler(client: Client, message: Message):
    user_telegram_id = message.from_user.id
    db = get_db_session()

    # Step 1: Check if global API keys are configured
    if not EXCHANGE_API_KEY or not EXCHANGE_SECRET_KEY:
        await message.reply_text(
            "متاسفانه امکان ردیابی پرتفوی در حال حاضر به دلیل عدم تنظیم کلیدهای API سراسری وجود ندارد. "
            "لطفا با مدیر ربات تماس بگیرید.\n\n"
            "قابلیت اتصال کلید API شخصی شما به زودی اضافه خواهد شد."
        )
        db.close()
        return

    # Step 2: Fetch balances from exchange
    await message.reply_text("در حال دریافت اطلاعات موجودی از صرافی... لطفا کمی صبر کنید.")
    balances_data = await fetch_balances_from_exchange(user_telegram_id, db) # db is passed but not used in current fetch_balances

    if isinstance(balances_data, dict) and "error" in balances_data:
        error_message = balances_data.get("message", "خطای نامشخصی هنگام دریافت موجودی از صرافی رخ داد.")
        await message.reply_text(f"خطا در دریافت موجودی: {error_message}")
        db.close()
        return
    
    if not balances_data: # Empty balances or other issue not caught by error dict
        await message.reply_text("موجودی قابل توجهی در حساب شما یافت نشد یا خطایی در دریافت اطلاعات رخ داد.")
        db.close()
        return

    # Step 3: Update database
    update_success = update_user_portfolio(db, user_telegram_id, balances_data, DEFAULT_EXCHANGE_NAME)
    if not update_success:
        await message.reply_text("خطایی در بروزرسانی اطلاعات پرتفوی در پایگاه داده رخ داد.")
        # Continue to display whatever is in DB or fetched, if possible
    
    # Step 4: Retrieve portfolio from DB to ensure consistency
    db_user = db.query(WebUser).filter(WebUser.telegram_id == user_telegram_id).first()
    if not db_user:
        await message.reply_text("کاربر در سیستم یافت نشد.") # Should not happen if /start worked
        db.close()
        return

    portfolio_items = db.query(WebPortfolio).filter_by(user_id=db_user.id, exchange=DEFAULT_EXCHANGE_NAME.upper()).all()

    if not portfolio_items:
        await message.reply_text("پرتفوی شما در حال حاضر خالی است یا هیچ دارایی با موجودی قابل توجهی یافت نشد.")
        db.close()
        return

    # Step 5: Calculate values
    response_text = f"**پرتفوی شما در صرافی {DEFAULT_EXCHANGE_NAME.upper()}:**\n\n"
    total_portfolio_value_toman = 0.0
    
    # Initialize a single exchange client for fetching all prices
    # (Re-using global keys for this example)
    price_exchange_client = await get_exchange_client(EXCHANGE_API_KEY, EXCHANGE_SECRET_KEY, DEFAULT_EXCHANGE_NAME)
    if not price_exchange_client:
        await message.reply_text("خطا در اتصال به صرافی برای دریافت قیمت‌ها. نمایش پرتفوی بدون ارزش‌گذاری دلاری/تومانی.")
        # Fallback: display amounts only
        for item in portfolio_items:
            if item.amount > 0: # Only display assets with positive amount
                 response_text += f"{item.asset}: {item.amount:.6f}\n"
        await message.reply_text(response_text)
        db.close()
        if price_exchange_client: await price_exchange_client.close()
        return

    for item in portfolio_items:
        if item.amount <= 0: # Skip assets with zero or negative amount after update
            continue

        asset_usd_price = await get_asset_price_in_usd(price_exchange_client, item.asset)
        asset_value_toman = 0.0
        price_info_str = "(قیمت دلاری یافت نشد)"

        if asset_usd_price > 0:
            asset_value_usd = item.amount * asset_usd_price
            asset_value_toman = asset_value_usd * USD_TOMAN_RATE
            total_portfolio_value_toman += asset_value_toman
            price_info_str = f"(هر واحد ${asset_usd_price:,.2f} / معادل {asset_value_toman:,.0f} تومان)"
        
        response_text += f"{item.asset}: {item.amount:.6f} {price_info_str}\n"

    if price_exchange_client:
        await price_exchange_client.close()

    response_text += f"\n**ارزش کل تخمینی پرتفوی: {total_portfolio_value_toman:,.0f} تومان**\n"
    response_text += f"(نرخ دلار به تومان استفاده شده: {USD_TOMAN_RATE:,.0f})"

    await message.reply_text(response_text, disable_web_page_preview=True)
    db.close()

# --- Chart Command ---
@app.on_message(filters.command("chart"))
async def chart_command_handler(client: Client, message: Message):
    user_telegram_id = message.from_user.id
    command_parts = message.text.split()

    if len(command_parts) < 2:
        await message.reply_text(
            "لطفا نماد را برای نمودار مشخص کنید. مثال: `/chart BTC/USDT` یا `/chart ETH/USDT RSI,EMA,MACD`"
        )
        return

    symbol = command_parts[1].upper()
    requested_indicators_str = command_parts[2] if len(command_parts) > 2 else "RSI,EMA"
    requested_indicators = [ind.strip().upper() for ind in requested_indicators_str.split(',')]
    
    # Validate allowed indicators (optional, but good practice)
    allowed_indicators = ['RSI', 'EMA', 'MACD', 'BBANDS']
    indicators_to_use = [ind for ind in requested_indicators if ind in allowed_indicators]
    if not indicators_to_use: # Default if no valid indicators provided or all are invalid
        indicators_to_use = ['RSI', 'EMA']


    await message.reply_text(f"در حال آماده‌سازی نمودار برای {symbol} با اندیکاتورهای: {', '.join(indicators_to_use)}...")

    # 1. Fetch historical data
    df, error_msg = await fetch_historical_data(symbol=symbol, timeframe='1d', limit=100) # Using default exchange from chart_utils
    if error_msg:
        await message.reply_text(f"خطا در دریافت اطلاعات قیمت: {error_msg}")
        return
    if df is None or df.empty:
        await message.reply_text(f"اطلاعات قیمتی برای نماد {symbol} یافت نشد.")
        return

    # 2. Add indicators
    try:
        df_with_indicators = add_indicators(df, indicators_requested=indicators_to_use)
        if df_with_indicators.empty:
            await message.reply_text(f"پس از افزودن اندیکاتورها، داده‌ای برای رسم نمودار {symbol} باقی نماند. ممکن است به داده‌های بیشتری نیاز باشد.")
            return
    except Exception as e:
        await message.reply_text(f"خطا در محاسبه اندیکاتورها: {e}")
        print(f"Error calculating indicators for {symbol}: {e}")
        return
        
    # 3. Generate SVG chart
    try:
        svg_bytes = generate_price_chart_svg(df_with_indicators, symbol, indicators_to_plot=indicators_to_use)
    except Exception as e:
        await message.reply_text(f"خطا در تولید نمودار: {e}")
        print(f"Error generating chart for {symbol}: {e}")
        return

    # 4. Send chart
    try:
        svg_file_like = io.BytesIO(svg_bytes)
        svg_file_like.name = f"{symbol.replace('/', '_')}_chart.svg" # Pyrogram needs a name for documents
        
        await client.send_document(
            chat_id=message.chat.id,
            document=svg_file_like,
            caption=f"نمودار تکنیکال برای {symbol} با اندیکاتورهای ({', '.join(indicators_to_use)})",
            file_name=svg_file_like.name # Explicitly set filename
        )
    except Exception as e:
        await message.reply_text(f"خطا در ارسال نمودار: {e}")
        print(f"Error sending chart for {symbol}: {e}")


if __name__ == "__main__":
    # Ensure tables are created.
    # This is also done in web/main.py on startup and bot/tasks.py for Celery.
    # It's good practice to ensure tables exist before the bot starts.
    from web.database import Base as WebAppBase # User, News, Calculation, Portfolio, Filter models use this
    WebAppBase.metadata.create_all(bind=engine)
    
    # Start APScheduler and load active filters
    start_scheduler()
    # We need to run load_active_filters_on_startup in the bot's event loop
    # or pass the bot client to it if it's run separately.
    # For simplicity here, assuming it's called after bot is initialized.
    # await load_active_filters_on_startup(app) # This needs to be called within an async context / after app is running

    print("Bot starting...")
    try:
        # app.run() will block here. For scheduler loading, it's better to do it in an on_startup type event
        # or right before app.run() if the function is synchronous.
        # Since load_active_filters_on_startup is async, it's tricky here without a proper startup hook.
        # For now, we'll rely on manual loading or a separate script for production.
        # A simplified approach for this environment:
        # asyncio.get_event_loop().run_until_complete(load_active_filters_on_startup(app))
        app.run() # This blocks
    finally:
        shutdown_scheduler()
        print("Bot stopped.")

# --- Scanner (Filter) Commands and Callbacks ---

# Main /scan command
@app.on_message(filters.command("scan"))
async def scan_command_handler(client: Client, message: Message):
    await message.reply_text(
        "به بخش مدیریت اسکنرها خوش آمدید. چه کاری می‌خواهید انجام دهید؟",
        reply_markup=get_scanner_main_menu_keyboard()
    )

# Callback for main scanner menu options
@app.on_callback_query(filters.regex("^scan_(create_start|list)$"))
async def scanner_menu_callback_handler(client: Client, callback_query: CallbackQuery):
    action = callback_query.data
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id

    await callback_query.answer()

    if action == "scan_create_start":
        conversation_state[chat_id] = {
            "step": "create_filter_name", 
            "filter_data": {"user_id": user_id, "params": {}} # Store user_id (telegram_id)
        }
        await callback_query.message.edit_text("لطفا یک نام برای اسکنر جدید خود وارد کنید:")
        # Next input will be handled by a general message handler or client.listen

    elif action == "scan_list":
        db = get_db_session()
        try:
            # Fetch user's internal ID
            db_bot_user = db.query(WebUser).filter(WebUser.telegram_id == user_id).first()
            if not db_bot_user:
                await callback_query.message.edit_text("کاربر یافت نشد. لطفا ابتدا ربات را با /start راه‌اندازی کنید.")
                return

            user_filters = db.query(DBFilter).filter(DBFilter.user_id == db_bot_user.id).order_by(DBFilter.created_at.desc()).all()
            if not user_filters:
                await callback_query.message.edit_text(
                    "شما هنوز هیچ اسکنری ایجاد نکرده‌اید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ایجاد اسکنر جدید", callback_data="scan_create_start")]])
                )
            else:
                await callback_query.message.edit_text(
                    "لیست اسکنرهای شما:",
                    reply_markup=get_user_filters_list_keyboard(user_filters, current_page=0)
                )
        finally:
            db.close()

# Callback for filter list pagination
@app.on_callback_query(filters.regex("^scan_list_page_"))
async def scanner_list_page_callback_handler(client: Client, callback_query: CallbackQuery):
    page = int(callback_query.data.split("_")[-1])
    user_id = callback_query.from_user.id
    await callback_query.answer()
    db = get_db_session()
    try:
        db_bot_user = db.query(WebUser).filter(WebUser.telegram_id == user_id).first()
        if not db_bot_user: return # Should not happen
        user_filters = db.query(DBFilter).filter(DBFilter.user_id == db_bot_user.id).order_by(DBFilter.created_at.desc()).all()
        await callback_query.message.edit_text(
            "لیست اسکنرهای شما:",
            reply_markup=get_user_filters_list_keyboard(user_filters, current_page=page)
        )
    finally:
        db.close()


# General message handler for scanner creation steps (simplified)
# This assumes only one user is creating a filter at a time per bot instance,
# or conversation_state correctly isolates by chat_id.
@app.on_message(filters.private & ~filters.command(None)) # Catches text messages that are not commands
async def scanner_creation_message_handler(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id # telegram_id
    
    if chat_id not in conversation_state or "step" not in conversation_state[chat_id]:
        # Not part of a known conversation, or state is corrupted
        # await message.reply_text("برای شروع، از دستورات موجود مانند /scan استفاده کنید.")
        return 

    state = conversation_state[chat_id]
    current_step = state.get("step")
    filter_data = state.get("filter_data", {})

    if current_step == "create_filter_name":
        filter_data["name"] = message.text.strip()
        state["step"] = "create_filter_timeframe"
        await message.reply_text("نام اسکنر ذخیره شد. حالا تایم فریم را انتخاب کنید:", reply_markup=get_scanner_timeframe_keyboard())
    
    elif current_step == "create_filter_symbols_custom":
        symbols_text = message.text.strip().upper()
        filter_data["symbols"] = [s.strip() for s in symbols_text.split(',') if s.strip()]
        if not filter_data["symbols"]:
            await message.reply_text("لیست نمادها نمی‌تواند خالی باشد. لطفا دوباره وارد کنید یا 'لغو' را بزنید.")
            return
        state["step"] = "create_filter_condition_indicator"
        state["condition_count"] = state.get("condition_count", 0) + 1
        await message.reply_text(
            f"نمادها ذخیره شدند: {', '.join(filter_data['symbols'])}. "
            f"حالا شرط شماره {state['condition_count']} را تعریف کنید: اندیکاتور را انتخاب کنید.",
            reply_markup=get_scanner_condition_indicator_keyboard()
        )

    elif current_step == "create_filter_condition_period":
        try:
            period = int(message.text.strip())
            if period <= 0: raise ValueError("Period must be positive")
            # current_condition_key is like 'condition_1', 'condition_2', etc.
            current_condition_key = f"condition_{state['condition_count']}"
            filter_data["params"][current_condition_key]["period"] = period
            state["step"] = "create_filter_condition_operator"
            await message.reply_text(
                f"دوره زمانی برای {filter_data['params'][current_condition_key]['type']} روی {period} تنظیم شد. "
                "حالا عملگر را انتخاب کنید (مثلا <, >):",
                reply_markup=get_scanner_condition_operator_keyboard(filter_data['params'][current_condition_key]['type'])
            )
        except ValueError:
            await message.reply_text("دوره زمانی نامعتبر است. لطفا یک عدد صحیح مثبت وارد کنید.")

    elif current_step == "create_filter_condition_value":
        try:
            value_str = message.text.strip()
            # float(value_str) # Validate if it's a number, actual type might vary
            current_condition_key = f"condition_{state['condition_count']}"
            filter_data["params"][current_condition_key]["value"] = value_str # Store as string, scanner_utils will parse
            state["step"] = "create_filter_add_another_condition"
            await message.reply_text(
                f"مقدار شرط برای {filter_data['params'][current_condition_key]['type']} روی {value_str} تنظیم شد. "
                "آیا می‌خواهید شرط دیگری اضافه کنید؟",
                reply_markup=get_scanner_add_another_condition_keyboard()
            )
        except ValueError:
             await message.reply_text("مقدار نامعتبر است. لطفا یک عدد وارد کنید.")
    else:
        # User might be typing something not expected in the current conversation flow
        # You might want to add a message here or ignore.
        pass


# Callbacks for scanner creation and management
@app.on_callback_query(filters.regex("^scan_"))
async def scanner_actions_callback_handler(client: Client, callback_query: CallbackQuery):
    action = callback_query.data
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id # telegram_id

    state = conversation_state.get(chat_id, {})
    filter_data = state.get("filter_data", {})
    
    await callback_query.answer() # Acknowledge early

    # --- Creation Flow Callbacks ---
    if action.startswith("scan_set_timeframe_"):
        if state.get("step") != "create_filter_timeframe": return # Wrong state
        timeframe = action.split("_")[-1]
        filter_data["timeframe"] = timeframe
        state["step"] = "create_filter_symbols_type"
        await callback_query.message.edit_text(
            f"تایم فریم روی {timeframe} تنظیم شد. حالا نوع نمادها را انتخاب کنید:",
            reply_markup=get_scanner_symbols_type_keyboard()
        )

    elif action == "scan_set_symbols_default":
        if state.get("step") != "create_filter_symbols_type": return
        filter_data["symbols"] = None # None means default (e.g., top N)
        state["step"] = "create_filter_condition_indicator"
        state["condition_count"] = state.get("condition_count", 0) + 1
        await callback_query.message.edit_text(
            "نمادها روی پیشفرض تنظیم شدند. "
            f"حالا شرط شماره {state['condition_count']} را تعریف کنید: اندیکاتور را انتخاب کنید.",
            reply_markup=get_scanner_condition_indicator_keyboard()
        )

    elif action == "scan_set_symbols_custom":
        if state.get("step") != "create_filter_symbols_type": return
        state["step"] = "create_filter_symbols_custom"
        await callback_query.message.edit_text("لطفا لیست نمادهای مورد نظر را با کاما (,) جدا کرده و ارسال کنید (مثال: BTC/USDT,ETH/USDT):")

    elif action.startswith("scan_cond_indicator_"):
        if state.get("step") != "create_filter_condition_indicator": return
        indicator_type = action.split("_")[-1]
        current_condition_key = f"condition_{state['condition_count']}"
        filter_data["params"][current_condition_key] = {"type": indicator_type}
        
        if indicator_type in ["RSI", "EMA"]: # Indicators that need a period
            state["step"] = "create_filter_condition_period"
            await callback_query.message.edit_text(f"اندیکاتور: {indicator_type}. حالا دوره زمانی را وارد کنید (مثلا 14 برای RSI، 20 برای EMA):")
        else: # For indicators not needing period (e.g. Volume_USD, Price - if implemented)
            state["step"] = "create_filter_condition_operator"
            await callback_query.message.edit_text(
                f"اندیکاتور: {indicator_type}. حالا عملگر را انتخاب کنید:",
                reply_markup=get_scanner_condition_operator_keyboard(indicator_type)
            )
    
    elif action.startswith("scan_cond_operator_"):
        if state.get("step") != "create_filter_condition_operator": return
        operator = action.split("_")[-1]
        current_condition_key = f"condition_{state['condition_count']}"
        filter_data["params"][current_condition_key]["operator"] = operator
        state["step"] = "create_filter_condition_value"
        await callback_query.message.edit_text(f"عملگر: {operator}. حالا مقدار مورد نظر برای شرط را وارد کنید (مثلا 30 برای RSI < 30):")

    elif action == "scan_cond_add_another_yes":
        if state.get("step") != "create_filter_add_another_condition": return
        state["step"] = "create_filter_condition_indicator"
        state["condition_count"] = state.get("condition_count", 0) + 1
        await callback_query.message.edit_text(
            f"شرط قبلی ذخیره شد. حالا شرط شماره {state['condition_count']} را تعریف کنید: اندیکاتور را انتخاب کنید.",
            reply_markup=get_scanner_condition_indicator_keyboard()
        )

    elif action == "scan_cond_finish" or action == "scan_create_save": # scan_create_save could be a final button
        if not filter_data.get("name") or not filter_data.get("timeframe") or not filter_data.get("params"):
            await callback_query.message.edit_text("اطلاعات اسکنر ناقص است. لطفا از ابتدا شروع کنید یا مراحل را کامل کنید.")
            if chat_id in conversation_state: del conversation_state[chat_id]
            return

        db = get_db_session()
        try:
            db_bot_user = db.query(WebUser).filter(WebUser.telegram_id == user_id).first()
            if not db_bot_user:
                await callback_query.message.edit_text("کاربر برای ذخیره اسکنر یافت نشد.")
                if chat_id in conversation_state: del conversation_state[chat_id]
                return

            new_filter = DBFilter(
                user_id=db_bot_user.id,
                name=filter_data["name"],
                params=filter_data["params"],
                symbols=filter_data.get("symbols"),
                timeframe=filter_data["timeframe"],
                active=True 
            )
            db.add(new_filter)
            db.commit()
            db.refresh(new_filter)
            
            # Schedule the job
            await schedule_filter_job(new_filter, client) # Pass the bot client instance
            
            await callback_query.message.edit_text(
                f"اسکنر '{new_filter.name}' با موفقیت ایجاد و فعال شد!\n"
                f"این اسکنر هر {new_filter.timeframe} اجرا خواهد شد."
            )
        except IntegrityError: # Should not happen if name is not unique per user, but good to have
            db.rollback()
            await callback_query.message.edit_text("خطا: اسکنری با این نام از قبل برای شما وجود دارد.")
        except Exception as e:
            db.rollback()
            await callback_query.message.edit_text(f"خطا در ذخیره اسکنر: {e}")
            print(f"Error saving filter: {e}")
        finally:
            if chat_id in conversation_state: del conversation_state[chat_id]
            db.close()

    elif action == "scan_create_cancel" or action == "scan_cond_cancel_current":
        # For scan_cond_cancel_current, we might just go back one step or clear current condition
        # For simplicity, both cancel the whole creation process for now.
        if chat_id in conversation_state: del conversation_state[chat_id]
        await callback_query.message.edit_text("ایجاد اسکنر لغو شد.", reply_markup=get_scanner_main_menu_keyboard())


    # --- Management Callbacks (View, Run, Toggle, Delete) ---
    elif action.startswith("scan_view_"):
        filter_id_to_view = int(action.split("_")[-1])
        db = get_db_session()
        try:
            filter_obj = db.query(DBFilter).filter(DBFilter.id == filter_id_to_view).first()
            # Add check if filter_obj.user_id matches callback_query.from_user.id (after getting internal user ID)
            if filter_obj:
                params_str = "\n".join([f"  - {k}: {v}" for k, v in filter_obj.params.items()])
                symbols_str = ", ".join(filter_obj.symbols) if filter_obj.symbols else "نمادهای پیشفرض"
                status_str = "فعال" if filter_obj.active else "غیرفعال"
                last_triggered_str = filter_obj.last_triggered_at.strftime("%Y-%m-%d %H:%M UTC") if filter_obj.last_triggered_at else "هرگز"

                detail_text = (
                    f"**جزئیات اسکنر: {filter_obj.name}**\n\n"
                    f"شناسه: `{filter_obj.id}`\n"
                    f"وضعیت: **{status_str}**\n"
                    f"تایم فریم: {filter_obj.timeframe}\n"
                    f"نمادها: {symbols_str}\n"
                    f"آخرین اجرا با نتیجه: {last_triggered_str}\n\n"
                    f"شرایط:\n{params_str}"
                )
                await callback_query.message.edit_text(detail_text, reply_markup=get_single_filter_manage_keyboard(filter_obj))
            else:
                await callback_query.message.edit_text("اسکنر یافت نشد.")
        finally:
            db.close()

    elif action.startswith("scan_run_"):
        filter_id_to_run = int(action.split("_")[-1])
        await callback_query.message.edit_text(f"در حال اجرای دستی اسکنر با شناسه {filter_id_to_run}...")
        db = get_db_session()
        try:
            filter_obj = db.query(DBFilter).filter(DBFilter.id == filter_id_to_run).first()
            # Add user ownership check here
            if filter_obj:
                triggered_symbols, msg, err_msg = await run_manual_scan(db, filter_obj, client, user_id) # Pass client and user_id for notification
                if err_msg:
                    await callback_query.message.reply_text(f"خطا در اجرای اسکنر: {err_msg}")
                elif msg:
                    await callback_query.message.reply_text(msg) # run_manual_scan already sends if client is passed
                else:
                    await callback_query.message.reply_text(f"اسکنر '{filter_obj.name}' اجرا شد اما هیچ نمادی با شرایط مطابقت نداشت.")
            else:
                await callback_query.message.edit_text("اسکنر برای اجرا یافت نشد.")
        finally:
            db.close()

    elif action.startswith("scan_toggle_"):
        filter_id_to_toggle = int(action.split("_")[-1])
        db = get_db_session()
        try:
            filter_obj = db.query(DBFilter).filter(DBFilter.id == filter_id_to_toggle).first()
            # Add user ownership check
            if filter_obj:
                filter_obj.active = not filter_obj.active
                db.commit()
                if filter_obj.active:
                    await schedule_filter_job(filter_obj, client)
                    await callback_query.message.edit_text(f"اسکنر '{filter_obj.name}' فعال شد و در زمان‌بند قرار گرفت.", reply_markup=get_single_filter_manage_keyboard(filter_obj))
                else:
                    remove_filter_job(filter_obj.id)
                    await callback_query.message.edit_text(f"اسکنر '{filter_obj.name}' غیرفعال شد و از زمان‌بند حذف گردید.", reply_markup=get_single_filter_manage_keyboard(filter_obj))
            else:
                await callback_query.message.edit_text("اسکنر برای تغییر وضعیت یافت نشد.")
        finally:
            db.close()

    elif action.startswith("scan_delete_"):
        filter_id_to_delete = int(action.split("_")[-1])
        # Consider adding a confirmation step here
        db = get_db_session()
        try:
            filter_obj = db.query(DBFilter).filter(DBFilter.id == filter_id_to_delete).first()
            # Add user ownership check
            if filter_obj:
                remove_filter_job(filter_obj.id) # Remove from scheduler first
                db.delete(filter_obj)
                db.commit()
                await callback_query.message.edit_text(f"اسکنر '{filter_obj.name}' با موفقیت حذف شد.", reply_markup=get_scanner_main_menu_keyboard()) # Go back to main menu
            else:
                await callback_query.message.edit_text("اسکنر برای حذف یافت نشد.")
        finally:
            db.close()
    
    # Fallback for unhandled scan_ prefixed callbacks
    elif action.startswith("scan_") and not any(action.startswith(known_prefix) for known_prefix in [
        "scan_create_start", "scan_list", "scan_list_page_", "scan_set_timeframe_", "scan_set_symbols_",
        "scan_cond_indicator_", "scan_cond_operator_", "scan_cond_add_another_yes", "scan_cond_finish",
        "scan_create_save", "scan_create_cancel", "scan_cond_cancel_current", "scan_view_", "scan_run_",
        "scan_toggle_", "scan_delete_"
    ]):
        print(f"هشدار: کال‌بک اسکنر ناشناخته دریافت شد: {action}")
        # await callback_query.message.edit_text("دستور اسکنر نامعتبر است.")


# --- Main Bot Startup ---
async def main(): # Renamed from if __name__ == "__main__": to allow calling from entrypoint
    from web.database import Base as WebAppBase # User, News, Calculation, Portfolio, Filter models use this
    WebAppBase.metadata.create_all(bind=engine)
    
    start_scheduler()
    await load_active_filters_on_startup(app) # Pass the Pyrogram client instance
    
    print("Bot starting with Pyrogram client...")
    await app.start() # Start Pyrogram client
    print("Pyrogram client started. Bot is running.")
    
    # Keep the main coroutine alive (Pyrogram's app.run() does this, but here we started manually)
    while app.is_running:
        await asyncio.sleep(3600) # Or some other mechanism to keep alive / handle signals

    # This part will be reached on graceful shutdown if the loop above is exited
    shutdown_scheduler()
    await app.stop()
    print("Bot stopped.")

if __name__ == "__main__":
    # This is the main entry point now
    # Ensure any setup needed before starting the bot is done here
    # For example, initial DB checks or migrations if you had them.
    
    # The 'app.run()' approach is simpler for Pyrogram if you don't have complex async startup needs.
    # The 'await app.start()' and manual loop is for more control over the startup/shutdown sequence.
    # Let's revert to the simpler app.run() for now and call async startup functions just before it.
    
    # --- Simplified Startup for this context ---
    from web.database import Base as WebAppBase 
    WebAppBase.metadata.create_all(bind=engine)
    
    async def run_bot_with_scheduler():
        # This function will be run by asyncio.run()
        await app.start() # Manually start the client
        print("Pyrogram client started.")
        
        start_scheduler()
        print("APScheduler started.")
        
        await load_active_filters_on_startup(app) # Load filters
        print("Active filters loaded and scheduled.")
        
        print("Bot is now fully operational.")
        # Keep the bot alive; Pyrogram usually handles this with app.run()
        # For manual start, we need to keep the event loop running.
        # A simple way is to wait indefinitely or until a stop signal.
        await asyncio.Event().wait() # This will wait forever
        
        # ---- This part below might not be reached easily with simple asyncio.Event().wait() ----
        # Consider signal handling for graceful shutdown if needed.
        # print("Shutting down...")
        # shutdown_scheduler()
        # await app.stop()
        # print("Bot stopped.")

    # If running this file directly:
    # For production, you'd likely have a more robust entrypoint script.
    # The `app.run()` method is often sufficient and handles the event loop.
    # The more complex `main()` above with `app.start()` is for cases where you need
    # finer control *after* Pyrogram's own event loop has started but before it idles,
    # or if integrating with other async frameworks.
    
    # Let's use the standard app.run() and ensure async setup is compatible.
    # `load_active_filters_on_startup` can be tricky if not called from within the same event loop
    # that Pyrogram uses. A common pattern is to use Pyrogram's `idle()` after starting tasks.

    async def bot_startup_tasks():
        start_scheduler()
        await load_active_filters_on_startup(app) # Pass the client instance 'app'
    
    app.on_startup(bot_startup_tasks)
    app.on_shutdown(shutdown_scheduler)

    print("Bot starting with app.run()...")
    app.run()
    print("Bot stopped.")

# --- Subscription Payment Commands and Handlers ---

@app.on_message(filters.command("upgrade"))
async def upgrade_command_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if not PAYMENT_PROVIDER_TOKEN:
        await message.reply_text(
            "متاسفانه امکان ارتقا در حال حاضر وجود ندارد. مدیر ربات هنوز درگاه پرداخت را تنظیم نکرده است."
        )
        print("هشدار: PAYMENT_PROVIDER_TOKEN تنظیم نشده است.")
        return

    # Check if user is already pro
    db = get_db_session()
    try:
        db_user = db.query(WebUser).filter(WebUser.telegram_id == user_id).first()
        if db_user and db_user.is_pro:
            await message.reply_text("شما در حال حاضر عضو Pro هستید!")
            return
    finally:
        db.close()

    title = "اشتراک Pro ماهانه"
    description = (
        "دسترسی کامل به تمامی امکانات ربات شامل تایم‌فریم‌های کوتاه در اسکنر، "
        "نوتیف‌های فوری، و اندیکاتورهای پیشرفته در نمودارها."
    )
    # Unique payload for this specific payment attempt
    payload = f"pro_sub_user_{user_id}_{int(datetime.now().timestamp())}"
    
    prices = [LabeledPrice(label="اشتراک Pro - 1 ماه", amount=PRO_SUBSCRIPTION_PRICE_CENTS)]

    try:
        await client.send_invoice(
            chat_id=message.chat.id,
            title=title,
            description=description,
            payload=payload,
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency=PRO_SUBSCRIPTION_CURRENCY,
            prices=prices,
            # Optional: Add photo_url, photo_width, photo_height for a nice image
            # photo_url="https://yourdomain.com/path/to/pro_icon.png",
            # photo_width=512,
            # photo_height=512,
            # start_parameter="upgrade_pro" # For deep linking if needed
        )
    except Exception as e:
        await message.reply_text("خطایی در ایجاد فاکتور پرداخت رخ داد. لطفا بعدا تلاش کنید.")
        print(f"Error sending invoice: {e}")

@app.on_pre_checkout_query()
async def pre_checkout_query_handler(client: Client, query: PreCheckoutQuery):
    # This handler must quickly answer whether the bot is ready to accept the payment.
    # For simple cases like a digital subscription, it's usually always OK.
    # For physical goods, you might check stock here.
    
    # You can also inspect query.payload here if you need to validate it
    # or check something specific about the user or item before confirming.
    print(f"PreCheckoutQuery دریافت شد برای کاربر {query.from_user.id}, payload: {query.payload}")
    
    # For this subscription, we assume it's always available.
    await query.answer(ok=True)
    # If there was an issue:
    # await query.answer(ok=False, error_message="متاسفانه مشکلی در پردازش پرداخت شما پیش آمد.")

@app.on_message(filters.successful_payment)
async def successful_payment_handler(client: Client, message: Message):
    user_id = message.from_user.id
    payment_info = message.successful_payment
    
    print(f"پرداخت موفق از کاربر {user_id}:")
    print(f"  Currency: {payment_info.currency}")
    print(f"  Total Amount: {payment_info.total_amount}")
    print(f"  Invoice Payload: {payment_info.invoice_payload}")
    print(f"  Telegram Payment Charge ID: {payment_info.telegram_payment_charge_id}")
    print(f"  Provider Payment Charge ID: {payment_info.provider_payment_charge_id}")

    # Update user status in the database
    db = get_db_session()
    try:
        db_user = db.query(WebUser).filter(WebUser.telegram_id == user_id).first()
        if db_user:
            db_user.is_pro = True
            # Potential future enhancement: store subscription start/end date
            # db_user.pro_subscription_start_date = datetime.now(timezone.utc)
            # db_user.pro_subscription_end_date = datetime.now(timezone.utc) + timedelta(days=30)
            db.commit()
            print(f"کاربر {user_id} به وضعیت Pro ارتقا یافت.")
            await message.reply_text(
                "پرداخت شما با موفقیت انجام شد! 🎉 حساب شما به Pro ارتقا یافت.\n"
                "از امکانات ویژه لذت ببرید!"
            )
        else:
            # This case should ideally not happen if user initiated /upgrade after /start
            print(f"خطا: کاربر {user_id} پس از پرداخت موفق در دیتابیس یافت نشد.")
            await message.reply_text(
                "پرداخت شما موفق بود، اما مشکلی در فعال‌سازی حساب Pro شما رخ داد. لطفا با پشتیبانی تماس بگیرید."
            )
    except Exception as e:
        db.rollback()
        print(f"خطا در بروزرسانی وضعیت کاربر {user_id} به Pro پس از پرداخت: {e}")
        await message.reply_text(
            "پرداخت شما موفق بود، اما مشکلی در بروزرسانی حساب شما رخ داد. لطفا با پشتیبانی تماس بگیرید و اطلاعات پرداخت را ارائه دهید."
        )
    finally:
        db.close()
