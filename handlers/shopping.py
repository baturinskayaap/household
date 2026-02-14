"""
Обработчики для раздела "Список покупок" Telegram-бота.
Содержит функции для отображения, добавления, отметки и очистки пунктов списка.
"""

import logging
from typing import Union

from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

from utils import send_message
from keyboards import (
    get_shopping_keyboard,
    get_shopping_items_keyboard,
    get_shopping_clear_confirmation,
    get_shopping_back_keyboard,
    get_shopping_back_to_stream_keyboard,
    get_shopping_add_stream_keyboard,
    get_cancel_keyboard,
)
import config

logger = logging.getLogger(__name__)


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

def _is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором."""
    return user_id in config.ADMIN_IDS


# ================== ОСНОВНОЕ МЕНЮ ==================

async def show_shopping_menu(update: Union[Update, CallbackQuery], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать меню списка покупок (для текстовых сообщений и callback)."""
    try:
        message = "🛒 Список покупок"
        keyboard = get_shopping_keyboard()
        await send_message(update, message, keyboard)
    except Exception as e:
        logger.error(f"Error in show_shopping_menu: {e}")
        await send_message(update, "❌ Ошибка при открытии списка покупок")


async def show_shopping_list(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать меню списка покупок (для inline-кнопок)."""
    try:
        keyboard = get_shopping_keyboard()
        message = "🛒 Список покупок"
        # Здесь query точно CallbackQuery, можно использовать edit_message_text напрямую,
        # но для единообразия тоже через send_message:
        await send_message(query, message, keyboard)
    except Exception as e:
        logger.error(f"Error in show_shopping_list: {e}")
        await send_message(query, "❌ Ошибка при открытии списка покупок")


# ================== ОТОБРАЖЕНИЕ ПУНКТОВ ==================

async def show_shopping_items(
    update: Union[Update, CallbackQuery],
    context: ContextTypes.DEFAULT_TYPE,
    show_checked: bool = None
) -> None:
    """
    Показать список покупок с кнопками для отметки.
    Работает как с Update, так и с CallbackQuery.
    """
    try:
        # Определяем user_id в зависимости от типа
        if isinstance(update, CallbackQuery):
            user_id = update.from_user.id
        else:
            user_id = update.effective_user.id

        db = context.bot_data["db"]

        if show_checked is None:
            show_checked = context.user_data.get("shopping_show_checked", True)
        else:
            context.user_data["shopping_show_checked"] = show_checked

        items = db.get_shopping_items(show_checked=show_checked)

        if not items:
            await send_message(
                update,
                "📝 Список покупок пуст. Добавьте первый пункт!",
                get_shopping_keyboard()
            )
            return

        stats = db.get_shopping_item_count()

        message_lines = ["🛒 Список покупок:\n"]
        if stats['total'] > 0:
            message_lines.append(
                f"📊 Всего: {stats['total']} | ✅ Отмечено: {stats['checked']} | ⬜️ Неотмечено: {stats['unchecked']}\n"
            )
        for item in items:
            message_lines.append(f"{item.format_for_display()}")

        keyboard = get_shopping_items_keyboard(items, stats, show_checked)
        await send_message(update, "\n".join(message_lines), keyboard, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in show_shopping_items: {e}")
        await send_message(update, "❌ Ошибка при получении списка покупок")


async def toggle_shopping_view(update: Union[Update, CallbackQuery], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Переключить режим отображения (показывать/скрывать отмеченные пункты)."""
    # Определяем user_id
    if isinstance(update, CallbackQuery):
        user_id = update.from_user.id
    else:
        user_id = update.effective_user.id

    current = context.user_data.get("shopping_show_checked", True)
    await show_shopping_items(update, context, show_checked=not current)


# ================== ДОБАВЛЕНИЕ ПУНКТОВ (ПОТОКОВЫЙ РЕЖИМ) ==================

async def add_shopping_item(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начать потоковое добавление новых пунктов в список покупок."""
    context.user_data["state"] = "adding_shopping_stream"
    await query.edit_message_text(
        "➕ **Режим добавления пунктов**\n\n"
        "Просто отправляйте названия пунктов, и они будут автоматически добавляться в список.\n"
        "Каждый пункт в отдельном сообщении.\n\n"
        "Примеры:\n"
        "• Молоко, 2л\n"
        "• Хлеб\n"
        "• Яйца 10 шт.\n\n"
        "Нажмите 'Завершить добавление', когда закончите.",
        reply_markup=get_shopping_add_stream_keyboard()
    )


async def process_shopping_stream_item(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_message: str
) -> None:
    """Обработка добавления пункта в потоковом режиме."""
    user_id = update.effective_user.id

    if not _is_admin(user_id):
        context.user_data.pop("state", None)
        await update.message.reply_text("❌ У вас нет прав для выполнения этого действия.")
        return

    item_text = user_message.strip()
    if not item_text:
        await update.message.reply_text(
            "❌ Название пункта не может быть пустым.",
            reply_markup=get_shopping_back_to_stream_keyboard()
        )
        return

    db = context.bot_data["db"]
    try:
        success = db.add_shopping_item(item_text)
    except Exception as e:
        logger.error(f"Ошибка при добавлении в БД: {e}")
        success = False

    if success:
        await update.message.reply_text(
            f"✅ Добавлено: *{item_text}*",
            parse_mode='Markdown',
            reply_markup=get_shopping_back_to_stream_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ Пункт '*{item_text}*' уже есть в списке.",
            parse_mode='Markdown',
            reply_markup=get_shopping_back_to_stream_keyboard()
        )
    # Состояние не удаляем – остаёмся в потоке


async def exit_shopping_stream(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выход из режима потокового добавления."""
    context.user_data.pop("state", None)
    db = context.bot_data["db"]
    stats = db.get_shopping_item_count()
    await query.edit_message_text(
        f"🔚 **Режим добавления завершен**\n\n"
        f"📊 Статистика списка покупок:\n"
        f"• Всего пунктов: {stats['total']}\n"
        f"• Отмечено: {stats['checked']}\n"
        f"• Не отмечено: {stats['unchecked']}\n\n"
        f"Можете продолжить управление списком:",
        reply_markup=get_shopping_keyboard()
    )


# ================== ДОБАВЛЕНИЕ ОДНОГО ПУНКТА (СТАРЫЙ РЕЖИМ) ==================

async def process_shopping_item(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_message: str
) -> None:
    """Обработка добавления одного пункта в список покупок (не потоковый режим)."""
    user_id = update.effective_user.id

    if not _is_admin(user_id):
        context.user_data.pop("state", None)
        await update.message.reply_text("❌ У вас нет прав для выполнения этого действия.")
        return

    item_text = user_message.strip()
    if not item_text:
        await update.message.reply_text(
            "❌ Название пункта не может быть пустым.",
            reply_markup=get_cancel_keyboard()
        )
        return

    db = context.bot_data["db"]
    success = db.add_shopping_item(item_text)

    if success:
        await update.message.reply_text(
            f"✅ Пункт добавлен: {item_text}",
            reply_markup=get_shopping_back_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ Пункт '{item_text}' уже есть в списке (и не отмечен).",
            reply_markup=get_cancel_keyboard()
        )

    context.user_data.pop("state", None)


# ================== ОТМЕТКА ПУНКТА ==================

async def toggle_shopping_item(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int
) -> None:
    """Переключить статус отметки пункта."""
    try:
        db = context.bot_data["db"]
        item = db.toggle_shopping_item(item_id)

        if not item:
            await query.edit_message_text("❌ Пункт не найден")
            return

        user_id = query.from_user.id
        show_checked = context.user_data.get("shopping_show_checked", True)
        items = db.get_shopping_items(show_checked=show_checked)

        if not items:
            await query.edit_message_text(
                "📝 Список покупок пуст. Добавьте новый пункт!",
                reply_markup=get_shopping_keyboard()
            )
            return

        stats = db.get_shopping_item_count()

        message_lines = ["🛒 Список покупок:\n"]
        if stats['total'] > 0:
            message_lines.append(
                f"📊 Всего: {stats['total']} | ✅ Отмечено: {stats['checked']} | ⬜️ Неотмечено: {stats['unchecked']}\n"
            )
        for item in items:
            message_lines.append(f"{item.format_for_display()}")

        keyboard = get_shopping_items_keyboard(items, stats, show_checked)
        await query.edit_message_text("\n".join(message_lines), reply_markup=keyboard, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error toggling shopping item: {e}")
        await query.edit_message_text("❌ Ошибка при обновлении пункта")


# ================== ОЧИСТКА СПИСКА ==================

async def clear_checked_shopping_items(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подтверждение очистки отмеченных пунктов."""
    db = context.bot_data["db"]
    stats = db.get_shopping_item_count()

    if stats['checked'] == 0:
        await query.edit_message_text(
            "✅ Нет отмеченных пунктов для очистки.",
            reply_markup=get_shopping_back_keyboard()
        )
        return

    keyboard = get_shopping_clear_confirmation("checked")
    await query.edit_message_text(
        f"🧹 Вы уверены, что хотите удалить {stats['checked']} отмеченных пунктов?",
        reply_markup=keyboard
    )


async def clear_all_shopping_items(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подтверждение очистки всего списка покупок."""
    db = context.bot_data["db"]
    stats = db.get_shopping_item_count()

    if stats['total'] == 0:
        await query.edit_message_text(
            "📝 Список покупок и так пуст.",
            reply_markup=get_shopping_back_keyboard()
        )
        return

    keyboard = get_shopping_clear_confirmation("all")
    await query.edit_message_text(
        f"🗑️ Вы уверены, что хотите удалить весь список ({stats['total']} пунктов)?",
        reply_markup=keyboard
    )


async def quick_clear_all_shopping_items(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Быстрая очистка всего списка из главного меню (сразу запрос подтверждения)."""
    db = context.bot_data["db"]
    stats = db.get_shopping_item_count()

    if stats['total'] == 0:
        await query.edit_message_text(
            "📝 Список покупок и так пуст.",
            reply_markup=get_shopping_keyboard()
        )
        return

    keyboard = get_shopping_clear_confirmation("all")
    await query.edit_message_text(
        f"🗑️ Вы уверены, что хотите удалить весь список ({stats['total']} пунктов)?",
        reply_markup=keyboard
    )


async def confirm_clear_checked_items(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подтверждение удаления отмеченных пунктов."""
    db = context.bot_data["db"]
    deleted_count = db.delete_checked_items()
    await query.edit_message_text(
        f"✅ Удалено {deleted_count} отмеченных пунктов.",
        reply_markup=get_shopping_back_keyboard()
    )


async def confirm_clear_all_items(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подтверждение удаления всего списка."""
    db = context.bot_data["db"]
    deleted_count = db.delete_all_shopping_items()
    await query.edit_message_text(
        f"✅ Удалено {deleted_count} пунктов. Список очищен.",
        reply_markup=get_shopping_back_keyboard()
    )