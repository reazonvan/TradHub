from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.order import OrderStatus

class OrderItemBase(BaseModel):
    """
    Базовая схема элемента заказа
    """
    product_id: int
    quantity: int = Field(1, ge=1)
    
class OrderItemCreate(OrderItemBase):
    """
    Схема для создания элемента заказа
    """
    pass

class OrderItem(OrderItemBase):
    """
    Схема элемента заказа для ответа API
    """
    id: int
    order_id: int
    price: float
    
    class Config:
        orm_mode = True

class OrderBase(BaseModel):
    """
    Базовая схема заказа
    """
    seller_id: int
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    """
    Схема для создания заказа
    """
    items: List[OrderItemBase]
    
class OrderUpdate(BaseModel):
    """
    Схема для обновления заказа
    """
    status: Optional[str] = None
    notes: Optional[str] = None

class Order(OrderBase):
    """
    Схема заказа для ответа API
    """
    id: int
    buyer_id: int
    status: str
    total_amount: float
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    items: List[OrderItem] = []
    
    class Config:
        orm_mode = True

class OrderDetail(Order):
    """
    Расширенная схема заказа с дополнительной информацией
    """
    buyer: 'UserInfo' 
    seller: 'UserInfo'
    
    class Config:
        orm_mode = True

# Схема пользователя для заказов
class UserInfo(BaseModel):
    id: int
    username: str
    
    class Config:
        orm_mode = True

# Обновляем ссылки
OrderDetail.update_forward_refs()

class ReviewBase(BaseModel):
    """
    Базовая схема отзыва
    """
    product_id: int
    seller_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    
    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Рейтинг должен быть от 1 до 5')
        return v
    
class ReviewCreate(ReviewBase):
    """
    Схема для создания отзыва
    """
    pass

class ReviewUpdate(BaseModel):
    """
    Схема для обновления отзыва
    """
    rating: Optional[int] = None
    comment: Optional[str] = None
    
    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Рейтинг должен быть от 1 до 5')
        return v

class Review(ReviewBase):
    """
    Схема отзыва для ответа API
    """
    id: int
    reviewer_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        
class ReviewDetail(Review):
    """
    Расширенная схема отзыва с информацией о пользователе
    """
    reviewer: UserInfo
    
    class Config:
        orm_mode = True 