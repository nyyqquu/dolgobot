import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN', '8287466021:AAHsTS7NKl3KirUrk82Q5tIrURd_oIu7srk')

# Firebase
FIREBASE_CREDENTIALS_PATH = 'firebase_key.json'

# Currencies
CURRENCIES = ['EUR', 'USD', 'RUB', 'GEL', 'TRY', 'THB']

# Default currency
DEFAULT_CURRENCY = 'EUR'

# Notification types
NOTIFICATION_BALANCE_ONLY = 'balance_only'
NOTIFICATION_ALL_EXPENSES = 'all_expenses'
NOTIFICATION_DAILY_DIGEST = 'daily_digest'
NOTIFICATION_OFF = 'off'

# Expense categories
EXPENSE_CATEGORIES = {
    '🍽': 'Еда',
    '🚕': 'Такси',
    '🏨': 'Жильё',
    '🎟': 'Билеты',
    '🛒': 'Покупки',
    '🎉': 'Развлечения'
}
