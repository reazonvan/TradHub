from datetime import datetime, timedelta
from typing import Optional, Union, Any, Dict
import re
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from collections import defaultdict
import time
import random
import string
import os
import logging

from app.config import settings
from app.database import get_db
from app.models.user import User, PhoneVerification
from app.schemas.user import TokenData

# Глобальные переменные для rate limiting и блокировки аккаунтов
LOGIN_ATTEMPTS = defaultdict(list)  # username -> list of timestamps
BLOCKED_USERS = defaultdict(float)  # username -> timestamp until blocked
MAX_ATTEMPTS = 5  # Максимальное количество попыток
BLOCK_DURATION = 900  # Время блокировки в секундах (15 минут)
ATTEMPT_WINDOW = 300  # Окно времени для подсчета попыток (5 минут)

def check_password_strength(password: str) -> bool:
    """
    Проверяет сложность пароля по следующим критериям:
    - Минимум 8 символов
    - Содержит заглавные и строчные буквы
    - Содержит цифры
    - Содержит спецсимволы
    """
    if len(password) < 8:
        return False
        
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    return all([has_upper, has_lower, has_digit, has_special])

def check_rate_limit(username: str) -> None:
    """
    Проверка rate limiting и блокировки
    """
    current_time = time.time()
    
    # Проверка блокировки
    if username in BLOCKED_USERS:
        block_end = BLOCKED_USERS[username]
        if current_time < block_end:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Аккаунт заблокирован на {int(block_end - current_time)} секунд"
            )
        else:
            del BLOCKED_USERS[username]
            LOGIN_ATTEMPTS[username] = []

    # Очистка старых попыток
    LOGIN_ATTEMPTS[username] = [t for t in LOGIN_ATTEMPTS[username] 
                              if current_time - t < ATTEMPT_WINDOW]
    
    # Проверка количества попыток
    if len(LOGIN_ATTEMPTS[username]) >= MAX_ATTEMPTS:
        BLOCKED_USERS[username] = current_time + BLOCK_DURATION
        LOGIN_ATTEMPTS[username] = []
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Превышено количество попыток. Аккаунт заблокирован на {BLOCK_DURATION} секунд"
        )

def record_login_attempt(username: str, success: bool) -> None:
    """
    Запись попытки входа
    """
    if not success:
        LOGIN_ATTEMPTS[username].append(time.time())

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Схема авторизации OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка соответствия пароля хешу
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Создание хеша пароля
    """
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена доступа
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_password_reset_token(email: str) -> str:
    """
    Создание токена для сброса пароля
    """
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {"sub": email, "exp": expire, "type": "password_reset"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password_reset_token(token: str) -> str:
    """
    Проверка токена сброса пароля и получение email
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный токен сброса пароля"
            )
        
        return email
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен сброса пароля"
        )

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Получение пользователя по имени пользователя
    """
    return db.query(User).filter(User.username == username).first()

def get_user_by_token(token: str, db: Session) -> Optional[User]:
    """
    Получение пользователя по токену
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        user = get_user_by_username(db, username)
        return user
    except JWTError:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Получение текущего пользователя по токену
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт неактивен"
        )
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Получение текущего активного пользователя
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт неактивен"
        )
    return current_user

def is_admin(user: User) -> bool:
    """
    Проверка является ли пользователь администратором
    """
    return user.role == "admin"

async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Получение текущего пользователя с правами администратора
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    return current_user

def get_cookie_user(request):
    """
    Получение текущего пользователя из cookie
    """
    try:
        # Получаем токен из cookie
        token = request.cookies.get("access_token")
        if not token:
            return None
        
        # Если токен в формате "Bearer <token>", удаляем префикс
        if token.startswith("Bearer "):
            token = token[7:]
        
        # Проверяем валидность токена
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username = payload.get("sub")
            if not username:
                return None
                
            # Проверяем срок действия токена
            exp = payload.get("exp")
            if not exp or datetime.utcnow() > datetime.fromtimestamp(exp):
                return None
        except JWTError:
            return None
        
        # Получаем пользователя из базы данных
        db = next(get_db())
        user = get_user_by_username(db, username)
        
        # Проверяем активность пользователя
        if user and not user.is_active:
            return None
            
        return user
    except Exception as e:
        print(f"Ошибка при получении пользователя из cookie: {e}")
        return None

def get_current_seller(current_user: User = Depends(get_current_user)) -> User:
    """
    Получение текущего пользователя-продавца
    """
    if current_user.role != "seller" and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуется роль продавца."
        )
    return current_user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Получение текущего пользователя-администратора
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуется роль администратора."
        )
    return current_user

async def authenticate_user(username: str, password: str, db: Session) -> Union[User, bool]:
    """
    Аутентификация пользователя
    """
    try:
        # Проверка rate limiting
        check_rate_limit(username)
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            record_login_attempt(username, False)
            return False
            
        if not verify_password(password, user.hashed_password):
            record_login_attempt(username, False)
            return False
            
        # Успешная аутентификация
        record_login_attempt(username, True)
        return user
        
    except HTTPException as e:
        # Пробрасываем исключения от rate limiting
        raise e
    except Exception as e:
        record_login_attempt(username, False)
        return False

