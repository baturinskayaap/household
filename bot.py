import logging
from telegram.error import BadRequest
from telegram import Update, ReplyKeyboardRemove, CallbackQuery
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from datetime import time
import config
# try:
#     import config_dev as config
# except ImportError:
#     import config
from database import Database
from reminder_system import ReminderSystem
from utils import format_reminder_message
from keyboards import (
    # Новые клавиатуры
    get_main_keyboard,
    get_tasks_menu_keyboard,
    # Существующие клавиатуры
    get_tasks_keyboard, get_management_keyboard, get_task_selection_keyboard,
    get_confirmation_keyboard, get_cancel_keyboard, get_back_keyboard,
    # Клавиатуры для списка покупок
    get_shopping_keyboard, get_shopping_items_keyboard,
    get_shopping_clear_confirmation,
    get_shopping_back_keyboard, get_shopping_back_to_stream_keyboard,
    get_shopping_add_stream_keyboard,
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
        """Обработчик команды /start с новой основной клавиатурой"""
        try:
            welcome_text = """
Привет!

Используй кнопки ниже для быстрого доступа
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
            
            if text == "📋 Задачи":
                await self.show_tasks_menu(update, context)
            elif text == "🛒 Покупки":
                await self.show_shopping_menu(update, context)
            else:
                await self.handle_user_state(update, context)
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await update.message.reply_text("❌ Ошибка при обработке сообщения")
    
    # ================== НОВЫЕ МЕТОДЫ ДЛЯ НОВОЙ СТРУКТУРЫ ==================
    
    async def show_tasks_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню задач"""
        try:
            message = "📋 Управление задачами"
            keyboard = get_tasks_menu_keyboard()
            
            # Простая и понятная логика
            if isinstance(update, CallbackQuery):
                # Это callback query напрямую
                await update.edit_message_text(message, reply_markup=keyboard)
            elif hasattr(update, 'callback_query') and update.callback_query:
                # Это update с callback_query
                await update.callback_query.edit_message_text(message, reply_markup=keyboard)
            elif hasattr(update, 'message') and update.message:
                # Это update с message
                await update.message.reply_text(message, reply_markup=keyboard)
            else:
                # Последний вариант
                await self.send_message(update, message, keyboard)
                    
        except Exception as e:
            logger.error(f"Error in show_tasks_menu: {e}")
            # Простое сообщение об ошибке
            try:
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text("❌ Ошибка при открытии меню задач")
            except:
                pass
    
    async def show_shopping_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню списка покупок для текстовых сообщений"""
        try:
            message = """
🛒 Список покупок
            """
            keyboard = get_shopping_keyboard()
            await update.message.reply_text(message, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error in show_shopping_menu: {e}")
            await update.message.reply_text("❌ Ошибка при открытии списка покупок")
    
    # ================== МЕТОДЫ ДЛЯ СПИСКА ПОКУПОК (обновлены) ==================
    
    async def show_shopping_list(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню списка покупок (для inline-кнопок)"""
        try:
            keyboard = get_shopping_keyboard()
            message = """
🛒 Список покупок
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
            
            # Получаем статистику для передачи в клавиатуру
            stats = self.db.get_shopping_item_count()
            
            # Формируем сообщение
            message_lines = ["🛒 Список покупок:\n"]
            
            # Добавляем статистику в заголовок
            if stats['total'] > 0:
                message_lines.append(f"📊 Всего: {stats['total']} | ✅ Отмечено: {stats['checked']} | ⬜️ Неотмечено: {stats['unchecked']}\n")
            
            # Добавляем пункты
            for item in items:
                message_lines.append(f"{item.format_for_display()}")
            
            # Создаем клавиатуру с передачей статистики
            keyboard = get_shopping_items_keyboard(items, stats, show_checked)
            
            try:
                await query.edit_message_text(
                    "\n".join(message_lines), 
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    await query.answer()
                else:
                    raise
            
        except Exception as e:
            logger.error(f"Error in show_shopping_items: {e}")
            await query.edit_message_text("❌ Ошибка при получении списка покупок")
    
    async def quick_clear_all_shopping_items(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Быстрая очистка всего списка покупок из главного меню"""
        try:
            stats = self.db.get_shopping_item_count()
            
            if stats['total'] == 0:
                await query.edit_message_text(
                    "📝 Список покупок и так пуст.",
                    reply_markup=get_shopping_keyboard()
                )
                return
            
            # Используем существующее подтверждение
            keyboard = get_shopping_clear_confirmation("all")
            await query.edit_message_text(
                f"🗑️ Вы уверены, что хотите удалить весь список ({stats['total']} пунктов)?",
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in quick_clear_all_shopping_items: {e}")
            await query.edit_message_text("❌ Ошибка при очистке списка")
    
    async def add_shopping_item(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Начать потоковое добавление новых пунктов в список покупок"""
        try:
            user_id = query.from_user.id
            # Новое состояние для потокового добавления
            self.user_states[user_id] = "adding_shopping_stream"
            
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
            
        except Exception as e:
            logger.error(f"Error in add_shopping_item: {e}")
            await query.edit_message_text("❌ Ошибка при начале добавления пунктов")
    
    async def process_shopping_stream_item(self, update, user_message):
        """Обработка добавления пункта в потоковом режиме"""
        user_id = update.effective_user.id
        item_text = user_message.strip()
        
        if not item_text:
            await update.message.reply_text(
                "❌ Название пункта не может быть пустым.",
                reply_markup=get_shopping_back_to_stream_keyboard()
            )
            return
        
        try:
            success = self.db.add_shopping_item(item_text)
        except Exception as e:
            logger.error(f"Ошибка при добавлении в БД: {e}")
            success = False
        
        if success:
            # Краткое подтверждение
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
        
        # Состояние НЕ удаляем - остаемся в режиме потока
        # Пользователь может продолжать добавлять пункты
    
    async def exit_shopping_stream(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Выход из режима потокового добавления"""
        try:
            user_id = query.from_user.id
            # Очищаем состояние
            if user_id in self.user_states:
                del self.user_states[user_id]
            
            # Показываем статистику добавленных пунктов
            stats = self.db.get_shopping_item_count()
            
            await query.edit_message_text(
                f"🔚 **Режим добавления завершен**\n\n"
                f"📊 Статистика списка покупок:\n"
                f"• Всего пунктов: {stats['total']}\n"
                f"• Отмечено: {stats['checked']}\n"
                f"• Не отмечено: {stats['unchecked']}\n\n"
                f"Можете продолжить управление списком:",
                reply_markup=get_shopping_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error exiting shopping stream: {e}")
            await query.edit_message_text("❌ Ошибка при завершении добавления")
    
    async def handle_user_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка состояний пользователя"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_states:
            return
        
        state = self.user_states[user_id]
        
        # Проверяем, что есть текст сообщения
        if not update.message or not update.message.text:
            return
        
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
            elif state == "adding_shopping_stream":
                # Новый потоковый режим
                await self.process_shopping_stream_item(update, user_message)
                    
        except Exception as e:
            logger.error(f"Error handling user state {state}: {e}")
            
            # Отправляем сообщение об ошибке только если есть message
            if update.message:
                await update.message.reply_text("❌ Ошибка при обработке запроса")
            
            # Удаляем состояние только для НЕ потоковых режимов
            if state != "adding_shopping_stream":
                if user_id in self.user_states:
                    del self.user_states[user_id]
            else:
                logger.info(f"Ошибка в потоковом режиме, но состояние сохраняется")
    
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
                
                # Получаем статистику для клавиатуры
                stats = self.db.get_shopping_item_count()
                
                # Формируем сообщение
                message_lines = ["🛒 Список покупок:\n"]
                
                # Добавляем статистику
                if stats['total'] > 0:
                    message_lines.append(f"📊 Всего: {stats['total']} | ✅ Отмечено: {stats['checked']} | ⬜️ Неотмечено: {stats['unchecked']}\n")
                
                # Добавляем пункты
                for item in items:
                    message_lines.append(f"{item.format_for_display()}")
                
                # Создаем клавиатуру с передачей статистики
                keyboard = get_shopping_items_keyboard(items, stats, show_checked)
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
    
    async def process_shopping_item(self, update, user_message):
        """Обработка добавления нового пункта в список покупок (старый режим - один пункт)"""
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
        
        # Удаляем состояние (старый режим - одноразовый)
        user_id = update.effective_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    # ================== СУЩЕСТВУЮЩИЕ МЕТОДЫ (с минимальными изменениями) ==================
    
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
    
    async def quick_done_with_inline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрая отметка выполнения через inline-кнопки"""
        try:
            tasks = self.db.get_all_tasks()
            urgent_tasks = []
            
            for task in tasks:
                try:
                    # Безопасная проверка
                    if task.last_done is None:
                        # Задача никогда не выполнялась
                        urgent_tasks.append(task)
                    elif task.is_overdue():
                        urgent_tasks.append(task)
                    else:
                        days_left = task.days_until_due()
                        if days_left <= 2:
                            urgent_tasks.append(task)
                except Exception as e:
                    logger.error(f"Error checking task {task.name}: {e}")
                    # В случае ошибки добавляем задачу в срочные
                    urgent_tasks.append(task)
            
            if not urgent_tasks:
                await self.send_message(update, "🎉 Нет срочных задач для выполнения!")
                return
            
            keyboard = get_tasks_keyboard(show_all=False)
            await self.send_message(update, "✅ Выберите задачу для отметки выполнения:", keyboard)
            
        except Exception as e:
            logger.error(f"Error in quick_done_with_inline: {e}")
            await self.send_message(update, "❌ Ошибка при получении списка задач")

    async def manage_tasks(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Управление задачами"""
        try:
            keyboard = get_management_keyboard()
            message = "🛠️ Управление задачами"
            await query.edit_message_text(message, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error in manage_tasks: {e}")
            await query.edit_message_text("❌ Ошибка при открытии управления задачами")
    
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
            # ================== НОВЫЕ ОБРАБОТЧИКИ ДЛЯ НОВОЙ СТРУКТУРЫ ==================
            if data == "tasks_main":
                await self.show_tasks_menu(query, context)
            
            elif data == "back_to_main":
                await self.show_main_menu(query)
            elif data == "back_to_tasks_menu":
                await self.show_tasks_menu(query, context)    
            
            # ================== ОБРАБОТКА СПИСКА ПОКУПОК ==================
            elif data == "shopping_list":
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
            
            elif data == "shopping_exit_stream":
                await self.exit_shopping_stream(query, context)
            
            elif data == "shopping_quick_clear":
                await self.quick_clear_all_shopping_items(query, context)
            
            # ================== ОБРАБОТКА ЗАДАЧ ==================
            elif data.startswith("done_"):
                task_id = int(data.split("_")[1])
                await self.mark_task_done_from_button(query, task_id)
            
            elif data == "refresh_tasks":
                await self.show_tasks_with_keyboard(query, context, show_all=True)
            elif data == "show_all_tasks":
                await self.show_tasks_with_keyboard(query, context, show_all=True)
            
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
            elif data == "manage_tasks":
                await self.manage_tasks(query, context)
            
            elif data == "show_urgent_tasks":
                await self.show_tasks_with_keyboard(update, context, show_all=False)
            elif data == "no_action":
                await query.answer()  # Просто отвечаем без действий
                
            elif data == "back_to_manage":
                keyboard = get_management_keyboard()
                await query.edit_message_text("🛠️ Управление задачами", reply_markup=keyboard)

            
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
        """Показать главное меню (универсальный возврат)"""
        keyboard = get_main_keyboard()
        await query.edit_message_text(
            "👋 Главное меню\n\nВыберите раздел:",
            reply_markup=keyboard
        )
    
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
            # Простая логика определения типа
            if isinstance(update, CallbackQuery):
                # Это CallbackQuery
                await update.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            elif hasattr(update, 'edit_message_text'):
                # Это что-то с методом edit_message_text
                await update.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            elif hasattr(update, 'callback_query') and update.callback_query:
                # Это Update с callback_query
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            elif hasattr(update, 'message') and update.message:
                # Это Update с message
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                logger.error(f"Unknown update type in send_message: {type(update)}")
                # Если ничего не помогло, попробуем ответить в чат через message
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
                elif hasattr(update, 'effective_chat'):
                    # Прямой вызов через бота, если есть application
                    if self.application and self.application.bot:
                        await self.application.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
            
        except BadRequest as e:
            if "Message is not modified" in str(e):
                # Игнорируем ошибку
                if hasattr(update, 'answer'):
                    await update.answer()
            else:
                logger.error(f"BadRequest in send_message: {e}")
        except Exception as e:
            logger.error(f"Error in send_message: {e}")
        
    def run(self):
        """Запуск бота"""
        try:
            self.application = Application.builder().token(config.BOT_TOKEN).build()
            # Основные команды
            self.application.add_handler(CommandHandler("start", self.start))
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