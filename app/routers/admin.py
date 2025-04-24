from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import sqlalchemy as sa
import enum

from app.database import get_db
from app.models.user import User, UserRole
from app.models.product import Product, ProductStatus, ProductImage, ModerationHistory, ModerationAction
from app.models.order import Order, OrderStatus
from app.schemas.user import User as UserSchema
from app.schemas.product import ProductDetail
from app.schemas.order import OrderDetail
from app.security import get_current_admin

router = APIRouter()

# Добавим модель для истории модерации
class ModerationAction(str, enum.Enum):
    """
    Перечисление действий модерации
    """
    APPROVED = "approved"
    REJECTED = "rejected"
    REVERTED = "reverted"
    EDITED = "edited"

@router.get("/users", response_model=List[UserSchema])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение списка всех пользователей для администратора
    """
    query = db.query(User)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            sa.or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term),
                User.full_name.ilike(search_term)
            )
        )
    
    users = query.offset(skip).limit(limit).all()
    return users

@router.put("/users/{user_id}/activate", response_model=UserSchema)
async def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Активация пользователя
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    user.is_active = True
    db.commit()
    db.refresh(user)
    
    return user

@router.put("/users/{user_id}/deactivate", response_model=UserSchema)
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Деактивация пользователя
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Проверка, что это не единственный администратор
    if user.role == UserRole.ADMIN.value:
        admin_count = db.query(User).filter(User.role == UserRole.ADMIN.value, User.is_active == True).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя деактивировать последнего администратора"
            )
    
    user.is_active = False
    db.commit()
    db.refresh(user)
    
    return user

@router.put("/users/{user_id}/make-admin", response_model=UserSchema)
async def make_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Назначение пользователя администратором
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    user.role = UserRole.ADMIN.value
    db.commit()
    db.refresh(user)
    
    return user

@router.get("/products/moderation", response_class=HTMLResponse)
async def get_moderation_page(
    request: Request,
    status: str = "moderation",
    page: int = 1,
    limit: int = 12,
    search: str = None,
    game_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Страница модерации предметов с фильтрами
    """
    from app.main import templates
    
    # Базовый запрос
    query = db.query(Product)
    
    # Фильтрация по статусу
    if status == "moderation":
        query = query.filter(Product.status == ProductStatus.MODERATION.value)
    elif status == "active":
        query = query.filter(Product.status == ProductStatus.ACTIVE.value)
    elif status == "hidden":
        query = query.filter(Product.status == ProductStatus.HIDDEN.value)
    
    # Поиск по названию или продавцу
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            sa.or_(
                Product.title.ilike(search_term),
                Product.description.ilike(search_term),
                sa.and_(
                    Product.seller_id == User.id,
                    User.username.ilike(search_term)
                )
            )
        )
    
    # Фильтрация по игре/категории
    if game_id:
        from app.models.product import Category
        query = query.join(Product.categories).filter(Category.id == game_id)
    
    # Общее количество для пагинации
    total_count = query.count()
    
    # Сортировка и пагинация
    query = query.order_by(Product.created_at.desc())
    items = query.offset((page - 1) * limit).limit(limit).all()
    
    # Добавляем текстовый статус и класс бейджа
    for item in items:
        if item.status == ProductStatus.MODERATION.value:
            item.status_text = "На модерации"
            item.status_badge = "moderation"
        elif item.status == ProductStatus.ACTIVE.value:
            item.status_text = "Одобрен"
            item.status_badge = "active"
        elif item.status == ProductStatus.HIDDEN.value:
            item.status_text = "Отклонен"
            item.status_badge = "hidden"
        else:
            item.status_text = "Неизвестно"
            item.status_badge = "secondary"
    
    # Получаем список игр для фильтра
    from app.models.product import Category
    games = db.query(Category).filter(Category.parent_id.is_(None)).all()
    
    # Создаем объект пагинации
    total_pages = (total_count + limit - 1) // limit  # Округление вверх
    
    pagination = {
        "page": page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_url": f"/admin/moderation?page={page-1}&status={status}&search={search or ''}&game_id={game_id or ''}",
        "next_url": f"/admin/moderation?page={page+1}&status={status}&search={search or ''}&game_id={game_id or ''}"
    }
    
    # Словарь фильтров для передачи в шаблон
    filters = {
        "status": status,
        "search": search,
        "game_id": str(game_id) if game_id else None
    }
    
    # Если это HTMX запрос, возвращаем только содержимое
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse("admin/moderation_items.html", {
            "request": request,
            "items": items,
            "pagination": pagination,
            "filters": filters,
            "games": games
        })
    
    # Иначе возвращаем полный шаблон
    return templates.TemplateResponse("admin/moderation.html", {
        "request": request,
        "items": items,
        "pagination": pagination,
        "filters": filters,
        "games": games
    })

