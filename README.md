# Persian Crypto Telegram Bot

## 1. Overview

A comprehensive Telegram bot that integrates news, calculators, portfolio tracking, technical analysis, and advanced scanners into a single interface. The bot’s user-facing language is Persian (Farsi). It features a rich admin panel, user management, and subscription tiers.

## 2. Prerequisites

Before you begin, ensure you have the following installed:

*   **Python**: Version 3.10+
*   **Docker**: Latest stable version
*   **Docker Compose**: Latest stable version
*   **Git**: For cloning the repository

You will also need to obtain several API keys and tokens as listed in the Environment Configuration section.

## 3. Environment Configuration

The project uses a `.env` file to manage environment variables. Create a file named `.env` in the root directory of the project by copying the example file (if one exists, otherwise create it manually) and fill in the required values.

**Example `.env` structure:**

```env
# Telegram API Credentials (from my.telegram.org)
TELEGRAM_API_ID=YOUR_TELEGRAM_API_ID
TELEGRAM_API_HASH=YOUR_TELEGRAM_API_HASH

# Telegram Bot Token (from BotFather)
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
BOT_USERNAME=YOUR_BOT_USERNAME # e.g., MyCryptoBot

# Database Configuration (MySQL)
DB_CONNECTION_STRING=mysql+mysqlclient://root:${MYSQL_ROOT_PASSWORD}@db:3306/${MYSQL_DATABASE}
MYSQL_ROOT_PASSWORD=your_strong_mysql_root_password
MYSQL_DATABASE=crypto_bot_db
MYSQL_USER=root # Or a dedicated user
MYSQL_PASSWORD=${MYSQL_ROOT_PASSWORD} # Or the dedicated user's password

# Celery Configuration (using Redis)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# News Module - RSS Feeds (JSON string or comma-separated)
# Example: [{"name": "Cointelegraph Farsi", "url": "https://cointelegraph.com/rss/tag/farsi", "category": "general"}]
RSS_FEEDS='[{"name": "Cointelegraph Farsi", "url": "https://cointelegraph.com/rss/tag/farsi", "category": "general"}]'

# Portfolio Module - Exchange API Keys (e.g., Binance Testnet)
# IMPORTANT: For real funds, ensure maximum security for these keys.
EXCHANGE_API_KEY=YOUR_EXCHANGE_API_KEY
EXCHANGE_SECRET_KEY=YOUR_EXCHANGE_SECRET_KEY
DEFAULT_EXCHANGE_NAME=binance # Or another CCXT-supported exchange

# Currency Conversion
USD_TOMAN_RATE=500000 # Approximate rate, update as needed

# Subscription Payments
PAYMENT_PROVIDER_TOKEN=YOUR_TELEGRAM_PAYMENT_PROVIDER_TOKEN # From BotFather (e.g., Stripe Test Token)
PRO_SUBSCRIPTION_PRICE_USD=1000 # Price in cents (e.g., 1000 for $10.00)
PRO_SUBSCRIPTION_CURRENCY=USD
WEBHOOK_DOMAIN=https://yourdomain.com # Publicly accessible domain for FastAPI webhook (Needed for payment confirmation webhook)

# FastAPI Admin Panel & JWT
SECRET_KEY=a_very_strong_and_long_random_secret_key_for_jwt # For JWT token generation
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_strong_admin_password

# Redis (Optional, if connecting from outside Docker network directly)
# REDIS_HOST=redis
# REDIS_PORT=6379
```

### 3.1. How to Obtain API Keys and Tokens:

