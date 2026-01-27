import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from models import Task, ShoppingItem

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="household_dev.db"):
        self.db_path = db_path
        self.init_db()
        self.create_shopping_table()
    
    def init_db(self):
        """Инициализация таблиц"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица задач
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                interval_days INTEGER NOT NULL,
                last_done TIMESTAMP,
                last_done_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (last_done_by) REFERENCES users (chat_id)
            )
        ''')
        
        # Таблица для хранения истории выполнений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                done_by INTEGER,
                done_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (done_by) REFERENCES users (chat_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Добавляем стандартные задачи при первом запуске
        self.add_default_tasks()
    
    def create_shopping_table(self):
        """Создание таблицы для списка покупок"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shopping_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_text TEXT NOT NULL,
                is_checked BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_default_tasks(self):
        """Добавление стандартных задач при первом запуске"""
        default_tasks = [
            ("Помыть полы", 7),
            ("Пропылесосить", 7),
            ("Помыть ванну", 21),
            ("Приготовить еду", 3),
            ("Поменять постельное", 7)
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]
        
        if count == 0:
            for task_name, interval in default_tasks:
                cursor.execute(
                    "INSERT INTO tasks (name, interval_days) VALUES (?, ?)",
                    (task_name, interval)
                )
        
        conn.commit()
        conn.close()
    
    def get_all_tasks(self) -> List[Task]:
        """Получить все задачи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, interval_days, last_done, last_done_by, created_at 
            FROM tasks 
            ORDER BY name
        ''')
        
        tasks = []
        for row in cursor.fetchall():
            task = Task(
                id=row[0],
                name=row[1],
                interval_days=row[2],
                last_done=datetime.fromisoformat(row[3]) if row[3] else None,
                last_done_by=row[4],
                created_at=datetime.fromisoformat(row[5]) if row[5] else None
            )
            tasks.append(task)
        
        conn.close()
        return tasks
    
    # ================== МЕТОДЫ ДЛЯ СПИСКА ПОКУПОК ==================
    
    def add_shopping_item(self, item_text: str) -> bool:
        """Добавить пункт в список покупок"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, нет ли уже такого пункта (неотмеченного)
            cursor.execute('''
                SELECT id FROM shopping_items 
                WHERE LOWER(item_text) = LOWER(?) AND is_checked = 0
            ''', (item_text,))
            
            existing_item = cursor.fetchone()
            if existing_item:
                conn.close()
                return False
            
            # Добавляем новый пункт
            cursor.execute('''
                INSERT INTO shopping_items (item_text, is_checked) 
                VALUES (?, 0)
            ''', (item_text,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error adding shopping item: {e}")
            return False
    
    def get_shopping_items(self, show_checked: bool = True) -> List[ShoppingItem]:
        """Получить все пункты списка покупок"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, item_text, is_checked, created_at 
                FROM shopping_items 
                ORDER BY is_checked, created_at DESC
            '''
            
            if not show_checked:
                query = '''
                    SELECT id, item_text, is_checked, created_at 
                    FROM shopping_items 
                    WHERE is_checked = 0
                    ORDER BY created_at DESC
                '''
            
            cursor.execute(query)
            
            items = []
            for row in cursor.fetchall():
                item = ShoppingItem(
                    id=row[0],
                    item_text=row[1],
                    is_checked=bool(row[2]),
                    created_at=datetime.fromisoformat(row[3]) if row[3] else datetime.now()
                )
                items.append(item)
            
            conn.close()
            return items
            
        except Exception as e:
            logger.error(f"Error getting shopping items: {e}")
            return []
    
    def toggle_shopping_item(self, item_id: int) -> Optional[ShoppingItem]:
        """Переключить статус отметки пункта"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Получаем текущее состояние
            cursor.execute('''
                SELECT id, item_text, is_checked, created_at 
                FROM shopping_items 
                WHERE id = ?
            ''', (item_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            
            # Переключаем статус
            current_status = bool(row[2])
            new_status = 0 if current_status else 1
            
            cursor.execute('''
                UPDATE shopping_items 
                SET is_checked = ? 
                WHERE id = ?
            ''', (new_status, item_id))
            
            conn.commit()
            conn.close()
            
            # Возвращаем обновленный объект
            return ShoppingItem(
                id=row[0],
                item_text=row[1],
                is_checked=new_status,
                created_at=datetime.fromisoformat(row[3]) if row[3] else datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error toggling shopping item: {e}")
            return None
    
    def delete_checked_items(self) -> int:
        """Удалить все отмеченные пункты"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Считаем сколько удаляем
            cursor.execute('SELECT COUNT(*) FROM shopping_items WHERE is_checked = 1')
            count = cursor.fetchone()[0]
            
            # Удаляем
            cursor.execute('DELETE FROM shopping_items WHERE is_checked = 1')
            
            conn.commit()
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"Error deleting checked items: {e}")
            return 0
    
    def delete_all_shopping_items(self) -> int:
        """Удалить все пункты списка покупок"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Считаем сколько удаляем
            cursor.execute('SELECT COUNT(*) FROM shopping_items')
            count = cursor.fetchone()[0]
            
            # Удаляем
            cursor.execute('DELETE FROM shopping_items')
            
            conn.commit()
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"Error deleting all shopping items: {e}")
            return 0
    
    def get_shopping_item_count(self) -> Dict[str, int]:
        """Получить статистику по списку покупок"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM shopping_items WHERE is_checked = 0')
            unchecked = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM shopping_items WHERE is_checked = 1')
            checked = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total': unchecked + checked,
                'unchecked': unchecked,
                'checked': checked
            }
            
        except Exception as e:
            logger.error(f"Error getting shopping item count: {e}")
            return {'total': 0, 'unchecked': 0, 'checked': 0}
    # ================== КОНЕЦ МЕТОДОВ ДЛЯ СПИСКА ПОКУПОК ==================
    
    def mark_task_done(self, task_id: int, user_chat_id: int, username: str, first_name: str):
        """Отметить задачу выполненной"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Добавляем/обновляем пользователя
        cursor.execute('''
            INSERT OR REPLACE INTO users (chat_id, username, first_name) 
            VALUES (?, ?, ?)
        ''', (user_chat_id, username, first_name))
        
        # Обновляем задачу
        current_time = datetime.now().isoformat()
        cursor.execute('''
            UPDATE tasks 
            SET last_done = ?, last_done_by = ? 
            WHERE id = ?
        ''', (current_time, user_chat_id, task_id))
        
        # Добавляем запись в историю
        cursor.execute('''
            INSERT INTO task_history (task_id, done_by, done_at) 
            VALUES (?, ?, ?)
        ''', (task_id, user_chat_id, current_time))
        
        conn.commit()
        conn.close()
    
    def find_task_by_name(self, task_name: str) -> Optional[Task]:
        """Найти задачу по названию (регистронезависимо)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, interval_days, last_done, last_done_by, created_at 
            FROM tasks 
            WHERE LOWER(name) LIKE LOWER(?)
        ''', (f'%{task_name}%',))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Task(
                id=row[0],
                name=row[1],
                interval_days=row[2],
                last_done=datetime.fromisoformat(row[3]) if row[3] else None,
                last_done_by=row[4],
                created_at=datetime.fromisoformat(row[5]) if row[5] else None
            )
        return None
    
    def get_user_name(self, chat_id: int) -> str:
        """Получить имя пользователя по chat_id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT first_name FROM users WHERE chat_id = ?', (chat_id,))
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else "Неизвестный пользователь"
    
    def get_overdue_tasks(self) -> List[Task]:
        """Получить список просроченных задач"""
        tasks = self.get_all_tasks()
        return [task for task in tasks if task.is_overdue()]
    
    def get_tasks_due_soon(self, days_threshold: int = 2) -> List[Task]:
        """Получить задачи, которые скоро должны быть выполнены"""
        tasks = self.get_all_tasks()
        due_soon = []
        
        for task in tasks:
            if task.last_done and not task.is_overdue():
                days_until_due = task.days_until_due()
                if 0 < days_until_due <= days_threshold:
                    due_soon.append(task)
        
        return due_soon
    
    def get_user_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Получить расширенную статистику по пользователям"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Статистика выполненных задач по пользователям
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT 
                u.first_name,
                COUNT(th.id) as task_count,
                GROUP_CONCAT(DISTINCT t.name) as task_names
            FROM task_history th
            JOIN users u ON th.done_by = u.chat_id
            JOIN tasks t ON th.task_id = t.id
            WHERE th.done_at >= ?
            GROUP BY u.first_name
            ORDER BY task_count DESC
        ''', (since_date,))
        
        user_stats = {}
        total_tasks = 0
        
        for row in cursor.fetchall():
            user_name, count, task_names = row
            user_stats[user_name] = {
                'task_count': count,
                'tasks': task_names.split(',') if task_names else []
            }
            total_tasks += count
        
        # Самые частые задачи
        cursor.execute('''
            SELECT 
                t.name,
                COUNT(th.id) as completion_count
            FROM task_history th
            JOIN tasks t ON th.task_id = t.id
            WHERE th.done_at >= ?
            GROUP BY t.name
            ORDER BY completion_count DESC
            LIMIT 5
        ''', (since_date,))
        
        popular_tasks = cursor.fetchall()
        
        # Статистика по дням недели
        cursor.execute('''
            SELECT 
                strftime('%w', th.done_at) as weekday,
                COUNT(th.id) as task_count
            FROM task_history th
            WHERE th.done_at >= ?
            GROUP BY weekday
            ORDER BY weekday
        ''', (since_date,))
        
        weekday_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'user_stats': user_stats,
            'total_tasks': total_tasks,
            'popular_tasks': popular_tasks,
            'weekday_stats': weekday_stats,
            'period_days': days
        }
    
    def get_completion_rate(self, task_id: int, days: int = 30) -> float:
        """Получить процент своевременного выполнения задачи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Получаем интервал задачи
        cursor.execute('SELECT interval_days FROM tasks WHERE id = ?', (task_id,))
        interval = cursor.fetchone()[0]
        
        # Считаем выполненные вовремя (в пределах интервала + 1 день grace period)
        cursor.execute('''
            SELECT COUNT(*) 
            FROM task_history th1
            WHERE th1.task_id = ? 
            AND th1.done_at >= ?
            AND NOT EXISTS (
                SELECT 1 
                FROM task_history th2 
                WHERE th2.task_id = th1.task_id 
                AND th2.done_at < th1.done_at 
                AND th2.done_at > datetime(th1.done_at, ?)
            )
        ''', (task_id, since_date, f'-{interval + 1} days'))
        
        on_time = cursor.fetchone()[0]
        
        # Общее количество выполнений
        cursor.execute('''
            SELECT COUNT(*) 
            FROM task_history 
            WHERE task_id = ? AND done_at >= ?
        ''', (task_id, since_date))
        
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return (on_time / total * 100) if total > 0 else 0

    # ДОБАВЛЯЕМ НОВЫЕ МЕТОДЫ ДЛЯ УПРАВЛЕНИЯ ЗАДАЧАМИ

    def add_new_task(self, name: str, interval_days: int) -> bool:
        """Добавить новую задачу"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, нет ли уже задачи с таким названием
            cursor.execute("SELECT id FROM tasks WHERE LOWER(name) = LOWER(?)", (name,))
            existing_task = cursor.fetchone()
            
            if existing_task:
                conn.close()
                return False
            
            # Добавляем новую задачу
            cursor.execute(
                "INSERT INTO tasks (name, interval_days) VALUES (?, ?)",
                (name, interval_days)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error adding new task: {e}")
            return False

    def update_task_interval(self, task_id: int, new_interval: int) -> bool:
        """Обновить интервал выполнения задачи"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE tasks SET interval_days = ? WHERE id = ?",
                (new_interval, task_id)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating task interval: {e}")
            return False

    def delete_task(self, task_id: int) -> bool:
        """Удалить задачу и связанную историю"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Удаляем историю выполнений задачи
            cursor.execute("DELETE FROM task_history WHERE task_id = ?", (task_id,))
            
            # Удаляем саму задачу
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False
    def rename_task(self, task_id: int, new_name: str) -> bool:
        """Переименовать задачу"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, нет ли уже задачи с таким названием
            cursor.execute("SELECT id FROM tasks WHERE LOWER(name) = LOWER(?) AND id != ?", (new_name, task_id))
            existing_task = cursor.fetchone()
            
            if existing_task:
                conn.close()
                return False
            
            # Переименовываем задачу
            cursor.execute("UPDATE tasks SET name = ? WHERE id = ?", (new_name, task_id))
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error renaming task: {e}")
            return False
    
    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Получить задачу по ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, interval_days, last_done, last_done_by, created_at 
                FROM tasks WHERE id = ?
            ''', (task_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return Task(
                    id=row[0],
                    name=row[1],
                    interval_days=row[2],
                    last_done=datetime.fromisoformat(row[3]) if row[3] else None,
                    last_done_by=row[4],
                    created_at=datetime.fromisoformat(row[5]) if row[5] else None
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting task by ID: {e}")
            return None