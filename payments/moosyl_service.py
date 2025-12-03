# # payments/moosyl_service.py
# """
# Moosyl Payment Gateway Integration Service
# """

# import requests
# import logging
# from decimal import Decimal
# from typing import Dict, Optional
# from django.conf import settings

# logger = logging.getLogger(__name__)


# class MoosylPaymentService:
#     """خدمة التكامل مع Moosyl Payment Gateway"""
    
#     def __init__(self):
#         self.secret_key = settings.MOOSYL_SECRET_KEY
#         self.base_url = settings.MOOSYL_BASE_URL
#         self.timeout = settings.MOOSYL_TIMEOUT
    
#     def _get_headers(self) -> Dict[str, str]:
#         """إنشاء Headers للطلبات"""
#         return {
#             'Authorization': self.secret_key,
#             'Content-Type': 'application/json',
#         }
    
#     def create_payment_request(
#         self,
#         amount: Decimal,
#         transaction_id: str,
#         phone_number: str = None, 
#     ) -> Dict:
#         """
#         إنشاء طلب دفع جديد
        
#         Args:
#             amount: المبلغ بالأوقية
#             transaction_id: معرف فريد للمعاملة
        
#         Returns:
#             Dict: استجابة من Moosyl تحتوي على transactionId
#         """
#         try:
#             payload = {
#             'transactionId': transaction_id,
#             'amount': int(amount),  
#             # ✅ تحويل إلى string
#             'phoneNumber': phone_number,            }
            
#             # 🔍 DEBUG
#             print(f"🔑 Secret Key: {self.secret_key[:20]}...")
#             print(f"📦 Payload: {payload}")
            
#             # ✅ الـ endpoint الصحيح
#             url = f'{self.base_url}/payment-request'
#             print(f"🌐 URL: {url}")
            
#             response = requests.post(
#                 url,
#                 headers=self._get_headers(),
#                 json=payload,
#                 timeout=self.timeout
#             )
            
#             # 🔍 DEBUG
#             print(f"📊 Status Code: {response.status_code}")
#             print(f"📄 Response: {response.text}")
            
#             response.raise_for_status()
#             result = response.json()
            
#             logger.info(f"✅ Moosyl payment request created: {transaction_id}")
#             return {
#                 'success': True,
#                 'transaction_id': result.get('transactionId'),
#                 'data': result
#             }
        
#         except requests.exceptions.RequestException as e:
#             logger.error(f"❌ Moosyl payment request failed: {str(e)}")
#             return {
#                 'success': False,
#                 'error': str(e),
#                 'message': 'فشل إنشاء طلب الدفع'
#             }
        
#     def verify_payment(self, transaction_id: str) -> Dict:
#         """
#         التحقق من حالة الدفع
        
#         Args:
#             transaction_id: معرف المعاملة
        
#         Returns:
#             Dict: حالة الدفع
#         """
#         try:
#             url = f'{self.base_url}/payment-request/{transaction_id}'
#             response = requests.get(
#                 url,
#                 headers=self._get_headers(),
#                 timeout=self.timeout
#             )
            
#             response.raise_for_status()
#             result = response.json()
            
#             return {
#                 'success': True,
#                 'status': result.get('status'),
#                 'amount': result.get('amount'),
#                 'data': result
#             }
        
#         except requests.exceptions.RequestException as e:
#             logger.error(f"❌ Payment verification failed: {str(e)}")
#             return {
#                 'success': False,
#                 'error': str(e)
#             }


# # إنشاء instance واحد للاستخدام
# moosyl_service = MoosylPaymentService()