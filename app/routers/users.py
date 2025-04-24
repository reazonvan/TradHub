from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional, Dict, Any
import os
import shutil
from uuid import uuid4
from datetime import datetime, timedelta
import pytz

from app.database import get_db
from app.models.user import User, UserRole
from app.models.order import Order, Review
from app.models.product import Product
from app.schemas.user import User as UserSchema, UserUpdate, UserCreate, UserResponse
from app.security import get_current_user, get_current_admin, get_password_hash, verify_password, check_password_strength
from app.config import settings
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# === API маршруты ===

@router.get("/", response_model=List[UserSchema])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение списка пользователей (только для администраторов)
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserSchema)
async def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации о пользователе по ID
    """
    # Обычные пользователи могут видеть только себя
    if current_user.role != UserRole.ADMIN.value and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра информации о другом пользователе"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return user

@router.put("/me", response_model=UserSchema)
async def update_user_me(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновление информации о текущем пользователе
    """
    # Проверка email на уникальность, если он указан
    if user_data.email and user_data.email != current_user.email:
        db_user = db.query(User).filter(User.email == user_data.email).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )
    
    # Обновляем поля пользователя
    for key, value in user_data.dict(exclude_unset=True).items():
        setattr(current_user, key, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/me/avatar", response_model=UserSchema)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Загрузка аватара пользователя
    """
    # Проверка размера файла
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Размер файла превышает максимально допустимый ({settings.MAX_UPLOAD_SIZE} байт)"
        )
    
    # Проверка типа файла
    content_type = file.content_type
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Файл должен быть изображением"
        )
    
    # Создаем директорию для загрузок, если она не существует
    upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Создаем уникальное имя файла
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    # Удаляем старый аватар, если он есть
    if current_user.avatar:
        old_avatar_path = os.path.join(settings.UPLOAD_DIR, current_user.avatar)
        if os.path.exists(old_avatar_path):
            os.remove(old_avatar_path)
    
    # Обновляем путь к аватару в базе данных
    relative_path = os.path.join("avatars", unique_filename)
    current_user.avatar = relative_path
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/me/become-seller", response_model=UserSchema)
async def become_seller(
    description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Переход пользователя в статус продавца
    """
    # Проверка, что пользователь еще не продавец
    if current_user.role == UserRole.SELLER.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь уже является продавцом"
        )
    
    # Обновляем роль и описание пользователя
    current_user.role = UserRole.SELLER.value
    current_user.seller_description = description
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя
    """
    # Проверяем существование пользователя
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )
    
    # Проверяем сложность пароля
    if not check_password_strength(user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать минимум 8 символов, заглавные и строчные буквы, цифры и спецсимволы"
        )
    
    # Создаем нового пользователя
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# === HTML маршруты для браузера ===

@router.get("/profile", response_class=HTMLResponse)
async def user_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Страница профиля пользователя
    """
    # Подготавливаем дополнительные данные для профиля
    context = {"request": request, "user": current_user}
    
    # Если пользователь является продавцом, добавляем статистику
    if current_user.role == UserRole.SELLER.value:
        # Количество активных товаров
        active_products = db.query(func.count(Product.id)).filter(
            Product.seller_id == current_user.id,
            Product.is_active == True
        ).scalar()
        
        # Количество завершенных заказов
        completed_orders = db.query(func.count(Order.id)).filter(
            Order.seller_id == current_user.id,
            Order.status == "completed"
        ).scalar()
        
        # Количество продаж
        sales_count = db.query(func.count(Order.id)).filter(
            Order.seller_id == current_user.id,
            Order.status.in_(["completed", "delivered"])
        ).scalar()
        
        # Количество отзывов
        reviews_count = db.query(func.count(Review.id)).filter(
            Review.seller_id == current_user.id
        ).scalar()
        
        context.update({
            "active_products": active_products,
            "completed_orders": completed_orders,
            "sales_count": sales_count,
            "reviews_count": reviews_count
        })
    
    # Добавляем историю активности (пример, в реальном приложении нужна модель для логирования)
    # Здесь просто создаем примеры действий
    activity_log = []
    
    # Последние заказы пользователя как покупателя
    recent_orders = db.query(Order).filter(
        Order.buyer_id == current_user.id
    ).order_by(desc(Order.created_at)).limit(3).all()
    
    for order in recent_orders:
        activity_log.append({
            "timestamp": order.created_at,
            "description": f"Создан заказ №{order.id} на сумму {order.total_amount}",
            "type": "Заказ",
            "color": "#4e73df"  # синий
        })
    
    # Если продавец, добавляем информацию о продажах
    if current_user.role == UserRole.SELLER.value:
        recent_sales = db.query(Order).filter(
            Order.seller_id == current_user.id
        ).order_by(desc(Order.created_at)).limit(3).all()
        
        for sale in recent_sales:
            activity_log.append({
                "timestamp": sale.created_at,
                "description": f"Получен заказ №{sale.id} от покупателя",
                "type": "Продажа",
                "color": "#1cc88a"  # зеленый
            })
    
    # Сортируем все действия по времени
    activity_log.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Ограничиваем количество записей
    activity_log = activity_log[:5]
    
    context["activity_log"] = activity_log
    
    return templates.TemplateResponse("account/profile.html", context)

