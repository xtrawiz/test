from typing import Dict, Union, Tuple

# --- Profit/Loss Calculator ---
def calculate_profit_loss(buy_price: float, sell_price: float, quantity: float) -> Dict[str, float]:
    """
    Calculates profit or loss amount and percentage.
    """
    if buy_price <= 0:
        raise ValueError("قیمت خرید باید بیشتر از صفر باشد.")
    
    profit_or_loss_amount = (sell_price - buy_price) * quantity
    profit_or_loss_percentage = ((sell_price - buy_price) / buy_price) * 100
    
    return {
        "profit_or_loss_amount": profit_or_loss_amount,
        "profit_or_loss_percentage": profit_or_loss_percentage,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "quantity": quantity
    }

# --- Currency Converter ---
# For now, using a fixed dictionary. This can be expanded later.
FIXED_EXCHANGE_RATES = {
    "USD_IRR": 500000.0,  # 1 USD to IRR
    "IRR_USD": 1 / 500000.0, # 1 IRR to USD
    "BTC_USD": 60000.0,   # 1 BTC to USD
    "USD_BTC": 1 / 60000.0,  # 1 USD to BTC
    "ETH_USD": 3000.0,    # 1 ETH to USD
    "USD_ETH": 1 / 3000.0,   # 1 USD to ETH
    # Add more pairs as needed
}

def get_supported_currencies() -> Dict[str, str]:
    """Returns a dictionary of supported currency pairs for user display."""
    return {
        "USD_IRR": "دلار آمریکا به ریال ایران",
        "IRR_USD": "ریال ایران به دلار آمریکا",
        "BTC_USD": "بیت‌کوین به دلار آمریکا",
        "USD_BTC": "دلار آمریکا به بیت‌کوین",
        "ETH_USD": "اتریوم به دلار آمریکا",
        "USD_ETH": "دلار آمریکا به اتریوم",
    }

def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict[str, Union[float, str]]:
    """
    Converts an amount from one currency to another using fixed rates.
    """
    pair = f"{from_currency.upper()}_{to_currency.upper()}"
    if pair not in FIXED_EXCHANGE_RATES:
        raise ValueError(f"نرخ تبدیل برای {from_currency} به {to_currency} یافت نشد.")
    
    rate = FIXED_EXCHANGE_RATES[pair]
    converted_amount = amount * rate
    
    return {
        "original_amount": amount,
        "from_currency": from_currency.upper(),
        "to_currency": to_currency.upper(),
        "rate_used": rate,
        "converted_amount": converted_amount
    }

# --- Margin Calculator ---
def calculate_margin(entry_price: float, exit_price: float, quantity: float, leverage: float, position_type: str) -> Dict[str, float]:
    """
    Calculates PnL and ROE for a margin trade.
    position_type should be 'long' or 'short'.
    """
    if entry_price <= 0 or quantity <= 0 or leverage <= 0:
        raise ValueError("قیمت ورود، مقدار و اهرم باید بیشتر از صفر باشند.")
    if position_type not in ['long', 'short']:
        raise ValueError("نوع پوزیشن باید 'long' یا 'short' باشد.")

    if position_type == 'long':
        pnl = (exit_price - entry_price) * quantity
    else: # short
        pnl = (entry_price - exit_price) * quantity
        
    initial_margin = (entry_price * quantity) / leverage
    if initial_margin == 0: # Avoid division by zero if entry_price or quantity is zero (though validated above)
        roe_percentage = float('inf') if pnl > 0 else float('-inf') if pnl < 0 else 0
    else:
        roe_percentage = (pnl / initial_margin) * 100
        
    return {
        "pnl": pnl,
        "roe_percentage": roe_percentage,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "quantity": quantity,
        "leverage": leverage,
        "position_type": position_type,
        "initial_margin": initial_margin
    }

# --- What-If Calculator ---
def calculate_whatif(initial_investment: float, current_price: float, target_price: float) -> Dict[str, float]:
    """
    Calculates potential profit and number of units purchasable.
    """
    if initial_investment <= 0 or current_price <= 0:
        raise ValueError("سرمایه اولیه و قیمت فعلی باید بیشتر از صفر باشند.")
    if target_price <=0:
        raise ValueError("قیمت هدف باید بیشتر از صفر باشد.")

    units_purchasable = initial_investment / current_price
    potential_profit_at_target = (target_price - current_price) * units_purchasable
    
    return {
        "initial_investment": initial_investment,
        "current_price": current_price,
        "target_price": target_price,
        "units_purchasable": units_purchasable,
        "potential_profit_at_target": potential_profit_at_target
    }

if __name__ == '__main__':
    # Simple test cases
    print("Profit/Loss:", calculate_profit_loss(buy_price=100, sell_price=120, quantity=10))
    try:
        print("Currency Conversion:", convert_currency(amount=100, from_currency="USD", to_currency="IRR"))
        print("Currency Conversion:", convert_currency(amount=1, from_currency="BTC", to_currency="USD"))
    except ValueError as e:
        print(e)
    print("Margin Calculation (Long):", calculate_margin(entry_price=50000, exit_price=52000, quantity=1, leverage=10, position_type='long'))
    print("Margin Calculation (Short):", calculate_margin(entry_price=50000, exit_price=48000, quantity=1, leverage=10, position_type='short'))
    print("What-If Calculation:", calculate_whatif(initial_investment=1000, current_price=50, target_price=70))
