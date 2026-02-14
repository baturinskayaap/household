# utils.py
import logging
from datetime import datetime
from typing import List, Optional, Union, Any

from telegram import Update, CallbackQuery
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from models import Task

logger = logging.getLogger(__name__)


def format_reminder_message(overdue_tasks: List[Task], due_soon_tasks: List[Task]) -> str:
    """Форматирование сообщения для напоминаний"""
    message_lines = ["🔔 Ежедневное напоминание о задачах:\n"]

    if overdue_tasks:
        message_lines.append("📛 ПРОСРОЧЕННЫЕ ЗАДАЧИ:")
        for task in overdue_tasks:
            overdue_days = (task.days_since_done() or 0) - task.interval_days
            message_lines.append(f"🔴 {task.name} - просрочено на {overdue_days} дней")
        message_lines.append("")

    if due_soon_tasks:
        message_lines.append("⏰ СКОРО НУЖНО ВЫПОЛНИТЬ:")
        for task in due_soon_tasks:
            days_left = task.days_until_due()
            message_lines.append(f"🟡 {task.name} - осталось {days_left} дней")
        message_lines.append("")

    message_lines.append("Используйте /done [задача] чтобы отметить выполнение")
    return "\n".join(message_lines)


def validate_time_string(time_str: str) -> bool:
    """Проверка корректности строки времени"""
    try:
        hours, minutes = map(int, time_str.split(':'))
        return 0 <= hours <= 23 and 0 <= minutes <= 59
    except (ValueError, AttributeError):
        return False


def get_weekday_name(weekday_num: int) -> str:
    """Получить название дня недели"""
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    return days[weekday_num] if 0 <= weekday_num < 7 else "Неизвестно"


def safe_datetime_parse(date_string: Optional[str]) -> Optional[datetime]:
    """Безопасное преобразование строки в datetime"""
    if not date_string:
        return None
    try:
        return datetime.fromisoformat(date_string)
    except (ValueError, TypeError):
        return None


async def send_message(
    update: Union[Update, CallbackQuery],
    text: str,
    reply_markup: Any = None,
    parse_mode: str = 'HTML'
) -> None:
    """
    Универсальный метод отправки сообщений.
    Работает как с Update, так и с CallbackQuery.
    """
    try:
        # Если это CallbackQuery - редактируем сообщение
        if isinstance(update, CallbackQuery):
            await update.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return

        # Если это Update, проверяем наличие callback_query внутри
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return

        # Если это Update с сообщением - отвечаем
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return

        # Если это что-то другое с методом edit_message_text (редкий случай)
        if hasattr(update, 'edit_message_text'):
            await update.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return

        logger.error(f"Unknown update type in send_message: {type(update)}")
        # fallback: пробуем отправить в чат через bot, если есть effective_chat
        if hasattr(update, 'effective_chat') and hasattr(update, '_bot'):
            bot = update._bot
            await bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            if hasattr(update, 'answer'):
                await update.answer()
        else:
            logger.error(f"BadRequest in send_message: {e}")
    except Exception as e:
        logger.error(f"Error in send_message: {e}")