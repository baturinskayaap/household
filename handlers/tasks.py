"""
Обработчики для раздела "Задачи" Telegram-бота.
Содержит функции для отображения, добавления, изменения и удаления задач.
"""

import logging
from typing import Union

from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

from utils import send_message
from keyboards import (
    get_tasks_menu_keyboard,
    get_tasks_keyboard,
    get_management_keyboard,
    get_task_selection_keyboard,
    get_confirmation_keyboard,
    get_cancel_keyboard,
    get_back_keyboard,
)

logger = logging.getLogger(__name__)


# ================== ОТОБРАЖЕНИЕ МЕНЮ И ЗАДАЧ ==================

async def show_tasks_menu(update: Union[Update, CallbackQuery], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать меню задач."""
    try:
        message = "📋 Управление задачами"
        keyboard = get_tasks_menu_keyboard()
        await send_message(update, message, keyboard)
    except Exception as e:
        logger.error(f"Error in show_tasks_menu: {e}")
        await send_message(update, "❌ Ошибка при открытии меню задач")


async def show_tasks_with_keyboard(
    update: Union[Update, CallbackQuery],
    context: ContextTypes.DEFAULT_TYPE,
    show_all: bool = True
) -> None:
    """Показать список задач с инлайн-кнопками."""
    try:
        db = context.bot_data["db"]
        tasks = db.get_all_tasks()

        if not tasks:
            await send_message(update, "📝 Задачи еще не настроены.")
            return

        message_lines = ["📋 Список домашних задач:\n"]

        for task in tasks:
            status_line = task.format_status(db.get_user_name)
            message_lines.append(status_line)

        overdue_count = sum(1 for task in tasks if task.is_overdue())
        if overdue_count > 0:
            message_lines.append(f"\n⚠️  Всего просрочено задач: {overdue_count}")

        message_lines.append("\n💡 Нажмите на кнопку с задачей, чтобы отметить её выполненной")

        # Передаём список задач в клавиатуру
        keyboard = get_tasks_keyboard(tasks, show_all=show_all)
        await send_message(update, "\n".join(message_lines), keyboard)

    except Exception as e:
        logger.error(f"Error in show_tasks_with_keyboard: {e}")
        await send_message(update, "❌ Ошибка при получении списка задач")


async def manage_tasks(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать меню управления задачами."""
    try:
        keyboard = get_management_keyboard()
        message = "🛠️ Управление задачами"
        await query.edit_message_text(message, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in manage_tasks: {e}")
        await query.edit_message_text("❌ Ошибка при открытии управления задачами")


# ================== ОТМЕТКА ВЫПОЛНЕНИЯ ==================

async def mark_task_done_from_button(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    task_id: int
) -> None:
    """Отметить задачу выполненной при нажатии на инлайн-кнопку."""
    try:
        db = context.bot_data["db"]
        task = db.get_task_by_id(task_id)

        if not task:
            await query.edit_message_text("❌ Задача не найдена")
            return

        db.mark_task_done(
            task_id=task.id,
            user_chat_id=query.from_user.id,
            username=query.from_user.username or "нет",
            first_name=query.from_user.first_name or "Аноним"
        )

        tasks = db.get_all_tasks()
        message_lines = ["📋 Список домашних задач:\n"]

        for t in tasks:
            status_line = t.format_status(db.get_user_name)
            message_lines.append(status_line)

        overdue_count = sum(1 for t in tasks if t.is_overdue())
        if overdue_count > 0:
            message_lines.append(f"\n⚠️  Всего просрочено задач: {overdue_count}")

        message_lines.append(f"\n✅ {query.from_user.first_name} выполнил(а): {task.name}")

        # Передаём обновлённый список задач
        keyboard = get_tasks_keyboard(tasks, show_all=True)
        await query.edit_message_text("\n".join(message_lines), reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in mark_task_done_from_button: {e}")
        await query.edit_message_text("❌ Ошибка при отметке задачи")


# ================== ДОБАВЛЕНИЕ НОВОЙ ЗАДАЧИ ==================

async def handle_add_task(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начать процесс добавления новой задачи."""
    context.user_data["state"] = "waiting_for_new_task"
    await query.edit_message_text(
        "📝 Добавление новой задачи:\n\n"
        "Отправьте сообщение в формате:\n"
        "Название задачи | интервал_в_днях\n\n"
        "Пример: Полить цветы | 3",
        reply_markup=get_cancel_keyboard()
    )


async def process_new_task(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str) -> None:
    """Обработать ввод новой задачи из состояния."""
    if "|" not in user_message:
        await update.message.reply_text(
            "❌ Неверный формат. Используйте: Название | интервал_в_днях\n"
            "Пример: Полить цветы | 3",
            reply_markup=get_cancel_keyboard()
        )
        return

    task_name, interval_str = user_message.split("|", 1)
    task_name = task_name.strip()
    interval_str = interval_str.strip()

    if not task_name or not interval_str.isdigit():
        await update.message.reply_text(
            "❌ Неверный формат. Интервал должен быть числом.",
            reply_markup=get_cancel_keyboard()
        )
        return

    interval = int(interval_str)
    db = context.bot_data["db"]
    success = db.add_new_task(task_name, interval)

    if success:
        await update.message.reply_text(
            f"✅ Задача добавлена:\n"
            f"Название: {task_name}\n"
            f"Интервал: {interval} дней",
            reply_markup=get_back_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ Задача с названием '{task_name}' уже существует.",
            reply_markup=get_cancel_keyboard()
        )

    # Очищаем состояние
    context.user_data.pop("state", None)


# ================== ИЗМЕНЕНИЕ ИНТЕРВАЛА ==================

async def show_task_selection_for_interval(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать список задач для выбора изменения интервала."""
    db = context.bot_data["db"]
    tasks = db.get_all_tasks()
    keyboard = get_task_selection_keyboard(tasks, "edit_interval")
    await query.edit_message_text(
        "📅 Выберите задачу для изменения интервала:",
        reply_markup=keyboard
    )


async def start_interval_edit(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
    """Запросить новый интервал для задачи."""
    context.user_data["state"] = f"waiting_interval_{task_id}"
    await query.edit_message_text(
        "📅 Введите новый интервал в днях для этой задачи:",
        reply_markup=get_cancel_keyboard()
    )


async def process_interval_update(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_message: str,
    state: str
) -> None:
    """Обработать ввод нового интервала."""
    if not user_message.isdigit():
        await update.message.reply_text(
            "❌ Интервал должен быть числом.",
            reply_markup=get_cancel_keyboard()
        )
        return

    new_interval = int(user_message)
    task_id = int(state.split("_")[2])

    db = context.bot_data["db"]
    task = db.get_task_by_id(task_id)

    if task:
        success = db.update_task_interval(task_id, new_interval)
        if success:
            await update.message.reply_text(
                f"✅ Интервал обновлен:\n"
                f"Задача: {task.name}\n"
                f"Новый интервал: {new_interval} дней",
                reply_markup=get_back_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при обновлении интервала",
                reply_markup=get_back_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ Задача не найдена",
            reply_markup=get_back_keyboard()
        )

    context.user_data.pop("state", None)


# ================== ПЕРЕИМЕНОВАНИЕ ЗАДАЧИ ==================

async def show_task_selection_for_rename(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать список задач для выбора переименования."""
    db = context.bot_data["db"]
    tasks = db.get_all_tasks()
    keyboard = get_task_selection_keyboard(tasks, "rename")
    await query.edit_message_text(
        "✏️ Выберите задачу для переименования:",
        reply_markup=keyboard
    )


async def start_rename_task(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, task_id: int) -> None:
    """Запросить новое название для задачи."""
    db = context.bot_data["db"]
    task = db.get_task_by_id(task_id)

    if not task:
        await query.edit_message_text("❌ Задача не найдена")
        return

    context.user_data["state"] = f"waiting_rename_{task_id}"
    await query.edit_message_text(
        f"✏️ Переименование задачи:\n"
        f"Текущее название: {task.name}\n\n"
        f"Введите новое название:",
        reply_markup=get_cancel_keyboard()
    )


async def process_rename_task(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_message: str,
    state: str
) -> None:
    """Обработать ввод нового названия задачи."""
    new_name = user_message.strip()

    if not new_name:
        await update.message.reply_text(
            "❌ Название не может быть пустым.",
            reply_markup=get_cancel_keyboard()
        )
        return

    task_id = int(state.split("_")[2])

    db = context.bot_data["db"]
    task = db.get_task_by_id(task_id)

    if task:
        success = db.rename_task(task_id, new_name)
        if success:
            await update.message.reply_text(
                f"✅ Задача переименована:\n"
                f"Старое название: {task.name}\n"
                f"Новое название: {new_name}",
                reply_markup=get_back_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ Задача с названием '{new_name}' уже существует.",
                reply_markup=get_back_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ Задача не найдена",
            reply_markup=get_back_keyboard()
        )

    context.user_data.pop("state", None)


# ================== УДАЛЕНИЕ ЗАДАЧИ ==================

async def show_task_selection_for_delete(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать список задач для выбора удаления."""
    db = context.bot_data["db"]
    tasks = db.get_all_tasks()
    keyboard = get_task_selection_keyboard(tasks, "delete")
    await query.edit_message_text(
        "🗑️ Выберите задачу для удаления:",
        reply_markup=keyboard
    )


async def confirm_delete_task(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    task_id: int
) -> None:
    """Показать подтверждение удаления задачи."""
    db = context.bot_data["db"]
    task = db.get_task_by_id(task_id)

    if not task:
        await query.edit_message_text("❌ Задача не найдена")
        return

    keyboard = get_confirmation_keyboard("delete", task_id)
    await query.edit_message_text(
        f"🗑️ Вы уверены, что хотите удалить задачу?\n\n"
        f"Название: {task.name}\n"
        f"Интервал: {task.interval_days} дней",
        reply_markup=keyboard
    )


async def execute_delete_task(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    task_id: int
) -> None:
    """Выполнить удаление задачи после подтверждения."""
    db = context.bot_data["db"]
    task = db.get_task_by_id(task_id)

    if not task:
        await query.edit_message_text("❌ Задача не найдена")
        return

    success = db.delete_task(task_id)
    if success:
        await query.edit_message_text(
            f"✅ Задача '{task.name}' удалена",
            reply_markup=get_back_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при удалении задачи",
            reply_markup=get_back_keyboard()
        )