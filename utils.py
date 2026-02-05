from database import Database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Utils:
    """Вспомогательные функции"""
    
    @staticmethod
    def format_amount(amount: float, currency: str) -> str:
        """Форматирование суммы"""
        return f"{amount:.2f} {currency}"
    
    @staticmethod
    def get_participant_name(user_id: int, participants: list) -> str:
        """Получить имя участника по ID"""
        for p in participants:
            if p['user_id'] == user_id:
                return p['first_name']
        return "Неизвестный"
    
    @staticmethod
    def format_summary(chat_id: int) -> str:
        """Форматировать сводку долгов"""
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        debts = Database.get_debts(chat_id)
        participants = Database.get_participants(chat_id)
        currency = trip['currency']
        
        if not debts:
            return f"📌 *Сводка долгов ({currency})*\n\n✅ Все расчёты завершены!\n\nОбновлено: {datetime.now().strftime('%H:%M')}"
        
        text = f"📌 *Сводка долгов ({currency})*\n\n"
        
        for debt in debts:
            from_name = Utils.get_participant_name(debt['from_id'], participants)
            to_name = Utils.get_participant_name(debt['to_id'], participants)
            amount = Utils.format_amount(debt['amount'], currency)
            text += f"{from_name} → {to_name}: *{amount}*\n"
        
        text += f"\nОбновлено: {datetime.now().strftime('%H:%M')}"
        return text
    
    @staticmethod
    def format_debts_for_user(chat_id: int, user_id: int, debt_type: str = "i_owe") -> str:
        """Форматировать долги для конкретного пользователя"""
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        debts = Database.get_debts(chat_id)
        participants = Database.get_participants(chat_id)
        currency = trip['currency']
        
        if debt_type == "i_owe":
            # Я должен
            my_debts = [d for d in debts if d['from_id'] == user_id]
            
            if not my_debts:
                return f"✅ Ты никому не должен!"
            
            text = f"💰 *Ты должен ({currency}):*\n\n"
            total = 0
            for debt in my_debts:
                to_name = Utils.get_participant_name(debt['to_id'], participants)
                amount = debt['amount']
                text += f"{to_name}: *{Utils.format_amount(amount, currency)}*\n"
                total += amount
            
            text += f"\n📊 Итого: *{Utils.format_amount(total, currency)}*"
            return text
        
        else:  # owe_me
            # Мне должны
            debts_to_me = [d for d in debts if d['to_id'] == user_id]
            
            if not debts_to_me:
                return f"✅ Тебе никто не должен!"
            
            text = f"💵 *Тебе должны ({currency}):*\n\n"
            total = 0
            for debt in debts_to_me:
                from_name = Utils.get_participant_name(debt['from_id'], participants)
                amount = debt['amount']
                text += f"{from_name}: *{Utils.format_amount(amount, currency)}*\n"
                total += amount
            
            text += f"\n📊 Итого: *{Utils.format_amount(total, currency)}*"
            return text
    
    @staticmethod
    def format_expense_details(expense: dict, participants: list, currency: str) -> str:
        """Форматировать детали расхода"""
        payer_name = Utils.get_participant_name(expense['payer_id'], participants)
        amount = Utils.format_amount(expense['amount'], currency)
        
        beneficiary_names = [
            Utils.get_participant_name(b_id, participants) 
            for b_id in expense['beneficiaries']
        ]
        
        category = expense.get('category', '')
        comment = expense.get('comment', 'Без комментария')
        
        text = f"🧾 *Расход*\n\n"
        text += f"💰 Сумма: *{amount}*\n"
        text += f"👤 Платил: {payer_name}\n"
        text += f"👥 За: {', '.join(beneficiary_names)}\n"
        if category:
            text += f"📁 Категория: {category}\n"
        text += f"📝 Комментарий: {comment}\n"
        text += f"📅 Дата: {expense['created_at'].strftime('%d.%m.%Y %H:%M')}"
        
        return text
    
    @staticmethod
    def format_history(chat_id: int, limit: int = 10) -> str:
        """Форматировать историю расходов"""
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        expenses = Database.get_expenses(chat_id)[:limit]
        participants = Database.get_participants(chat_id)
        currency = trip['currency']
        
        if not expenses:
            return "📝 История расходов пуста"
        
        text = f"🧾 *История расходов*\n\n"
        
        for expense in expenses:
            payer_name = Utils.get_participant_name(expense['payer_id'], participants)
            amount = Utils.format_amount(expense['amount'], currency)
            comment = expense.get('comment', 'Без названия')
            category = expense.get('category', '')
            
            text += f"{category} *{amount}* — {comment}\n"
            text += f"   Платил: {payer_name}\n"
            text += f"   {expense['created_at'].strftime('%d.%m %H:%M')}\n\n"
        
        return text
    
    @staticmethod
    def is_user_in_trip(user_id: int, chat_id: int) -> bool:
        """Проверить, является ли пользователь участником поездки"""
        participants = Database.get_participants(chat_id)
        return any(p['user_id'] == user_id for p in participants)
    
    @staticmethod
    def validate_amount(text: str) -> tuple:
        """Валидация суммы"""
        try:
            # Заменяем запятую на точку
            text = text.replace(',', '.')
            amount = float(text)
            
            if amount <= 0:
                return False, "Сумма должна быть больше нуля"
            
            if amount > 1000000:
                return False, "Сумма слишком большая"
            
            return True, amount
        except ValueError:
            return False, "Введите корректную сумму (например: 1250 или 1250.50)"
