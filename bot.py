import logging
from telegram.error import BadRequest
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from datetime import time
#import config
try:
    import config_dev as config
except ImportError:
    import config
from database import Database
from reminder_system import ReminderSystem
from utils import format_reminder_message
from keyboards import (
    get_main_keyboard,
    get_tasks_keyboard, get_management_keyboard,
    get_reminders_keyboard, get_task_selection_keyboard,
    get_confirmation_keyboard, get_cancel_keyboard, get_back_keyboard,
    # Новые импорты для списка покупок
    get_shopping_keyboard, get_shopping_items_keyboard,
    get_shopping_clear_confirmation, get_shopping_stats_keyboard,
    get_shopping_back_keyboard
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HouseholdBot:
    def __init__(self):
        self.db = Database()
        self.reminder_system = ReminderSystem(self.db)
        self.application = None
        self.user_states = {}
        # Добавляем состояние для просмотра отмеченных пунктов покупок
        self.shopping_show_checked = {}
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start с основной клавиатурой"""
        try:
            welcome_text = """
👋 Привет! Я бот для управления домашними делами

📱 Используйте кнопки ниже для быстрого доступа:

📋 Список задач - все задачи с кнопками
⏰ Ближайшие - срочные задачи
📊 Статистика - ваша активность
✅ Выполнить - отметка выполнения
🛠️ Управление - редактирование задач
🔔 Напоминания - уведомления
🛒 Список покупок - управление покупками
            """
            keyboard = get_main_keyboard()
            await update.message.reply_text(welcome_text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error in /start: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений от кнопок"""
        try:
            text = update.message.text
            user_id = update.effective_user.id
            
            if text == "📋 Список задач":
                await self.show_tasks_with_keyboard(update, context)
            elif text == "⏰ Ближайшие":
                await self.show_next_tasks(update, context)
            elif text == "📊 Статистика":
                await self.show_stats(update, context)
            elif text == "✅ Выполнить":
                await self.quick_done_with_inline(update, context)
            elif text == "🛠️ Управление":
                await self.manage_tasks(update, context)
            elif text == "🔔 Напоминания":
                await self.reminder_settings(update, context)
            elif text == "🛒 Список покупок":
            # Создаем fake query для текстового сообщения
                class FakeQuery:
                    def __init__(self, update):
                        self.from_user = update.effective_user
                        self.message = update.message
                        self.edit_message_text = self._edit_message_text
                    
                    async def _edit_message_text(self, text, reply_markup=None):
                        await self.message.reply_text(text, reply_markup=reply_markup)
                
                fake_query = FakeQuery(update)
                await self.show_shopping_list(fake_query, context)
            else:
                await self.handle_user_state(update, context)    
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await update.message.reply_text("❌ Ошибка при обработке сообщения")
    
    # ================== МЕТОДЫ ДЛЯ СПИСКА ПОКУПОК ==================
    
    async def show_shopping_list(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню списка покупок"""
        try:
            keyboard = get_shopping_keyboard()
            message = """
    🛒 Список покупок:

    • Добавить новый пункт
    • Просмотреть/отметить пункты
    • Очистить отмеченные или весь список
    • Статистика списка
            """
            await query.edit_message_text(message, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error in show_shopping_list: {e}")
            await query.edit_message_text("❌ Ошибка при открытии списка покупок")
    
    async def show_shopping_items(self, query, context: ContextTypes.DEFAULT_TYPE, show_checked=True):
        """Показать список покупок с кнопками для отметки"""
        try:
            user_id = query.from_user.id
            items = self.db.get_shopping_items(show_checked=show_checked)
            
            if not items:
                await query.edit_message_text(
                    "📝 Список покупок пуст. Добавьте первый пункт!",
                    reply_markup=get_shopping_keyboard()
                )
                return
            
            # Обновляем настройку отображения для пользователя
            self.shopping_show_checked[user_id] = show_checked
            
            message_lines = ["🛒 Список покупок:\n"]
            
            # Показываем статистику
            stats = self.db.get_shopping_item_count()
            if stats['total'] > 0:
                message_lines.append(f"📊 Всего: {stats['total']} | ✅ Отмечено: {stats['checked']} | ⬜️ Неотмечено: {stats['unchecked']}\n")
            
            for item in items:
                message_lines.append(f"{item.format_for_display()}")
            
            keyboard = get_shopping_items_keyboard(items, show_checked)
            
            # Используем try-except для обработки ошибки
            try:
                await query.edit_message_text(
                    "\n".join(message_lines), 
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    # Просто отвечаем на запрос без изменения сообщения
                    await query.answer()
                else:
                    raise
            
        except Exception as e:
            logger.error(f"Error in show_shopping_items: {e}")
            await query.edit_message_text("❌ Ошибка при получении списка покупок")
    
    async def add_shopping_item(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Начать добавление нового пункта в список покупок"""
        try:
            user_id = query.from_user.id  # Используем query.from_user вместо update.effective_user
            self.user_states[user_id] = "waiting_for_shopping_item"
            
            await query.edit_message_text(  # Используем query.edit_message_text
                "➕ Добавление нового пункта в список покупок:\n\n"
                "Просто напишите название пункта.\n"
                "Например: Молоко, 2л",
                reply_markup=get_cancel_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error in add_shopping_item: {e}")
            await query.edit_message_text("❌ Ошибка при добавлении пункта")
    
    async def toggle_shopping_item(self, query, item_id: int):
        """Переключить статус отметки пункта"""
        try:
            item = self.db.toggle_shopping_item(item_id)
            
            if item:
                user_id = query.from_user.id
                show_checked = self.shopping_show_checked.get(user_id, True)
                
                items = self.db.get_shopping_items(show_checked=show_checked)
                if not items:
                    await query.edit_message_text(
                        "📝 Список покупок пуст. Добавьте новый пункт!",
                        reply_markup=get_shopping_keyboard()
                    )
                    return
                
                # Обновляем сообщение
                message_lines = ["🛒 Список покупок:\n"]
                
                stats = self.db.get_shopping_item_count()
                if stats['total'] > 0:
                    message_lines.append(f"📊 Всего: {stats['total']} | ✅ Отмечено: {stats['checked']} | ⬜️ Неотмечено: {stats['unchecked']}\n")
                
                for item in items:
                    message_lines.append(f"{item.format_for_display()}")
                
                keyboard = get_shopping_items_keyboard(items, show_checked)
                await query.edit_message_text("\n".join(message_lines), reply_markup=keyboard)
            else:
                await query.edit_message_text("❌ Пункт не найден")
                
        except Exception as e:
            logger.error(f"Error toggling shopping item: {e}")
            await query.edit_message_text("❌ Ошибка при обновлении пункта")
    
    async def clear_checked_shopping_items(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение очистки отмеченных пунктов"""
        try:
            stats = self.db.get_shopping_item_count()
            
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
            
        except Exception as e:
            logger.error(f"Error in clear_checked_shopping_items: {e}")
            await query.edit_message_text("❌ Ошибка при очистке списка")
    
    async def clear_all_shopping_items(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение очистки всего списка покупок"""
        try:
            stats = self.db.get_shopping_item_count()
            
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
            
        except Exception as e:
            logger.error(f"Error in clear_all_shopping_items: {e}")
            await query.edit_message_text("❌ Ошибка при очистке списка")
    
    async def confirm_clear_checked_items(self, query):
        """Подтверждение удаления отмеченных пунктов"""
        try:
            deleted_count = self.db.delete_checked_items()
            
            await query.edit_message_text(
                f"✅ Удалено {deleted_count} отмеченных пунктов.",
                reply_markup=get_shopping_back_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error confirming clear checked items: {e}")
            await query.edit_message_text("❌ Ошибка при удалении пунктов")
    
    async def confirm_clear_all_items(self, query):
        """Подтверждение удаления всего списка"""
        try:
            deleted_count = self.db.delete_all_shopping_items()
            
            await query.edit_message_text(
                f"✅ Удалено {deleted_count} пунктов. Список очищен.",
                reply_markup=get_shopping_back_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error confirming clear all items: {e}")
            await query.edit_message_text("❌ Ошибка при очистке списка")
    
    async def show_shopping_stats(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику списка покупок"""
        try:
            stats = self.db.get_shopping_item_count()
            
            message_lines = ["📊 Статистика списка покупок:\n"]
            message_lines.append(f"📈 Всего пунктов: {stats['total']}")
            message_lines.append(f"✅ Отмечено: {stats['checked']}")
            message_lines.append(f"⬜️ Не отмечено: {stats['unchecked']}")
            
            if stats['total'] > 0:
                percentage = (stats['checked'] / stats['total']) * 100
                message_lines.append(f"📊 Завершено: {percentage:.1f}%")
            
            keyboard = get_shopping_stats_keyboard()
            await query.edit_message_text("\n".join(message_lines), reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error in show_shopping_stats: {e}")
            await query.edit_message_text("❌ Ошибка при получении статистики")
    
    async def process_shopping_item(self, update, user_message):
        """Обработка добавления нового пункта в список покупок"""
        item_text = user_message.strip()
        
        if not item_text:
            await update.message.reply_text(
                "❌ Название пункта не может быть пустым.",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        success = self.db.add_shopping_item(item_text)
        
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
        
        user_id = update.effective_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    # ================== КОНЕЦ МЕТОДОВ ДЛЯ СПИСКА ПОКУПОК ==================
    
    async def show_tasks_with_keyboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE, show_all=True):
        """Показать задачи с инлайн-кнопками"""
        try:
            tasks = self.db.get_all_tasks()
            
            if not tasks:
                await self.send_message(update, "📝 Задачи еще не настроены.")
                return
            
            message_lines = ["📋 Список домашних задач:\n"]
            
            for task in tasks:
                status_line = task.format_status(self.db.get_user_name)
                message_lines.append(status_line)
            
            overdue_count = sum(1 for task in tasks if task.is_overdue())
            if overdue_count > 0:
                message_lines.append(f"\n⚠️  Всего просрочено задач: {overdue_count}")
            
            message_lines.append("\n💡 Нажмите на кнопку с задачей, чтобы отметить её выполненной")
            
            keyboard = get_tasks_keyboard(show_all=show_all)
            await self.send_message(update, "\n".join(message_lines), keyboard)
        
        except Exception as e:
            logger.error(f"Error in show_tasks_with_keyboard: {e}")
            await self.send_message(update, "❌ Ошибка при получении списка задач")
    
    async def show_next_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать ближайшие задачи"""
        try:
            tasks = self.db.get_all_tasks()
            
            tasks_sorted = sorted(tasks, key=lambda t: (
                0 if t.is_overdue() else 1,
                t.days_until_due() if not t.is_overdue() else float('inf')
            ))
            
            message_lines = ["⏰ Ближайшие задачи:\n"]
            
            for task in tasks_sorted[:5]:
                if task.is_overdue():
                    overdue_days = (task.days_since_done() or 0) - task.interval_days
                    message_lines.append(f"🔔 {task.name} - просрочено на {overdue_days} дн.")
                else:
                    days_left = task.days_until_due()
                    message_lines.append(f"⏳ {task.name} - через {days_left} дн.")
            
            await self.send_message(update, "\n".join(message_lines))
        
        except Exception as e:
            logger.error(f"Error in show_next_tasks: {e}")
            await self.send_message(update, "❌ Ошибка при получении списка задач.")
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику"""
        try:
            stats = self.db.get_user_statistics(days=30)
            
            message_lines = [f"📊 Статистика за 30 дней:\n"]
            message_lines.append(f"📈 Всего выполнено задач: {stats['total_tasks']}")
            
            if stats['user_stats']:
                message_lines.append("\n👥 Распределение:")
                for user_name, user_data in stats['user_stats'].items():
                    percentage = (user_data['task_count'] / stats['total_tasks'] * 100) if stats['total_tasks'] > 0 else 0
                    message_lines.append(f"   {user_name}: {user_data['task_count']} ({percentage:.1f}%)")
            
            await self.send_message(update, "\n".join(message_lines))
        
        except Exception as e:
            logger.error(f"Error in show_stats: {e}")
            await self.send_message(update, "❌ Ошибка при получении статистики.")
    
    async def quick_done_with_inline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрая отметка выполнения через inline-кнопки"""
        try:
            tasks = self.db.get_all_tasks()
            urgent_tasks = [t for t in tasks if t.is_overdue() or t.days_until_due() <= 2]
            
            if not urgent_tasks:
                await self.send_message(update, "🎉 Нет срочных задач для выполнения!")
                return
            
            keyboard = get_tasks_keyboard(show_all=False)
            await self.send_message(update, "✅ Выберите задачу для отметки выполнения:", keyboard)
            
        except Exception as e:
            logger.error(f"Error in quick_done_with_inline: {e}")
            await self.send_message(update, "❌ Ошибка при получении списка задач")
    
    async def manage_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Управление задачами"""
        try:
            keyboard = get_management_keyboard()
            message = """
🛠️ Управление задачами:

• Добавить новую задачу
• Изменить интервал выполнения
• Переименовать задачу
• Удалить задачу
            """
            await self.send_message(update, message, keyboard)
        except Exception as e:
            logger.error(f"Error in manage_tasks: {e}")
            await self.send_message(update, "❌ Ошибка при открытии управления задачами")
    
    async def reminder_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Настройки напоминаний"""
        try:
            keyboard = get_reminders_keyboard()
            message = """
🔔 Управление напоминаниями:

• Ежедневные напоминания приходят в 17:00
• Недельная статистика - по воскресеньям в 18:00

Для настройки времени измените config.py
            """
            await self.send_message(update, message, keyboard)
            
        except Exception as e:
            logger.error(f"Error in reminder_settings: {e}")
            await self.send_message(update, "❌ Ошибка при открытии настроек напоминаний")
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на инлайн-кнопки"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if user_id not in config.ADMIN_IDS:
            await query.edit_message_text("❌ У вас нет прав для выполнения этого действия")
            return
        
        data = query.data
        
        try:
            # ================== ОБРАБОТКА СПИСКА ПОКУПОК ==================
            if data == "shopping_list":
                await self.show_shopping_list(query, context)
            
            elif data == "back_to_shopping":
                await self.show_shopping_list(query, context)
            
            elif data == "shopping_show":
                user_id = query.from_user.id
                show_checked = self.shopping_show_checked.get(user_id, True)
                await self.show_shopping_items(query, context, show_checked=show_checked)
            
            elif data == "shopping_toggle_view":
                user_id = query.from_user.id
                current = self.shopping_show_checked.get(user_id, True)
                await self.show_shopping_items(query, context, show_checked=not current)
            
            elif data == "shopping_add":
                await self.add_shopping_item(query, context)
            
            elif data.startswith("shopping_toggle_"):
                item_id = int(data.split("_")[2])
                await self.toggle_shopping_item(query, item_id)
            
            elif data == "shopping_clear_checked":
                await self.clear_checked_shopping_items(query, context)
            
            elif data == "shopping_clear_all":
                await self.clear_all_shopping_items(query, context)
            
            elif data == "shopping_confirm_clear_checked":
                await self.confirm_clear_checked_items(query)
            
            elif data == "shopping_confirm_clear_all":
                await self.confirm_clear_all_items(query)
            
            elif data == "shopping_stats":
                await self.show_shopping_stats(query, context)
            
            # ================== ОБРАБОТКА ЗАДАЧ ==================
            elif data.startswith("done_"):
                task_id = int(data.split("_")[1])
                await self.mark_task_done_from_button(query, task_id)
            
            elif data == "refresh_tasks":
                await self.show_tasks_with_keyboard(query, context, show_all=True)
            elif data == "quick_done":
                await self.quick_done_with_inline_from_button(query)
            elif data == "show_all_tasks":
                await self.show_tasks_with_keyboard(query, context, show_all=True)
            elif data == "show_urgent_tasks":
                await self.show_tasks_with_keyboard(query, context, show_all=False)
            
            elif data == "add_task":
                await self.handle_add_task(query)
            elif data == "edit_interval":
                keyboard = get_task_selection_keyboard("edit_interval")
                await query.edit_message_text("📅 Выберите задачу для изменения интервала:", reply_markup=keyboard)
            elif data == "rename_task":
                keyboard = get_task_selection_keyboard("rename")
                await query.edit_message_text("✏️ Выберите задачу для переименования:", reply_markup=keyboard)
            elif data == "delete_task":
                keyboard = get_task_selection_keyboard("delete")
                await query.edit_message_text("🗑️ Выберите задачу для удаления:", reply_markup=keyboard)
            
            elif data == "show_tasks":
                await self.show_tasks_with_keyboard(query, context, show_all=True)
            elif data == "back_to_main":
                await self.show_main_menu(query)
            elif data == "back_to_manage":
                await self.manage_tasks(query, context)
       
            elif data == "reminder_settings":
                await self.reminder_settings_from_button(query)
            elif data == "show_stats":
                await self.show_stats_from_button(query)
            
            elif data == "cancel_action":
                await self.show_main_menu(query)
            
            elif data.startswith("edit_interval_"):
                task_id = int(data.split("_")[2])
                self.user_states[user_id] = f"waiting_interval_{task_id}"
                await query.edit_message_text(
                    f"📅 Введите новый интервал в днях для этой задачи:",
                    reply_markup=get_cancel_keyboard()
                )
            
            elif data.startswith("rename_"):
                task_id = int(data.split("_")[1])
                self.user_states[user_id] = f"waiting_rename_{task_id}"
                task = self.db.get_task_by_id(task_id)
                if task:
                    await query.edit_message_text(
                        f"✏️ Переименование задачи:\n"
                        f"Текущее название: {task.name}\n\n"
                        f"Введите новое название:",
                        reply_markup=get_cancel_keyboard()
                    )
                else:
                    await query.edit_message_text("❌ Задача не найдена")
            
            elif data.startswith("delete_"):
                task_id = int(data.split("_")[1])
                task = self.db.get_task_by_id(task_id)
                if task:
                    keyboard = get_confirmation_keyboard("delete", task_id)
                    await query.edit_message_text(
                        f"🗑️ Вы уверены, что хотите удалить задачу?\n\n"
                        f"Название: {task.name}\n"
                        f"Интервал: {task.interval_days} дней",
                        reply_markup=keyboard
                    )
                else:
                    await query.edit_message_text("❌ Задача не найдена")
            
            elif data.startswith("confirm_delete_"):
                task_id = int(data.split("_")[2])
                await self.confirm_delete_task(query, task_id)
            
            else:
                await query.edit_message_text("❌ Неизвестное действие")
                
        except Exception as e:
            logger.error(f"Error in button handler: {e}")
            await query.edit_message_text("❌ Произошла ошибка при обработке действия")
    
    async def mark_task_done_from_button(self, query, task_id):
        """Отметка задачи выполненной из кнопки"""
        task = self.db.get_task_by_id(task_id)
        
        if task:
            self.db.mark_task_done(
                task_id=task.id,
                user_chat_id=query.from_user.id,
                username=query.from_user.username or "нет",
                first_name=query.from_user.first_name or "Аноним"
            )
            
            tasks = self.db.get_all_tasks()
            message_lines = ["📋 Список домашних задач:\n"]
            
            for t in tasks:
                status_line = t.format_status(self.db.get_user_name)
                message_lines.append(status_line)
            
            overdue_count = sum(1 for t in tasks if t.is_overdue())
            if overdue_count > 0:
                message_lines.append(f"\n⚠️  Всего просрочено задач: {overdue_count}")
            
            message_lines.append(f"\n✅ {query.from_user.first_name} выполнил(а): {task.name}")
            
            keyboard = get_tasks_keyboard(show_all=True)
            await query.edit_message_text("\n".join(message_lines), reply_markup=keyboard)
        else:
            await query.edit_message_text("❌ Задача не найдена")
    
    async def quick_done_with_inline_from_button(self, query):
        """Быстрая отметка выполнения из inline-кнопки"""
        try:
            tasks = self.db.get_all_tasks()
            urgent_tasks = [t for t in tasks if t.is_overdue() or t.days_until_due() <= 2]
            
            if not urgent_tasks:
                await query.edit_message_text("🎉 Нет срочных задач для выполнения!")
                return
            
            keyboard = get_tasks_keyboard(show_all=False)
            await query.edit_message_text(
                "✅ Выберите задачу для отметки выполнения:",
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in quick_done_with_inline_from_button: {e}")
            await query.edit_message_text("❌ Ошибка при получении списка задач")
    
    async def handle_add_task(self, query):
        """Обработка добавления задачи"""
        self.user_states[query.from_user.id] = "waiting_for_new_task"
        await query.edit_message_text(
            "📝 Добавление новой задачи:\n\n"
            "Отправьте сообщение в формате:\n"
            "Название задачи | интервал_в_днях\n\n"
            "Пример: Полить цветы | 3",
            reply_markup=get_cancel_keyboard()
        )
    
    async def reminder_settings_from_button(self, query):
        """Настройки напоминаний из кнопки"""
        message = """
⚙️ Настройки напоминаний:

Текущее время напоминаний:
• Ежедневные: 17:00
• Недельные: воскресенье 18:00

Для изменения отредактируйте config.py
        """
        await query.edit_message_text(message, reply_markup=get_back_keyboard())
    
    async def show_stats_from_button(self, query):
        """Статистика из кнопки"""
        await self.show_stats(query, None)
    
    async def confirm_delete_task(self, query, task_id):
        """Подтверждение удаления задачи"""
        task = self.db.get_task_by_id(task_id)
        
        if task:
            success = self.db.delete_task(task_id)
            if success:
                await query.edit_message_text(f"✅ Задача '{task.name}' удалена", reply_markup=get_back_keyboard())
            else:
                await query.edit_message_text("❌ Ошибка при удалении задачи", reply_markup=get_back_keyboard())
        else:
            await query.edit_message_text("❌ Задача не найдена", reply_markup=get_back_keyboard())
    
    async def show_main_menu(self, query):
        """Показать главное меню через inline-клавиатуру"""
        welcome_text = "👋 Главное меню\n\n📱 Используйте кнопки ниже для быстрого доступа:"
        from keyboards import get_main_inline_keyboard
        keyboard = get_main_inline_keyboard()
        await query.edit_message_text(welcome_text, reply_markup=keyboard)
    
    async def handle_user_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка состояний пользователя"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_states:
            return
        
        state = self.user_states[user_id]
        user_message = update.message.text
        
        try:
            if state == "waiting_for_new_task":
                await self.process_new_task(update, user_message)
            elif state.startswith("waiting_interval_"):
                await self.process_interval_update(update, user_message, state)
            elif state.startswith("waiting_rename_"):
                await self.process_rename_task(update, user_message, state)
            elif state == "waiting_for_shopping_item":
                await self.process_shopping_item(update, user_message)
                
        except Exception as e:
            logger.error(f"Error handling user state: {e}")
            await update.message.reply_text("❌ Ошибка при обработке запроса")
            if user_id in self.user_states:
                del self.user_states[user_id]
    
    async def process_new_task(self, update, user_message):
        """Обработка добавления новой задачи"""
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
        success = self.db.add_new_task(task_name, interval)
        
        if success:
            await update.message.reply_text(
                f"✅ Задача добавлена:\n"
                f"Название: {task_name}\n"
                f"Интервал: {interval} дней"
            )
        else:
            await update.message.reply_text(
                f"❌ Задача с названием '{task_name}' уже существует."
            )
        
        del self.user_states[update.effective_user.id]
    
    async def process_interval_update(self, update, user_message, state):
        """Обработка обновления интервала"""
        task_id = int(state.split("_")[2])
        
        if not user_message.isdigit():
            await update.message.reply_text(
                "❌ Интервал должен быть числом.",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        new_interval = int(user_message)
        task = self.db.get_task_by_id(task_id)
        
        if task:
            success = self.db.update_task_interval(task_id, new_interval)
            if success:
                await update.message.reply_text(
                    f"✅ Интервал обновлен:\n"
                    f"Задача: {task.name}\n"
                    f"Новый интервал: {new_interval} дней"
                )
            else:
                await update.message.reply_text("❌ Ошибка при обновлении интервала")
        else:
            await update.message.reply_text("❌ Задача не найдена")
        
        del self.user_states[update.effective_user.id]
    
    async def process_rename_task(self, update, user_message, state):
        """Обработка переименования задачи"""
        task_id = int(state.split("_")[2])
        new_name = user_message.strip()
        
        if not new_name:
            await update.message.reply_text(
                "❌ Название не может быть пустым.",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        task = self.db.get_task_by_id(task_id)
        if task:
            success = self.db.rename_task(task_id, new_name)
            if success:
                await update.message.reply_text(
                    f"✅ Задача переименована:\n"
                    f"Старое название: {task.name}\n"
                    f"Новое название: {new_name}"
                )
            else:
                await update.message.reply_text(
                    f"❌ Задача с названием '{new_name}' уже существует."
                )
        else:
            await update.message.reply_text("❌ Задача не найдена")
        
        del self.user_states[update.effective_user.id]
    
    async def send_message(self, update, text, reply_markup=None):
        """Универсальный метод отправки сообщений"""
        try:
            if hasattr(update, 'message') and update.message:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await update.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        except BadRequest as e:
            if "Message is not modified" in str(e):
                # Игнорируем ошибку
                if hasattr(update, 'answer'):
                    await update.answer()
            else:
                raise
    
    # Команды для текстового интерфейса (оставляем для совместимости)
    async def add_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /add_task"""
        self.user_states[update.effective_user.id] = "waiting_for_new_task"
        await update.message.reply_text(
            "📝 Добавление новой задачи:\n\n"
            "Отправьте сообщение в формате:\n"
            "Название задачи | интервал_в_днях\n\n"
            "Пример: Полить цветы | 3",
            reply_markup=get_cancel_keyboard()
        )
    
    async def delete_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /delete_task"""
        try:
            tasks = self.db.get_all_tasks()
            
            if not tasks:
                await update.message.reply_text("📝 Нет задач для удаления.")
                return
            
            keyboard = get_task_selection_keyboard("delete")
            await update.message.reply_text("🗑️ Выберите задачу для удаления:", reply_markup=keyboard)
                
        except Exception as e:
            logger.error(f"Error in /delete_task: {e}")
            await update.message.reply_text("❌ Ошибка при удалении задачи")
    
    async def edit_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /edit_task"""
        try:
            tasks = self.db.get_all_tasks()
            
            if not tasks:
                await update.message.reply_text("📝 Нет задач для редактирования.")
                return
            
            keyboard = get_task_selection_keyboard("edit_interval")
            await update.message.reply_text("📅 Выберите задачу для изменения интервала:", reply_markup=keyboard)
                
        except Exception as e:
            logger.error(f"Error in /edit_task: {e}")
            await update.message.reply_text("❌ Ошибка при редактировании задачи")
    
    async def mark_task_done(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /done"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ Укажите задачу. Например: /done полы\n"
                    "Посмотреть все задачи: /tasks"
                )
                return
            
            task_query = " ".join(context.args)
            task = self.db.find_task_by_name(task_query)
            
            if not task:
                await update.message.reply_text(
                    f"❌ Задача '{task_query}' не найдена.\n"
                    "Посмотреть все задачи: /tasks"
                )
                return
            
            user = update.effective_user
            self.db.mark_task_done(
                task_id=task.id,
                user_chat_id=user.id,
                username=user.username or "нет",
                first_name=user.first_name or "Аноним"
            )
            
            await update.message.reply_text(
                f"✅ Отлично! {user.first_name} выполнил(а) задачу: {task.name}\n"
                f"Следующее выполнение через {task.interval_days} дней."
            )
        
        except Exception as e:
            logger.error(f"Error in /done: {e}")
            await update.message.reply_text("❌ Ошибка при отметке задачи.")
    
    def run(self):
        """Запуск бота"""
        try:
            self.application = Application.builder().token(config.BOT_TOKEN).build()
            
            # Основные команды
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("tasks", self.show_tasks_with_keyboard))
            self.application.add_handler(CommandHandler("done", self.mark_task_done))
            self.application.add_handler(CommandHandler("stats", self.show_stats))
            self.application.add_handler(CommandHandler("next", self.show_next_tasks))
            
            # Команды управления
            self.application.add_handler(CommandHandler("manage", self.manage_tasks))
            self.application.add_handler(CommandHandler("add_task", self.add_task_command))
            self.application.add_handler(CommandHandler("delete_task", self.delete_task_command))
            self.application.add_handler(CommandHandler("edit_task", self.edit_task_command))
            
            # Обработчики кнопок и сообщений
            self.application.add_handler(CallbackQueryHandler(self.button_handler))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
            
            # Запускаем бота
            logger.info("🤖 Бот запускается...")
            self.application.run_polling()
            
        except Exception as e:
            logger.error(f"💥 Критическая ошибка при запуске бота: {e}")

if __name__ == "__main__":
    bot = HouseholdBot()
    bot.run()