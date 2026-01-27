from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

@dataclass
class Task:
    id: int
    name: str
    interval_days: int
    last_done: Optional[datetime] = None
    last_done_by: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def days_since_done(self) -> Optional[int]:
        if not self.last_done:
            return None
        return (datetime.now() - self.last_done).days
    
    def is_overdue(self) -> bool:
        if not self.last_done:
            return True
        return self.days_since_done() >= self.interval_days
    
    def days_until_due(self) -> int:
        if not self.last_done:
            return 0
        days_passed = self.days_since_done() or 0
        return max(0, self.interval_days - days_passed)
    
    def get_status_emoji(self) -> str:
        """Получить смайлик статуса"""
        if self.last_done is None:
            return "🔔"  # Никогда не выполнялось
        elif self.is_overdue():
            return "🔔"  # Просрочено
        else:
            return "⏳"  # Ожидает выполнения
    
    def format_status(self, user_name_func) -> str:
        """Форматировать строку статуса задачи"""
        emoji = self.get_status_emoji()
        
        if self.last_done is None:
            status_text = f"{emoji} {self.name} - никогда не выполнялось"
        elif self.is_overdue():
            overdue_days = (self.days_since_done() or 0) - self.interval_days
            done_by = user_name_func(self.last_done_by) if self.last_done_by else "Неизвестно"
            status_text = f"{emoji} {self.name} - просрочено на {overdue_days} дн. (последний раз: {done_by})"
        else:
            days_ago = self.days_since_done() or 0
            days_left = self.interval_days - days_ago
            done_by = user_name_func(self.last_done_by) if self.last_done_by else "Неизвестно"
            status_text = f"{emoji} {self.name} - {days_ago} дн. назад (осталось {days_left} дн., выполнял: {done_by})"
        
        return status_text

@dataclass
class ShoppingItem:
    """Модель элемента списка покупок"""
    id: int
    item_text: str
    is_checked: bool
    created_at: datetime
    
    def format_for_display(self) -> str:
        """Форматирование для отображения в списке"""
        status = "✅" if self.is_checked else "⬜️"
        text = f"<s>{self.item_text}</s>" if self.is_checked else self.item_text
        return f"{status} {text}"
    
    def toggle_checked(self) -> None:
        """Переключить состояние отметки"""
        self.is_checked = not self.is_checked