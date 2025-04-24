"""
Сервис для отправки SMS-сообщений через различных провайдеров
"""

import requests
import hashlib
import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from app.config import (
    SMS_PROVIDER, SMS_API_KEY, SMS_FROM, SMS_TEST_MODE,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER
)

# Настройка логирования
logger = logging.getLogger("sms_service")


class SMSProviderBase(ABC):
    """
    Базовый класс для всех SMS-провайдеров
    """
    @abstractmethod
    def send_message(self, phone: str, message: str) -> Tuple[bool, str]:
        """
        Отправляет SMS на указанный номер с указанным текстом
        Возвращает: (успех, сообщение)
        """
        pass


class SMSRuProvider(SMSProviderBase):
    """
    Провайдер для отправки SMS через SMS.ru
    API документация: https://sms.ru/api
    """
    API_URL = "https://sms.ru/sms/send"
    
    def __init__(self, api_key: str, from_name: str = "", test_mode: bool = False):
        self.api_key = api_key
        self.from_name = from_name
        self.test_mode = test_mode
    
    def send_message(self, phone: str, message: str) -> Tuple[bool, str]:
        """
        Отправляет SMS на указанный номер с указанным текстом
        через API SMS.ru
        """
        # Формирование номера телефона
        # Убираем '+' для SMS.ru и проверяем, что номер начинается с 7
        if phone.startswith('+'):
            phone = phone[1:]
            
        if not phone.startswith('7'):
            return False, "Номер должен начинаться с +7"
        
        params = {
            'api_id': self.api_key,
            'to': phone,
            'msg': message,
            'json': 1,  # Ответ в формате JSON
        }
        
        # Добавление имени отправителя, если указано
        if self.from_name:
            params['from'] = self.from_name
            
        # Тестовый режим (без реальной отправки)
        if self.test_mode:
            params['test'] = 1
            
        try:
            logger.debug(f"Отправка SMS на номер {phone}: {message[:20]}...")
            response = requests.post(self.API_URL, data=params)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Проверяем статус отправки
                if response_data.get('status_code') == 100:
                    sms_id = list(response_data.get('sms', {}).values())[0].get('sms_id', 'unknown')
                    return True, f"SMS успешно отправлено (ID: {sms_id})"
                else:
                    error = response_data.get('status_text', 'Неизвестная ошибка')
                    logger.error(f"Ошибка отправки SMS: {error}")
                    return False, f"Ошибка отправки SMS: {error}"
            else:
                logger.error(f"Ошибка HTTP: {response.status_code}, {response.text}")
                return False, f"Ошибка HTTP: {response.status_code}"
                
        except Exception as e:
            logger.exception(f"Исключение при отправке SMS: {str(e)}")
            return False, f"Ошибка отправки SMS: {str(e)}"


class TwilioProvider(SMSProviderBase):
    """
    Провайдер для отправки SMS через Twilio
    API документация: https://www.twilio.com/docs/sms
    """
    API_URL = "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.api_url = self.API_URL.format(account_sid=account_sid)
    
    def send_message(self, phone: str, message: str) -> Tuple[bool, str]:
        """
        Отправляет SMS на указанный номер с указанным текстом
        через API Twilio
        """
        # Проверяем номер
        if not phone.startswith('+'):
            phone = f"+{phone}"
            
        params = {
            'From': self.from_number,
            'To': phone,
            'Body': message
        }
        
        try:
            logger.debug(f"Отправка SMS на номер {phone}: {message[:20]}...")
            response = requests.post(
                self.api_url,
                data=params,
                auth=(self.account_sid, self.auth_token)
            )
            
            if response.status_code in (200, 201):
                response_data = response.json()
                return True, f"SMS успешно отправлено (SID: {response_data.get('sid', 'unknown')})"
            else:
                logger.error(f"Ошибка HTTP: {response.status_code}, {response.text}")
                return False, f"Ошибка HTTP: {response.status_code}"
                
        except Exception as e:
            logger.exception(f"Исключение при отправке SMS: {str(e)}")
            return False, f"Ошибка отправки SMS: {str(e)}"


class MockSMSProvider(SMSProviderBase):
    """
    Эмуляция отправки SMS для разработки и тестирования
    """
    def send_message(self, phone: str, message: str) -> Tuple[bool, str]:
        """
        Эмулирует отправку SMS (выводит в лог)
        """
        logger.info(f"[MOCK SMS] На номер {phone} отправлено сообщение: {message}")
        print(f"[MOCK SMS] На номер {phone} отправлено сообщение: {message}")
        return True, "SMS успешно отправлено (эмуляция)"


def get_sms_provider() -> SMSProviderBase:
    """
    Фабрика для получения настроенного SMS-провайдера
    """
    provider = SMS_PROVIDER.lower()
    
    if provider == "sms_ru":
        if not SMS_API_KEY:
            logger.warning("API ключ SMS.ru не настроен, используется заглушка")
            return MockSMSProvider()
        return SMSRuProvider(SMS_API_KEY, SMS_FROM, SMS_TEST_MODE)
        
    elif provider == "twilio":
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER]):
            logger.warning("Настройки Twilio неполные, используется заглушка")
            return MockSMSProvider()
        return TwilioProvider(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER)
        
    else:
        logger.warning(f"Неизвестный провайдер SMS: {provider}, используется заглушка")
        return MockSMSProvider()


def send_verification_code(phone: str, code: str) -> Tuple[bool, str]:
    """
    Отправляет SMS с кодом подтверждения на указанный номер телефона
    """
    provider = get_sms_provider()
    message = f"Ваш код подтверждения для TradeHub: {code}"
    return provider.send_message(phone, message) 