import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import logging
import json
import os

logger = logging.getLogger(__name__)

def initialize_firebase():
    """Безопасная инициализация Firebase"""
    if firebase_admin._apps:
        logger.info("Firebase already initialized")
        return firestore.client()
    
    firebase_creds = os.getenv('FIREBASE_CREDENTIALS')
    
    if firebase_creds:
        try:
            cred_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(cred_dict)
            logger.info("Firebase credentials loaded from environment variable")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse FIREBASE_CREDENTIALS: {e}")
            raise
    else:
        try:
            cred = credentials.Certificate('firebase_key.json')
            logger.info("Firebase credentials loaded from local file")
        except FileNotFoundError:
            logger.error("Firebase credentials not found. Set FIREBASE_CREDENTIALS environment variable.")
            raise
    
    firebase_admin.initialize_app(cred)
    logger.info("Firebase initialized successfully")
    return firestore.client()

db = initialize_firebase()


class Database:
    """Класс для работы с Firebase Firestore"""
    
    @staticmethod
    def create_trip(chat_id: int, name: str, currency: str, creator_id: int):
        """Создать новую поездку"""
        try:
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
            logger.info(f"Created trip '{name}' for chat {chat_id}")
            return trip_data
        except Exception as e:
            logger.error(f"Error creating trip: {e}")
            return None
    
    @staticmethod
    def get_trip(chat_id: int):
        """Получить поездку по chat_id"""
        try:
            doc = db.collection('trips').document(str(chat_id)).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting trip {chat_id}: {e}")
            return None
    
    @staticmethod
    def add_participant(chat_id: int, user_id: int, username: str, first_name: str):
        """Добавить участника в поездку"""
        try:
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
                    logger.info(f"Added participant @{username or user_id} to trip {chat_id}")
                    return True
                else:
                    for p in participants:
                        if p['user_id'] == user_id:
                            if p.get('username') != username or p.get('first_name') != first_name:
                                p['username'] = username or ''
                                p['first_name'] = first_name
                                trip_ref.update({'participants': participants})
                                logger.info(f"Updated participant info for {user_id}")
                            break
                    return True
            return False
        except Exception as e:
            logger.error(f"Error adding participant: {e}")
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
                    participants: list, description: str = '', category: str = '💸'):
        """Создать долг"""
        try:
            if not participants or len(participants) < 2:
                logger.error("Need at least 2 participants (including payer)")
                return None
            
            if payer_id not in participants:
                logger.error(f"Payer {payer_id} not in participants list")
                return None
            
            amount_per_person = amount / len(participants)
            debtors = [p for p in participants if p != payer_id]
            
            if not debtors:
                logger.error("No debtors found (payer cannot owe to himself)")
                return None
            
            debt_group_data = {
                'chat_id': chat_id,
                'total_amount': amount,
                'payer_id': payer_id,
                'all_participants': participants,
                'description': description or 'Общий расход',
                'category': category,
                'created_at': datetime.now(),
                'is_deleted': False
            }
            
            debt_group_ref = db.collection('debt_groups').add(debt_group_data)
            debt_group_id = debt_group_ref[1].id
            
            individual_debts = []
            for debtor_id in debtors:
                debt_data = {
                    'debt_group_id': debt_group_id,
                    'chat_id': chat_id,
                    'debtor_id': debtor_id,
                    'creditor_id': payer_id,
                    'amount': amount_per_person,
                    'is_paid': False,
                    'paid_at': None,
                    'created_at': datetime.now()
                }
                debt_ref = db.collection('debts').add(debt_data)
                debt_data['id'] = debt_ref[1].id
                individual_debts.append(debt_data)
            
            logger.info(
                f"Created debt group {debt_group_id}: "
                f"{amount} / {len(participants)} participants = "
                f"{amount_per_person} per person, {len(debtors)} debtors"
            )
            
            return {
                'group_id': debt_group_id,
                'debts': individual_debts,
                'group_data': debt_group_data
            }
            
        except Exception as e:
            logger.error(f"Error creating debt: {e}")
            return None
    
    @staticmethod
    def get_debt_groups(chat_id: int):
        """Получить все группы долгов поездки (сортировка по дате)"""
        try:
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
        except Exception as e:
            logger.error(f"Error getting debt groups: {e}")
            return []
    
    @staticmethod
    def get_all_debt_groups(chat_id: int, limit: int = 20):
        """Получить ВСЕ группы долгов для истории (включая погашенные)"""
        try:
            debt_groups = db.collection('debt_groups')\
                .where('chat_id', '==', chat_id)\
                .where('is_deleted', '==', False)\
                .order_by('created_at', direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
            
            result = []
            for dg in debt_groups:
                data = dg.to_dict()
                data['id'] = dg.id
                result.append(data)
            return result
        except Exception as e:
            logger.error(f"Error getting all debt groups: {e}")
            return []
    
    @staticmethod
    def get_individual_debts(chat_id: int, user_id: int = None):
        """Получить индивидуальные долги"""
        try:
            query = db.collection('debts').where('chat_id', '==', chat_id)
            
            if user_id:
                query = query.where('debtor_id', '==', user_id)
            
            debts = query.order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            
            result = []
            for debt in debts:
                data = debt.to_dict()
                data['id'] = debt.id
                result.append(data)
            return result
        except Exception as e:
            logger.error(f"Error getting individual debts: {e}")
            return []
    
    @staticmethod
    def get_debts_to_user(chat_id: int, user_id: int):
        """Получить долги, где user_id - кредитор"""
        try:
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
        except Exception as e:
            logger.error(f"Error getting debts to user: {e}")
            return []
    
    @staticmethod
    def mark_debt_paid(debt_id: str):
        """Отметить долг как возвращенный"""
        try:
            debt_ref = db.collection('debts').document(debt_id)
            debt_ref.update({
                'is_paid': True,
                'paid_at': datetime.now()
            })
            logger.info(f"Marked debt {debt_id} as paid")
            
            debt = debt_ref.get()
            if debt.exists:
                return debt.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error marking debt as paid: {e}")
            return None
    
    @staticmethod
    def get_my_debts(chat_id: int, user_id: int):
        """Получить мои непогашенные долги"""
        try:
            debts = db.collection('debts')\
                .where('chat_id', '==', chat_id)\
                .where('debtor_id', '==', user_id)\
                .where('is_paid', '==', False)\
                .stream()
            
            result = []
            for debt in debts:
                data = debt.to_dict()
                data['id'] = debt.id
                
                try:
                    debt_group = db.collection('debt_groups').document(data['debt_group_id']).get()
                    if debt_group.exists:
                        data['group_info'] = debt_group.to_dict()
                except Exception as e:
                    logger.error(f"Error getting debt group info: {e}")
                    data['group_info'] = {
                        'description': 'Без описания',
                        'category': '💸'
                    }
                
                result.append(data)
            return result
        except Exception as e:
            logger.error(f"Error getting my debts: {e}")
            return []
    
    @staticmethod
    def get_debts_summary(chat_id: int):
        """Получить общую сводку долгов"""
        try:
            all_debts = db.collection('debts')\
                .where('chat_id', '==', chat_id)\
                .where('is_paid', '==', False)\
                .stream()
            
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
        except Exception as e:
            logger.error(f"Error getting debts summary: {e}")
            return []
    
    @staticmethod
    def get_user_settings(user_id: int):
        """Получить настройки пользователя"""
        try:
            doc = db.collection('user_settings').document(str(user_id)).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
        
        return {
            'notification_type': 'all',
            'language': 'ru'
        }
    
    @staticmethod
    def update_user_settings(user_id: int, **kwargs):
        """Обновить настройки пользователя"""
        try:
            doc_ref = db.collection('user_settings').document(str(user_id))
            doc_ref.set(kwargs, merge=True)
            logger.info(f"Updated settings for user {user_id}: {kwargs}")
            return True
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            return False
    
    @staticmethod
    def link_user_to_trip(user_id: int, chat_id: int):
        """Связать пользователя с поездкой"""
        try:
            doc_ref = db.collection('user_trips').document(str(user_id))
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                trips = data.get('trips', [])
                
                if chat_id not in trips:
                    trips.append(chat_id)
                
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
                doc_ref.set({
                    'active_trip': chat_id,
                    'trips': [chat_id],
                    'updated_at': datetime.now()
                })
            
            logger.info(f"Linked user {user_id} to trip {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error linking user to trip: {e}")
            return False
    
    @staticmethod
    def get_user_active_trip(user_id: int):
        """Получить активную поездку пользователя"""
        try:
            doc = db.collection('user_trips').document(str(user_id)).get()
            if doc.exists:
                return doc.to_dict().get('active_trip')
            return None
        except Exception as e:
            logger.error(f"Error getting user active trip: {e}")
            return None
    
    @staticmethod
    def get_user_trips(user_id: int):
        """Получить все поездки пользователя"""
        try:
            doc = db.collection('user_trips').document(str(user_id)).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting user trips: {e}")
            return None
    
    @staticmethod
    def set_active_trip(user_id: int, chat_id: int):
        """Установить активную поездку"""
        try:
            doc_ref = db.collection('user_trips').document(str(user_id))
            doc_ref.update({
                'active_trip': chat_id,
                'updated_at': datetime.now()
            })
            logger.info(f"Set active trip {chat_id} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting active trip: {e}")
            return False
    
    @staticmethod
    def delete_debt_group(debt_group_id: str):
        """Удалить группу долгов"""
        try:
            db.collection('debt_groups').document(debt_group_id).update({
                'is_deleted': True,
                'deleted_at': datetime.now()
            })
            logger.info(f"Soft-deleted debt group {debt_group_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting debt group: {e}")
            return False
    
    @staticmethod
    def delete_trip_completely(chat_id: int):
        """Полностью удалить поездку и все связанные данные"""
        try:
            debts = db.collection('debts').where('chat_id', '==', chat_id).stream()
            deleted_debts = 0
            for debt in debts:
                db.collection('debts').document(debt.id).delete()
                deleted_debts += 1
            
            debt_groups = db.collection('debt_groups').where('chat_id', '==', chat_id).stream()
            deleted_groups = 0
            for dg in debt_groups:
                db.collection('debt_groups').document(dg.id).delete()
                deleted_groups += 1
            
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
                        
                        if chat_id in trips:
                            trips.remove(chat_id)
                        
                        if data.get('active_trip') == chat_id:
                            new_active = trips[0] if trips else None
                            user_trips_ref.update({
                                'active_trip': new_active,
                                'trips': trips,
                                'updated_at': datetime.now()
                            })
                        else:
                            user_trips_ref.update({
                                'trips': trips,
                                'updated_at': datetime.now()
                            })
            
            db.collection('trips').document(str(chat_id)).delete()
            
            logger.info(
                f"Completely deleted trip {chat_id}: "
                f"{deleted_debts} debts, {deleted_groups} debt groups"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error deleting trip {chat_id}: {e}")
            return False