@router.get("/profile/edit", response_class=HTMLResponse)
async def update_user_profile_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Страница редактирования профиля пользователя
    """
    return templates.TemplateResponse(
        "account/edit_profile.html", 
        {"request": request, "user": current_user}
    )

@router.post("/profile/edit", response_class=HTMLResponse)
async def update_user_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обработка формы редактирования профиля
    """
    form = await request.form()
    email = form.get("email")
    full_name = form.get("full_name")
    phone = form.get("phone")
    seller_description = form.get("seller_description")
    
    # Проверяем email на уникальность
    if email and email != current_user.email:
        db_user = db.query(User).filter(User.email == email).first()
        if db_user:
            return templates.TemplateResponse(
                "account/edit_profile.html", 
                {
                    "request": request, 
                    "user": current_user, 
                    "error": "Пользователь с таким email уже существует"
                }
            )
    
    # Проверяем телефон на уникальность
    if phone and phone != current_user.phone:
        if not phone.startswith('+') or not phone[1:].isdigit():
            return templates.TemplateResponse(
                "account/edit_profile.html", 
                {
                    "request": request, 
                    "user": current_user, 
                    "error": "Укажите телефон в международном формате, например +7XXXXXXXXXX"
                }
            )
        
        db_user = db.query(User).filter(User.phone == phone).first()
        if db_user:
            return templates.TemplateResponse(
                "account/edit_profile.html", 
                {
                    "request": request, 
                    "user": current_user, 
                    "error": "Пользователь с таким номером телефона уже существует"
                }
            )
    
    # Обновляем данные пользователя
    current_user.email = email
    current_user.full_name = full_name
    current_user.phone = phone
    
    if current_user.role == UserRole.SELLER.value and seller_description:
        current_user.seller_description = seller_description
    
    db.commit()
    db.refresh(current_user)
    
    return templates.TemplateResponse(
        "account/edit_profile.html", 
        {
            "request": request, 
            "user": current_user, 
            "success": "Профиль успешно обновлен"
        }
    )