@router.get("/products/filter", response_class=HTMLResponse)
async def filter_products(
    request: Request,
    status: str = "all",
    game: str = "all",
    search: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    AJAX-эндпоинт для фильтрации товаров
    """
    from app.main import templates
    
    # Базовый запрос
    query = db.query(Product)
    
    # Фильтрация по статусу
    if status == "moderation":
        query = query.filter(Product.status == ProductStatus.MODERATION.value)
    elif status == "active":
        query = query.filter(Product.status == ProductStatus.ACTIVE.value)
    elif status == "hidden":
        query = query.filter(Product.status == ProductStatus.HIDDEN.value)
    
    # Поиск по названию
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            sa.or_(
                Product.title.ilike(search_term),
                sa.and_(
                    Product.seller_id == User.id,
                    User.username.ilike(search_term)
                )
            )
        )
    
    # Фильтрация по игре
    if game and game != "all":
        from app.models.product import Category
        query = query.join(Product.categories).filter(Category.id == int(game))
    
    # Пагинация и сортировка
    query = query.order_by(Product.created_at.desc())
    items = query.limit(24).all()
    
    # Добавляем текстовый статус и класс бейджа
    for item in items:
        if item.status == ProductStatus.MODERATION.value:
            item.status_text = "На модерации"
            item.status_badge = "moderation"
        elif item.status == ProductStatus.ACTIVE.value:
            item.status_text = "Одобрен"
            item.status_badge = "active"
        elif item.status == ProductStatus.HIDDEN.value:
            item.status_text = "Отклонен"
            item.status_badge = "hidden"
        else:
            item.status_text = "Неизвестно"
            item.status_badge = "secondary"
    
    return templates.TemplateResponse("admin/moderation_items_partial.html", {
        "request": request,
        "items": items
    })

@router.get("/products/moderation/{product_id}/details", response_class=HTMLResponse)
async def get_product_moderation_details(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение детальной информации о предмете для модерации
    """
    from app.main import templates
    
    # Получаем предмет по ID
    item = db.query(Product).filter(Product.id == product_id).first()
    if not item:
        return HTMLResponse(content="<div class='p-6'>Предмет не найден</div>")
    
    # Статистика по продавцу
    seller_stats = {
        "pending_items": db.query(Product).filter(
            Product.seller_id == item.seller_id,
            Product.status == ProductStatus.MODERATION.value
        ).count(),
        "rejected_items": db.query(Product).filter(
            Product.seller_id == item.seller_id,
            Product.status == ProductStatus.HIDDEN.value
        ).count()
    }
    
    # Добавляем текстовый статус и класс бейджа
    if item.status == ProductStatus.MODERATION.value:
        item.status_text = "На модерации"
        item.status_badge = "warning"
    elif item.status == ProductStatus.ACTIVE.value:
        item.status_text = "Одобрен"
        item.status_badge = "primary"
    elif item.status == ProductStatus.HIDDEN.value:
        item.status_text = "Отклонен"
        item.status_badge = "danger"
    else:
        item.status_text = "Неизвестно"
        item.status_badge = "secondary"
    
    # Получаем историю модерации
    moderation_history = (
        db.query(ModerationHistory)
        .filter(ModerationHistory.product_id == product_id)
        .order_by(ModerationHistory.created_at.desc())
        .all()
    )
    
    # Формируем данные для отображения
    history_items = []
    for record in moderation_history:
        action_text = ""
        if record.action == ModerationAction.APPROVED.value:
            action_text = "Предмет одобрен"
        elif record.action == ModerationAction.REJECTED.value:
            action_text = "Предмет отклонен"
        elif record.action == ModerationAction.REVERTED.value:
            action_text = "Возвращен на модерацию"
        elif record.action == ModerationAction.EDITED.value:
            action_text = "Изменен модератором"
        
        history_items.append({
            "action": record.action,
            "action_text": action_text,
            "date": record.created_at,
            "admin": record.admin.username,
            "reason": record.reason,
            "comment": record.comment
        })
    
    return templates.TemplateResponse("admin/moderation_details.html", {
        "request": request,
        "item": item,
        "seller_stats": seller_stats,
        "moderation_history": history_items
    })

@router.put("/products/{product_id}/approve", response_model=ProductDetail)
async def approve_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Одобрение товара модератором
    """
    from app.main import templates
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар не найден"
        )
    
    product.status = ProductStatus.ACTIVE.value
    
    # Создаем запись в истории модерации
    moderation_record = ModerationHistory(
        product_id=product_id,
        admin_id=current_user.id,
        action=ModerationAction.APPROVED.value
    )
    db.add(moderation_record)
    
    db.commit()
    db.refresh(product)
    
    # Для HTMX запросов возвращаем обновленное представление
    if "HX-Request" in request.headers:
        return await get_product_moderation_details(request, product_id, db, current_user)
    
    return product

@router.put("/products/{product_id}/reject", response_model=ProductDetail)
async def reject_product(
    request: Request,
    product_id: int,
    reason: str = Form(...),
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Отклонение товара модератором
    """
    from app.main import templates
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар не найден"
        )
    
    product.status = ProductStatus.HIDDEN.value
    
    # Создаем запись в истории модерации
    moderation_record = ModerationHistory(
        product_id=product_id,
        admin_id=current_user.id,
        action=ModerationAction.REJECTED.value,
        reason=reason,
        comment=comment
    )
    db.add(moderation_record)
    
    db.commit()
    db.refresh(product)
    
    # Для HTMX запросов возвращаем обновленное представление
    if "HX-Request" in request.headers:
        return await get_product_moderation_details(request, product_id, db, current_user)
    
    return product

