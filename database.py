import firebase_admin
from firebase_admin import credentials, firestore
from config import FIREBASE_CREDENTIALS_PATH
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase
cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()


class Database:
    """Класс для работы с Firebase Firestore"""
    
    @staticmethod
    def create_trip(chat_id: int, name: str, currency: str, creator_id: int):
        """Создать новую поездку"""
        trip_data = {
            'chat_id': chat_id,
            'name': name,
            'currency': currency,
            'creator_id': creator_id,
            'created_at': datetime.now(),
            'participants': [],
            'is_active': True
        }
        doc_ref = db.collection('trips').document(str(chat_id))
        doc_ref.set(trip_data)
        logger.info(f"Created trip for chat {chat_id}")
        return trip_data
    
    @staticmethod
    def get_trip(chat_id: int):
        """Получить поездку по chat_id"""
        doc = db.collection('trips').document(str(chat_id)).get()
        if doc.exists:
            return doc.to_dict()
        return None
    
    @staticmethod
    def add_participant(chat_id: int, user_id: int, username: str, first_name: str):
        """Добавить участника в поездку"""
        trip_ref = db.collection('trips').document(str(chat_id))
        trip = trip_ref.get()
        
        if trip.exists:
            participants = trip.to_dict().get('participants', [])
            
            # Проверяем, есть ли уже участник
            if not any(p['user_id'] == user_id for p in participants):
                participants.append({
                    'user_id': user_id,
                    'username': username or '',
                    'first_name': first_name,
                    'joined_at': datetime.now()
                })
                trip_ref.update({'participants': participants})
                logger.info(f"Added participant {user_id} to trip {chat_id}")
                return True
        return False
    
    @staticmethod
    def get_participants(chat_id: int):
        """Получить список участников поездки"""
        trip = Database.get_trip(chat_id)
        if trip:
            return trip.get('participants', [])
        return []
    
    @staticmethod
    def create_expense(chat_id: int, amount: float, payer_id: int, 
                      beneficiaries: list, comment: str = '', category: str = ''):
        """Создать новый расход"""
        expense_data = {
            'chat_id': chat_id,
            'amount': amount,
            'payer_id': payer_id,
            'beneficiaries': beneficiaries,  # list of user_ids
            'comment': comment,
            'category': category,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'is_deleted': False
        }
        doc_ref = db.collection('expenses').add(expense_data)
        expense_data['id'] = doc_ref[1].id
        logger.info(f"Created expense {expense_data['id']} for trip {chat_id}")
        return expense_data
    
    @staticmethod
    def get_expenses(chat_id: int):
        """Получить все расходы поездки"""
        expenses = db.collection('expenses')\
            .where('chat_id', '==', chat_id)\
            .where('is_deleted', '==', False)\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .stream()
        
        result = []
        for expense in expenses:
            data = expense.to_dict()
            data['id'] = expense.id
            result.append(data)
        return result
    
    @staticmethod
    def update_expense(expense_id: str, **kwargs):
        """Обновить расход"""
        kwargs['updated_at'] = datetime.now()
        db.collection('expenses').document(expense_id).update(kwargs)
        logger.info(f"Updated expense {expense_id}")
    
    @staticmethod
    def delete_expense(expense_id: str):
        """Удалить расход (мягкое удаление)"""
        db.collection('expenses').document(expense_id).update({
            'is_deleted': True,
            'deleted_at': datetime.now()
        })
        logger.info(f"Deleted expense {expense_id}")
    
    @staticmethod
    def get_user_settings(user_id: int):
        """Получить настройки пользователя"""
        doc = db.collection('user_settings').document(str(user_id)).get()
        if doc.exists:
            return doc.to_dict()
        return {
            'notification_type': 'balance_only',
            'language': 'ru'
        }
    
    @staticmethod
    def update_user_settings(user_id: int, **kwargs):
        """Обновить настройки пользователя"""
        doc_ref = db.collection('user_settings').document(str(user_id))
        doc_ref.set(kwargs, merge=True)
        logger.info(f"Updated settings for user {user_id}")
    
    @staticmethod
    def link_user_to_trip(user_id: int, chat_id: int):
        """Связать пользователя с поездкой для ЛС"""
        doc_ref = db.collection('user_trips').document(str(user_id))
        doc_ref.set({
            'active_trip': chat_id,
            'trips': firestore.ArrayUnion([chat_id]),
            'updated_at': datetime.now()
        }, merge=True)
        logger.info(f"Linked user {user_id} to trip {chat_id}")
    
    @staticmethod
    def get_user_active_trip(user_id: int):
        """Получить активную поездку пользователя"""
        doc = db.collection('user_trips').document(str(user_id)).get()
        if doc.exists:
            return doc.to_dict().get('active_trip')
        return None
    
    @staticmethod
    def calculate_balances(chat_id: int):
        """Рассчитать балансы между участниками"""
        expenses = Database.get_expenses(chat_id)
        participants = Database.get_participants(chat_id)
        
        if not participants:
            return {}
        
        # Создаем словарь балансов
        balances = {p['user_id']: 0 for p in participants}
        
        for expense in expenses:
            payer_id = expense['payer_id']
            amount = expense['amount']
            beneficiaries = expense['beneficiaries']
            
            if not beneficiaries:
                continue
            
            # Сумма на человека
            per_person = amount / len(beneficiaries)
            
            # Плательщик получает деньги
            balances[payer_id] += amount
            
            # Бенефициары должны заплатить
            for beneficiary_id in beneficiaries:
                balances[beneficiary_id] -= per_person
        
        return balances
    
    @staticmethod
    def get_debts(chat_id: int):
        """Получить упрощенные долги (кто кому сколько должен)"""
        balances = Database.calculate_balances(chat_id)
        
        # Разделяем на должников и кредиторов
        debtors = {k: -v for k, v in balances.items() if v < -0.01}
        creditors = {k: v for k, v in balances.items() if v > 0.01}
        
        debts = []
        
        # Простой алгоритм сведения долгов
        for debtor_id, debt_amount in sorted(debtors.items(), key=lambda x: x[1], reverse=True):
            for creditor_id, credit_amount in sorted(creditors.items(), key=lambda x: x[1], reverse=True):
                if debt_amount < 0.01 or credit_amount < 0.01:
                    continue
                
                transfer_amount = min(debt_amount, credit_amount)
                debts.append({
                    'from_id': debtor_id,
                    'to_id': creditor_id,
                    'amount': round(transfer_amount, 2)
                })
                
                debtors[debtor_id] -= transfer_amount
                creditors[creditor_id] -= transfer_amount
                debt_amount -= transfer_amount
                credit_amount -= transfer_amount
        
        return debts
