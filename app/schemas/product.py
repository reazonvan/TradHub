from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.product import ProductStatus

class CategoryBase(BaseModel):
    """
    Базовая схема категории
    """
    name: str
    slug: str = Field(..., regex=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    """
    Схема для создания категории
    """
    pass

class Category(CategoryBase):
    """
    Схема категории для ответа API
    """
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True
        
class CategoryWithChildren(Category):
    """
    Схема категории с подкатегориями
    """
    subcategories: List['CategoryWithChildren'] = []
    
    class Config:
        orm_mode = True

# Для рекурсивной схемы подкатегорий
CategoryWithChildren.update_forward_refs()

class ProductImageBase(BaseModel):
    """
    Базовая схема изображения товара
    """
    image_url: str
    is_primary: bool = False

class ProductImageCreate(ProductImageBase):
    """
    Схема для создания изображения товара
    """
    pass

class ProductImage(ProductImageBase):
    """
    Схема изображения товара для ответа API
    """
    id: int
    product_id: int
    
    class Config:
        orm_mode = True

class ProductBase(BaseModel):
    """
    Базовая схема товара
    """
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    price: float = Field(..., gt=0)
    quantity: int = Field(1, ge=0)

class ProductCreate(ProductBase):
    """
    Схема для создания товара
    """
    category_ids: List[int] = []
    thumbnail: Optional[str] = None
    
    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Цена должна быть больше нуля')
        return round(v, 2)  # Округляем до 2 знаков после запятой

class ProductUpdate(BaseModel):
    """
    Схема для обновления товара
    """
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    thumbnail: Optional[str] = None
    status: Optional[str] = None
    category_ids: Optional[List[int]] = None
    
    @validator('price')
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Цена должна быть больше нуля')
        return round(v, 2) if v is not None else v

class Product(ProductBase):
    """
    Схема товара для ответа API
    """
    id: int
    seller_id: int
    thumbnail: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    categories: List[Category] = []
    images: List[ProductImage] = []
    
    class Config:
        orm_mode = True

class ProductDetail(Product):
    """
    Расширенная схема товара с подробной информацией
    """
    seller: 'UserInfo'  # Импортируем из user.py позже
    
    class Config:
        orm_mode = True

# Определим сокращенную схему пользователя для товаров, чтобы избежать циклических импортов
class UserInfo(BaseModel):
    id: int
    username: str
    seller_rating: float
    
    class Config:
        orm_mode = True

# Обновляем ссылки на UserInfo
ProductDetail.update_forward_refs() 