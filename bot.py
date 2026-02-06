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

# Настройка логирования (УСИЛЕНО!)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Включить DEBUG для видимости всех действий
logging.getLogger('handlers').setLevel(logging.DEBUG)


async def post_init(application: Application):
    """Инициализация после запуска бота"""
    bot = await application.bot.get_me()
    logger.info(f"Bot started: @{bot.username} (ID: {bot.id})")


def main():
    """Запуск бота"""
    logger.info("Starting TripSplit Bot...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    bot_username = "dolgotripbot"
    
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
    application.add_handler(CommandHandler('join', handlers.join_trip_command, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler('summary', handlers.summary_command))
    application.add_handler(CommandHandler('participants', handlers.participants_command))
    application.add_handler(CommandHandler('deletetrip', handlers.delete_trip_command, filters=filters.ChatType.GROUPS))
    
    # ============ CONVERSATION HANDLERS ============
    
    application.add_handler(trip_conversation)
    
    # ============ CALLBACK HANDLERS ============
    
    application.add_handler(CallbackQueryHandler(
        handlers.update_notification_settings, 
        pattern='^notif_'
    ))
    
    application.add_handler(CallbackQueryHandler(handlers.callback_handler))
    
    # ============ TEXT HANDLERS ============
    
    # Обработчик долгов в ГРУППЕ (начинается с цифры)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND & filters.Regex(r'^\d+'),
        handlers.handle_group_expense_text
    ))
    
    # Обработчик обычных сообщений в группе
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        handlers.handle_group_message
    ))
    
    # Обработчик сообщений в ЛС
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        handlers.handle_private_message
    ))
    
    # ============ ERROR HANDLER (УЛУЧШЕННЫЙ!) ============
    
    async def error_handler(update: Update, context):
        """Обработка ошибок С ПОЛНЫМ ЛОГИРОВАНИЕМ"""
        import traceback
        
        # ПОЛНЫЙ traceback в лог
        logger.error("="*50)
        logger.error("EXCEPTION CAUGHT!")
        logger.error(f"Update: {update}")
        logger.error(f"Error: {context.error}")
        logger.error("Full traceback:")
        logger.error(''.join(traceback.format_exception(None, context.error, context.error.__traceback__)))
        logger.error("="*50)
        
        try:
            if update and update.effective_message:
                # Отправить ошибку в чат ДЛЯ ОТЛАДКИ
                error_text = (
                    f"❌ Произошла ошибка:\n\n"
                    f"`{type(context.error).__name__}: {str(context.error)}`\n\n"
                    f"Напишите /help для справки"
                )
                await update.effective_message.reply_text(
                    error_text,
                    parse_mode='Markdown'
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
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")


if __name__ == '__main__':
    main()
