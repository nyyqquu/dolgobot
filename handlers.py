from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from database import Database
from keyboards import Keyboards
from utils import Utils
import logging

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
TRIP_NAME, TRIP_CURRENCY = range(2)
EXPENSE_AMOUNT, EXPENSE_PAYER, EXPENSE_BENEFICIARIES, EXPENSE_COMMENT, EXPENSE_CATEGORY, EXPENSE_CONFIRM = range(6)


class Handlers:
    """Обработчики команд и callback'ов"""
    
    def __init__(self, bot_username: str):
        self.bot_username = bot_username
    
    # ============ КОМАНДЫ ============
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user = update.effective_user
        chat = update.effective_chat
        
        # Если это личный чат
        if chat.type == 'private':
            # Проверяем deep link параметры
            if context.args:
                arg = context.args[0]
                
                if arg == 'cabinet':
                    return await self.show_dm_cabinet(update, context)
                
                elif arg.startswith('expense_'):
                    chat_id = int(arg.split('_')[1])
                    context.user_data['expense_chat_id'] = chat_id
                    return await self.start_expense_flow(update, context)
                
                elif arg.startswith('debts_'):
                    chat_id = int(arg.split('_')[1])
                    return await self.show_debts_dm(update, context, chat_id)
                
                elif arg.startswith('history_'):
                    chat_id = int(arg.split('_')[1])
                    return await self.show_history_dm(update, context, chat_id)
            
            # Обычный старт в ЛС
            text = (
                "👋 Привет! Я *TripSplit Bot* — помогаю считать долги в путешествиях.\n\n"
                "🎯 Основные возможности:\n"
                "• Автоматический расчёт долгов\n"
                "• Учёт общих расходов\n"
                "• Прозрачная история трат\n\n"
                "📱 Чтобы начать:\n"
                "1. Добавьте меня в групповой чат поездки\n"
                "2. Создайте поездку командой /newtrip\n"
                "3. Добавляйте расходы и следите за долгами!\n\n"
                "Выберите действие:"
            )
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.dm_main_menu()
            )
        
        else:
            # В групповом чате
            text = (
                f"👋 Привет, {user.first_name}!\n\n"
                "Я помогу вам считать расходы в путешествии.\n"
                "Используйте /newtrip чтобы создать поездку."
            )
            await update.message.reply_text(text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        text = (
            "ℹ️ *Помощь по боту*\n\n"
            "*Команды для группового чата:*\n"
            "/newtrip — Создать новую поездку\n"
            "/summary — Показать сводку долгов\n"
            "/expense — Добавить расход\n"
            "/participants — Показать участников\n\n"
            "*В личном кабинете:*\n"
            "📌 Долги — посмотреть кто кому должен\n"
            "🧾 История — все расходы поездки\n"
            "🔔 Уведомления — настроить оповещения\n\n"
            "💡 *Как работает бот:*\n"
            "1. Создайте поездку в групповом чате\n"
            "2. Добавляйте расходы через личный кабинет\n"
            "3. Бот автоматически рассчитает долги\n"
            "4. Следите за балансом в реальном времени"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def newtrip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создание новой поездки"""
        chat = update.effective_chat
        
        # Проверяем, что это групповой чат
        if chat.type == 'private':
            await update.message.reply_text(
                "❌ Эту команду нужно использовать в групповом чате поездки!"
            )
            return ConversationHandler.END
        
        # Проверяем, нет ли уже поездки
        existing_trip = Database.get_trip(chat.id)
        if existing_trip:
            await update.message.reply_text(
                f"ℹ️ Поездка *{existing_trip['name']}* уже создана для этого чата.\n\n"
                "Используйте /summary для просмотра сводки.",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        text = (
            "🎒 *Создание поездки*\n\n"
            "Создать поездку для этого чата?"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.create_trip_confirm()
        )
        
        return TRIP_NAME
    
    async def trip_create_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение создания поездки"""
        query = update.callback_query
        await query.answer()
        
        chat = query.message.chat
        
        # Используем название чата как название поездки по умолчанию
        context.user_data['trip_name'] = chat.title or "Моя поездка"
        
        text = (
            f"📝 Название поездки: *{context.user_data['trip_name']}*\n\n"
            "Теперь выберите валюту поездки:"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.currency_selection()
        )
        
        return TRIP_CURRENCY
    
    async def trip_currency_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор валюты поездки"""
        query = update.callback_query
        await query.answer()
        
        currency = query.data.split('_')[1]
        chat = query.message.chat
        user = query.from_user
        
        # Создаем поездку
        trip = Database.create_trip(
            chat_id=chat.id,
            name=context.user_data['trip_name'],
            currency=currency,
            creator_id=user.id
        )
        
        # Добавляем создателя как участника
        Database.add_participant(
            chat_id=chat.id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        
        text = (
            f"✅ Поездка *{trip['name']}* ({currency}) создана!\n\n"
            "📱 Следующие шаги:\n"
            "1. Каждый участник должен открыть личный кабинет\n"
            "2. Добавьте первый расход\n\n"
            "Нажмите кнопку ниже, чтобы открыть личный кабинет:"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.open_dm_button(self.bot_username)
        )
        
        # Показываем главное меню группы
        await query.message.reply_text(
            "🎯 Главное меню:",
            reply_markup=Keyboards.main_group_menu()
        )
        
        return ConversationHandler.END
    
    async def trip_create_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена создания поездки"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text("❌ Создание поездки отменено.")
        return ConversationHandler.END
    
    async def summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать сводку долгов"""
        chat = update.effective_chat
        
        if chat.type == 'private':
            await update.message.reply_text(
                "❌ Эту команду нужно использовать в групповом чате поездки!"
            )
            return
        
        trip = Database.get_trip(chat.id)
        if not trip:
            await update.message.reply_text(
                "❌ Поездка не найдена. Создайте её командой /newtrip"
            )
            return
        
        summary_text = Utils.format_summary(chat.id)
        
        await update.message.reply_text(
            summary_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.summary_actions(self.bot_username, chat.id)
        )
    
    async def participants_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать участников"""
        chat = update.effective_chat
        
        if chat.type == 'private':
            await update.message.reply_text(
                "❌ Эту команду нужно использовать в групповом чате!"
            )
            return
        
        trip = Database.get_trip(chat.id)
        if not trip:
            await update.message.reply_text(
                "❌ Поездка не найдена. Создайте её командой /newtrip"
            )
            return
        
        participants = Database.get_participants(chat.id)
        
        if not participants:
            text = "👥 Участников пока нет.\n\nОткройте личный кабинет, чтобы присоединиться."
        else:
            text = f"👥 *Участники поездки* ({len(participants)}):\n\n"
            for p in participants:
                text += f"• {p['first_name']}"
                if p.get('username'):
                    text += f" (@{p['username']})"
                text += "\n"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.open_dm_button(self.bot_username)
        )
    
    async def expense_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить расход (перенаправление в ЛС)"""
        chat = update.effective_chat
        
        if chat.type == 'private':
            # Если в ЛС, начинаем процесс добавления расхода
            return await self.start_expense_flow(update, context)
        
        # В групповом чате
        trip = Database.get_trip(chat.id)
        if not trip:
            await update.message.reply_text(
                "❌ Поездка не найдена. Создайте её командой /newtrip"
            )
            return
        
        text = (
            "➕ *Добавить расход*\n\n"
            "Для удобства заполним расход в личном кабинете.\n"
            "Нажмите кнопку ниже:"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.add_expense_dm_button(self.bot_username, chat.id)
        )
    
    # ============ ЛИЧНЫЙ КАБИНЕТ ============
    
    async def show_dm_cabinet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать личный кабинет"""
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user = query.from_user
            message = query.message
        else:
            user = update.effective_user
            message = update.message
        
        # Получаем активную поездку пользователя
        active_trip_id = Database.get_user_active_trip(user.id)
        
        if active_trip_id:
            trip = Database.get_trip(active_trip_id)
            text = (
                f"👤 *Личный кабинет*\n\n"
                f"🎒 Активная поездка: *{trip['name']}*\n"
                f"💱 Валюта: {trip['currency']}\n\n"
                "Выберите действие:"
            )
        else:
            text = (
                "👤 *Личный кабинет*\n\n"
                "У вас пока нет активной поездки.\n\n"
                "Чтобы начать:\n"
                "1. Добавьте бота в групповой чат\n"
                "2. Создайте поездку командой /newtrip\n"
                "3. Откройте личный кабинет из группы"
            )
        
        if update.callback_query:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.dm_main_menu() if active_trip_id else None
            )
        else:
            await message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.dm_main_menu() if active_trip_id else None
            )
    
    async def show_debts_dm(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int = None):
        """Показать долги в ЛС"""
        query = update.callback_query
        if query:
            await query.answer()
            user = query.from_user
        else:
            user = update.effective_user
        
        if not chat_id:
            chat_id = Database.get_user_active_trip(user.id)
        
        if not chat_id:
            text = "❌ Активная поездка не найдена"
            if query:
                await query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return
        
        # Добавляем пользователя как участника, если его нет
        trip = Database.get_trip(chat_id)
        if trip:
            Database.add_participant(chat_id, user.id, user.username, user.first_name)
            Database.link_user_to_trip(user.id, chat_id)
        
        text = "📌 *Мои долги*\n\nВыберите вкладку:"
        
        if query:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.debts_tabs()
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.debts_tabs()
            )
    
    async def show_i_owe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать мои долги"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        chat_id = Database.get_user_active_trip(user.id)
        
        if not chat_id:
            await query.edit_message_text("❌ Активная поездка не найдена")
            return
        
        text = Utils.format_debts_for_user(chat_id, user.id, "i_owe")
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.debts_tabs()
        )
    
    async def show_owe_me(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать кто мне должен"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        chat_id = Database.get_user_active_trip(user.id)
        
        if not chat_id:
            await query.edit_message_text("❌ Активная поездка не найдена")
            return
        
        text = Utils.format_debts_for_user(chat_id, user.id, "owe_me")
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.debts_tabs()
        )
    
    async def show_history_dm(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int = None):
        """Показать историю расходов"""
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user = query.from_user
        else:
            user = update.effective_user
        
        if not chat_id:
            chat_id = Database.get_user_active_trip(user.id)
        
        if not chat_id:
            text = "❌ Активная поездка не найдена"
            if update.callback_query:
                await query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return
        
        text = Utils.format_history(chat_id)
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="dm_back")]]
        
        if update.callback_query:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def show_notifications_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать настройки уведомлений"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        settings = Database.get_user_settings(user.id)
        current_type = settings.get('notification_type', 'balance_only')
        
        text = (
            "🔔 *Настройки уведомлений*\n\n"
            "Выберите, когда получать уведомления:"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.notification_settings(current_type)
        )
    
    async def update_notification_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновить настройки уведомлений"""
        query = update.callback_query
        await query.answer("✅ Настройки обновлены")
        
        user = query.from_user
        notif_type = query.data.split('_')[1]
        
        Database.update_user_settings(user.id, notification_type=notif_type)
        
        # Обновляем сообщение
        await self.show_notifications_settings(update, context)
    
    # ============ ДОБАВЛЕНИЕ РАСХОДА ============
    
    async def start_expense_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс добавления расхода"""
        user = update.effective_user
        
        # Получаем chat_id из контекста или user_data
        chat_id = context.user_data.get('expense_chat_id')
        if not chat_id:
            chat_id = Database.get_user_active_trip(user.id)
        
        if not chat_id:
            text = "❌ Активная поездка не найдена"
            if update.callback_query:
                await update.callback_query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return ConversationHandler.END
        
        trip = Database.get_trip(chat_id)
        if not trip:
            text = "❌ Поездка не найдена"
            if update.callback_query:
                await update.callback_query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return ConversationHandler.END
        
        # Сохраняем chat_id в контекст
        context.user_data['expense_chat_id'] = chat_id
        context.user_data['expense_data'] = {}
        
        text = (
            f"➕ *Новый расход* ({trip['currency']})\n\n"
            "Шаг 1/4: Введите сумму\n\n"
            "Например: 1250 или 1250.50"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.skip_or_cancel()
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.skip_or_cancel()
            )
        
        return EXPENSE_AMOUNT
    
    async def expense_amount_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод суммы расхода"""
        text = update.message.text
        
        # Валидация суммы
        is_valid, result = Utils.validate_amount(text)
        
        if not is_valid:
            await update.message.reply_text(
                f"❌ {result}\n\nПопробуйте ещё раз:",
                reply_markup=Keyboards.skip_or_cancel()
            )
            return EXPENSE_AMOUNT
        
        # Сохраняем сумму
        context.user_data['expense_data']['amount'] = result
        
        # Переходим к выбору плательщика
        chat_id = context.user_data['expense_chat_id']
        participants = Database.get_participants(chat_id)
        
        text = (
            f"✅ Сумма: *{result}*\n\n"
            "Шаг 2/4: Кто оплатил?"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.expense_payer_selection(participants)
        )
        
        return EXPENSE_PAYER
    
    async def expense_payer_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор плательщика"""
        query = update.callback_query
        await query.answer()
        
        payer_id = int(query.data.split('_')[1])
        context.user_data['expense_data']['payer_id'] = payer_id
        
        chat_id = context.user_data['expense_chat_id']
        participants = Database.get_participants(chat_id)
        payer_name = Utils.get_participant_name(payer_id, participants)
        
        text = (
            f"✅ Платил: *{payer_name}*\n\n"
            "Шаг 3/4: За кого этот расход?"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.expense_beneficiaries()
        )
        
        return EXPENSE_BENEFICIARIES
    
    async def expense_beneficiaries_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """За всех участников"""
        query = update.callback_query
        await query.answer()
        
        chat_id = context.user_data['expense_chat_id']
        participants = Database.get_participants(chat_id)
        
        beneficiary_ids = [p['user_id'] for p in participants]
        context.user_data['expense_data']['beneficiaries'] = beneficiary_ids
        
        text = (
            "✅ За: *всех участников*\n\n"
            "Шаг 4/4: Добавить комментарий?\n\n"
            "Или выберите категорию:"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.expense_category()
        )
        
        return EXPENSE_CATEGORY
    
    async def expense_beneficiaries_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбрать конкретных участников"""
        query = update.callback_query
        await query.answer()
        
        chat_id = context.user_data['expense_chat_id']
        participants = Database.get_participants(chat_id)
        
        context.user_data['selected_beneficiaries'] = []
        
        text = "Выберите участников (можно несколько):"
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.participant_selection(participants, [])
        )
        
        return EXPENSE_BENEFICIARIES
    
    async def expense_participant_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Переключить выбор участника"""
        query = update.callback_query
        await query.answer()
        
        user_id = int(query.data.split('_')[2])
        selected = context.user_data.get('selected_beneficiaries', [])
        
        if user_id in selected:
            selected.remove(user_id)
        else:
            selected.append(user_id)
        
        context.user_data['selected_beneficiaries'] = selected
        
        chat_id = context.user_data['expense_chat_id']
        participants = Database.get_participants(chat_id)
        
        await query.edit_message_reply_markup(
            reply_markup=Keyboards.participant_selection(participants, selected)
        )
        
        return EXPENSE_BENEFICIARIES
    
    async def expense_participant_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбрать всех участников"""
        query = update.callback_query
        await query.answer()
        
        chat_id = context.user_data['expense_chat_id']
        participants = Database.get_participants(chat_id)
        
        selected = [p['user_id'] for p in participants]
        context.user_data['selected_beneficiaries'] = selected
        
        await query.edit_message_reply_markup(
            reply_markup=Keyboards.participant_selection(participants, selected)
        )
        
        return EXPENSE_BENEFICIARIES
    
    async def expense_participant_done(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершить выбор участников"""
        query = update.callback_query
        await query.answer()
        
        selected = context.user_data.get('selected_beneficiaries', [])
        
        if not selected:
            await query.answer("❌ Выберите хотя бы одного участника", show_alert=True)
            return EXPENSE_BENEFICIARIES
        
        context.user_data['expense_data']['beneficiaries'] = selected
        
        text = (
            f"✅ За: *{len(selected)} участников*\n\n"
            "Шаг 4/4: Добавить комментарий?\n\n"
            "Или выберите категорию:"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.expense_category()
        )
        
        return EXPENSE_CATEGORY
    
    async def expense_category_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор категории"""
        query = update.callback_query
        await query.answer()
        
        category = query.data.split('_')[1]
        context.user_data['expense_data']['category'] = category
        
        text = (
            f"✅ Категория: {category}\n\n"
            "Хотите добавить комментарий?\n"
            "Напишите текст или нажмите \"Пропустить\":"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.skip_or_cancel()
        )
        
        return EXPENSE_COMMENT
    
    async def expense_category_skip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пропустить категорию"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "Хотите добавить комментарий?\n"
            "Напишите текст или нажмите \"Пропустить\":"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.skip_or_cancel()
        )
        
        return EXPENSE_COMMENT
    
    async def expense_comment_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод комментария"""
        if update.message:
            comment = update.message.text
            context.user_data['expense_data']['comment'] = comment
        
        # Показываем подтверждение
        return await self.expense_show_confirm(update, context)
    
    async def expense_comment_skip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пропустить комментарий"""
        query = update.callback_query
        await query.answer()
        
        # Показываем подтверждение
        return await self.expense_show_confirm(update, context)
    
    async def expense_show_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать подтверждение расхода"""
        expense_data = context.user_data['expense_data']
        chat_id = context.user_data['expense_chat_id']
        
        trip = Database.get_trip(chat_id)
        participants = Database.get_participants(chat_id)
        
        amount = expense_data['amount']
        payer_name = Utils.get_participant_name(expense_data['payer_id'], participants)
        beneficiary_names = [
            Utils.get_participant_name(b_id, participants)
            for b_id in expense_data['beneficiaries']
        ]
        category = expense_data.get('category', '')
        comment = expense_data.get('comment', 'Без комментария')
        
        text = (
            "📝 *Подтверждение расхода*\n\n"
            f"💰 Сумма: *{Utils.format_amount(amount, trip['currency'])}*\n"
            f"👤 Платил: {payer_name}\n"
            f"👥 За: {', '.join(beneficiary_names)}\n"
        )
        
        if category:
            text += f"📁 Категория: {category}\n"
        text += f"📝 Комментарий: {comment}\n\n"
        text += "Всё верно?"
        
        if update.message:
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.expense_confirm()
            )
        else:
            query = update.callback_query
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.expense_confirm()
            )
        
        return EXPENSE_CONFIRM
    
    async def expense_save(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранить расход"""
        query = update.callback_query
        await query.answer("💾 Сохраняем...")
        
        expense_data = context.user_data['expense_data']
        chat_id = context.user_data['expense_chat_id']
        
        # Создаем расход в БД
        expense = Database.create_expense(
            chat_id=chat_id,
            amount=expense_data['amount'],
            payer_id=expense_data['payer_id'],
            beneficiaries=expense_data['beneficiaries'],
            comment=expense_data.get('comment', ''),
            category=expense_data.get('category', '')
        )
        
        trip = Database.get_trip(chat_id)
        participants = Database.get_participants(chat_id)
        payer_name = Utils.get_participant_name(expense_data['payer_id'], participants)
        
        # Уведомление в ЛС
        await query.edit_message_text(
            f"✅ Расход добавлен!\n\n"
            f"💰 {Utils.format_amount(expense_data['amount'], trip['currency'])}\n"
            f"👤 Платил: {payer_name}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Публикуем в группу
        try:
            category = expense_data.get('category', '')
            comment = expense_data.get('comment', 'расход')
            
            group_text = (
                f"✅ Расход добавлен: *{Utils.format_amount(expense_data['amount'], trip['currency'])}*\n"
                f"{category} {comment}\n"
                f"Платил: {payer_name}"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=group_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Обновляем сводку в группе
            summary_text = Utils.format_summary(chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=summary_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.summary_actions(self.bot_username, chat_id)
            )
            
        except Exception as e:
            logger.error(f"Error sending to group: {e}")
        
        # Отправляем уведомления участникам
        await self.send_expense_notifications(context, chat_id, expense, participants)
        
        # Очищаем данные
        context.user_data.clear()
        
        return ConversationHandler.END
    
    async def send_expense_notifications(self, context: ContextTypes.DEFAULT_TYPE, 
                                        chat_id: int, expense: dict, participants: list):
        """Отправить уведомления участникам"""
        trip = Database.get_trip(chat_id)
        
        for participant in participants:
            user_id = participant['user_id']
            
            # Не отправляем плательщику
            if user_id == expense['payer_id']:
                continue
            
            settings = Database.get_user_settings(user_id)
            notif_type = settings.get('notification_type', 'balance_only')
            
            # Проверяем настройки уведомлений
            if notif_type == 'off':
                continue
            
            # Для "balance_only" отправляем только если пользователь - бенефициар
            if notif_type == 'balance_only' and user_id not in expense['beneficiaries']:
                continue
            
            try:
                payer_name = Utils.get_participant_name(expense['payer_id'], participants)
                text = (
                    f"🔔 *Новый расход в поездке \"{trip['name']}\"*\n\n"
                    f"💰 Сумма: {Utils.format_amount(expense['amount'], trip['currency'])}\n"
                    f"👤 Платил: {payer_name}\n"
                )
                
                if expense.get('comment'):
                    text += f"📝 {expense['comment']}\n"
                
                # Показываем обновленный баланс
                debts_text = Utils.format_debts_for_user(chat_id, user_id, "i_owe")
                text += f"\n{debts_text}"
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send notification to {user_id}: {e}")
    
    async def expense_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена добавления расхода"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text("❌ Добавление расхода отменено.")
        
        context.user_data.clear()
        return ConversationHandler.END
    
    # ============ CALLBACK HANDLERS ============
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Общий обработчик callback'ов"""
        query = update.callback_query
        data = query.data
        
        # Навигация в ЛС
        if data == "dm_back":
            return await self.show_dm_cabinet(update, context)
        
        elif data == "dm_debts":
            return await self.show_debts_dm(update, context)
        
        elif data == "dm_history":
            return await self.show_history_dm(update, context)
        
        elif data == "dm_notifications":
            return await self.show_notifications_settings(update, context)
        
        elif data == "debts_i_owe":
            return await self.show_i_owe(update, context)
        
        elif data == "debts_owe_me":
            return await self.show_owe_me(update, context)
        
        # Групповой чат
        elif data == "add_expense":
            return await self.expense_command(update, context)
        
        elif data == "show_summary":
            chat = query.message.chat
            trip = Database.get_trip(chat.id)
            if trip:
                summary_text = Utils.format_summary(chat.id)
                await query.edit_message_text(
                    summary_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=Keyboards.summary_actions(self.bot_username, chat.id)
                )
            await query.answer()
        
        elif data == "show_participants":
            await query.answer()
            chat = query.message.chat
            trip = Database.get_trip(chat.id)
            if trip:
                participants = Database.get_participants(chat.id)
                text = f"👥 *Участники* ({len(participants)}):\n\n"
                for p in participants:
                    text += f"• {p['first_name']}\n"
                await query.edit_message_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
                    ]])
                )
        
        elif data == "back_to_menu":
            await query.answer()
            await query.edit_message_text(
                "🎯 Главное меню:",
                reply_markup=Keyboards.main_group_menu()
            )
        
        else:
            await query.answer()
