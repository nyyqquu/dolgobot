from database import Database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Utils:
    """Вспомогательные функции"""
    
    @staticmethod
    def format_amount(amount: float, currency: str) -> str:
        """Форматирование суммы с двумя знаками после запятой"""
        return f"{amount:.2f} {currency}"
    
    @staticmethod
    def get_participant_name(user_id: int, participants: list, use_tag: bool = True) -> str:
        """
        Получить имя участника по ID
        
        use_tag=True:  @username (для ЛС, кнопок, прямого взаимодействия)
        use_tag=False: username без @ (для сводок, чтобы не спамить)
        """
        for p in participants:
            if p['user_id'] == user_id:
                if p.get('username'):
                    if use_tag:
                        return f"@{p['username']}"
                    else:
                        return p['username']
                return p['first_name']
        return "Неизвестный"
    
    @staticmethod
    def get_debt_group_info(debt_group_id: str) -> dict:
        """
        Получить информацию о группе долгов
        Возвращает dict с description и category
        """
        try:
            from firebase_admin import firestore
            db = firestore.client()
            
            debt_group = db.collection('debt_groups').document(debt_group_id).get()
            if debt_group.exists:
                data = debt_group.to_dict()
                return {
                    'description': data.get('description', 'Без описания'),
                    'category': data.get('category', '💸'),
                    'currency': data.get('currency', 'EUR')
                }
        except Exception as e:
            logger.error(f"Error getting debt group info: {e}")
        
        return {'description': 'Без описания', 'category': '💸', 'currency': 'EUR'}
    
    @staticmethod
    def format_summary(chat_id: int) -> str:
        """
        Форматировать сводку долгов для группы (с валютами)
        БЕЗ @ чтобы не спамить уведомлениями
        """
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        summary = Database.get_debts_summary(chat_id)
        participants = Database.get_participants(chat_id)
        
        if not summary:
            return f"📌 *Сводка долгов*\n\n✅ Все долги погашены!\n\nОбновлено: {datetime.now().strftime('%H:%M')}"
        
        # Группируем по валютам
        by_currency = {}
        for debt_summary in summary:
            currency = debt_summary.get('currency', trip['currency'])
            if currency not in by_currency:
                by_currency[currency] = []
            by_currency[currency].append(debt_summary)
        
        text = f"📌 *Сводка долгов*\n\n"
        
        # Выводим по каждой валюте
        for currency, debts in by_currency.items():
            text += f"💱 *{currency}:*\n"
            for debt_summary in debts:
                debtor_name = Utils.get_participant_name(debt_summary['debtor_id'], participants, use_tag=False)
                creditor_name = Utils.get_participant_name(debt_summary['creditor_id'], participants, use_tag=False)
                amount = Utils.format_amount(debt_summary['total_amount'], currency)
                text += f"{debtor_name} → {creditor_name}: *{amount}*\n"
            text += "\n"
        
        text += f"Обновлено: {datetime.now().strftime('%H:%M')}"
        return text
    
    @staticmethod
    def format_my_debts(chat_id: int, user_id: int) -> str:
        """
        Форматировать мои долги (что я должен)
        С @ потому что это ЛС — можно кликнуть и написать
        """
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        my_debts = Database.get_my_debts(chat_id, user_id)
        participants = Database.get_participants(chat_id)
        
        if not my_debts:
            return "✅ У вас нет долгов!"
        
        text = f"💰 *Мои долги:*\n\n"
        
        for debt in my_debts:
            creditor_name = Utils.get_participant_name(debt['creditor_id'], participants, use_tag=True)
            currency = debt.get('currency', trip['currency'])
            amount = Utils.format_amount(debt['amount'], currency)
            
            group_info = debt.get('group_info', {})
            description = group_info.get('description', 'Без описания')
            category = group_info.get('category', '💸')
            
            text += f"{category} *{description}*\n"
            text += f"Должен {creditor_name}: *{amount}*\n\n"
        
        # Группируем итог по валютам
        totals = {}
        for d in my_debts:
            currency = d.get('currency', trip['currency'])
            if currency not in totals:
                totals[currency] = 0
            totals[currency] += d['amount']
        
        text += "📊 *Итого долгов:*\n"
        for currency, total in totals.items():
            text += f"• {Utils.format_amount(total, currency)}\n"
        
        return text
    
    @staticmethod
    def format_debts_to_me(chat_id: int, user_id: int) -> str:
        """
        Форматировать долги мне (кто мне должен)
        С @ потому что это ЛС
        """
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        debts_to_me = Database.get_debts_to_user(chat_id, user_id)
        participants = Database.get_participants(chat_id)
        
        if not debts_to_me:
            return "✅ Вам никто не должен!"
        
        text = f"💵 *Мне должны:*\n\n"
        
        debts_by_debtor = {}
        for debt in debts_to_me:
            debtor_id = debt['debtor_id']
            if debtor_id not in debts_by_debtor:
                debts_by_debtor[debtor_id] = []
            debts_by_debtor[debtor_id].append(debt)
        
        for debtor_id, debts in debts_by_debtor.items():
            debtor_name = Utils.get_participant_name(debtor_id, participants, use_tag=True)
            
            # Группируем по валютам для каждого должника
            totals = {}
            for d in debts:
                currency = d.get('currency', trip['currency'])
                if currency not in totals:
                    totals[currency] = 0
                totals[currency] += d['amount']
            
            text += f"*{debtor_name}:*\n"
            for currency, total in totals.items():
                text += f"• {Utils.format_amount(total, currency)}\n"
            
            for debt in debts:
                debt_info = Utils.get_debt_group_info(debt['debt_group_id'])
                text += f"  {debt_info['category']} {debt_info['description']}\n"
            
            text += "\n"
        
        # Общий итог по валютам
        all_totals = {}
        for d in debts_to_me:
            currency = d.get('currency', trip['currency'])
            if currency not in all_totals:
                all_totals[currency] = 0
            all_totals[currency] += d['amount']
        
        text += "📊 *Итого должны:*\n"
        for currency, total in all_totals.items():
            text += f"• {Utils.format_amount(total, currency)}\n"
        
        return text
    
    @staticmethod
    def format_history(chat_id: int) -> str:
        """
        Форматировать историю КАК В БАНКЕ
        Все события: создание долгов + погашение долгов
        БЕЗ @ чтобы не спамить
        """
        trip = Database.get_trip(chat_id)
        if not trip:
            return "❌ Поездка не найдена"
        
        events = Database.get_history_events(chat_id)
        participants = Database.get_participants(chat_id)
        
        if not events:
            return "📝 *История операций*\n\nИстория пуста."
        
        text = f"🧾 *История операций*\n\n"
        
        for event in events:
            timestamp = event['timestamp'].strftime('%d.%m.%Y %H:%M')
            currency = event.get('currency', trip['currency'])
            
            if event['type'] == 'debt_created':
                payer_name = Utils.get_participant_name(event['payer_id'], participants, use_tag=False)
                amount = Utils.format_amount(event['total_amount'], currency)
                category = event.get('category', '💸')
                description = event.get('description', 'Долг')
                
                text += f"➕ *Новый долг*\n"
                text += f"{category} {description}\n"
                text += f"💰 {amount}\n"
                text += f"👤 Заплатил: {payer_name}\n"
                text += f"🕐 {timestamp}\n\n"
            
            elif event['type'] == 'debt_paid':
                debtor_name = Utils.get_participant_name(event['debtor_id'], participants, use_tag=False)
                creditor_name = Utils.get_participant_name(event['creditor_id'], participants, use_tag=False)
                amount = Utils.format_amount(event['amount'], currency)
                category = event.get('category', '💸')
                description = event.get('description', 'Долг')
                
                text += f"✅ *Долг возвращен*\n"
                text += f"{category} {description}\n"
                text += f"💰 {amount}\n"
                text += f"👤 {debtor_name} → {creditor_name}\n"
                text += f"🕐 {timestamp}\n\n"
        
        return text
    
    @staticmethod
    def is_user_in_trip(user_id: int, chat_id: int) -> bool:
        """Проверить, является ли пользователь участником поездки"""
        participants = Database.get_participants(chat_id)
        return any(p['user_id'] == user_id for p in participants)
    
    @staticmethod
    def validate_amount(text: str) -> tuple:
        """
        Валидация суммы долга
        Возвращает (bool, float|str): (успех, сумма или текст ошибки)
        """
        try:
            text = text.replace(',', '.')
            amount = float(text)
            
            if amount <= 0:
                return False, "Сумма должна быть больше нуля"
            
            if amount > 10000000:
                return False, "Сумма слишком большая (макс. 10,000,000)"
            
            return True, amount
        except ValueError:
            return False, "Введите корректную сумму (например: 1250 или 1250.50)"
    
    @staticmethod
    def parse_participants_from_text(text: str, all_participants: list) -> list:
        """
        Извлечь участников из текста по @username или имени
        
        Приоритет:
        1. @username (точное совпадение)
        2. first_name (точное совпадение без учёта регистра)
        
        Возвращает: список user_id
        """
        mentioned_ids = []
        words = text.split()
        
        for word in words:
            if word.startswith('@'):
                username = word[1:].lower().strip('.,!?;:')
                for p in all_participants:
                    if p.get('username', '').lower() == username:
                        if p['user_id'] not in mentioned_ids:
                            mentioned_ids.append(p['user_id'])
                        break
            else:
                word_clean = word.lower().strip('.,!?;:')
                for p in all_participants:
                    if p['first_name'].lower() == word_clean:
                        if p['user_id'] not in mentioned_ids:
                            mentioned_ids.append(p['user_id'])
                        break
        
        return mentioned_ids
