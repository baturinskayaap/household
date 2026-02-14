# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram import ReplyKeyboardRemove


def remove_reply_keyboard():
    """Убрать reply-клавиатуру"""
    return ReplyKeyboardRemove()


# ================== ОСНОВНЫЕ КЛАВИАТУРЫ ==================

def get_main_keyboard():
    """Основная reply-клавиатура для быстрого доступа (3 кнопки)"""
    keyboard = [
        ["📋 Задачи", "🛒 Покупки"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_main_inline_keyboard():
    """Inline-клавиатура для главного меню"""
    keyboard = [
        [InlineKeyboardButton("📋 Задачи", callback_data="tasks_main")],
        [InlineKeyboardButton("🛒 Покупки", callback_data="shopping_list")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tasks_menu_keyboard():
    """Клавиатура для меню задач"""
    keyboard = [
        [InlineKeyboardButton("📝 Все задачи", callback_data="show_tasks")],
        [InlineKeyboardButton("🛠️ Управление задачами", callback_data="manage_tasks")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ================== КЛАВИАТУРЫ ДЛЯ ЗАДАЧ (с параметрами) ==================

def get_tasks_keyboard(tasks, show_all=False):
    """
    Клавиатура для быстрого выполнения задач.
    Принимает список задач (уже полученных из БД) для избежания прямого обращения к БД.
    """
    keyboard = []

    if not tasks:
        keyboard.append([InlineKeyboardButton("📝 Нет задач - добавьте первую!", callback_data="add_task")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_tasks_menu")])
        return InlineKeyboardMarkup(keyboard)

    # Показываем только срочные задачи или все
    if not show_all:
        filtered_tasks = []
        for task in tasks:
            if task.last_done is None:
                # Задачи, которые никогда не выполнялись, считаем срочными
                filtered_tasks.append(task)
            elif task.is_overdue():
                filtered_tasks.append(task)
            elif task.days_until_due() <= 2:
                filtered_tasks.append(task)
        tasks = filtered_tasks

    if not tasks:
        keyboard.append([InlineKeyboardButton("🎉 Все задачи выполнены!", callback_data="refresh_tasks")])
        keyboard.append([InlineKeyboardButton("📋 Показать все задачи", callback_data="show_all_tasks")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_tasks_menu")])
        return InlineKeyboardMarkup(keyboard)

    # Создаем кнопки по 2 в ряд
    for i in range(0, len(tasks), 2):
        row = []
        for task in tasks[i:i+2]:
            if task.last_done is None:
                emoji = "🆕"  # Новая задача
            elif task.is_overdue():
                emoji = "🔴"  # Просрочено
            elif task.days_until_due() <= 1:
                emoji = "🟡"  # Срочно
            else:
                emoji = "✅"  # В норме

            # Обрезаем длинные названия
            task_name = task.name
            if len(task_name) > 15:
                task_name = task_name[:12] + "..."

            row.append(InlineKeyboardButton(
                f"{emoji} {task_name}",
                callback_data=f"done_{task.id}"
            ))
        keyboard.append(row)

    # Дополнительные кнопки
    # Примечание: all_tasks_count здесь не передаётся, поэтому для определения наличия всех задач
    # можно использовать логику: если мы в режиме show_all, то показываем кнопку "Только срочные",
    # иначе если есть задачи, которые не вошли в filtered_tasks (т.е. не срочные), то показываем "Показать все".
    # Но проще: пусть логику решает обработчик, а клавиатура просто отображает переданные задачи.
    # Для кнопок "Показать все" / "Только срочные" мы можем использовать show_all как признак:
    if show_all:
        keyboard.append([InlineKeyboardButton("⏰ Только срочные", callback_data="show_urgent_tasks")])
    else:
        # Если мы не в режиме show_all, но есть задачи (возможно, отфильтрованные), предложим показать все
        # но только если есть задачи, которые могли быть отфильтрованы. В упрощённом варианте просто добавим кнопку
        # "Показать все", но чтобы избежать дублирования, проверим наличие всех задач по сравнению с исходным списком
        # (исходный список не передаётся). Оставим как есть: кнопка появляется только если мы в режиме не-show_all,
        # что логично: пользователь хочет вернуться к полному списку.
        keyboard.append([InlineKeyboardButton("📋 Показать все задачи", callback_data="show_all_tasks")])

    keyboard.append([
        InlineKeyboardButton("🔄 Обновить", callback_data="refresh_tasks"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_tasks_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_management_keyboard():
    """Клавиатура для управления задачами"""
    keyboard = [
        [InlineKeyboardButton("📝 Добавить задачу", callback_data="add_task")],
        [InlineKeyboardButton("⚙️ Редактировать интервал", callback_data="edit_interval")],
        [InlineKeyboardButton("✏️ Переименовать задачу", callback_data="rename_task")],
        [InlineKeyboardButton("🗑️ Удалить задачу", callback_data="delete_task")],
        [InlineKeyboardButton("📋 Список задач", callback_data="show_tasks")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_tasks_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_task_selection_keyboard(tasks, action):
    """
    Клавиатура для выбора задачи.
    Принимает список задач и действие (префикс callback_data).
    """
    keyboard = []

    for task in tasks:
        keyboard.append([InlineKeyboardButton(
            f"{task.name} ({task.interval_days} дн.)",
            callback_data=f"{action}_{task.id}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_manage")])

    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(action: str, task_id: int):
    """Клавиатура подтверждения для опасных действий"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}_{task_id}"),
            InlineKeyboardButton("❌ Нет", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_keyboard():
    """Клавиатура отмены действия"""
    keyboard = [
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard():
    """Простая кнопка назад в главное меню"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ================== КЛАВИАТУРЫ ДЛЯ СПИСКА ПОКУПОК ==================

def get_shopping_keyboard():
    """Основная клавиатура списка покупок"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить пункт", callback_data="shopping_add")],
        [InlineKeyboardButton("📋 Показать список", callback_data="shopping_show")],
        [InlineKeyboardButton("🗑️ Быстрая очистка", callback_data="shopping_quick_clear")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_shopping_items_keyboard(items, stats, show_checked=True):
    """
    Клавиатура с пунктами списка покупок

    Args:
        items: список ShoppingItem
        stats: статистика списка (total, checked, unchecked)
        show_checked: показывать отмеченные пункты
    """
    keyboard = []

    if not items:
        keyboard.append([InlineKeyboardButton("📝 Список покупок пуст", callback_data="no_action")])
        keyboard.append([InlineKeyboardButton("➕ Добавить пункт", callback_data="shopping_add")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_shopping")])
        return InlineKeyboardMarkup(keyboard)

    # Создаем кнопки для каждого пункта
    for item in items:
        status = "✅" if item.is_checked else "⬜️"
        button_text = f"{status} {item.item_text}"
        if item.is_checked and len(button_text) > 40:
            button_text = button_text[:37] + "..."

        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"shopping_toggle_{item.id}")
        ])

    # Кнопки управления видом
    toggle_text = "⬜️ Только неотмеченные" if show_checked else "✅ Показать все"
    keyboard.append([
        InlineKeyboardButton(toggle_text, callback_data="shopping_toggle_view"),
        InlineKeyboardButton("🔄 Обновить", callback_data="shopping_show")
    ])

    # Кнопки добавления и очистки
    row = [
        InlineKeyboardButton("➕ Добавить", callback_data="shopping_add"),
    ]
    if stats['checked'] > 0:
        row.append(InlineKeyboardButton("🧹 Отмеченные", callback_data="shopping_clear_checked"))
    keyboard.append(row)

    # Кнопка очистки всего списка, если есть пункты
    if stats['total'] > 0:
        keyboard.append([
            InlineKeyboardButton("🗑️ Очистить все", callback_data="shopping_clear_all")
        ])

    # Кнопка возврата
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_shopping")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_shopping_clear_confirmation(clear_type="checked"):
    """Клавиатура подтверждения очистки списка покупок"""
    if clear_type == "checked":
        text = "🧹 Очистить отмеченные?"
        callback = "shopping_confirm_clear_checked"
    else:
        text = "🗑️ Очистить весь список?"
        callback = "shopping_confirm_clear_all"

    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=callback),
            InlineKeyboardButton("❌ Нет", callback_data="shopping_show")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_shopping_stats_keyboard():
    """Клавиатура для статистики списка покупок"""
    keyboard = [
        [InlineKeyboardButton("📋 Показать список", callback_data="shopping_show")],
        [InlineKeyboardButton("➕ Добавить пункт", callback_data="shopping_add")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_shopping")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_shopping_back_keyboard():
    """Клавиатура для возврата в меню списка покупок"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад в список покупок", callback_data="back_to_shopping")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_shopping_add_stream_keyboard():
    """Клавиатура для режима потокового добавления пунктов"""
    keyboard = [
        [InlineKeyboardButton("🔚 Завершить добавление", callback_data="shopping_exit_stream")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_shopping_back_to_stream_keyboard():
    """Клавиатура для возврата в потоковый режим после добавления"""
    keyboard = [
        [InlineKeyboardButton("🔚 Завершить", callback_data="shopping_exit_stream")]
    ]
    return InlineKeyboardMarkup(keyboard)