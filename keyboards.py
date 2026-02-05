from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CURRENCIES


class Keyboards:
    """Класс для создания клавиатур"""
    
    @staticmethod
    def main_group_menu():
        """Главное меню для группового чата"""
        keyboard = [
            [InlineKeyboardButton("➕ Добавить долг", callback_data="show_add_expense_info")],
            [InlineKeyboardButton("📌 Сводка долгов", callback_data="show_summary")],
            [InlineKeyboardButton("🧑‍🤝‍🧑 Участники", callback_data="show_participants")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def currency_selection():
        """Выбор валюты"""
        keyboard = []
        row = []
        for i, currency in enumerate(CURRENCIES):
            row.append(InlineKeyboardButton(currency, callback_data=f"currency_{currency}"))
            if (i + 1) % 3 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="currency_cancel")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def dm_main_menu(show_switch_trip=False):
        """Главное меню личного кабинета"""
        keyboard = [
            [InlineKeyboardButton("📌 Долги", callback_data="dm_debts")],
            [InlineKeyboardButton("🧾 История", callback_data="dm_history")],
        ]
        
        if show_switch_trip:
            keyboard.append([InlineKeyboardButton("🔄 Сменить поездку", callback_data="dm_switch_trip")])
        
        keyboard.append([InlineKeyboardButton("🔔 Уведомления", callback_data="dm_notifications")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def debts_tabs():
        """Вкладки долгов"""
        keyboard = [
            [
                InlineKeyboardButton("💰 Я должен", callback_data="debts_i_owe"),
                InlineKeyboardButton("💵 Мне должны", callback_data="debts_owe_me")
            ],
            [InlineKeyboardButton("🔄 Обновить", callback_data="debts_refresh")],
            [InlineKeyboardButton("🔙 На главную", callback_data="dm_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def notification_settings(current_type):
        """Настройки уведомлений"""
        options = [
            ("all", "✅ Все уведомления"),
            ("off", "❌ Выключить")
        ]
        
        keyboard = []
        for option_value, option_text in options:
            prefix = "✔️ " if option_value == current_type else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{prefix}{option_text}",
                    callback_data=f"notif_{option_value}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 На главную", callback_data="dm_back")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def open_dm_button(bot_username):
        """Кнопка открытия ЛС"""
        keyboard = [
            [InlineKeyboardButton(
                "🧑 Открыть личный кабинет",
                url=f"https://t.me/{bot_username}?start=cabinet"
            )]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def summary_actions(bot_username, chat_id):
        """Действия под сводкой"""
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="show_summary")],
            [
                InlineKeyboardButton(
                    "📌 Мои долги",
                    url=f"https://t.me/{bot_username}?start=debts_{chat_id}"
                ),
                InlineKeyboardButton(
                    "🧾 История",
                    url=f"https://t.me/{bot_username}?start=history_{chat_id}"
                )
            ],
            [InlineKeyboardButton("🔙 На главную", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def debt_pay_button(debt_id):
        """Кнопка оплаты долга (для должника)"""
        keyboard = [
            [InlineKeyboardButton("✅ Вернул долг", callback_data=f"pay_debt_{debt_id}")],
            [InlineKeyboardButton("🔙 К долгам", callback_data="debts_i_owe")],
            [InlineKeyboardButton("🏠 На главную", callback_data="dm_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def my_debts_list(debts):
        """Список моих долгов с кнопками оплаты (должник)"""
        keyboard = []
        
        for debt in debts:
            group_info = debt.get('group_info', {})
            description = group_info.get('description', 'Долг')
            category = group_info.get('category', '💸')
            
            max_length = 30
            if len(description) > max_length:
                description = description[:max_length] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{category} {description}",
                    callback_data=f"show_debt_{debt['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 На главную", callback_data="dm_back")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def debts_to_me_list(debts):
        """Список долгов мне с кнопками подтверждения (кредитор)"""
        keyboard = []
        
        for debt in debts:
            group_info = debt.get('group_info', {})
            description = group_info.get('description', 'Долг')
            category = group_info.get('category', '💸')
            
            max_length = 30
            if len(description) > max_length:
                description = description[:max_length] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{category} {description}",
                    callback_data=f"show_debt_creditor_{debt['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 На главную", callback_data="dm_back")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def debt_confirm_button(debt_id):
        """Кнопка подтверждения возврата долга (для кредитора)"""
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить возврат", callback_data=f"confirm_debt_{debt_id}")],
            [InlineKeyboardButton("🔙 К долгам", callback_data="debts_owe_me")],
            [InlineKeyboardButton("🏠 На главную", callback_data="dm_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
