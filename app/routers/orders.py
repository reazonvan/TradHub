from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.order import Order, OrderItem, OrderStatus, Review
from app.models.product import Product
from app.schemas.order import (
    Order as OrderSchema,
    OrderCreate,
    OrderUpdate,
    OrderDetail,
    Review as ReviewSchema,
    ReviewCreate,
    ReviewDetail
)
from app.security import get_current_user, get_current_seller, get_current_admin
from app.routers.chat import create_chat_for_order

router = APIRouter()

@router.get("/", response_model=List[OrderSchema])
async def read_orders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка заказов пользователя (продавца или покупателя)
    """
    if current_user.role == "admin":
        # Администраторы видят все заказы
        orders = db.query(Order).offset(skip).limit(limit).all()
    else:
        # Обычные пользователи видят только свои заказы
        orders = db.query(Order).filter(
            (Order.buyer_id == current_user.id) | (Order.seller_id == current_user.id)
        ).offset(skip).limit(limit).all()
    
    return orders

@router.get("/{order_id}", response_model=OrderDetail)
async def read_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации о заказе по ID
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден"
        )
    
    # Проверка прав доступа
    if current_user.role != "admin" and current_user.id != order.buyer_id and current_user.id != order.seller_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра этого заказа"
        )
    
    return order

@router.post("/", response_model=OrderDetail)
async def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создание нового заказа
    """
    # Проверка существования продавца
    seller = db.query(User).filter(User.id == order_data.seller_id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продавец не найден"
        )
    
    # Проверка, что продавец имеет соответствующую роль
    if seller.role != "seller" and seller.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указанный пользователь не является продавцом"
        )
    
    # Проверка, что покупатель не является продавцом
    if current_user.id == order_data.seller_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Продавец не может создать заказ у самого себя"
        )
    
    # Проверка наличия товаров
    if not order_data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заказ должен содержать хотя бы один товар"
        )
    
    # Проверка товаров и расчет общей суммы
    total_amount = 0
    order_items = []
    
    for item_data in order_data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Товар с ID {item_data.product_id} не найден"
            )
        
        # Проверка, что товар принадлежит указанному продавцу
        if product.seller_id != order_data.seller_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Товар с ID {item_data.product_id} не принадлежит указанному продавцу"
            )
        
        # Проверка наличия товара
        if product.quantity < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недостаточное количество товара с ID {item_data.product_id}"
            )
        
        # Создание элемента заказа
        order_item = OrderItem(
            product_id=product.id,
            quantity=item_data.quantity,
            price=product.price
        )
        
        # Добавляем в общую сумму
        total_amount += product.price * item_data.quantity
        
        # Обновляем остаток товара
        product.quantity -= item_data.quantity
        
        order_items.append(order_item)
    
    # Создаем новый заказ
    db_order = Order(
        buyer_id=current_user.id,
        seller_id=order_data.seller_id,
        status=OrderStatus.PENDING.value,
        total_amount=total_amount,
        notes=order_data.notes
    )
    
    # Добавляем товары к заказу
    db_order.items = order_items
    
    # Сохраняем заказ в базу данных
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Создаем чат для заказа
    await create_chat_for_order(db_order.id, db)
    
    return db_order

@router.put("/{order_id}", response_model=OrderDetail)
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновление статуса заказа
    """
    # Получаем заказ
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if db_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден"
        )
    
    # Проверка прав доступа
    is_seller = current_user.id == db_order.seller_id
    is_buyer = current_user.id == db_order.buyer_id
    is_admin = current_user.role == "admin"
    
    if not (is_seller or is_buyer or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для обновления этого заказа"
        )
    
    # Проверка статуса в зависимости от роли
    if order_data.status:
        if order_data.status == OrderStatus.CANCELLED.value:
            # Отменить заказ может покупатель, продавец или админ
            pass
        elif order_data.status == OrderStatus.COMPLETED.value:
            # Завершить заказ может покупатель или админ
            if not (is_buyer or is_admin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Только покупатель может завершить заказ"
                )
            # Устанавливаем дату завершения
            db_order.completed_at = datetime.utcnow()
        elif order_data.status == OrderStatus.PROCESSING.value:
            # Перевести в обработку может продавец или админ
            if not (is_seller or is_admin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Только продавец может перевести заказ в обработку"
                )
        elif order_data.status == OrderStatus.REFUNDED.value:
            # Возврат может сделать только админ
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Только администратор может оформить возврат"
                )
    
    # Обновляем поля заказа
    update_data = order_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_order, key, value)
    
    db.commit()
    db.refresh(db_order)
    
    return db_order

@router.post("/{order_id}/reviews", response_model=ReviewDetail)
async def create_review(
    order_id: int,
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создание отзыва о товаре и продавце
    """
    # Получаем заказ
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if db_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден"
        )
    
    # Проверка, что текущий пользователь является покупателем
    if current_user.id != db_order.buyer_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только покупатель может оставить отзыв"
        )
    
    # Проверка, что заказ завершен
    if db_order.status != OrderStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отзыв можно оставить только для завершенного заказа"
        )
    
    # Проверка, что отзыв для этого заказа еще не оставлен
    existing_review = db.query(Review).filter(
        Review.reviewer_id == current_user.id,
        Review.product_id == review_data.product_id,
        Review.seller_id == review_data.seller_id
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже оставили отзыв для этого товара"
        )
    
    # Проверка, что товар был в заказе
    product_in_order = False
    for item in db_order.items:
        if item.product_id == review_data.product_id:
            product_in_order = True
            break
    
    if not product_in_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот товар не был в заказе"
        )
    
    # Проверка, что продавец соответствует заказу
    if review_data.seller_id != db_order.seller_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указанный продавец не соответствует заказу"
        )
    
    # Создаем новый отзыв
    db_review = Review(
        reviewer_id=current_user.id,
        seller_id=review_data.seller_id,
        product_id=review_data.product_id,
        rating=review_data.rating,
        comment=review_data.comment
    )
    
    # Сохраняем отзыв в базу данных
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    # Обновляем рейтинг продавца
    seller = db.query(User).filter(User.id == review_data.seller_id).first()
    seller_reviews = db.query(Review).filter(Review.seller_id == review_data.seller_id).all()
    
    if seller_reviews:
        total_rating = sum(review.rating for review in seller_reviews)
        seller.seller_rating = total_rating / len(seller_reviews)
        db.commit()
    
    return db_review

@router.get("/reviews/{product_id}", response_model=List[ReviewDetail])
async def read_product_reviews(
    product_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Получение списка отзывов о товаре
    """
    reviews = db.query(Review).filter(Review.product_id == product_id).offset(skip).limit(limit).all()
    return reviews 