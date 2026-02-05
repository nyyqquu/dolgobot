import os
from dotenv import load_dotenv

load_dotenv()

# ============ TELEGRAM BOT ============

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError(
        "❌ BOT_TOKEN not found!\n"
        "Set it in Railway environment variables or create .env file:\n"
        "BOT_TOKEN=your_bot_token_here"
    )

# ============ FIREBASE ============

FIREBASE_CREDENTIALS_PATH = 'firebase_key.json'

# ============ CURRENCIES ============

CURRENCIES = ['EUR', 'USD', 'RUB', 'THB', 'GEL', 'TRY', 'CNY']
DEFAULT_CURRENCY = 'EUR'

# ============ NOTIFICATIONS ============

NOTIFICATION_ALL = 'all'
NOTIFICATION_OFF = 'off'

# ============ EXPENSE CATEGORIES ============

EXPENSE_CATEGORIES = {
    '💸': 'Общее',
    '🍽': 'Еда',
    '🚕': 'Такси',
    '🏨': 'Жильё',
    '🎟': 'Билеты',
    '🛒': 'Покупки',
    '🎉': 'Развлечения'
}

DEFAULT_CATEGORY = '💸'
