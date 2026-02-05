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
from handlers import Handlers, TRIP_NAME, TRIP_CURRENCY, EXPENSE_AMOUNT, EXPENSE_PAYER, EXPENSE_BENEFICIARIES, EXPENSE_COMMENT, EXPENSE_CATEGORY, EXPENSE_CONFIRM

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Запуск бота"""
    logger.info("Starting TripSplit Bot...")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Username вашего бота (БЕЗ @)
    bot_username = "dolgotripbot"
    
    # Инициализируем обработчики
    handlers = Handlers(bot_username)
    
    # ============ CONVERSATION HANDLERS ============
    
    # Создание поездки
    trip_conversation = ConversationHandler(
        entry_points=[CommandHandler('newtrip', handlers.newtrip_command)],
        states={
            TRIP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.trip_name_input),
                CallbackQueryHandler(handlers.use_chat_name, pattern='^use_chat_name$'),
                CallbackQueryHandler(handlers.trip_create_cancel, pattern='^trip_create_cancel$'),
            ],
            TRIP_CURRENCY: [
                CallbackQueryHandler(handlers.trip_currency_select, pattern='^currency_'),
                CallbackQueryHandler(handlers.trip_create_cancel, pattern='^currency_cancel$'),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handlers.trip_create_cancel, pattern='^trip_create_cancel$')
        ],
        name="trip_conversation",
        persistent=False
    )
    
    # Добавление долга (ИСПРАВЛЕНО: start_debt_flow вместо start_expense_flow)
    expense_conversation = ConversationHandler(
        entry_points=[
            CommandHandler('expense', handlers.expense_command),
            CallbackQueryHandler(handlers.start_debt_flow, pattern='^add_expense$'),
        ],
        states={
            EXPENSE_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.expense_amount_input),
                CallbackQueryHandler(handlers.expense_cancel, pattern='^cancel$'),
            ],
            EXPENSE_PAYER: [
                CallbackQueryHandler(handlers.expense_payer_select, pattern='^payer_'),
                CallbackQueryHandler(handlers.expense_cancel, pattern='^cancel$'),
            ],
            EXPENSE_CATEGORY: [
                CallbackQueryHandler(handlers.expense_category_select, pattern='^category_'),
                CallbackQueryHandler(handlers.expense_category_skip, pattern='^category_skip$'),
                CallbackQueryHandler(handlers.expense_cancel, pattern='^cancel$'),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handlers.expense_cancel, pattern='^cancel$')
        ],
        name="expense_conversation",
        persistent=False,
        allow_reentry=True
    )
    
    # ============ COMMAND HANDLERS ============
    
    application.add_handler(CommandHandler('start', handlers.start_command))
    application.add_handler(CommandHandler('help', handlers.help_command))
    application.add_handler(CommandHandler('summary', handlers.summary_command))
    application.add_handler(CommandHandler('participants', handlers.participants_command))
    
    # ============ CONVERSATION HANDLERS ============
    
    application.add_handler(trip_conversation)
    application.add_handler(expense_conversation)
    
    # ============ CALLBACK HANDLERS ============
    
    # Уведомления
    application.add_handler(CallbackQueryHandler(
        handlers.update_notification_settings, 
        pattern='^notif_'
    ))
    
    # Общий обработчик callback'ов (должен быть последним)
    application.add_handler(CallbackQueryHandler(handlers.callback_handler))
    
    # ============ ERROR HANDLER ============
    
    async def error_handler(update: Update, context):
        """Обработка ошибок"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка. Попробуйте ещё раз или напишите /help"
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    application.add_error_handler(error_handler)
    
    # ============ ЗАПУСК БОТА ============
    
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
