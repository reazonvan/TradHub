from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.user import UserRole

class UserBase(BaseModel):
    """
    Базовая схема пользователя
    """
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    
class UserCreate(UserBase):
    """
    Схема для создания пользователя
    """
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен быть не менее 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' for c in v):
            raise ValueError('Пароль должен содержать хотя бы один специальный символ')
        return v
    
    @validator('phone')
    def phone_format(cls, v):
        if v and (not v.startswith('+') or not v[1:].isdigit()):
            raise ValueError('Номер телефона должен быть в международном формате, например +7XXXXXXXXXX')
        return v
    
class UserUpdate(BaseModel):
    """
    Схема для обновления пользователя
    """
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    seller_description: Optional[str] = None

class UserInDB(UserBase):
    """
    Схема пользователя в базе данных
    """
    id: int
    role: str
    is_active: bool
    avatar: Optional[str] = None
    seller_rating: float = 0.0
    seller_description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class User(UserInDB):
    """
    Схема для ответа API - без чувствительных данных
    """
    pass

class UserLogin(BaseModel):
    """
    Схема для входа пользователя
    """
    email: EmailStr
    password: str

class Token(BaseModel):
    """
    Схема токена доступа
    """
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    """
    Схема данных токена
    """
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None

class UserResponse(UserInDB):
    """
    Схема для ответа при создании пользователя
    """
    class Config:
        orm_mode = True 