@router.put("/products/{product_id}/revert-to-moderation", response_model=ProductDetail)
async def revert_product_to_moderation(
    request: Request,
    product_id: int,
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Возвращение предмета на модерацию
    """
    from app.main import templates
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар не найден"
        )
    
    product.status = ProductStatus.MODERATION.value
    
    # Создаем запись в истории модерации
    moderation_record = ModerationHistory(
        product_id=product_id,
        admin_id=current_user.id,
        action=ModerationAction.REVERTED.value,
        comment=comment
    )
    db.add(moderation_record)
    
    db.commit()
    db.refresh(product)
    
    # Для HTMX запросов возвращаем обновленное представление
    if "HX-Request" in request.headers:
        return await get_product_moderation_details(request, product_id, db, current_user)
    
    return product

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение статистики для панели администратора
    """
    # Количество пользователей
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    sellers = db.query(User).filter(User.role == UserRole.SELLER.value).count()
    admins = db.query(User).filter(User.role == UserRole.ADMIN.value).count()
    
    # Количество товаров
    total_products = db.query(Product).count()
    active_products = db.query(Product).filter(Product.status == ProductStatus.ACTIVE.value).count()
    moderation_products = db.query(Product).filter(Product.status == ProductStatus.MODERATION.value).count()
    hidden_products = db.query(Product).filter(Product.status == ProductStatus.HIDDEN.value).count()
    
    # Средняя цена товаров
    avg_price = db.query(sa.func.avg(Product.price)).scalar() or 0
    
    # Количество заказов
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(Order.status == OrderStatus.PENDING.value).count()
    completed_orders = db.query(Order).filter(Order.status == OrderStatus.COMPLETED.value).count()
    cancelled_orders = db.query(Order).filter(Order.status == OrderStatus.CANCELLED.value).count()
    
    # Статистика за последний месяц
    month_ago = datetime.utcnow() - timedelta(days=30)
    new_users_month = db.query(User).filter(User.created_at >= month_ago).count()
    new_orders_month = db.query(Order).filter(Order.created_at >= month_ago).count()
    
    # Продажи за месяц
    month_sales = db.query(sa.func.sum(Order.total_amount)).filter(
        Order.status == OrderStatus.COMPLETED.value,
        Order.created_at >= month_ago
    ).scalar() or 0
    
    # Сумма всех завершенных заказов
    total_sales = db.query(sa.func.sum(Order.total_amount)).filter(
        Order.status == OrderStatus.COMPLETED.value
    ).scalar() or 0
    
    # Средний чек
    avg_order = 0
    if completed_orders > 0:
        avg_order = total_sales / completed_orders
    
    # Комиссии (демонстрационные расчеты)
    platform_fee = total_sales * 0.1  # 10% комиссия платформы
    payment_fee = total_sales * 0.02  # 2% комиссия платежной системы
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "sellers": sellers,
            "admins": admins,
            "new_month": new_users_month
        },
        "products": {
            "total": total_products,
            "active": active_products,
            "moderation": moderation_products,
            "hidden": hidden_products,
            "avg_price": float(avg_price)
        },
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "completed": completed_orders,
            "cancelled": cancelled_orders,
            "new_month": new_orders_month,
            "avg_completion_time": "24ч"  # Демонстрационные данные
        },
        "sales": {
            "total": float(total_sales),
            "month": float(month_sales),
            "avg_order": float(avg_order),
            "platform_fee": float(platform_fee),
            "payment_fee": float(payment_fee)
        }
    }

