from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_calculator_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Returns an InlineKeyboardMarkup for the main calculator menu.
    """
    keyboard = [
        [
            InlineKeyboardButton("ماشین حساب سود و زیان", callback_data="calc_profit"),
        ],
        [
            InlineKeyboardButton("ماشین حساب تبدیل ارز", callback_data="calc_convert"),
        ],
        [
            InlineKeyboardButton("ماشین حساب مارجین", callback_data="calc_margin"),
        ],
        [
            InlineKeyboardButton("ماشین حساب چه می‌شد اگر؟", callback_data="calc_whatif"),
        ],
        [
            InlineKeyboardButton("راهنمای تبدیل ارز", callback_data="calc_convert_help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Scanner Keyboards ---
def get_scanner_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("ایجاد اسکنر جدید", callback_data="scan_create_start")],
        [InlineKeyboardButton("لیست اسکنرهای من", callback_data="scan_list")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_scanner_timeframe_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("1 دقیقه", callback_data="scan_set_timeframe_1m"), # Primarily for testing
            InlineKeyboardButton("5 دقیقه", callback_data="scan_set_timeframe_5m"),
            InlineKeyboardButton("15 دقیقه", callback_data="scan_set_timeframe_15m"),
        ],
        [
            InlineKeyboardButton("1 ساعت", callback_data="scan_set_timeframe_1h"),
            InlineKeyboardButton("4 ساعت", callback_data="scan_set_timeframe_4h"),
            InlineKeyboardButton("1 روز", callback_data="scan_set_timeframe_1d"),
        ],
        [InlineKeyboardButton("لغو ایجاد اسکنر", callback_data="scan_create_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_scanner_symbols_type_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("نمادهای پیشفرض (20 برتر USDT)", callback_data="scan_set_symbols_default")],
        [InlineKeyboardButton("وارد کردن نمادهای دلخواه", callback_data="scan_set_symbols_custom")],
        [InlineKeyboardButton("لغو ایجاد اسکنر", callback_data="scan_create_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_scanner_condition_indicator_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("RSI", callback_data="scan_cond_indicator_RSI"),
            InlineKeyboardButton("EMA", callback_data="scan_cond_indicator_EMA"),
            # InlineKeyboardButton("Volume (USD)", callback_data="scan_cond_indicator_VOLUME_USD"), # Future
            # InlineKeyboardButton("Price", callback_data="scan_cond_indicator_PRICE"), # Future
        ],
        [InlineKeyboardButton("لغو این شرط", callback_data="scan_cond_cancel_current")],
        [InlineKeyboardButton("اتمام و ذخیره اسکنر (بدون شرط جدید)", callback_data="scan_cond_finish")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_scanner_condition_operator_keyboard(indicator_type: str) -> InlineKeyboardMarkup:
    # Operators might vary based on indicator (e.g., crossover for EMAs)
    keyboard = [
        [
            InlineKeyboardButton("کمتر از (<)", callback_data=f"scan_cond_operator_<"),
            InlineKeyboardButton("بیشتر از (>)", callback_data=f"scan_cond_operator_>"),
        ],
        [
            InlineKeyboardButton("کمتر یا مساوی (<=)", callback_data=f"scan_cond_operator_<="),
            InlineKeyboardButton("بیشتر یا مساوی (>=)", callback_data=f"scan_cond_operator_>="),
        ],
        # Add "==" if needed, or "crosses" for more complex scenarios later
        [InlineKeyboardButton("لغو این شرط", callback_data="scan_cond_cancel_current")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_scanner_add_another_condition_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("افزودن شرط دیگر", callback_data="scan_cond_add_another_yes")],
        [InlineKeyboardButton("اتمام و ذخیره اسکنر", callback_data="scan_cond_finish")],
        [InlineKeyboardButton("لغو ایجاد اسکنر", callback_data="scan_create_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_user_filters_list_keyboard(filters: list, current_page: int = 0, items_per_page: int = 5) -> InlineKeyboardMarkup:
    keyboard = []
    
    # Pagination
    start_index = current_page * items_per_page
    end_index = start_index + items_per_page
    paginated_filters = filters[start_index:end_index]

    for f in paginated_filters:
        status_emoji = "🟢" if f.active else "🔴"
        keyboard.append([
            InlineKeyboardButton(f"{status_emoji} {f.name} ({f.timeframe})", callback_data=f"scan_view_{f.id}")
        ])
    
    pagination_buttons = []
    if current_page > 0:
        pagination_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"scan_list_page_{current_page-1}"))
    if end_index < len(filters):
        pagination_buttons.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"scan_list_page_{current_page+1}"))
    
    if pagination_buttons:
        keyboard.append(pagination_buttons)
        
    keyboard.append([InlineKeyboardButton("ایجاد اسکنر جدید", callback_data="scan_create_start")])
    keyboard.append([InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="main_menu")]) # Assuming a main_menu callback
    return InlineKeyboardMarkup(keyboard)


def get_single_filter_manage_keyboard(filter_obj) -> InlineKeyboardMarkup:
    status_toggle_text = "غیرفعال کردن" if filter_obj.active else "فعال کردن"
    keyboard = [
        [
            InlineKeyboardButton("اجرای دستی", callback_data=f"scan_run_{filter_obj.id}"),
            InlineKeyboardButton(status_toggle_text, callback_data=f"scan_toggle_{filter_obj.id}"),
        ],
        [
            # InlineKeyboardButton("ویرایش", callback_data=f"scan_edit_{filter_obj.id}"), # TODO for future
            InlineKeyboardButton("حذف", callback_data=f"scan_delete_{filter_obj.id}"),
        ],
        [InlineKeyboardButton("بازگشت به لیست اسکنرها", callback_data="scan_list")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_currency_selection_keyboard(supported_currencies: dict, direction: str) -> InlineKeyboardMarkup:
    """
    Returns an InlineKeyboardMarkup for selecting a currency.
    direction: 'from' or 'to'
    """
    keyboard = []
    row = []
    for code, name in supported_currencies.items():
        # We only want the first part of the pair for selection (e.g., USD from USD_IRR)
        currency_code = code.split('_')[0] if direction == 'from' else code.split('_')[1]
        
        # Avoid duplicate buttons if multiple pairs involve the same currency (e.g. USD in USD_IRR and USD_BTC)
        # This simple approach might need refinement for complex scenarios
        if not any(btn.callback_data == f"select_currency_{direction}_{currency_code}" for r in keyboard for btn in r):
            row.append(InlineKeyboardButton(f"{currency_code} ({name.split(' به ')[0 if direction == 'from' else 1]})", callback_data=f"select_currency_{direction}_{currency_code}"))
            if len(row) == 2: # Adjust number of buttons per row as needed
                keyboard.append(row)
                row = []
    if row: # Add any remaining buttons
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("لغو", callback_data="cancel_conversion")])
    return InlineKeyboardMarkup(keyboard)

def get_position_type_keyboard() -> InlineKeyboardMarkup:
    """
    Returns an InlineKeyboardMarkup for selecting position type (long/short).
    """
    keyboard = [
        [
            InlineKeyboardButton("لانگ (خرید)", callback_data="select_pos_long"),
            InlineKeyboardButton("شورت (فروش)", callback_data="select_pos_short"),
        ],
        [
            InlineKeyboardButton("لغو", callback_data="cancel_margin_calc")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
