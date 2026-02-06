from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from database import Database
from keyboards import Keyboards
from utils import Utils
import logging
import asyncio

logger = logging.getLogger(__name__)

TRIP_NAME, TRIP_CURRENCY = range(2)


class Handlers:
    """Обработчики команд и callback'ов"""
    
    def __init__(self, bot_username: str):
        self.bot_username = bot_username
    
    async def handle_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сообщений в группе для автодобавления участников"""
        user = update.effective_user
        chat = update.effective_chat
        
        if user.is_bot:
            return
        
        trip = Database.get_trip(chat.id)
        if trip:
            Database.add_participant(
                chat_id=chat.id,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            Database.link_user_to_trip(user.id, chat.id)
    
    async def handle_private_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений в ЛС"""
        return await self.show_dm_cabinet(update, context)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user = update.effective_user
        chat = update.effective_chat
        
        if chat.type == 'private':
            if context.args:
                arg = context.args[0]
                
                if arg == 'cabinet':
                    return await self.show_dm_cabinet(update, context)
                
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
                        f"👤 Личный кабинет\n\n"
                        f"🎒 Активная поездка: {trip['name']}\n"
                        f"💱 Валюта: {trip['currency']}\n\n"
                        "Выберите действие:"
                    )
                    await update.message.reply_text(
                        text,
                        reply_markup=Keyboards.dm_main_menu()
                    )
                    return
            
            text = (
                "👋 Привет! Я TripSplit Bot — помогаю считать долги в путешествиях.\n\n"
                "🎯 Основные возможности:\n"
                "• Автоматический расчёт долгов\n"
                "• Учёт общих расходов\n"
                "• Прозрачная история трат\n\n"
                "📱 Чтобы начать:\n"
                "1. Добавьте меня в групповой чат поездки\n"
                "2. Создайте поездку командой /newtrip\n"
                "3. Пишите долги прямо в группе:\n"
                "   2000 @user описание\n"
                "   2000 THB @user описание (с валютой)\n\n"
                "💡 У вас пока нет активной поездки."
            )
            
            await update.message.reply_text(text)
        
        else:
            Database.add_participant(
                chat_id=chat.id,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            Database.link_user_to_trip(user.id, chat.id)
            
            trip = Database.get_trip(chat.id)
            if trip:
                text = (
                    f"🎒 {trip['name']}\n"
                    f"💱 Валюта: {trip['currency']}\n\n"
                    "Управление поездкой:"
                )
                await update.message.reply_text(
                    text,
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
            "ℹ️ Помощь по боту\n\n"
            "Команды для группового чата:\n"
            "/newtrip — Создать новую поездку\n"
            "/join — Присоединиться к поездке\n"
            "/start — Показать меню поездки\n"
            "/summary — Показать сводку долгов\n"
            "/participants — Показать участников\n"
            "/deletetrip — Удалить поездку и все данные\n\n"
            "Быстрое добавление долга В ГРУППЕ:\n"
            "2000 @участник1 @участник2 описание\n"
            "2000 THB @участник такси (с валютой)\n\n"
            "Пример: 2000 @саша @никита такси\n"
            "С валютой: 500 RUB @катя кофе\n\n"
            "Поддерживаемые валюты:\n"
            "EUR, USD, RUB, THB, GEL, TRY, CNY\n\n"
            "В личном кабинете:\n"
            "📌 Долги — посмотреть свои долги\n"
            "🧾 История — все долги поездки\n"
            "✅ Вернул долг — отметить возврат\n"
            "✅ Подтвердить возврат — если вам вернули долг"
        )
        
        await update.message.reply_text(text)
    
    async def join_trip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрое присоединение к поездке"""
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type == 'private':
            await update.message.reply_text(
                "❌ Эту команду нужно использовать в групповом чате поездки!"
            )
            return
        
        trip = Database.get_trip(chat.id)
        if not trip:
            sent = await update.message.reply_text(
                "❌ Поездка не создана. Используйте /newtrip"
            )
            await asyncio.sleep(5)
            try:
                await update.message.delete()
                await sent.delete()
            except:
                pass
            return
        
        Database.add_participant(
            chat_id=chat.id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        Database.link_user_to_trip(user.id, chat.id)
        
        username_display = f"@{user.username}" if user.username else user.first_name
        sent = await update.message.reply_text(
            f"✅ {username_display} добавлен в поездку {trip['name']}!"
        )
        
        await asyncio.sleep(3)
        try:
            await update.message.delete()
            await sent.delete()
        except Exception as e:
            logger.error(f"Failed to delete join messages: {e}")
    
    async def newtrip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создание новой поездки"""
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type == 'private':
            await update.message.reply_text(
                "❌ Эту команду нужно использовать в групповом чате поездки!"
            )
            return ConversationHandler.END
        
        Database.add_participant(
            chat_id=chat.id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        Database.link_user_to_trip(user.id, chat.id)
        
        existing_trip = Database.get_trip(chat.id)
        if existing_trip:
            text = (
                f"ℹ️ Поездка {existing_trip['name']} уже создана для этого чата.\n\n"
                "Используйте /start для управления или /deletetrip для удаления."
            )
            await update.message.reply_text(text)
            return ConversationHandler.END
        
        text = (
            "🎒 Создание поездки\n\n"
            "Как назовём поездку?\n"
            "Напишите название или нажмите кнопку, чтобы использовать название чата."
        )
        
        keyboard = [
            [InlineKeyboardButton(f"✅ {chat.title}", callback_data="use_chat_name")],
            [InlineKeyboardButton("❌ Отмена", callback_data="trip_create_cancel")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        context.user_data['default_trip_name'] = chat.title or "Моя поездка"
        
        return TRIP_NAME
    
    async def trip_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод названия поездки"""
        trip_name = update.message.text
        chat = update.effective_chat
        
        try:
            await update.message.delete()
        except:
            pass
        
        if len(trip_name) > 100:
            await context.bot.send_message(
                chat_id=chat.id,
                text="❌ Название слишком длинное (макс. 100 символов). Попробуйте ещё раз:"
            )
            return TRIP_NAME
        
        context.user_data['trip_name'] = trip_name
        
        text = (
            f"📝 Название: {trip_name}\n\n"
            "Теперь выберите валюту поездки:"
        )
        
        await context.bot.send_message(
            chat_id=chat.id,
            text=text,
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
            f"📝 Название: {trip_name}\n\n"
            "Теперь выберите валюту поездки:"
        )
        
        await query.edit_message_text(
            text,
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
        
        Database.add_participant(
            chat_id=chat.id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        Database.link_user_to_trip(user.id, chat.id)
        
        text = (
            f"✅ Поездка {trip['name']} ({currency}) создана!\n\n"
            f"👥 Участники добавляются автоматически\n"
            f"💡 Или используйте /join для быстрого добавления\n\n"
            f"💸 Добавление долгов:\n"
            f"2000 @user описание — валюта {currency}\n"
            f"2000 THB @user такси — другая валюта\n\n"
            f"Управление поездкой:"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.main_group_menu()
        )
        
        summary_text = f"📌 Сводка долгов ({currency})\n\n✅ Пока долгов нет"
        await context.bot.send_message(
            chat_id=chat.id,
            text=summary_text,
            reply_markup=Keyboards.summary_actions(self.bot_username, chat.id)
        )
        
        return ConversationHandler.END
    
    async def cancel_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Универсальный обработчик отмены"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text("❌ Отменено.")
        context.user_data.clear()
        return ConversationHandler.END
    
    async def delete_trip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить поездку и все связанные данные"""
        chat = update.effective_chat
        user = update.effective_user
        
        trip = Database.get_trip(chat.id)
        if not trip:
            await update.message.reply_text("❌ Поездка не найдена")
            return
        
        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            if member.status not in ['creator', 'administrator'] and trip['creator_id'] != user.id:
                await update.message.reply_text("❌ Только создатель поездки или админы могут удалить поездку")
                return
        except:
            pass
        
        keyboard = [
            [InlineKeyboardButton("⚠️ Да, удалить всё", callback_data=f"confirm_delete_trip_{chat.id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete_trip")]
        ]
        
        text = (
            f"⚠️ Удаление поездки \"{trip['name']}\"\n\n"
            "Будут удалены:\n"
            "• Все долги\n"
            "• История расходов\n"
            "• Участники\n"
            "• Вся информация о поездке\n\n"
            "⚠️ Это действие нельзя отменить!"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать сводку долгов"""
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type == 'private':
            await update.message.reply_text(
                "❌ Эту команду нужно использовать в групповом чате поездки!"
            )
            return
        
        Database.add_participant(
            chat_id=chat.id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        Database.link_user_to_trip(user.id, chat.id)
        
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
        user = update.effective_user
        
        if chat.type == 'private':
            await update.message.reply_text(
                "❌ Эту команду нужно использовать в групповом чате!"
            )
            return
        
        Database.add_participant(
            chat_id=chat.id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        Database.link_user_to_trip(user.id, chat.id)
        
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
            text = f"👥 Участники поездки \"{trip['name']}\" ({len(participants)}):\n\n"
            for p in participants:
                if p.get('username'):
                    text += f"• @{p['username']} ({p['first_name']})\n"
                else:
                    text += f"• {p['first_name']}\n"
        
        await update.message.reply_text(text)
    
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
            
            user_trips_doc = Database.get_user_trips(user.id)
            trip_count = len(user_trips_doc.get('trips', [])) if user_trips_doc else 1
            
            text = (
                f"👤 Личный кабинет\n\n"
                f"🎒 Активная поездка: {trip['name']}\n"
                f"💱 Валюта: {trip['currency']}\n"
            )
            
            if trip_count > 1:
                text += f"📊 У вас {trip_count} поездок\n"
            
            text += "\nВыберите действие:"
            
            keyboard_markup = Keyboards.dm_main_menu(show_switch_trip=(trip_count > 1))
        else:
            text = (
                "👤 Личный кабинет\n\n"
                "У вас пока нет активной поездки.\n\n"
                "Чтобы начать:\n"
                "1. Добавьте бота в групповой чат\n"
                "2. Создайте поездку командой /newtrip\n"
                "3. Используйте /join для присоединения"
            )
            keyboard_markup = None
        
        if update.callback_query:
            await query.edit_message_text(
                text,
                reply_markup=keyboard_markup
            )
        else:
            await message.reply_text(
                text,
                reply_markup=keyboard_markup
            )
    
    async def show_trip_switch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список поездок для переключения"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_trips_doc = Database.get_user_trips(user.id)
        
        if not user_trips_doc or not user_trips_doc.get('trips'):
            await query.edit_message_text(
                "❌ У вас нет других поездок",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="dm_back")
                ]])
            )
            return
        
        active_trip_id = user_trips_doc.get('active_trip')
        trip_ids = user_trips_doc.get('trips', [])
        
        text = "🔄 Переключение поездки\n\nВыберите активную поездку:\n\n"
        
        keyboard = []
        for trip_id in trip_ids:
            trip = Database.get_trip(trip_id)
            if trip:
                is_active = "✅ " if trip_id == active_trip_id else ""
                text += f"{is_active}{trip['name']} ({trip['currency']})\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{is_active}{trip['name']}",
                        callback_data=f"switch_trip_{trip_id}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="dm_back")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def switch_active_trip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Переключить активную поездку"""
        query = update.callback_query
        await query.answer("✅ Поездка переключена!")
        
        user = query.from_user
        trip_id = int(query.data.split('_')[2])
        
        Database.set_active_trip(user.id, trip_id)
        
        return await self.show_dm_cabinet(update, context)
    
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
        
        text = "📌 Мои долги\n\nВыберите вкладку:"
        
        if query:
            await query.edit_message_text(
                text,
                reply_markup=Keyboards.debts_tabs()
            )
        else:
            await update.message.reply_text(
                text,
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
        """Показать кто мне должен (С КНОПКАМИ!)"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        chat_id = Database.get_user_active_trip(user.id)
        
        if not chat_id:
            await query.edit_message_text("❌ Активная поездка не найдена")
            return
        
        debts_to_me = Database.get_debts_to_user(chat_id, user.id)
        
        if not debts_to_me:
            text = "✅ Вам никто не должен!"
            await query.edit_message_text(
                text,
                reply_markup=Keyboards.debts_tabs()
            )
            return
        
        for debt in debts_to_me:
            try:
                from firebase_admin import firestore
                db_instance = firestore.client()
                debt_group = db_instance.collection('debt_groups').document(debt['debt_group_id']).get()
                if debt_group.exists:
                    debt['group_info'] = debt_group.to_dict()
            except:
                debt['group_info'] = {'description': 'Долг', 'category': '💸'}
        
        text = Utils.format_debts_to_me(chat_id, user.id)
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.debts_to_me_list(debts_to_me)
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
            keyboard = None
        else:
            text = Utils.format_history(chat_id)
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="dm_back")]]
        
        if update.callback_query:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
    
    async def show_notifications_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать настройки уведомлений"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        settings = Database.get_user_settings(user.id)
        current_type = settings.get('notification_type', 'all')
        
        text = (
            "🔔 Настройки уведомлений\n\n"
            "Выберите, когда получать уведомления:"
        )
        
        await query.edit_message_text(
            text,
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
    
    async def handle_group_expense_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Парсинг сообщения типа 2000 @user1 @user2 описание в группе"""
        text = update.message.text
        chat = update.effective_chat
        user = update.effective_user
        
        Database.add_participant(
            chat_id=chat.id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        Database.link_user_to_trip(user.id, chat.id)
        
        trip = Database.get_trip(chat.id)
        if not trip:
            return
        
        participants = Database.get_participants(chat.id)
        
        amount, currency, remaining_text = Utils.parse_currency_from_text(text)
        
        if amount is None:
            sent = await update.message.reply_text(
                "❌ Неверный формат. Используйте:\n2000 @user описание или\n2000 THB @user описание",
                reply_to_message_id=update.message.message_id
            )
            await asyncio.sleep(5)
            try:
                await sent.delete()
                await update.message.delete()
            except:
                pass
            return
        
        if currency is None:
            currency = trip['currency']
        
        mentioned_ids = Utils.parse_participants_from_text(remaining_text, participants)
        
        payer_id = user.id
        
        if payer_id not in mentioned_ids:
            mentioned_ids.append(payer_id)
        
        if len(mentioned_ids) == 1 and mentioned_ids[0] == payer_id:
            sent = await update.message.reply_text(
                "❌ Нельзя создать долг только на себя!\n\n"
                "Укажите минимум 1 другого участника через @",
                reply_to_message_id=update.message.message_id
            )
            await asyncio.sleep(5)
            try:
                await sent.delete()
                await update.message.delete()
            except:
                pass
            return
        
        description_parts = []
        for part in remaining_text.split():
            if not part.startswith('@') and not any(p['first_name'].lower() in part.lower() for p in participants):
                description_parts.append(part)
        
        description = ' '.join(description_parts) if description_parts else "Общий расход"
        
        debt_result = Database.create_debt(
            chat_id=chat.id,
            amount=amount,
            payer_id=payer_id,
            participants=mentioned_ids,
            description=description,
            category='💸',
            currency=currency
        )
        
        if not debt_result:
            sent = await update.message.reply_text(
                "❌ Ошибка создания долга",
                reply_to_message_id=update.message.message_id
            )
            await asyncio.sleep(5)
            try:
                await sent.delete()
                await update.message.delete()
            except:
                pass
            return
        
        debtors = [p for p in mentioned_ids if p != payer_id]
        amount_per_person = amount / len(mentioned_ids)
        
        debtor_names = [Utils.get_participant_name(d, participants) for d in debtors]
        payer_name = Utils.get_participant_name(payer_id, participants)
        
        response_text = (
            f"✅ Долг добавлен!\n\n"
            f"💸 {description}\n"
            f"💰 Общая сумма: {Utils.format_amount(amount, currency)}\n"
            f"👤 Заплатил: {payer_name}\n"
            f"💳 Долг каждого: {Utils.format_amount(amount_per_person, currency)}\n\n"
            f"👥 Должники ({len(debtors)}): {', '.join(debtor_names)}"
        )
        
        sent_response = await update.message.reply_text(
            response_text,
            reply_to_message_id=update.message.message_id
        )
        
        await asyncio.sleep(10)
        try:
            await update.message.delete()
            await sent_response.delete()
        except:
            pass
        
        summary_text = Utils.format_summary(chat.id)
        await context.bot.send_message(
            chat_id=chat.id,
            text=summary_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.summary_actions(self.bot_username, chat.id)
        )
        
        await self.send_debt_notifications(context, chat.id, debt_result, participants, trip)
    
    async def send_debt_notifications(self, context: ContextTypes.DEFAULT_TYPE, 
                                      chat_id: int, debt_result: dict, 
                                      participants: list, trip: dict):
        """Отправить уведомления о долге"""
        group_data = debt_result['group_data']
        individual_debts = debt_result['debts']
        
        payer_id = group_data['payer_id']
        payer_name = Utils.get_participant_name(payer_id, participants)
        description = group_data['description']
        category = group_data.get('category', '💸')
        currency = group_data.get('currency', trip['currency'])
        
        for debt in individual_debts:
            debtor_id = debt['debtor_id']
            amount = debt['amount']
            
            settings = Database.get_user_settings(debtor_id)
            if settings.get('notification_type') == 'off':
                continue
            
            try:
                text = (
                    f"🔔 Новый долг в \"{trip['name']}\"\n\n"
                    f"{category} {description}\n"
                    f"💰 Вы должны {payer_name}: {Utils.format_amount(amount, currency)}\n\n"
                    f"Нажмите /start чтобы посмотреть все долги"
                )
                
                await context.bot.send_message(
                    chat_id=debtor_id,
                    text=text
                )
            except Exception as e:
                logger.error(f"Failed to send notification to {debtor_id}: {e}")
        
        try:
            total_owed = sum(d['amount'] for d in individual_debts)
            text = (
                f"✅ Долг создан в \"{trip['name']}\"\n\n"
                f"{category} {description}\n"
                f"💰 Вам должны: {Utils.format_amount(total_owed, currency)}\n"
                f"👥 Должников: {len(individual_debts)}"
            )
            
            await context.bot.send_message(
                chat_id=payer_id,
                text=text
            )
        except Exception as e:
            logger.error(f"Failed to send notification to payer {payer_id}: {e}")
    
    async def show_debt_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детали конкретного долга с кнопкой оплаты (ДЛЯ ДОЛЖНИКА)"""
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
            currency = group_data.get('currency', trip['currency'])
        else:
            description = "Долг"
            category = "💸"
            currency = trip['currency']
        
        creditor_name = Utils.get_participant_name(debt['creditor_id'], participants)
        amount = Utils.format_amount(debt['amount'], currency)
        
        text = (
            f"{category} {description}\n\n"
            f"💰 Сумма: {amount}\n"
            f"👤 Должен: {creditor_name}\n"
            f"📅 Создан: {debt['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Вернули долг?"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.debt_pay_button(debt_id)
        )
    
    async def show_debt_detail_creditor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детали долга для КРЕДИТОРА с кнопкой подтверждения"""
        query = update.callback_query
        await query.answer()
        
        debt_id = query.data.split('_')[3]
        
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
            currency = group_data.get('currency', trip['currency'])
        else:
            description = "Долг"
            category = "💸"
            currency = trip['currency']
        
        debtor_name = Utils.get_participant_name(debt['debtor_id'], participants)
        amount = Utils.format_amount(debt['amount'], currency)
        
        text = (
            f"{category} {description}\n\n"
            f"💰 Сумма: {amount}\n"
            f"👤 Должник: {debtor_name}\n"
            f"📅 Создан: {debt['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Должник вернул вам деньги?"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.debt_confirm_button(debt_id)
        )
    
    async def pay_debt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отметить долг как возвращенный (ДОЛЖНИК НАЖАЛ)"""
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
        currency = trip['currency']
        if debt_group.exists:
            group_data = debt_group.to_dict()
            description = group_data.get('description', 'Долг')
            category = group_data.get('category', '💸')
            currency = group_data.get('currency', trip['currency'])
        
        await query.edit_message_text(
            f"✅ Долг возвращен!\n\n"
            f"{category} {description}\n"
            f"💰 Сумма: {Utils.format_amount(amount, currency)}\n"
            f"👤 Кредитор: {creditor_name}\n\n"
            f"Спасибо за честность! 🎉"
        )
        
        try:
            text = (
                f"💰 Долг возвращен!\n\n"
                f"👤 {debtor_name} вернул вам долг:\n"
                f"{category} {description}\n"
                f"💵 Сумма: {Utils.format_amount(amount, currency)}\n\n"
                f"Поездка: {trip['name']}"
            )
            
            await context.bot.send_message(
                chat_id=creditor_id,
                text=text
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
    
    async def confirm_debt_return(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кредитор подтверждает возврат долга"""
        query = update.callback_query
        await query.answer("✅ Возврат подтверждён!")
        
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
        currency = trip['currency']
        if debt_group.exists:
            group_data = debt_group.to_dict()
            description = group_data.get('description', 'Долг')
            category = group_data.get('category', '💸')
            currency = group_data.get('currency', trip['currency'])
        
        await query.edit_message_text(
            f"✅ Возврат подтверждён!\n\n"
            f"{category} {description}\n"
            f"💰 Сумма: {Utils.format_amount(amount, currency)}\n"
            f"👤 Должник: {debtor_name}\n\n"
            f"Спасибо за подтверждение! 🎉"
        )
        
        try:
            text = (
                f"✅ {creditor_name} подтвердил возврат долга\n\n"
                f"{category} {description}\n"
                f"💵 Сумма: {Utils.format_amount(amount, currency)}\n\n"
                f"Поездка: {trip['name']}"
            )
            
            await context.bot.send_message(
                chat_id=debtor_id,
                text=text
            )
        except Exception as e:
            logger.error(f"Failed to notify debtor: {e}")
        
        try:
            summary_text = Utils.format_summary(chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ {creditor_name} подтвердил возврат от {debtor_name}\n\n{summary_text}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to update group: {e}")
    
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
        
        elif data == "dm_switch_trip":
            return await self.show_trip_switch(update, context)
        
        elif data.startswith("switch_trip_"):
            return await self.switch_active_trip(update, context)
        
        elif data == "debts_i_owe":
            return await self.show_i_owe(update, context)
        
        elif data == "debts_owe_me":
            return await self.show_owe_me(update, context)
        
        elif data == "debts_refresh":
            return await self.show_debts_dm(update, context)
        
        elif data.startswith("show_debt_creditor_"):
            return await self.show_debt_detail_creditor(update, context)
        
        elif data.startswith("confirm_debt_"):
            return await self.confirm_debt_return(update, context)
        
        elif data.startswith("show_debt_"):
            return await self.show_debt_detail(update, context)
        
        elif data.startswith("pay_debt_"):
            return await self.pay_debt(update, context)

        elif data == "show_add_expense_info":
            await query.answer()
            chat = query.message.chat
            trip = Database.get_trip(chat.id)
            if trip:
                text = (
                    "➕ *Как добавить долг:*\n\n"
                    "Просто напишите в чат:\n"
                    "`сумма @участник1 @участник2 описание`\n\n"
                    "💡 *Примеры:*\n"
                    "`2000 @никита @саша такси`\n"
                    "`500 @катя кофе`\n"
                    "`15000 @петя @маша @иван отель`\n\n"
                    "💱 *С другой валютой:*\n"
                    "`2000 THB @никита такси`\n"
                    "`500 RUB @катя кофе`\n"
                    "`1000 CNY @петя сувениры`\n\n"
                    "Вы автоматически становитесь плательщиком!"
                )
                await query.edit_message_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 На главную", callback_data="back_to_menu")
                    ]])
                )
        
        elif data.startswith("confirm_delete_trip_"):
            await query.answer()
            chat_id = int(data.split('_')[3])
            
            success = Database.delete_trip_completely(chat_id)
            
            if success:
                await query.edit_message_text(
                    "✅ *Поездка удалена*\n\n"
                    "Все долги, история и участники удалены из базы данных.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text("❌ Ошибка удаления поездки")
        
        elif data == "cancel_delete_trip":
            await query.answer()
            await query.edit_message_text("❌ Удаление отменено")
        
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
                    if p.get('username'):
                        text += f"• @{p['username']} ({p['first_name']})\n"
                    else:
                        text += f"• {p['first_name']}\n"
                await query.edit_message_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 На главную", callback_data="back_to_menu")
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