*   **Telegram API ID & Hash (`TELEGRAM_API_ID`, `TELEGRAM_API_HASH`):**
    1.  Go to [my.telegram.org](https://my.telegram.org).
    2.  Log in with your Telegram account.
    3.  Click on "API development tools" and create a new application.
    4.  You will find the `api_id` and `api_hash`.
*   **Telegram Bot Token (`TELEGRAM_BOT_TOKEN`, `BOT_USERNAME`):**
    1.  Open Telegram and search for "BotFather".
    2.  Start a chat with BotFather and send the `/newbot` command.
    3.  Follow the instructions to choose a name and username for your bot. The username will be your `BOT_USERNAME`.
    4.  BotFather will provide you with an HTTP API token (`TELEGRAM_BOT_TOKEN`).
*   **Exchange API Keys (`EXCHANGE_API_KEY`, `EXCHANGE_SECRET_KEY`):**
    1.  Sign up for an account on a cryptocurrency exchange that CCXT supports (e.g., Binance, KuCoin).
    2.  Navigate to the API Management section of your exchange account.
    3.  Create new API keys. Ensure they have permissions for reading balances and fetching market data. Trading permissions are not strictly needed for current features but might be for future ones.
    4.  **Security Note:** For development, consider using testnet API keys if your exchange provides them.
*   **Payment Provider Token (`PAYMENT_PROVIDER_TOKEN`):**
    1.  In BotFather, select your bot.
    2.  Go to "Bot Settings" -> "Payments".
    3.  Choose a payment provider (e.g., Stripe, or select "TEST MODE" to use Telegram's test provider).
    4.  Follow the instructions to connect the provider. You will receive a token.
*   **`SECRET_KEY` (for JWT):**
    *   Generate a long, random string. You can use Python's `secrets` module: `python -c "import secrets; print(secrets.token_hex(32))"`

## 4. Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  **Set up the Environment File:**
    *   Create a `.env` file in the root directory.
    *   Copy the content from the "Example `.env` structure" section above into your `.env` file.
    *   Carefully fill in all the placeholder values (`YOUR_...`) with your actual API keys, tokens, and desired configurations.
3.  **Build and Run Docker Containers:**
    *   Ensure Docker and Docker Compose are running.
    *   Open a terminal in the project's root directory.
    *   Run the following command:
        ```bash
        docker-compose up --build -d
        ```
    *   The `--build` flag ensures images are built fresh. The `-d` flag runs containers in detached mode.
    *   Building the `bot` container might take some time the first time due to TA-Lib compilation.

## 5. Running the Bot

*   If the `docker-compose up --build -d` command was successful, all services (bot, web server, database, Redis, Celery) should be running.
*   **Bot Interaction:** Open Telegram and search for your bot's username (that you configured with BotFather). Start a chat with it and try the `/start` command.
*   **View Logs:** To view logs for all services:
    ```bash
    docker-compose logs -f
    ```
    To view logs for a specific service (e.g., the bot):
    ```bash
    docker-compose logs -f bot
    ```
*   **Stopping the Bot:**
    ```bash
    docker-compose down
    ```

## 6. Accessing the Admin Panel

*   Once the services are running, the FastAPI web application (which includes the admin panel) will be available.
*   Open your web browser and navigate to: `http://localhost:8000/admin`
    *   (The port `8000` is mapped in `docker-compose.yml`. If you changed it, use your configured port.)
*   Log in using the `ADMIN_USERNAME` and `ADMIN_PASSWORD` you set in your `.env` file.

## 7. Bot Features and Commands (Brief)

*(This section should ideally mirror the "Bot Features & Commands (Persian)" table from the specification for a quick reference. For brevity here, a few examples are listed.)*

*   **/start**: شروع/ثبت‌نام (Start/Register)
*   **/news [category]**: نمایش اخبار (Show news)
*   **/calc <type>**: ماشین‌حساب (Calculators: profit, convert, margin, whatif)
*   **/portfolio**: نمایش پرتفولیو (Show portfolio)
*   **/chart <symbol> [indicator]**: رسم نمودار تکنیکال (Technical chart)
*   **/scan create**: ایجاد اسکنر جدید (Create new scanner)
*   **/profile**: نمایش اطلاعات کاربر (Show user profile)
*   **/upgrade**: ارتقا به حساب پرو (Upgrade to Pro account)
*   **/help**: راهنما (Help)

## 8. Project Structure Overview

*(A brief overview of the main directories and their purpose)*

```
.
├── bot/                    # Pyrogram Bot, Celery tasks, utility modules
│   ├── Dockerfile
│   ├── main.py             # Main bot application
│   ├── tasks.py            # Celery tasks (e.g., news fetching)
│   ├── requirements.txt
│   └── ...                 # (calculators.py, chart_utils.py, etc.)
├── web/                    # FastAPI Web Application & Admin Panel
│   ├── Dockerfile
│   ├── main.py             # Main FastAPI application & Admin setup
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic schemas
│   ├── requirements.txt
│   └── ...                 # (admin_models.py, database.py)
├── .env                    # Environment variables (GIT IGNORED)
├── .gitignore
├── docker-compose.yml      # Docker Compose configuration
└── README.md               # This file
```

---

For detailed specifications, please refer to the original issue document.
```
