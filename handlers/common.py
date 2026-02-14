"""
Общие обработчики для Telegram-бота.
Содержит команду /start, диспетчер текстовых сообщений и единый обработчик callback-запросов.
"""

import logging

from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

from utils import send_message
from handlers import tasks, shopping
from keyboards import get_main_keyboard

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Показывает главное меню с reply-клавиатурой."""
    try:
        welcome_text = """
Привет!

Используй кнопки ниже для быстрого доступа
        """
        keyboard = get_main_keyboard()
        await send_message(update, welcome_text, keyboard)
    except Exception as e:
        logger.error(f"Error in /start: {e}")
        await send_message(update, "❌ Произошла ошибка. Попробуйте позже.")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Диспетчер текстовых сообщений.
    Проверяет состояние пользователя и перенаправляет в соответствующий модуль.
    Если состояния нет, обрабатывает команды из основного меню.
    """
    user_id = update.effective_user.id
    text = update.message.text

    # Проверяем, есть ли активное состояние
    state = context.user_data.get("state")
    if state:
        # Перенаправляем в зависимости от состояния
        if state == "adding_shopping_stream":
            await shopping.process_shopping_stream_item(update, context, text)
        elif state == "waiting_for_new_task":
            await tasks.process_new_task(update, context, text)
        elif state.startswith("waiting_interval_"):
            await tasks.process_interval_update(update, context, text, state)
        elif state.startswith("waiting_rename_"):
            await tasks.process_rename_task(update, context, text, state)
        elif state == "waiting_for_shopping_item":
            await shopping.process_shopping_item(update, context, text)
        else:
            # Неизвестное состояние – сбрасываем
            logger.warning(f"Unknown state {state} for user {user_id}, clearing")
            context.user_data.clear()
            await send_message(update, "❌ Неизвестное состояние. Начните заново.")
        return

    # Если состояния нет – обрабатываем команды из главного меню
    if text == "📋 Задачи":
        # ВОЗВРАЩАЕМ МЕНЮ ЗАДАЧ (а не сразу список)
        await tasks.show_tasks_menu(update, context)
    elif text == "🛒 Покупки":
        # Для покупок оставляем прямой показ списка (как и просили ранее)
        await shopping.show_shopping_items(update, context)
    else:
        await send_message(update, "❌ Неизвестная команда. Используйте кнопки меню.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Единый обработчик всех inline-кнопок.
    Разбирает callback_data и вызывает соответствующие функции из модулей.
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # Проверка прав администратора
    import config
    if user_id not in config.ADMIN_IDS:
        await query.edit_message_text("❌ У вас нет прав для выполнения этого действия")
        return

    try:
        # ================== ОБЩИЕ ДЕЙСТВИЯ ==================
        if data == "back_to_main":
            # Возвращаемся в главное меню с reply-клавиатурой
            await query.edit_message_text(
                "👋 Главное меню\n\nВыберите раздел:",
                reply_markup=get_main_keyboard()
            )
        elif data == "back_to_tasks_menu":
            # Возврат в меню задач
            await tasks.show_tasks_menu(query, context)

        # ================== ЗАДАЧИ ==================
        elif data == "tasks_main":
            await tasks.show_tasks_menu(query, context)
        elif data == "show_tasks":
            await tasks.show_tasks_with_keyboard(query, context, show_all=True)
        elif data == "show_urgent_tasks":
            await tasks.show_tasks_with_keyboard(query, context, show_all=False)
        elif data == "refresh_tasks":
            await tasks.show_tasks_with_keyboard(query, context, show_all=True)
        elif data == "manage_tasks":
            await tasks.manage_tasks(query, context)
        elif data == "add_task":
            await tasks.handle_add_task(query, context)
        elif data == "edit_interval":
            await tasks.show_task_selection_for_interval(query, context)
        elif data == "rename_task":
            await tasks.show_task_selection_for_rename(query, context)
        elif data == "delete_task":
            await tasks.show_task_selection_for_delete(query, context)
        elif data.startswith("done_"):
            task_id = int(data.split("_")[1])
            await tasks.mark_task_done_from_button(query, context, task_id)
        elif data.startswith("edit_interval_"):
            task_id = int(data.split("_")[2])
            await tasks.start_interval_edit(query, context, task_id)
        elif data.startswith("rename_"):
            task_id = int(data.split("_")[1])
            await tasks.start_rename_task(query, context, task_id)
        elif data.startswith("delete_"):
            task_id = int(data.split("_")[1])
            await tasks.confirm_delete_task(query, context, task_id)
        elif data.startswith("confirm_delete_"):
            task_id = int(data.split("_")[2])
            await tasks.execute_delete_task(query, context, task_id)
        elif data == "back_to_manage":
            await tasks.manage_tasks(query, context)

        # ================== СПИСОК ПОКУПОК ==================
        elif data == "shopping_show":
            await shopping.show_shopping_items(query, context)
        elif data == "shopping_toggle_view":
            await shopping.toggle_shopping_view(query, context)
        elif data == "shopping_add":
            await shopping.add_shopping_item(query, context)
        elif data.startswith("shopping_toggle_"):
            item_id = int(data.split("_")[2])
            await shopping.toggle_shopping_item(query, context, item_id)
        elif data == "shopping_clear_checked":
            await shopping.clear_checked_shopping_items(query, context)
        elif data == "shopping_clear_all":
            await shopping.clear_all_shopping_items(query, context)
        elif data == "shopping_confirm_clear_checked":
            await shopping.confirm_clear_checked_items(query, context)
        elif data == "shopping_confirm_clear_all":
            await shopping.confirm_clear_all_items(query, context)
        elif data == "shopping_exit_stream":
            await shopping.exit_shopping_stream(query, context)
        elif data == "shopping_quick_clear":
            await shopping.quick_clear_all_shopping_items(query, context)
        elif data == "back_to_shopping":
            # Перенаправляем в главное меню, так как прямого меню покупок больше нет
            await query.edit_message_text(
                "👋 Главное меню\n\nВыберите раздел:",
                reply_markup=get_main_keyboard()
            )    

        # ================== ПРОЧЕЕ ==================
        elif data == "cancel_action":
            # Очищаем состояние и возвращаемся в главное меню
            context.user_data.clear()
            await query.edit_message_text(
                "👋 Главное меню\n\nВыберите раздел:",
                reply_markup=get_main_keyboard()
            )
        elif data == "no_action":
            # Просто игнорируем
            pass
        else:
            logger.warning(f"Unknown callback data: {data}")
            await query.edit_message_text("❌ Неизвестное действие")

    except Exception as e:
        logger.error(f"Error in handle_callback: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка при обработке действия")