# Функции для SMS-верификации
def generate_sms_code(length=6):
    """
    Генерирует случайный цифровой код указанной длины
    """
    return ''.join(random.choices(string.digits, k=length))

def create_phone_verification(db, phone, expiration_minutes=10):
    """
    Создает новую запись верификации телефона с случайным кодом
    """
    # Проверяем, есть ли уже активный код для этого номера
    existing = db.query(PhoneVerification).filter(
        PhoneVerification.phone == phone,
        PhoneVerification.is_verified == False,
        PhoneVerification.expires_at > datetime.utcnow()
    ).first()
    
    # Если есть активный код - возвращаем его
    if existing:
        return existing.code
        
    # Если нет - создаем новый
    code = generate_sms_code()
    expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)
    
    verification = PhoneVerification(
        phone=phone,
        code=code,
        expires_at=expires_at
    )
    
    db.add(verification)
    db.commit()
    db.refresh(verification)
    
    return code

def send_sms_code(phone, code):
    """
    Отправляет SMS с кодом подтверждения
    """
    from app.services.sms_service import send_verification_code
    
    # Отправляем код через выбранный SMS-провайдер
    success, message = send_verification_code(phone, code)
    
    # Логируем результат
    if success:
        print(f"[SMS ОТПРАВЛЕНО] {message}")
    else:
        print(f"[ОШИБКА ОТПРАВКИ SMS] {message}")
    
    return success

def verify_phone_code(db, phone, code):
    """
    Проверяет правильность кода подтверждения
    """
    verification = db.query(PhoneVerification).filter(
        PhoneVerification.phone == phone,
        PhoneVerification.is_verified == False,
        PhoneVerification.expires_at > datetime.utcnow()
    ).first()
    
    if not verification:
        return False, "Код подтверждения не найден или истек срок его действия"
    
    # Увеличиваем счетчик попыток
    verification.attempts += 1
    db.commit()
    
    # Если слишком много попыток, блокируем
    if verification.attempts > 5:
        return False, "Превышено количество попыток. Запросите новый код"
    
    # Проверяем сам код
    if verification.code != code:
        return False, "Неверный код подтверждения"
    
    # Помечаем верификацию как успешную
    verification.is_verified = True
    db.commit()
    
    return True, "Номер телефона успешно подтвержден"

# Добавление защиты от атак через публичный туннель
class ServeoSecurity:
    """
    Класс для обеспечения дополнительной безопасности при работе через публичный туннель
    """
    
    @staticmethod
    def is_serveo_request(request) -> bool:
        """
        Проверяет, является ли запрос направленным через Serveo
        """
        host = request.headers.get("host", "")
        return "serveo.net" in host
    
    @staticmethod
    def limit_admin_access(request) -> bool:
        """
        Ограничивает доступ к административным функциям через Serveo
        только для определенных IP-адресов
        """
        # Если запрос не через Serveo, разрешаем (будет проверка обычной авторизации)
        if not ServeoSecurity.is_serveo_request(request):
            return True
            
        # Для Serveo проверяем IP клиента
        client_ip = request.headers.get("x-forwarded-for") or request.client.host
        
        # Белый список IP для доступа к админке через Serveo (из файла)
        whitelist_file = "admin_ip_whitelist.txt"
        
        try:
            if os.path.exists(whitelist_file):
                with open(whitelist_file, "r") as f:
                    whitelist = [line.strip() for line in f.readlines() if line.strip()]
                    
                # Если IP в белом списке, разрешаем доступ
                if client_ip in whitelist:
                    return True
        except Exception as e:
            logging.error(f"Ошибка при проверке белого списка IP: {str(e)}")
        
        # По умолчанию запрещаем доступ к админке через Serveo
        return False
    
    @staticmethod
    def check_rate_limit(request, limit_key: str, max_requests: int = 10, per_minutes: int = 1) -> bool:
        """
        Проверяет ограничение скорости запросов для защиты от брутфорса и DoS
        """
        # Если запрос не через Serveo, не ограничиваем
        if not ServeoSecurity.is_serveo_request(request):
            return True
            
        # Получаем IP клиента
        client_ip = request.headers.get("x-forwarded-for") or request.client.host
        
        # Создаем ключ для Redis
        redis_key = f"ratelimit:{limit_key}:{client_ip}"
        
        # Используем Redis для отслеживания количества запросов
        try:
            from app.database import redis_client
            
            # Получаем текущее значение счетчика
            count = redis_client.get(redis_key)
            
            if count is None:
                # Если счетчик не существует, создаем новый
                redis_client.set(redis_key, 1, ex=per_minutes*60)
                return True
            
            # Увеличиваем счетчик
            count = int(count) + 1
            redis_client.set(redis_key, count, keepttl=True)
            
            # Проверяем превышение лимита
            if count > max_requests:
                logging.warning(f"Превышен лимит запросов: {limit_key} от {client_ip}, {count}/{max_requests}")
                return False
                
            return True
        except Exception as e:
            logging.error(f"Ошибка при проверке ограничения скорости: {str(e)}")
            # В случае ошибки разрешаем запрос
            return True 