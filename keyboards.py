from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config import CURRENCIES, EXPENSE_CATEGORIES


class Keyboards:
    """Класс для создания ]клавиатур"""
    
      @staticmethod
    def main_group_menu():
        """Главное меню для группового чата"""
        keyboard = [
            [InlineKeyboardButton("➕ Добавить расход", callback_data="add_expense")],
            [InlineKeyboardButton("📌 Сводка долгов", callback_data="show_summary")],
            [InlineKeyboardButton("🧑‍🤝‍🧑 Участники", callback_data="show_participants")],
            [InlineKeyboardButton("🗑 Очистить сообщения бота", callback_data="clear_bot_messages")]
        ]
        return InlineKeyboardMarkup(keyboard)

    
    @staticmethod
    def create_trip_confirm():
        """Подтверждение создания поездки"""
        keyboard = [
            [InlineKeyboardButton("✅ Создать", callback_data="trip_create_confirm")],
            [InlineKeyboardButton("❌ Отмена", callback_data="trip_create_cancel")]
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
    def skip_or_cancel():
        """Пропустить или отменить"""
        keyboard = [
            [InlineKeyboardButton("⏭ Пропустить", callback_data="skip")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def dm_main_menu(show_switch_trip=False):
        """Главное меню личного кабинета (ИСПРАВЛЕНО)"""
        keyboard = [
            [InlineKeyboardButton("📌 Долги", callback_data="dm_debts")],
            [InlineKeyboardButton("🧾 История", callback_data="dm_history")],
        ]
        
        if show_switch_trip:
            keyboard.append([InlineKeyboardButton("🔄 Сменить поездку", callback_data="dm_switch_trip")])
        
        keyboard.append([InlineKeyboardButton("🔔 Уведомления", callback_data="dm_notifications")])
        keyboard.append([InlineKeyboardButton("⚙️ Настройки", callback_data="dm_settings")])
        
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
            [InlineKeyboardButton("🔙 Назад", callback_data="dm_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def participant_selection(participants, selected_ids=None):
        """Выбор участников"""
        if selected_ids is None:
            selected_ids = []
        
        keyboard = []
        for participant in participants:
            user_id = participant['user_id']
            name = participant['first_name']
            checkmark = "✅ " if user_id in selected_ids else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{checkmark}{name}", 
                    callback_data=f"participant_toggle_{user_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("👥 Выбрать всех", callback_data="participant_all"),
            InlineKeyboardButton("✅ Готово", callback_data="participant_done")
        ])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def expense_payer_selection(participants):
        """Выбор плательщика"""
        keyboard = []
        for participant in participants:
            keyboard.append([
                InlineKeyboardButton(
                    participant['first_name'],
                    callback_data=f"payer_{participant['user_id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def expense_beneficiaries():
        """За кого расход"""
        keyboard = [
            [InlineKeyboardButton("👥 За всех", callback_data="beneficiaries_all")],
            [InlineKeyboardButton("✅ Выбрать участников", callback_data="beneficiaries_select")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def expense_category():
        """Выбор категории расхода"""
        keyboard = []
        row = []
        for emoji, name in EXPENSE_CATEGORIES.items():
            row.append(InlineKeyboardButton(f"{emoji} {name}", callback_data=f"category_{emoji}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("⏭ Пропустить", callback_data="category_skip")])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def expense_confirm():
        """Подтверждение расхода"""
        keyboard = [
            [InlineKeyboardButton("✅ Сохранить", callback_data="expense_save")],
            [InlineKeyboardButton("✏️ Изменить", callback_data="expense_edit")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
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
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="dm_back")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def expense_actions(expense_id, is_author=False):
        """Действия с расходом"""
        keyboard = []
        if is_author:
            keyboard.append([
                InlineKeyboardButton("✏️ Редактировать", callback_data=f"expense_edit_{expense_id}"),
                InlineKeyboardButton("🗑 Удалить", callback_data=f"expense_delete_{expense_id}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="dm_history")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def delete_confirm(expense_id):
        """Подтверждение удаления"""
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"expense_delete_confirm_{expense_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="dm_history")]
        ]
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
    def add_expense_dm_button(bot_username, chat_id):
        """Кнопка добавления расхода через ЛС"""
        keyboard = [
            [InlineKeyboardButton(
                "✍️ Заполнить расход в ЛС",
                url=f"https://t.me/{bot_username}?start=expense_{chat_id}"
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
            [InlineKeyboardButton(
                "➕ Добавить расход",
                url=f"https://t.me/{bot_username}?start=expense_{chat_id}"
            )]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def debt_pay_button(debt_id):
        """Кнопка оплаты долга"""
        keyboard = [
            [InlineKeyboardButton("✅ Вернул долг", callback_data=f"pay_debt_{debt_id}")],
            [InlineKeyboardButton("🔙 Назад к долгам", callback_data="debts_i_owe")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def my_debts_list(debts):
        """Список моих долгов с кнопками оплаты"""
        keyboard = []
        
        for debt in debts:
            group_info = debt.get('group_info', {})
            description = group_info.get('description', 'Долг')[:30]
            category = group_info.get('category', '💸')
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{category} {description} - {debt['amount']:.0f}",
                    callback_data=f"show_debt_{debt['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="dm_back")])
        return InlineKeyboardMarkup(keyboard)
