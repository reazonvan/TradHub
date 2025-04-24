from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import Optional
import re
import json

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, User as UserSchema, Token
from app.security import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, create_password_reset_token, verify_password_reset_token,
    create_phone_verification, send_sms_code, verify_phone_code
)
from app.config import settings
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# === HTML маршруты для браузера ===

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Страница входа в систему
    """
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Обработка формы входа
    """
    # Поиск пользователя по email или имени пользователя
    user = db.query(User).filter(
        (User.email == username) | (User.username == username)
    ).first()
    
    # Проверка пользователя и пароля
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/login.html", 
            {"request": request, "error": "Неверный email/имя пользователя или пароль"}
        )
    
    # Проверка активности пользователя
    if not user.is_active:
        return templates.TemplateResponse(
            "auth/login.html", 
            {"request": request, "error": "Аккаунт неактивен"}
        )
    
    # Обновляем время последнего входа
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Данные для JWT токена
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_data = {
        "sub": user.username,
        "id": user.id,
        "role": user.role
    }
    
    # Создание токена
    access_token = create_access_token(
        data=access_token_data,
        expires_delta=access_token_expires
    )
    
    # Создаем редирект на главную с установкой cookie
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE,
        samesite="lax"
    )
    
    # Добавляем сообщение об успешном входе (через flash messages или другой механизм)
    print(f"Пользователь {user.username} успешно вошел в систему.")
    
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Страница регистрации нового пользователя
    """
    return templates.TemplateResponse("auth/register.html", {"request": request})

@router.post("/register", response_class=HTMLResponse)
async def register_submit(request: Request, db: Session = Depends(get_db)):
    """
    Обработка формы регистрации
    """
    try:
        # Получаем данные формы вручную
        form_data = await request.form()
        print(f"Полученные данные формы: {dict(form_data)}")
        
        # Извлекаем данные
        username = form_data.get("username", "")
        email = form_data.get("email", "")
        password = form_data.get("password", "")
        password_confirm = form_data.get("password_confirm", "")
        phone = form_data.get("phone", "")
        terms = form_data.get("terms", "off") == "on"
        phone_verified = form_data.get("phone_verified") == "true"
        
        # Сохраняем данные для возврата при ошибке
        saved_data = {"username": username, "email": email, "phone": phone}
        
        # Проверки:
        # 1. Все поля заполнены
        if not (username and email and password and password_confirm and phone):
            return templates.TemplateResponse(
                "auth/register.html", 
                {"request": request, "error": "Все поля должны быть заполнены", "form_data": saved_data}
            )
        
        # 2. Согласие с условиями
        if not terms:
            return templates.TemplateResponse(
                "auth/register.html", 
                {"request": request, "error": "Необходимо принять условия использования", "form_data": saved_data}
            )
        
        # 3. Проверка формата имени пользователя
        if not re.match(r"^[a-zA-Z0-9_-]{3,20}$", username):
            return templates.TemplateResponse(
                "auth/register.html", 
                {"request": request, "error": "Имя пользователя должно содержать от 3 до 20 символов (буквы, цифры, - и _)", "form_data": saved_data}
            )
        
        # 4. Проверка совпадения паролей
        if password != password_confirm:
            return templates.TemplateResponse(
                "auth/register.html", 
                {"request": request, "error": "Пароли не совпадают", "form_data": saved_data}
            )
        
        # 5. Проверка формата телефона
        if not phone.startswith('+') or not phone[1:].isdigit():
            return templates.TemplateResponse(
                "auth/register.html", 
                {"request": request, "error": "Укажите телефон в международном формате, например +7XXXXXXXXXX", "form_data": saved_data}
            )
        
        # 6. Проверка подтверждения телефона
        if not phone_verified:
            return templates.TemplateResponse(
                "auth/register.html", 
                {"request": request, "error": "Необходимо подтвердить номер телефона", "form_data": saved_data}
            )
        
        # 7. Проверка наличия пользователя с таким email
        db_user_email = db.query(User).filter(User.email == email).first()
        if db_user_email:
            return templates.TemplateResponse(
                "auth/register.html", 
                {"request": request, "error": "Пользователь с таким email уже существует", "form_data": saved_data}
            )
        
        # 8. Проверка наличия пользователя с таким username
        db_user_username = db.query(User).filter(User.username == username).first()
        if db_user_username:
            return templates.TemplateResponse(
                "auth/register.html", 
                {"request": request, "error": "Пользователь с таким именем уже существует", "form_data": saved_data}
            )
        
        # 9. Проверка наличия пользователя с таким телефоном
        db_user_phone = db.query(User).filter(User.phone == phone).first()
        if db_user_phone:
            return templates.TemplateResponse(
                "auth/register.html", 
                {"request": request, "error": "Пользователь с таким номером телефона уже существует", "form_data": saved_data}
            )
        
        # Создаем хеш пароля
        hashed_password = get_password_hash(password)
        
        # Создаем нового пользователя
        db_user = User(
            email=email,
            username=username,
            full_name=username,  # Используем никнейм вместо полного имени
            phone=phone,
            phone_verified=True,  # Телефон уже подтвержден
            hashed_password=hashed_password,
            role=UserRole.BUYER.value
        )
        
        # Сохраняем пользователя в базу данных
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Перенаправляем на страницу входа с сообщением об успехе
        return templates.TemplateResponse(
            "auth/login.html", 
            {
                "request": request, 
                "success": "Регистрация прошла успешно! Теперь вы можете войти в свой аккаунт."
            }
        )
    except Exception as e:
        print(f"Ошибка при обработке регистрации: {e}")
        return templates.TemplateResponse(
            "auth/register.html", 
            {"request": request, "error": f"Произошла ошибка при регистрации: {str(e)}"}
        )

@router.get("/verify-phone", response_class=HTMLResponse)
async def verify_phone_page(request: Request, phone: str = Query(...)):
    """
    Страница подтверждения номера телефона
    """
    return templates.TemplateResponse("auth/verify-phone.html", {"request": request, "phone": phone})

@router.post("/verify-phone", response_class=HTMLResponse)
async def verify_phone_submit(
    request: Request,
    phone: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Обработка формы подтверждения телефона
    """
    # Проверяем код
    is_valid, message = verify_phone_code(db, phone, code)
    
    if not is_valid:
        return templates.TemplateResponse(
            "auth/verify-phone.html", 
            {"request": request, "phone": phone, "error": message}
        )
    
    # Получаем данные регистрации из cookie
    registration_data = request.cookies.get("registration_data")
    if not registration_data:
        return templates.TemplateResponse(
            "auth/verify-phone.html", 
            {"request": request, "phone": phone, "error": "Данные регистрации не найдены. Пожалуйста, зарегистрируйтесь заново."}
        )
    
    try:
        reg_data = json.loads(registration_data)
        
        # Создаем нового пользователя
        db_user = User(
            email=reg_data["email"],
            username=reg_data["username"],
            full_name=reg_data["username"],  # Используем никнейм вместо полного имени
            phone=phone,
            phone_verified=True,  # Телефон подтвержден
            hashed_password=reg_data["password"],
            role=UserRole.BUYER.value
        )
        
        # Сохраняем пользователя в базу данных
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Возвращаем успешный ответ с перенаправлением на страницу входа
        response = templates.TemplateResponse(
            "auth/verify-phone.html", 
            {
                "request": request, 
                "phone": phone, 
                "success": "Ваш номер телефона подтвержден, и регистрация успешно завершена! Теперь вы можете войти в систему."
            }
        )
        
        # Удаляем временные данные из cookie
        response.delete_cookie(key="registration_data")
        
        return response
        
    except Exception as e:
        print(f"Ошибка при создании пользователя: {str(e)}")
        return templates.TemplateResponse(
            "auth/verify-phone.html", 
            {"request": request, "phone": phone, "error": f"Произошла ошибка при создании пользователя: {str(e)}"}
        )

