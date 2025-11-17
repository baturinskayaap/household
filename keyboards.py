from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from database import Database
from telegram import ReplyKeyboardRemove

def remove_reply_keyboard():
    """Убрать reply-клавиатуру"""
    return ReplyKeyboardRemove()
def get_main_inline_keyboard():
    """Inline-клавиатура для главного меню (для использования в callback queries)"""
    keyboard = [
        [
            InlineKeyboardButton("📋 Список задач", callback_data="show_tasks"),
            InlineKeyboardButton("⏰ Ближайшие", callback_data="show_urgent_tasks")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="show_stats"),
            InlineKeyboardButton("✅ Выполнить", callback_data="quick_done")
        ],
        [
            InlineKeyboardButton("🛠️ Управление", callback_data="manage_tasks"),
            InlineKeyboardButton("🔔 Напоминания", callback_data="reminder_settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
def get_main_keyboard():
    """Основная reply-клавиатура для быстрого доступа"""
    keyboard = [
        ["📋 Список задач", "⏰ Ближайшие"],
        ["📊 Статистика", "✅ Выполнить"],
        ["🛠️ Управление", "🔔 Напоминания"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_tasks_keyboard(show_all=False):
    """Клавиатура для быстрого выполнения задач"""
    db = Database()
    tasks = db.get_all_tasks()
    
    keyboard = []
    
    if not tasks:
        keyboard.append([InlineKeyboardButton("📝 Нет задач - добавьте первую!", callback_data="add_task")])
        return InlineKeyboardMarkup(keyboard)
    
    # Показываем только срочные задачи или все
    if not show_all:
        tasks = [t for t in tasks if t.is_overdue() or t.days_until_due() <= 2]
    
    if not tasks:
        keyboard.append([InlineKeyboardButton("🎉 Все задачи выполнены!", callback_data="refresh_tasks")])
        keyboard.append([InlineKeyboardButton("📋 Показать все задачи", callback_data="show_all_tasks")])
        return InlineKeyboardMarkup(keyboard)
    
    # Создаем кнопки по 2 в ряд
    for i in range(0, len(tasks), 2):
        row = []
        for task in tasks[i:i+2]:
            emoji = "🔴" if task.is_overdue() else "🟡" if task.days_until_due() <= 1 else "✅"
            row.append(InlineKeyboardButton(
                f"{emoji} {task.name}", 
                callback_data=f"done_{task.id}"
            ))
        keyboard.append(row)
    
    # Дополнительные кнопки
    if not show_all and len(tasks) < len(db.get_all_tasks()):
        keyboard.append([InlineKeyboardButton("📋 Показать все задачи", callback_data="show_all_tasks")])
    else:
        keyboard.append([InlineKeyboardButton("⏰ Только срочные", callback_data="show_urgent_tasks")])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Обновить", callback_data="refresh_tasks"),
        InlineKeyboardButton("📊 Статистика", callback_data="show_stats")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_management_keyboard():
    """Клавиатура для управления задачами"""
    keyboard = [
        [InlineKeyboardButton("📝 Добавить задачу", callback_data="add_task")],
        [InlineKeyboardButton("⚙️ Редактировать интервал", callback_data="edit_interval")],
        [InlineKeyboardButton("✏️ Переименовать задачу", callback_data="rename_task")],
        [InlineKeyboardButton("🗑️ Удалить задачу", callback_data="delete_task")],
        [
            InlineKeyboardButton("📋 Список задач", callback_data="show_tasks"),
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_reminders_keyboard():
    """Клавиатура для управления напоминаниями"""
    keyboard = [
        [InlineKeyboardButton("⚙️ Настройки напоминаний", callback_data="reminder_settings")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_task_selection_keyboard(action):
    """Клавиатура для выбора задачи"""
    db = Database()
    tasks = db.get_all_tasks()
    
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
    """Простая кнопка назад"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    return InlineKeyboardMarkup(keyboard)