@router.post("/profile/avatar", response_class=HTMLResponse)
async def upload_avatar_browser(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Загрузка аватара пользователя через браузер
    """
    try:
        # Проверка размера файла
        file_size = 0
        contents = await file.read()
        file_size = len(contents)
        await file.seek(0)
        
        if file_size > settings.MAX_UPLOAD_SIZE:
            return templates.TemplateResponse(
                "account/edit_profile.html", 
                {
                    "request": request, 
                    "user": current_user, 
                    "error": f"Размер файла превышает максимально допустимый ({settings.MAX_UPLOAD_SIZE / 1024 / 1024:.1f} МБ)"
                }
            )
        
        # Проверка типа файла
        content_type = file.content_type
        if not content_type.startswith("image/"):
            return templates.TemplateResponse(
                "account/edit_profile.html", 
                {
                    "request": request, 
                    "user": current_user, 
                    "error": "Файл должен быть изображением"
                }
            )
        
        # Создаем директорию для загрузок, если она не существует
        upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Создаем уникальное имя файла
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        # Удаляем старый аватар, если он есть
        if current_user.avatar:
            old_avatar_path = os.path.join(settings.UPLOAD_DIR, current_user.avatar)
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)
        
        # Обновляем путь к аватару в базе данных
        relative_path = os.path.join("avatars", unique_filename)
        current_user.avatar = relative_path
        db.commit()
        db.refresh(current_user)
        
        return templates.TemplateResponse(
            "account/edit_profile.html", 
            {
                "request": request, 
                "user": current_user, 
                "success": "Аватар успешно обновлен"
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "account/edit_profile.html", 
            {
                "request": request, 
                "user": current_user, 
                "error": f"Ошибка при загрузке аватара: {str(e)}"
            }
        )

@router.get("/profile/security", response_class=HTMLResponse)
async def user_security(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Страница безопасности профиля пользователя
    """
    # Здесь можно добавить получение списка сессий пользователя
    # В примере просто создадим фиктивные данные
    
    # Создаем примеры сессий
    sessions = [
        {
            "id": 1,
            "device": "Chrome на Windows",
            "device_icon": "desktop",
            "ip": "192.168.1.1",
            "location": "Москва, Россия",
            "created_at": datetime.now(pytz.UTC),
            "is_current": True
        },
        {
            "id": 2,
            "device": "Firefox на Mac",
            "device_icon": "laptop",
            "ip": "192.168.1.2",
            "location": "Санкт-Петербург, Россия",
            "created_at": datetime.now(pytz.UTC) - timedelta(days=1),
            "is_current": False
        },
        {
            "id": 3,
            "device": "Safari на iPhone",
            "device_icon": "mobile",
            "ip": "192.168.1.3",
            "location": "Екатеринбург, Россия",
            "created_at": datetime.now(pytz.UTC) - timedelta(days=2),
            "is_current": False
        }
    ]
    
    return templates.TemplateResponse(
        "account/security.html", 
        {"request": request, "user": current_user, "sessions": sessions}
    )

@router.post("/profile/security/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обработка формы смены пароля
    """
    form = await request.form()
    current_password = form.get("current_password")
    new_password = form.get("new_password")
    confirm_password = form.get("confirm_password")
    
    # Проверяем текущий пароль
    if not verify_password(current_password, current_user.hashed_password):
        return templates.TemplateResponse(
            "account/security.html", 
            {
                "request": request, 
                "user": current_user, 
                "password_error": "Неверный текущий пароль"
            }
        )
    
    # Проверяем совпадение паролей
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "account/security.html", 
            {
                "request": request, 
                "user": current_user, 
                "password_error": "Пароли не совпадают"
            }
        )
    
    # Проверяем сложность пароля
    if len(new_password) < 8:
        return templates.TemplateResponse(
            "account/security.html", 
            {
                "request": request, 
                "user": current_user, 
                "password_error": "Пароль должен быть не менее 8 символов"
            }
        )
    
    if not any(c.isupper() for c in new_password):
        return templates.TemplateResponse(
            "account/security.html", 
            {
                "request": request, 
                "user": current_user, 
                "password_error": "Пароль должен содержать хотя бы одну заглавную букву"
            }
        )
    
    if not any(c.isdigit() for c in new_password):
        return templates.TemplateResponse(
            "account/security.html", 
            {
                "request": request, 
                "user": current_user, 
                "password_error": "Пароль должен содержать хотя бы одну цифру"
            }
        )
    
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' for c in new_password):
        return templates.TemplateResponse(
            "account/security.html", 
            {
                "request": request, 
                "user": current_user, 
                "password_error": "Пароль должен содержать хотя бы один специальный символ"
            }
        )
    
    # Обновляем пароль
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return templates.TemplateResponse(
        "account/security.html", 
        {
            "request": request, 
            "user": current_user, 
            "password_success": "Пароль успешно изменен"
        }
    )

@router.post("/profile/security/2fa/enable", response_class=HTMLResponse)
async def enable_2fa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Включение двухфакторной аутентификации
    """
    # В реальном приложении здесь была бы логика генерации и сохранения секрета 2FA
    # и отображения QR-кода для сканирования
    
    # Для примера просто включаем флаг
    current_user.two_factor_enabled = True
    current_user.two_factor_secret = "some_secret_key"  # В реальном приложении здесь был бы настоящий секрет
    db.commit()
    
    return templates.TemplateResponse(
        "account/security.html", 
        {
            "request": request, 
            "user": current_user, 
            "tfa_success": "Двухфакторная аутентификация успешно включена"
        }
    )

@router.post("/profile/security/2fa/disable", response_class=HTMLResponse)
async def disable_2fa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отключение двухфакторной аутентификации
    """
    form = await request.form()
    password = form.get("password")
    
    # Проверяем пароль
    if not verify_password(password, current_user.hashed_password):
        return templates.TemplateResponse(
            "account/security.html", 
            {
                "request": request, 
                "user": current_user, 
                "tfa_error": "Неверный пароль"
            }
        )
    
    # Отключаем 2FA
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    db.commit()
    
    return templates.TemplateResponse(
        "account/security.html", 
        {
            "request": request, 
            "user": current_user, 
            "tfa_success": "Двухфакторная аутентификация отключена"
        }
    )

@router.post("/profile/security/sessions/{session_id}/terminate", response_class=HTMLResponse)
async def terminate_session(
    request: Request,
    session_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Завершение сессии пользователя
    """
    # В реальном приложении здесь была бы логика завершения конкретной сессии
    
    return templates.TemplateResponse(
        "account/security.html", 
        {
            "request": request, 
            "user": current_user,
            "sessions": [],  # Здесь нужно вернуть обновленный список сессий
            "tfa_success": "Сеанс успешно завершен"
        }
    )

@router.post("/profile/security/sessions/terminate-all", response_class=HTMLResponse)
async def terminate_all_sessions(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Завершение всех сессий пользователя кроме текущей
    """
    # В реальном приложении здесь была бы логика завершения всех сессий кроме текущей
    
    return templates.TemplateResponse(
        "account/security.html", 
        {
            "request": request, 
            "user": current_user,
            "sessions": [
                {
                    "id": 1,
                    "device": "Chrome на Windows",
                    "device_icon": "desktop",
                    "ip": "192.168.1.1",
                    "location": "Москва, Россия",
                    "created_at": datetime.now(pytz.UTC),
                    "is_current": True
                }
            ],
            "tfa_success": "Все сеансы успешно завершены"
        }
    )

@router.get("/profile/become-seller", response_class=HTMLResponse)
async def become_seller_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Страница для перехода в статус продавца
    """
    # Проверяем, не является ли пользователь уже продавцом
    if current_user.role == UserRole.SELLER.value:
        return RedirectResponse(url="/users/profile", status_code=status.HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse(
        "account/become_seller.html", 
        {"request": request, "user": current_user}
    )

@router.post("/profile/become-seller", response_class=HTMLResponse)
async def become_seller_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обработка формы перехода в статус продавца
    """
    form = await request.form()
    description = form.get("description")
    
    # Проверяем, не является ли пользователь уже продавцом
    if current_user.role == UserRole.SELLER.value:
        return RedirectResponse(url="/users/profile", status_code=status.HTTP_303_SEE_OTHER)
    
    # Проверяем наличие описания
    if not description or len(description.strip()) < 10:
        return templates.TemplateResponse(
            "account/become_seller.html", 
            {
                "request": request, 
                "user": current_user,
                "error": "Описание должно содержать не менее 10 символов"
            }
        )
    
    # Обновляем роль и описание пользователя
    current_user.role = UserRole.SELLER.value
    current_user.seller_description = description
    
    db.commit()
    db.refresh(current_user)
    
    # Перенаправляем на страницу профиля с сообщением об успехе
    return RedirectResponse(url="/users/profile", status_code=status.HTTP_303_SEE_OTHER) 