@router.get("/resend-code", response_class=RedirectResponse)
async def resend_code(
    request: Request,
    phone: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Повторная отправка SMS-кода
    """
    # Генерируем и отправляем новый код
    code = create_phone_verification(db, phone)
    send_sms_code(phone, code)
    
    # Перенаправляем на страницу верификации
    return RedirectResponse(url=f"/auth/verify-phone?phone={phone}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/check-username", response_class=PlainTextResponse)
async def check_username(
    username: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Проверка доступности имени пользователя
    """
    if len(username) < 3:
        return '<span class="text-red-500">Имя пользователя должно содержать не менее 3 символов</span>'
    
    user = db.query(User).filter(User.username == username).first()
    if user:
        return '<span class="text-red-500">Это имя пользователя уже занято</span>'
    
    return '<span class="text-green-500">Имя пользователя доступно</span>'

@router.get("/check-email", response_class=PlainTextResponse)
async def check_email(
    email: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Проверка доступности email
    """
    user = db.query(User).filter(User.email == email).first()
    if user:
        return '<span class="text-red-500">Этот email уже используется</span>'
    
    return '<span class="text-green-500">Email доступен</span>'

@router.get("/check-phone", response_class=PlainTextResponse)
async def check_phone(
    phone: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Проверка доступности номера телефона
    """
    # Проверяем формат телефона
    if not phone.startswith('+') or not phone[1:].isdigit():
        return '<span class="text-red-500">Укажите телефон в международном формате, например +7XXXXXXXXXX</span>'
        
    # Проверяем, что для российского номера после +7 ровно 10 цифр
    if phone.startswith('+7') and len(phone) != 12:
        return '<span class="text-red-500">Номер телефона должен содержать 10 цифр после +7</span>'
    
    user = db.query(User).filter(User.phone == phone).first()
    if user:
        return '<span class="text-red-500">Этот номер телефона уже используется</span>'
    
    return '<span class="text-green-500">Номер телефона доступен</span>'

@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """
    Страница запроса сброса пароля
    """
    return templates.TemplateResponse("auth/reset-password.html", {"request": request})

@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Обработка формы запроса сброса пароля
    """
    # Находим пользователя по email
    user = db.query(User).filter(User.email == email).first()
    
    # Если пользователь найден, создаем токен для сброса пароля
    # На фронтенде не показываем разный результат для безопасности
    if user:
        # Создание токена для сброса пароля
        reset_token = create_password_reset_token(user.email)
        
        # Здесь должна быть логика отправки email с токеном сброса пароля
        # В текущей реализации просто покажем успешное сообщение
        
        # Полная ссылка для сброса пароля (в реальной системе отправлять по email)
        reset_link = f"{settings.SITE_URL}/auth/set-new-password?token={reset_token}"
        
        # В реальном приложении здесь должен быть код отправки письма
        print(f"Ссылка для сброса пароля: {reset_link}")
    
    # Показываем сообщение об успешной отправке независимо от результата (защита от перебора)
    return templates.TemplateResponse(
        "auth/reset-password.html", 
        {
            "request": request, 
            "success": "Инструкции по сбросу пароля отправлены на указанный email (если он зарегистрирован в системе)"
        }
    )

@router.get("/set-new-password", response_class=HTMLResponse)
async def set_new_password_page(
    request: Request,
    token: str
):
    """
    Страница установки нового пароля после сброса
    """
    # Проверяем валидность токена (без расшифровки email)
    try:
        verify_password_reset_token(token)
    except:
        return templates.TemplateResponse(
            "auth/reset-password.html", 
            {"request": request, "error": "Недействительная или истекшая ссылка сброса пароля"}
        )
    
    return templates.TemplateResponse(
        "auth/set-new-password.html", 
        {"request": request, "reset_token": token}
    )

@router.post("/set-new-password", response_class=HTMLResponse)
async def set_new_password_submit(
    request: Request,
    reset_token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Обработка формы установки нового пароля
    """
    # Проверка совпадения паролей
    if password != password_confirm:
        return templates.TemplateResponse(
            "auth/set-new-password.html", 
            {"request": request, "reset_token": reset_token, "error": "Пароли не совпадают"}
        )
    
    # Проверяем токен и получаем email пользователя
    try:
        email = verify_password_reset_token(reset_token)
    except:
        return templates.TemplateResponse(
            "auth/reset-password.html", 
            {"request": request, "error": "Недействительная или истекшая ссылка сброса пароля"}
        )
    
    # Находим пользователя по email
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse(
            "auth/reset-password.html", 
            {"request": request, "error": "Пользователь не найден"}
        )
    
    # Создаем новый хеш пароля и обновляем пользователя
    hashed_password = get_password_hash(password)
    user.hashed_password = hashed_password
    db.commit()
    
    # Перенаправляем на страницу входа с сообщением об успехе
    return RedirectResponse(
        url="/auth/login", 
        status_code=status.HTTP_303_SEE_OTHER
    )

@router.get("/logout")
async def logout():
    """
    Выход из системы
    """
    # Создаем редирект на главную
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Удаляем cookie с токеном авторизации
    response.delete_cookie(key="access_token")
    
    # Для гарантированного удаления, устанавливаем в пустую строку и отрицательное max_age
    response.set_cookie(
        key="access_token",
        value="",
        expires=0,
        max_age=0,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax"
    )
    
    print("Пользователь вышел из системы.")
    
    return response

# === API маршруты для JSON ответов ===

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Получение JWT токена для аутентификации через API
    """
    # Поиск пользователя по email или имени пользователя
    user = db.query(User).filter(
        (User.email == form_data.username) | (User.username == form_data.username)
    ).first()
    
    # Проверка пользователя и пароля
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email/имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверка активности пользователя
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт неактивен"
        )
    
    # Обновляем время последнего входа
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Данные для JWT токена
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_data = {
        "sub": user.username,
        "id": user.id,
        "role": user.role
    }
    
    # Создание токена
    access_token = create_access_token(
        data=access_token_data,
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserSchema)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Регистрация нового пользователя через API
    """
    # Проверка наличия пользователя с таким email
    db_user_email = db.query(User).filter(User.email == user_data.email).first()
    if db_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    # Проверка наличия пользователя с таким username
    db_user_username = db.query(User).filter(User.username == user_data.username).first()
    if db_user_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )
    
    # Проверка наличия пользователя с таким номером телефона
    if user_data.phone:
        db_user_phone = db.query(User).filter(User.phone == user_data.phone).first()
        if db_user_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким номером телефона уже существует"
            )
    
    # Создаем хеш пароля
    hashed_password = get_password_hash(user_data.password)
    
    # Создаем нового пользователя
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.username,  # Используем никнейм вместо полного имени
        phone=user_data.phone,
        hashed_password=hashed_password,
        role=UserRole.BUYER.value
    )
    
    # Сохраняем пользователя в базу данных
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе
    """
    return current_user

# Тестовый маршрут для отправки SMS
@router.get("/test-sms", response_class=HTMLResponse)
async def test_sms_page(request: Request, current_user: User = Depends(get_current_user)):
    """
    Страница для тестирования отправки SMS
    Требует аутентификации и прав администратора
    """
    # Проверяем, что пользователь - администратор
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права администратора."
        )
    
    return templates.TemplateResponse("auth/test-sms.html", {"request": request})

@router.post("/test-sms", response_class=HTMLResponse)
async def test_sms_submit(
    request: Request,
    phone: str = Form(...),
    message: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """
    Обработка формы тестирования отправки SMS
    Требует аутентификации и прав администратора
    """
    # Проверяем, что пользователь - администратор
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права администратора."
        )
    
    from app.services.sms_service import get_sms_provider
    
    # Получаем провайдера SMS
    provider = get_sms_provider()
    
    # Отправляем SMS
    success, message_result = provider.send_message(phone, message)
    
    context = {
        "request": request,
        "success": message_result if success else None,
        "error": message_result if not success else None
    }
    
    return templates.TemplateResponse("auth/test-sms.html", context)

@router.post("/send-verification-code", response_class=PlainTextResponse)
async def send_verification_code(
    phone: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Отправляет код подтверждения на номер телефона без регистрации пользователя
    """
    # Проверка формата телефона
    if not phone.startswith('+') or not phone[1:].isdigit():
        return "ERROR: Укажите телефон в международном формате, например +7XXXXXXXXXX"
    
    # Проверка, не занят ли уже номер
    db_user_phone = db.query(User).filter(User.phone == phone).first()
    if db_user_phone:
        return "ERROR: Пользователь с таким номером телефона уже существует"
    
    # Генерируем и отправляем SMS-код
    from app.security import create_phone_verification, send_sms_code
    
    try:
        code = create_phone_verification(db, phone)
        success = send_sms_code(phone, code)
        
        if success:
            return "OK: Код подтверждения отправлен на ваш номер телефона"
        else:
            return "ERROR: Не удалось отправить код подтверждения. Пожалуйста, попробуйте позже"
    
    except Exception as e:
        print(f"Ошибка при отправке кода: {str(e)}")
        return f"ERROR: Произошла ошибка при отправке кода: {str(e)}"

@router.post("/verify-code", response_class=PlainTextResponse)
async def verify_code_endpoint(
    phone: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Проверяет код подтверждения номера телефона
    """
    from app.security import verify_phone_code
    
    try:
        is_valid, message = verify_phone_code(db, phone, code)
        
        if is_valid:
            return "OK: Код подтверждения верный. Номер телефона подтвержден"
        else:
            return f"ERROR: {message}"
    
    except Exception as e:
        print(f"Ошибка при проверке кода: {str(e)}")
        return f"ERROR: Произошла ошибка при проверке кода: {str(e)}" 