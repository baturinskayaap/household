"""
Точка входа в приложение Telegram-бота для домашних дел.
Создаёт и настраивает Application, инициализирует базу данных и систему напоминаний,
регистрирует все обработчики и запускает поллинг.
"""

import logging

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram import BotCommand

try:
    import config_dev as config
except ImportError:
    import config
from database import Database
from reminder_system import ReminderSystem
from handlers.common import start, handle_text_message, handle_callback

async def post_init(application: Application) -> None:
    """Устанавливает пустой список команд после инициализации бота."""
    await application.bot.set_my_commands([])
    logging.getLogger(__name__).info("Bot commands cleared.")

def main() -> None:
    """Основная функция запуска бота."""
    # Настройка логирования
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logger = logging.getLogger(__name__)

    logger.info("Инициализация базы данных...")
    db = Database()

    logger.info("Инициализация системы напоминаний...")
    reminder_system = ReminderSystem(db)

    logger.info("Создание приложения...")
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Сохраняем общие объекты в bot_data для доступа из обработчиков
    application.bot_data["db"] = db
    application.bot_data["reminder_system"] = reminder_system

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    # Запуск системы напоминаний (если требуется)
    # Предполагается, что reminder_system может запускать фоновые задачи или JobQueue
    # Если использует JobQueue, нужно передать application.job_queue
    # Здесь ожидаем метод start(application) или подобный
    if hasattr(reminder_system, "start"):
        reminder_system.start(application)

    logger.info("Бот запущен и готов к работе.")
    application.run_polling()


if __name__ == "__main__":
    main()