@router.get("/refresh-dashboard")
async def refresh_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Эндпоинт для обновления данных дашборда через HTMX
    """
    from app.main import templates
    stats = await get_dashboard_stats(db, current_user)
    
    # Вернуть только содержимое дашборда без всего шаблона
    return templates.TemplateResponse(
        "admin/dashboard_content.html", 
        {"request": request, "stats": stats}
    )

@router.get("/log/actions")
async def get_log_actions(
    type: str = "all",
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение последних действий из системного журнала
    Демонстрационные данные
    """
    # В реальном приложении здесь будет запрос к таблице с логами действий
    # Возвращаем демонстрационные данные для разных типов
    
    all_actions = [
        {
            "id": 1,
            "type": "product",
            "message": "Новый продукт добавлен на модерацию",
            "entity_id": 42,
            "entity_name": "Премиум шаблон для сайта",
            "user_id": 5,
            "user_name": "seller123",
            "timestamp": datetime.utcnow() - timedelta(minutes=10),
            "status": "success"
        },
        {
            "id": 2,
            "type": "user",
            "message": "Пользователь заблокирован",
            "entity_id": 15,
            "entity_name": "user123",
            "user_id": 1,
            "user_name": "admin",
            "timestamp": datetime.utcnow() - timedelta(hours=3),
            "status": "danger"
        },
        {
            "id": 3,
            "type": "order",
            "message": "Новый заказ создан",
            "entity_id": 123,
            "entity_name": "#12345",
            "user_id": 8,
            "user_name": "buyer456",
            "timestamp": datetime.utcnow() - timedelta(hours=6),
            "status": "success"
        },
        {
            "id": 4,
            "type": "system",
            "message": "Обновлены настройки сайта",
            "entity_id": None,
            "entity_name": None,
            "user_id": 1,
            "user_name": "admin",
            "timestamp": datetime.utcnow() - timedelta(days=1),
            "status": "info"
        },
        {
            "id": 5,
            "type": "user",
            "message": "Новая регистрация продавца",
            "entity_id": 22,
            "entity_name": "new_seller",
            "user_id": None,
            "user_name": None,
            "timestamp": datetime.utcnow() - timedelta(days=2),
            "status": "success"
        },
    ]
    
    # Фильтрация по типу
    if type != "all":
        filtered_actions = [action for action in all_actions if action["type"] == type]
    else:
        filtered_actions = all_actions
    
    # Ограничение количества записей
    actions = filtered_actions[:limit]
    
    # Форматирование для вывода в шаблоне
    formatted_actions = []
    for action in actions:
        # Определение цвета для индикатора
        border_class = "border-accent-teal"
        if action["status"] == "danger":
            border_class = "border-accent-coral"
        elif action["status"] == "info":
            border_class = "border-gray-400"
        elif action["status"] == "warning":
            border_class = "border-accent-blue"
        
        # Форматирование времени для отображения
        timestamp = action["timestamp"]
        now = datetime.utcnow()
        if now - timestamp < timedelta(minutes=60):
            time_text = f"{(now - timestamp).seconds // 60} минут назад"
        elif now - timestamp < timedelta(hours=24):
            time_text = f"{(now - timestamp).seconds // 3600} часов назад"
        else:
            days = (now - timestamp).days
            if days == 1:
                time_text = "Вчера"
            else:
                time_text = f"{days} дня назад"
        
        formatted_actions.append({
            "message": action["message"],
            "time_text": time_text,
            "border_class": border_class,
            "status": action["status"],
            "entity_id": action["entity_id"],
            "entity_name": action["entity_name"]
        })
    
    # Возвращаем HTML-фрагмент для вставки через HTMX
    html_content = ""
    for action in formatted_actions:
        badge_class = "badge-success"
        if action["status"] == "danger":
            badge_class = "badge-danger"
        elif action["status"] == "info":
            badge_class = ""
        elif action["status"] == "warning":
            badge_class = "badge-warning"
        
        html_content += f"""
        <div class="border-l-4 {action['border_class']} pl-4 py-1">
            <div class="flex justify-between">
                <p class="font-medium">{action['message']}</p>
                <span class="action-badge {badge_class}">{action['status'].upper()}</span>
            </div>
            <p class="text-sm text-gray-500">{action['time_text']}</p>
        </div>
        """
    
    return HTMLResponse(content=html_content)

