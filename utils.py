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
        """Форматировать сводку долгов (новая логика)"""
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        summary = Database.get_debts_summary(chat_id)
        participants = Database.get_participants(chat_id)
        currency = trip['currency']
        
        if not summary:
            return f"📌 *Сводка долгов ({currency})*\n\n✅ Все долги погашены!\n\nОбновлено: {datetime.now().strftime('%H:%M')}"
        
        text = f"📌 *Сводка долгов ({currency})*\n\n"
        
        for debt_summary in summary:
            debtor_name = Utils.get_participant_name(debt_summary['debtor_id'], participants)
            creditor_name = Utils.get_participant_name(debt_summary['creditor_id'], participants)
            amount = Utils.format_amount(debt_summary['total_amount'], currency)
            text += f"{debtor_name} → {creditor_name}: *{amount}*\n"
        
        text += f"\nОбновлено: {datetime.now().strftime('%H:%M')}"
        return text
    
    @staticmethod
    def format_my_debts(chat_id: int, user_id: int) -> str:
        """Форматировать мои долги (с кнопками возврата)"""
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        my_debts = Database.get_my_debts(chat_id, user_id)
        participants = Database.get_participants(chat_id)
        currency = trip['currency']
        
        if not my_debts:
            return f"✅ У вас нет долгов!"
        
        text = f"💰 *Мои долги ({currency}):*\n\n"
        
        for debt in my_debts:
            creditor_name = Utils.get_participant_name(debt['creditor_id'], participants)
            amount = Utils.format_amount(debt['amount'], currency)
            
            # Информация о группе долга
            group_info = debt.get('group_info', {})
            description = group_info.get('description', 'Без описания')
            category = group_info.get('category', '')
            
            text += f"{category} *{description}*\n"
            text += f"Должен {creditor_name}: *{amount}*\n"
            text += f"ID: `{debt['id']}`\n\n"
        
        total = sum(d['amount'] for d in my_debts)
        text += f"📊 Итого долгов: *{Utils.format_amount(total, currency)}*"
        
        return text
    
    @staticmethod
    def format_debts_to_me(chat_id: int, user_id: int) -> str:
        """Форматировать долги мне (кто мне должен)"""
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        debts_to_me = Database.get_debts_to_user(chat_id, user_id)
        participants = Database.get_participants(chat_id)
        currency = trip['currency']
        
        if not debts_to_me:
            return f"✅ Вам никто не должен!"
        
        text = f"💵 *Мне должны ({currency}):*\n\n"
        
        # Группируем по должникам
        debts_by_debtor = {}
        for debt in debts_to_me:
            debtor_id = debt['debtor_id']
            if debtor_id not in debts_by_debtor:
                debts_by_debtor[debtor_id] = []
            debts_by_debtor[debtor_id].append(debt)
        
        for debtor_id, debts in debts_by_debtor.items():
            debtor_name = Utils.get_participant_name(debtor_id, participants)
            total_from_debtor = sum(d['amount'] for d in debts)
            
            text += f"*{debtor_name}:* {Utils.format_amount(total_from_debtor, currency)}\n"
            
            for debt in debts:
                # Получаем инфо о долге
                debt_group = Database.get_trip(chat_id)  # Заглушка, нужно получить debt_group
                text += f"  • {debt.get('description', 'долг')}\n"
            
            text += "\n"
        
        total = sum(d['amount'] for d in debts_to_me)
        text += f"📊 Итого должны: *{Utils.format_amount(total, currency)}*"
        
        return text
    
    @staticmethod
    def format_history(chat_id: int, limit: int = 10) -> str:
        """Форматировать историю долгов"""
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        debt_groups = Database.get_debt_groups(chat_id)[:limit]
        participants = Database.get_participants(chat_id)
        currency = trip['currency']
        
        if not debt_groups:
            return "📝 История долгов пуста"
        
        text = f"🧾 *История долгов*\n\n"
        
        for dg in debt_groups:
            payer_name = Utils.get_participant_name(dg['payer_id'], participants)
            amount = Utils.format_amount(dg['total_amount'], currency)
            description = dg.get('description', 'Без описания')
            category = dg.get('category', '')
            
            text += f"{category} *{amount}* — {description}\n"
            text += f"   Заплатил: {payer_name}\n"
            text += f"   {dg['created_at'].strftime('%d.%m %H:%M')}\n\n"
        
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
            text = text.replace(',', '.')
            amount = float(text)
            
            if amount <= 0:
                return False, "Сумма должна быть больше нуля"
            
            if amount > 10000000:
                return False, "Сумма слишком большая"
            
            return True, amount
        except ValueError:
            return False, "Введите корректную сумму (например: 1250 или 1250.50)"
    
    @staticmethod
    def parse_participants_from_text(text: str, all_participants: list) -> list:
        """
        Извлечь участников из текста по @username или имени
        Возвращает список user_id
        """
        mentioned_ids = []
        
        # Ищем @username
        words = text.split()
        for word in words:
            if word.startswith('@'):
                username = word[1:].lower()
                for p in all_participants:
                    if p.get('username', '').lower() == username:
                        mentioned_ids.append(p['user_id'])
                        break
            else:
                # Ищем по имени
                for p in all_participants:
                    if p['first_name'].lower() in word.lower():
                        if p['user_id'] not in mentioned_ids:
                            mentioned_ids.append(p['user_id'])
                        break
        
        return mentioned_ids
