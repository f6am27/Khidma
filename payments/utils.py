"""
Moosyl Payment Integration Utilities
دوال التكامل مع بوابة الدفع Moosyl
"""

import requests
import hmac
import hashlib
from django.conf import settings
from decimal import Decimal
from django.conf import settings


class MoosylAPI:
    """
    Moosyl API Client
    """
    
    BASE_URL = settings.MOOSYL_BASE_URL
    
    def __init__(self):
        self.secret_key = settings.MOOSYL_SECRET_KEY
        self.publishable_key = settings.MOOSYL_PUBLISHABLE_KEY
        
        if not self.secret_key:
            raise ValueError("MOOSYL_SECRET_KEY not found in settings")
        if not self.publishable_key:
            raise ValueError("MOOSYL_PUBLISHABLE_KEY not found in settings")
    
    def create_payment_request(self, amount, transaction_id, metadata=None):
        """
        إنشاء طلب دفع جديد
        
        Args:
            amount (float): المبلغ بالأوقية (MRU)
            transaction_id (str): معرف فريد للمعاملة (من عندنا)
            metadata (dict): بيانات إضافية (اختياري)
        
        Returns:
            dict: {
                'success': bool,
                'transaction_id': str,  # من Moosyl
                'our_transaction_id': str,  # معرفنا
                'amount': float,
                'status': str
            }
        """
        url = f"{self.BASE_URL}/payment-request"
        
        headers = {
            'Authorization': self.secret_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'amount': int(amount),  # Moosyl يقبل integers فقط
            'transactionId': transaction_id
        }
        
        # إضافة metadata إذا وُجدت
        if metadata:
            payload['metadata'] = metadata
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=10  # 10 ثواني timeout
            )
            
            response.raise_for_status()  # رفع خطأ إذا status code != 200
            
            data = response.json()
            
            return {
                'success': True,
                'transaction_id': data.get('transactionId'),  # من Moosyl
                'our_transaction_id': transaction_id,  # معرفنا
                'amount': amount,
                'status': data.get('status', 'pending'),
                'raw_response': data
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'timeout',
                'message': 'طلب Moosyl استغرق وقتاً طويلاً'
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': 'request_failed',
                'message': str(e)
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': 'unknown',
                'message': f'خطأ غير متوقع: {str(e)}'
            }
    
    def verify_webhook_signature(self, payload, signature):
        """
        التحقق من توقيع Webhook
        
        Args:
            payload (bytes/str): محتوى الـ webhook
            signature (str): التوقيع من header 'x-webhook-signature'
        
        Returns:
            bool: True إذا كان التوقيع صحيح
        """
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        # حساب التوقيع المتوقع
        expected_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # مقارنة آمنة
        return hmac.compare_digest(expected_signature, signature)


def get_moosyl_client():
    """
    الحصول على instance من MoosylAPI
    """
    return MoosylAPI()