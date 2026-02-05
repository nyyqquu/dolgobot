import os
from dotenv import load_dotenv

load_dotenv()

# ============ TELEGRAM BOT ============

BOT_TOKEN = os.getenv('BOT_TOKEN', '8287466021:AAHsTS7NKl3KirUrk82Q5tIrURd_oIu7srk')

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