@router.get("/products/{product_id}/details", response_class=HTMLResponse)
async def get_product_details(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение детальной информации о предмете
    """
    from app.main import templates
    
    # Получаем предмет по ID
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return HTMLResponse(content="<div class='p-6 text-center text-red-500'>Предмет не найден</div>")
    
    # Добавляем текстовый статус и класс бейджа
    if product.status == ProductStatus.MODERATION.value:
        product.status_text = "На модерации"
        product.status_badge = "moderation"
    elif product.status == ProductStatus.ACTIVE.value:
        product.status_text = "Одобрен"
        product.status_badge = "active"
    elif product.status == ProductStatus.HIDDEN.value:
        product.status_text = "Отклонен"
        product.status_badge = "hidden"
    else:
        product.status_text = "Неизвестно"
        product.status_badge = "secondary"
    
    # Получаем изображения
    images = db.query(ProductImage).filter(ProductImage.product_id == product_id).all()
    
    # Статистика по продавцу
    seller_stats = {
        "pending_items": db.query(Product).filter(
            Product.seller_id == product.seller_id,
            Product.status == ProductStatus.MODERATION.value
        ).count(),
        "rejected_items": db.query(Product).filter(
            Product.seller_id == product.seller_id,
            Product.status == ProductStatus.HIDDEN.value
        ).count()
    }
    
    # История модерации (в продакшн надо хранить в отдельной таблице)
    moderation_history = []
    
    # Упрощенно: считаем, что текущий статус - последнее действие
    if product.status != ProductStatus.DRAFT.value:
        action_text = ""
        if product.status == ProductStatus.ACTIVE.value:
            action_text = "Предмет одобрен"
        elif product.status == ProductStatus.HIDDEN.value:
            action_text = "Предмет отклонен"
        elif product.status == ProductStatus.MODERATION.value:
            action_text = "Отправлен на модерацию"
        
        moderation_history.append({
            "action_text": action_text,
            "date": product.updated_at,
            "admin": current_user.username
        })
    
    return templates.TemplateResponse("admin/moderation_details.html", {
        "request": request,
        "item": product,
        "images": images,
        "seller_stats": seller_stats,
        "moderation_history": moderation_history
    }) 