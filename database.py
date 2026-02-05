import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import logging
import json
import os

logger = logging.getLogger(__name__)

# Initialize Firebase
firebase_creds = os.getenv('FIREBASE_CREDENTIALS')

if firebase_creds:
    try:
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
        logger.info("Firebase initialized from environment variable")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse FIREBASE_CREDENTIALS: {e}")
        raise
else:
    try:
        cred = credentials.Certificate('firebase_key.json')
        logger.info("Firebase initialized from local file")
    except FileNotFoundError:
        logger.error("Firebase credentials not found. Set FIREBASE_CREDENTIALS environment variable.")
        raise

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
    def create_debt(chat_id: int, amount: float, payer_id: int, 
                    participants: list, description: str = '', category: str = ''):
        """
        Создать долг
        Новая структура: один долг = много индивидуальных долгов
        """
        # Считаем количество участников БЕЗ плательщика
        debtors = [p for p in participants if p != payer_id]
        
        if not debtors:
            return None
        
        # Сумма на человека
        amount_per_person = amount / len(debtors)
        
        # Создаем общий долг (родительский документ)
        debt_group_data = {
            'chat_id': chat_id,
            'total_amount': amount,
            'payer_id': payer_id,
            'all_participants': participants,  # Все участники включая плательщика
            'description': description,
            'category': category,
            'created_at': datetime.now(),
            'is_deleted': False
        }
        
        debt_group_ref = db.collection('debt_groups').add(debt_group_data)
        debt_group_id = debt_group_ref[1].id
        
        # Создаем индивидуальные долги
        individual_debts = []
        for debtor_id in debtors:
            debt_data = {
                'debt_group_id': debt_group_id,
                'chat_id': chat_id,
                'debtor_id': debtor_id,  # Кто должен
                'creditor_id': payer_id,  # Кому должен
                'amount': amount_per_person,
                'is_paid': False,
                'paid_at': None,
                'created_at': datetime.now()
            }
            debt_ref = db.collection('debts').add(debt_data)
            debt_data['id'] = debt_ref[1].id
            individual_debts.append(debt_data)
        
        logger.info(f"Created debt group {debt_group_id} with {len(individual_debts)} individual debts")
        
        return {
            'group_id': debt_group_id,
            'debts': individual_debts,
            'group_data': debt_group_data
        }
    
    @staticmethod
    def get_debt_groups(chat_id: int):
        """Получить все группы долгов поездки"""
        debt_groups = db.collection('debt_groups')\
            .where('chat_id', '==', chat_id)\
            .where('is_deleted', '==', False)\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .stream()
        
        result = []
        for dg in debt_groups:
            data = dg.to_dict()
            data['id'] = dg.id
            result.append(data)
        return result
    
    @staticmethod
    def get_individual_debts(chat_id: int, user_id: int = None):
        """Получить индивидуальные долги"""
        query = db.collection('debts').where('chat_id', '==', chat_id)
        
        if user_id:
            # Долги конкретного пользователя (он должник)
            query = query.where('debtor_id', '==', user_id)
        
        debts = query.order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        
        result = []
        for debt in debts:
            data = debt.to_dict()
            data['id'] = debt.id
            result.append(data)
        return result
    
    @staticmethod
    def get_debts_to_user(chat_id: int, user_id: int):
        """Получить долги, где user_id - кредитор (ему должны)"""
        debts = db.collection('debts')\
            .where('chat_id', '==', chat_id)\
            .where('creditor_id', '==', user_id)\
            .where('is_paid', '==', False)\
            .stream()
        
        result = []
        for debt in debts:
            data = debt.to_dict()
            data['id'] = debt.id
            result.append(data)
        return result
    
    @staticmethod
    def mark_debt_paid(debt_id: str):
        """Отметить долг как возвращенный"""
        db.collection('debts').document(debt_id).update({
            'is_paid': True,
            'paid_at': datetime.now()
        })
        logger.info(f"Marked debt {debt_id} as paid")
        
        # Получаем данные долга для возврата
        debt = db.collection('debts').document(debt_id).get()
        if debt.exists:
            return debt.to_dict()
        return None
    
    @staticmethod
    def get_my_debts(chat_id: int, user_id: int):
        """Получить мои непогашенные долги"""
        debts = db.collection('debts')\
            .where('chat_id', '==', chat_id)\
            .where('debtor_id', '==', user_id)\
            .where('is_paid', '==', False)\
            .stream()
        
        result = []
        for debt in debts:
            data = debt.to_dict()
            data['id'] = debt.id
            
            # Получаем информацию о группе долга
            debt_group = db.collection('debt_groups').document(data['debt_group_id']).get()
            if debt_group.exists:
                data['group_info'] = debt_group.to_dict()
            
            result.append(data)
        return result
    
    @staticmethod
    def get_debts_summary(chat_id: int):
        """Получить общую сводку долгов"""
        all_debts = db.collection('debts')\
            .where('chat_id', '==', chat_id)\
            .where('is_paid', '==', False)\
            .stream()
        
        # Группируем долги: кто кому должен
        summary = {}
        
        for debt in all_debts:
            data = debt.to_dict()
            debtor_id = data['debtor_id']
            creditor_id = data['creditor_id']
            amount = data['amount']
            
            key = f"{debtor_id}_{creditor_id}"
            
            if key not in summary:
                summary[key] = {
                    'debtor_id': debtor_id,
                    'creditor_id': creditor_id,
                    'total_amount': 0
                }
            
            summary[key]['total_amount'] += amount
        
        return list(summary.values())
    
    @staticmethod
    def get_user_settings(user_id: int):
        """Получить настройки пользователя"""
        doc = db.collection('user_settings').document(str(user_id)).get()
        if doc.exists:
            return doc.to_dict()
        return {
            'notification_type': 'all',  # all, off
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
        
        # Получаем текущий документ
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            trips = data.get('trips', [])
            
            # Добавляем поездку в список, если её там нет
            if chat_id not in trips:
                trips.append(chat_id)
            
            # Если активной поездки нет, делаем эту активной
            if not data.get('active_trip'):
                doc_ref.update({
                    'active_trip': chat_id,
                    'trips': trips,
                    'updated_at': datetime.now()
                })
            else:
                doc_ref.update({
                    'trips': trips,
                    'updated_at': datetime.now()
                })
        else:
            # Создаем новый документ
            doc_ref.set({
                'active_trip': chat_id,
                'trips': [chat_id],
                'updated_at': datetime.now()
            })
        
        logger.info(f"Linked user {user_id} to trip {chat_id}")
    
    @staticmethod
    def get_user_active_trip(user_id: int):
        """Получить активную поездку пользователя"""
        doc = db.collection('user_trips').document(str(user_id)).get()
        if doc.exists:
            return doc.to_dict().get('active_trip')
        return None
    
    @staticmethod
    def get_user_trips(user_id: int):
        """Получить все поездки пользователя (НОВОЕ)"""
        doc = db.collection('user_trips').document(str(user_id)).get()
        if doc.exists:
            return doc.to_dict()
        return None
    
    @staticmethod
    def set_active_trip(user_id: int, chat_id: int):
        """Установить активную поездку (НОВОЕ)"""
        doc_ref = db.collection('user_trips').document(str(user_id))
        doc_ref.update({
            'active_trip': chat_id,
            'updated_at': datetime.now()
        })
        logger.info(f"Set active trip {chat_id} for user {user_id}")
    
    @staticmethod
    def delete_debt_group(debt_group_id: str):
        """Удалить группу долгов (мягкое удаление)"""
        db.collection('debt_groups').document(debt_group_id).update({
            'is_deleted': True,
            'deleted_at': datetime.now()
        })
        logger.info(f"Deleted debt group {debt_group_id}")
    @staticmethod
    def delete_trip_completely(chat_id: int):
        """Полностью удалить поездку и все связанные данные"""
        try:
            # 1. Удаляем все индивидуальные долги
            debts = db.collection('debts').where('chat_id', '==', chat_id).stream()
            for debt in debts:
                db.collection('debts').document(debt.id).delete()
            
            # 2. Удаляем все группы долгов
            debt_groups = db.collection('debt_groups').where('chat_id', '==', chat_id).stream()
            for dg in debt_groups:
                db.collection('debt_groups').document(dg.id).delete()
            
            # 3. Удаляем поездку из user_trips для всех участников
            trip = Database.get_trip(chat_id)
            if trip:
                participants = trip.get('participants', [])
                for p in participants:
                    user_id = p['user_id']
                    user_trips_ref = db.collection('user_trips').document(str(user_id))
                    user_trips_doc = user_trips_ref.get()
                    
                    if user_trips_doc.exists:
                        data = user_trips_doc.to_dict()
                        trips = data.get('trips', [])
                        
                        # Удаляем chat_id из списка поездок
                        if chat_id in trips:
                            trips.remove(chat_id)
                        
                        # Если это была активная поездка, сбрасываем её
                        if data.get('active_trip') == chat_id:
                            new_active = trips[0] if trips else None
                            user_trips_ref.update({
                                'active_trip': new_active,
                                'trips': trips
                            })
                        else:
                            user_trips_ref.update({'trips': trips})
            
            # 4. Удаляем саму поездку
            db.collection('trips').document(str(chat_id)).delete()
            
            logger.info(f"Completely deleted trip {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting trip {chat_id}: {e}")
            return False
