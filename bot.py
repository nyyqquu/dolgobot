import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)
from config import BOT_TOKEN
from handlers import Handlers, TRIP_NAME, TRIP_CURRENCY

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Инициализация после запуска бота"""
    bot = await application.bot.get_me()
    logger.info(f"Bot started: @{bot.username} (ID: {bot.id})")


def main():
    """Запуск бота"""
    logger.info("Starting TripSplit Bot...")
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Получаем username бота (будет установлен в post_init)
    bot_username = "dolgotripbot"  # fallback
    
    handlers = Handlers(bot_username)
    
    # ============ CONVERSATION HANDLERS ============
    
    # Создание поездки
    trip_conversation = ConversationHandler(
        entry_points=[CommandHandler('newtrip', handlers.newtrip_command)],
        states={
            TRIP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.trip_name_input),
                CallbackQueryHandler(handlers.use_chat_name, pattern='^use_chat_name$'),
                CallbackQueryHandler(handlers.cancel_handler, pattern='^trip_create_cancel$'),
            ],
            TRIP_CURRENCY: [
                CallbackQueryHandler(handlers.trip_currency_select, pattern='^currency_'),
                CallbackQueryHandler(handlers.cancel_handler, pattern='^currency_cancel$'),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handlers.cancel_handler, pattern='^trip_create_cancel$')
        ],
        name="trip_conversation",
        persistent=False
    )
    
    # ============ COMMAND HANDLERS ============
    
    application.add_handler(CommandHandler('start', handlers.start_command))
    application.add_handler(CommandHandler('help', handlers.help_command))
    application.add_handler(CommandHandler('summary', handlers.summary_command))
    application.add_handler(CommandHandler('participants', handlers.participants_command))
    application.add_handler(CommandHandler('deletetrip', handlers.delete_trip_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('clear', handlers.clear_bot_messages, filters=filters.ChatType.GROUPS))
    
    # ============ CONVERSATION HANDLERS ============
    
    application.add_handler(trip_conversation)
    
    # ============ CALLBACK HANDLERS ============
    
    # Специфичные callback'и (обрабатываются первыми)
    application.add_handler(CallbackQueryHandler(
        handlers.update_notification_settings, 
        pattern='^notif_'
    ))
    
    # Общий обработчик callback'ов (должен быть последним)
    application.add_handler(CallbackQueryHandler(handlers.callback_handler))
    
    # ============ TEXT HANDLERS ============
    
    # ВАЖНО: Порядок имеет значение! От специфичного к общему
    
    # 1. Обработчик долгов в ГРУППЕ (начинается с цифры)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND & filters.Regex(r'^\d+'),
        handlers.handle_group_expense_text
    ))
    
    # 2. Обработчик обычных сообщений в группе (для автодобавления участников)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        handlers.handle_group_message
    ))
    
    # 3. Обработчик сообщений в ЛС (показывает кабинет)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        handlers.handle_private_message
    ))
    
    # ============ ERROR HANDLER ============
    
    async def error_handler(update: Update, context):
        """Обработка ошибок"""
        logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка. Попробуйте ещё раз или напишите /help"
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    application.add_error_handler(error_handler)
    
    # ============ POST INIT ============
    
    application.post_init = post_init
    
    # ============ ЗАПУСК БОТА ============
    
    logger.info("Bot handlers configured. Starting polling...")
    
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True  # Игнорировать старые обновления при перезапуске
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")


if __name__ == '__main__':
    main()
