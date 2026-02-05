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
        
        if chat.type == 'private':
            if context.args:
                arg = context.args[0]
                
                if arg == 'cabinet':
                    return await self.show_dm_cabinet(update, context)
                
                elif arg.startswith('expense_'):
                    chat_id = int(arg.split('_')[1])
                    context.user_data['expense_chat_id'] = chat_id
                    return await self.start_debt_flow(update, context)
                
                elif arg.startswith('debts_'):
                    chat_id = int(arg.split('_')[1])
                    return await self.show_debts_dm(update, context, chat_id)
                
                elif arg.startswith('history_'):
                    chat_id = int(arg.split('_')[1])
                    return await self.show_history_dm(update, context, chat_id)
            
            active_trip_id = Database.get_user_active_trip(user.id)
            
            if active_trip_id:
                trip = Database.get_trip(active_trip_id)
                if trip:
                    text = (
                        f"👤 *Личный кабинет*\n\n"
                        f"🎒 Активная поездка: *{trip['name']}*\n"
                        f"💱 Валюта: {trip['currency']}\n\n"
                        "Выберите действие:"
                    )
                    await update.message.reply_text(
                        text,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=Keyboards.dm_main_menu()
                    )
                    return
            
            text = (
                "👋 Привет! Я *TripSplit Bot* — помогаю считать долги в путешествиях.\n\n"
                "🎯 Основные возможности:\n"
                "• Автоматический расчёт долгов\n"
                "• Учёт общих расходов\n"
                "• Прозрачная история трат\n\n"
                "📱 Чтобы начать:\n"
                "1. Добавьте меня в групповой чат поездки\n"
                "2. Создайте поездку командой /newtrip\n"
                "3. Все участники чата автоматически добавятся\n"
                "4. Добавляйте долги через @упоминания\n\n"
                "💡 У вас пока нет активной поездки."
            )
            
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        
        else:
            trip = Database.get_trip(chat.id)
            if trip:
                text = (
                    f"🎒 *{trip['name']}*\n"
                    f"💱 Валюта: {trip['currency']}\n\n"
                    "Управление поездкой:"
                )
                await update.message.reply_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=Keyboards.main_group_menu()
                )
            else:
                text = (
                    f"👋 Привет! Я помогу вести учёт расходов.\n\n"
                    "Создайте поездку командой /newtrip"
                )
                await update.message.reply_text(text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        text = (
            "ℹ️ *Помощь по боту*\n\n"
            "*Команды для группового чата:*\n"
            "/newtrip — Создать новую поездку\n"
            "/start — Показать меню поездки\n"
            "/summary — Показать сводку долгов\n"
            "/expense — Добавить долг\n"
            "/participants — Показать участников\n\n"
            "*Формат добавления долга:*\n"
            "`сумма @участник1 @участник2 описание`\n"
            "Пример: `2000 @саша @никита такси`\n\n"
            "*В личном кабинете:*\n"
            "📌 Долги — посмотреть свои долги\n"
            "🧾 История — все долги поездки\n"
            "✅ Вернул долг — отметить возврат"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def newtrip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создание новой поездки"""
        chat = update.effective_chat
        
        if chat.type == 'private':
            await update.message.reply_text(
                "❌ Эту команду нужно использовать в групповом чате поездки!"
            )
            return ConversationHandler.END
        
        existing_trip = Database.get_trip(chat.id)
        if existing_trip:
            text = (
                f"ℹ️ Поездка *{existing_trip['name']}* уже создана для этого чата.\n\n"
                "Используйте /start для управления."
            )
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return ConversationHandler.END
        
        text = (
            "🎒 *Создание поездки*\n\n"
            "Как назовём поездку?\n"
            "Напишите название или нажмите кнопку, чтобы использовать название чата."
        )
        
        keyboard = [
            [InlineKeyboardButton(f"✅ {chat.title}", callback_data="use_chat_name")],
            [InlineKeyboardButton("❌ Отмена", callback_data="trip_create_cancel")]
        ]
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        context.user_data['default_trip_name'] = chat.title or "Моя поездка"
        
        return TRIP_NAME
    
    async def trip_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод названия поездки"""
        trip_name = update.message.text
        
        if len(trip_name) > 100:
            await update.message.reply_text("❌ Название слишком длинное (макс. 100 символов). Попробуйте ещё раз:")
            return TRIP_NAME
        
        context.user_data['trip_name'] = trip_name
        
        text = (
            f"📝 Название: *{trip_name}*\n\n"
            "Теперь выберите валюту поездки:"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.currency_selection()
        )
        
        return TRIP_CURRENCY
    
    async def use_chat_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Использовать название чата как название поездки"""
        query = update.callback_query
        await query.answer()
        
        trip_name = context.user_data.get('default_trip_name', 'Моя поездка')
        context.user_data['trip_name'] = trip_name
        
        text = (
            f"📝 Название: *{trip_name}*\n\n"
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
        
        trip = Database.create_trip(
            chat_id=chat.id,
            name=context.user_data['trip_name'],
            currency=currency,
            creator_id=user.id
        )
        
        try:
            chat_members = await context.bot.get_chat_administrators(chat.id)
            added_count = 0
            
            for member in chat_members:
                if not member.user.is_bot:
                    Database.add_participant(
                        chat_id=chat.id,
                        user_id=member.user.id,
                        username=member.user.username,
                        first_name=member.user.first_name
                    )
                    added_count += 1
            
            participants_text = f"👥 Автоматически добавлено участников: {added_count}"
        except Exception as e:
            logger.error(f"Error getting chat members: {e}")
            Database.add_participant(
                chat_id=chat.id,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            participants_text = "👥 Добавлен создатель поездки"
        
        text = (
            f"✅ Поездка *{trip['name']}* ({currency}) создана!\n\n"
            f"{participants_text}\n\n"
            "📱 Следующие шаги:\n"
            "1. Откройте личный кабинет (кнопка ниже)\n"
            "2. Добавьте первый долг\n"
            "3. Следите за долгами в сводке"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.open_dm_button(self.bot_username)
        )
        
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"🎯 *{trip['name']}* — управление:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.main_group_menu()
        )
        
        summary_text = f"📌 *Сводка долгов ({currency})*\n\n✅ Пока долгов нет"
        await context.bot.send_message(
            chat_id=chat.id,
            text=summary_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.summary_actions(self.bot_username, chat.id)
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
            text = "👥 Участников пока нет."
        else:
            text = f"👥 *Участники поездки \"{trip['name']}\"* ({len(participants)}):\n\n"
            for p in participants:
                text += f"• {p['first_name']}"
                if p.get('username'):
                    text += f" (@{p['username']})"
                text += "\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def expense_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить долг (перенаправление в ЛС)"""
        chat = update.effective_chat
        
        if chat.type == 'private':
            return await self.start_debt_flow(update, context)
        
        trip = Database.get_trip(chat.id)
        if not trip:
            await update.message.reply_text(
                "❌ Поездка не найдена. Создайте её командой /newtrip"
            )
            return
        
        text = (
            "➕ *Добавить долг*\n\n"
            "Для удобства заполним долг в личном кабинете.\n"
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
                "3. Вы автоматически добавитесь в поездку"
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
        """Показать мои долги с кнопками"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        chat_id = Database.get_user_active_trip(user.id)
        
        if not chat_id:
            await query.edit_message_text("❌ Активная поездка не найдена")
            return
        
        my_debts = Database.get_my_debts(chat_id, user.id)
        
        if not my_debts:
            text = "✅ У вас нет долгов!"
            await query.edit_message_text(
                text,
                reply_markup=Keyboards.debts_tabs()
            )
            return
        
        text = Utils.format_my_debts(chat_id, user.id)
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.my_debts_list(my_debts)
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
        
        text = Utils.format_debts_to_me(chat_id, user.id)
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.debts_tabs()
        )
    
    async def show_history_dm(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int = None):
        """Показать историю долгов"""
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
        current_type = settings.get('notification_type', 'all')
        
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
        
        await self.show_notifications_settings(update, context)
    # ============ ДОБАВЛЕНИЕ ДОЛГА (НОВАЯ ЛОГИКА) ============
    
    async def start_debt_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс добавления долга"""
        user = update.effective_user
        
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
        
        context.user_data['expense_chat_id'] = chat_id
        context.user_data['expense_data'] = {}
        
        participants = Database.get_participants(chat_id)
        participants_text = ", ".join([f"@{p['username']}" if p.get('username') else p['first_name'] for p in participants])
        
        text = (
            f"➕ *Новый долг* ({trip['currency']})\n\n"
            "🎯 *Как это работает:*\n"
            "1. Вы пишете сумму и участников через @\n"
            "2. Бот делит сумму на всех участников\n"
            "3. Плательщик не должен сам себе\n"
            "4. Все получают уведомления\n\n"
            "📝 *Формат:*\n"
            "`Сумма @участник1 @участник2 описание`\n\n"
            "💡 *Пример:*\n"
            "`2000 @саша @никита @катя такси в аэропорт`\n\n"
            f"👥 Доступные участники:\n{participants_text}\n\n"
            "✍️ Напишите ваш долг:"
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
        """Новая логика: парсим всё из одного сообщения"""
        text = update.message.text
        chat_id = context.user_data['expense_chat_id']
        participants = Database.get_participants(chat_id)
        
        parts = text.split()
        
        is_valid, amount = Utils.validate_amount(parts[0])
        if not is_valid:
            await update.message.reply_text(
                f"❌ {amount}\n\n"
                "Начните сообщение с суммы, например:\n"
                "`2000 @саша @никита такси`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.skip_or_cancel()
            )
            return EXPENSE_AMOUNT
        
        mentioned_ids = Utils.parse_participants_from_text(text, participants)
        
        if len(mentioned_ids) < 2:
            await update.message.reply_text(
                "❌ Укажите минимум 2 участников через @ или по имени\n\n"
                "Пример: `2000 @никита @саша такси`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.skip_or_cancel()
            )
            return EXPENSE_AMOUNT
        
        description_parts = []
        for part in parts[1:]:
            if not part.startswith('@') and not any(p['first_name'].lower() in part.lower() for p in participants):
                description_parts.append(part)
        
        description = ' '.join(description_parts) if description_parts else "Общий расход"
        
        context.user_data['expense_data'] = {
            'amount': amount,
            'participants': mentioned_ids,
            'description': description
        }
        
        mentioned_participants = [p for p in participants if p['user_id'] in mentioned_ids]
        
        text = (
            f"✅ Сумма: *{amount}*\n"
            f"👥 Участники: {len(mentioned_ids)}\n"
            f"📝 Описание: {description}\n\n"
            "💳 Кто заплатил?"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.expense_payer_selection(mentioned_participants)
        )
        
        return EXPENSE_PAYER
    
    async def expense_payer_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор плательщика"""
        query = update.callback_query
        await query.answer()
        
        payer_id = int(query.data.split('_')[1])
        context.user_data['expense_data']['payer_id'] = payer_id
        
        text = "📁 Выберите категорию (опционально):"
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.expense_category()
        )
        
        return EXPENSE_CATEGORY
    
    async def expense_category_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор категории"""
        query = update.callback_query
        await query.answer()
        
        category = query.data.split('_')[1]
        context.user_data['expense_data']['category'] = category
        
        return await self.expense_confirm_and_save(update, context)
    
    async def expense_category_skip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пропустить категорию"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['expense_data']['category'] = '💸'
        
        return await self.expense_confirm_and_save(update, context)
    
    async def expense_confirm_and_save(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение и сохранение"""
        query = update.callback_query
        
        expense_data = context.user_data['expense_data']
        chat_id = context.user_data['expense_chat_id']
        
        trip = Database.get_trip(chat_id)
        participants = Database.get_participants(chat_id)
        
        amount = expense_data['amount']
        payer_id = expense_data['payer_id']
        debt_participants = expense_data['participants']
        description = expense_data['description']
        category = expense_data.get('category', '💸')
        
        payer_name = Utils.get_participant_name(payer_id, participants)
        
        debt_result = Database.create_debt(
            chat_id=chat_id,
            amount=amount,
            payer_id=payer_id,
            participants=debt_participants,
            description=description,
            category=category
        )
        
        if not debt_result:
            await query.edit_message_text("❌ Ошибка создания долга")
            return ConversationHandler.END
        
        debtors = [p for p in debt_participants if p != payer_id]
        amount_per_person = amount / len(debtors)
        
        await query.edit_message_text(
            f"✅ Долг добавлен!\n\n"
            f"{category} *{description}*\n"
            f"💰 Сумма: {Utils.format_amount(amount, trip['currency'])}\n"
            f"👤 Заплатил: {payer_name}\n"
            f"💳 На человека: {Utils.format_amount(amount_per_person, trip['currency'])}\n\n"
            f"Участников: {len(debt_participants)}\n"
            f"Должников: {len(debtors)}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            debtor_names = [Utils.get_participant_name(d, participants) for d in debtors]
            
            group_text = (
                f"💸 *Новый долг*\n\n"
                f"{category} *{description}*\n"
                f"💰 Сумма: {Utils.format_amount(amount, trip['currency'])}\n"
                f"👤 Заплатил: {payer_name}\n"
                f"💳 Должны по: {Utils.format_amount(amount_per_person, trip['currency'])}\n\n"
                f"👥 Должники: {', '.join(debtor_names)}"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=group_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            summary_text = Utils.format_summary(chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=summary_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.summary_actions(self.bot_username, chat_id)
            )
            
        except Exception as e:
            logger.error(f"Error sending to group: {e}")
        
        await self.send_debt_notifications(context, chat_id, debt_result, participants, trip)
        
        context.user_data.clear()
        return ConversationHandler.END
    
    async def send_debt_notifications(self, context: ContextTypes.DEFAULT_TYPE, 
                                      chat_id: int, debt_result: dict, 
                                      participants: list, trip: dict):
        """Отправить пуш-уведомления о новом долге"""
        group_data = debt_result['group_data']
        individual_debts = debt_result['debts']
        
        payer_id = group_data['payer_id']
        payer_name = Utils.get_participant_name(payer_id, participants)
        description = group_data['description']
        category = group_data.get('category', '💸')
        
        for debt in individual_debts:
            debtor_id = debt['debtor_id']
            amount = debt['amount']
            
            settings = Database.get_user_settings(debtor_id)
            if settings.get('notification_type') == 'off':
                continue
            
            try:
                text = (
                    f"🔔 *Новый долг в \"{trip['name']}\"*\n\n"
                    f"{category} {description}\n"
                    f"💰 Вы должны {payer_name}: *{Utils.format_amount(amount, trip['currency'])}*\n\n"
                    f"Нажмите /start чтобы посмотреть все долги"
                )
                
                await context.bot.send_message(
                    chat_id=debtor_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send notification to {debtor_id}: {e}")
        
        try:
            total_owed = sum(d['amount'] for d in individual_debts)
            text = (
                f"✅ *Долг создан в \"{trip['name']}\"*\n\n"
                f"{category} {description}\n"
                f"💰 Вам должны: *{Utils.format_amount(total_owed, trip['currency'])}*\n"
                f"👥 Должников: {len(individual_debts)}"
            )
            
            await context.bot.send_message(
                chat_id=payer_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send notification to payer {payer_id}: {e}")
    
    async def expense_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена добавления долга"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text("❌ Добавление долга отменено.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # ============ ВОЗВРАТ ДОЛГА ============
    
    async def show_debt_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детали конкретного долга с кнопкой оплаты"""
        query = update.callback_query
        await query.answer()
        
        debt_id = query.data.split('_')[2]
        
        from firebase_admin import firestore
        db_instance = firestore.client()
        
        debt_doc = db_instance.collection('debts').document(debt_id).get()
        if not debt_doc.exists:
            await query.edit_message_text("❌ Долг не найден")
            return
        
        debt = debt_doc.to_dict()
        chat_id = debt['chat_id']
        trip = Database.get_trip(chat_id)
        participants = Database.get_participants(chat_id)
        
        debt_group = db_instance.collection('debt_groups').document(debt['debt_group_id']).get()
        if debt_group.exists:
            group_data = debt_group.to_dict()
            description = group_data.get('description', 'Долг')
            category = group_data.get('category', '💸')
        else:
            description = "Долг"
            category = "💸"
        
        creditor_name = Utils.get_participant_name(debt['creditor_id'], participants)
        amount = Utils.format_amount(debt['amount'], trip['currency'])
        
        text = (
            f"{category} *{description}*\n\n"
            f"💰 Сумма: *{amount}*\n"
            f"👤 Должен: {creditor_name}\n"
            f"📅 Создан: {debt['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Вернули долг?"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.debt_pay_button(debt_id)
        )
    
    async def pay_debt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отметить долг как возвращенный"""
        query = update.callback_query
        await query.answer("✅ Долг отмечен как возвращенный!")
        
        debt_id = query.data.split('_')[2]
        
        debt_data = Database.mark_debt_paid(debt_id)
        
        if not debt_data:
            await query.edit_message_text("❌ Ошибка при обновлении долга")
            return
        
        chat_id = debt_data['chat_id']
        creditor_id = debt_data['creditor_id']
        debtor_id = debt_data['debtor_id']
        amount = debt_data['amount']
        
        trip = Database.get_trip(chat_id)
        participants = Database.get_participants(chat_id)
        
        debtor_name = Utils.get_participant_name(debtor_id, participants)
        creditor_name = Utils.get_participant_name(creditor_id, participants)
        
        from firebase_admin import firestore
        db_instance = firestore.client()
        
        debt_group = db_instance.collection('debt_groups').document(debt_data['debt_group_id']).get()
        description = "Долг"
        category = "💸"
        if debt_group.exists:
            group_data = debt_group.to_dict()
            description = group_data.get('description', 'Долг')
            category = group_data.get('category', '💸')
        
        await query.edit_message_text(
            f"✅ *Долг возвращен!*\n\n"
            f"{category} {description}\n"
            f"💰 Сумма: {Utils.format_amount(amount, trip['currency'])}\n"
            f"👤 Кредитор: {creditor_name}\n\n"
            f"Спасибо за честность! 🎉",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            text = (
                f"💰 *Долг возвращен!*\n\n"
                f"👤 {debtor_name} вернул вам долг:\n"
                f"{category} {description}\n"
                f"💵 Сумма: *{Utils.format_amount(amount, trip['currency'])}*\n\n"
                f"Поездка: {trip['name']}"
            )
            
            await context.bot.send_message(
                chat_id=creditor_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to notify creditor: {e}")
        
        try:
            summary_text = Utils.format_summary(chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ {debtor_name} вернул долг {creditor_name}\n\n{summary_text}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to update group: {e}")
    
    # ============ CALLBACK HANDLERS ============
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Общий обработчик callback'ов"""
        query = update.callback_query
        data = query.data
        
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
        
        elif data == "debts_refresh":
            return await self.show_debts_dm(update, context)
        
        elif data.startswith("show_debt_"):
            return await self.show_debt_detail(update, context)
        
        elif data.startswith("pay_debt_"):
            return await self.pay_debt(update, context)
        
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
                    text += f"• {p['first_name']}"
                    if p.get('username'):
                        text += f" (@{p['username']})"
                    text += "\n"
                await query.edit_message_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
                    ]])
                )
        
        elif data == "back_to_menu":
            await query.answer()
            chat = query.message.chat
            trip = Database.get_trip(chat.id)
            if trip:
                await query.edit_message_text(
                    f"🎯 *{trip['name']}* — управление:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=Keyboards.main_group_menu()
                )
        
        else:
            await query.answer()
