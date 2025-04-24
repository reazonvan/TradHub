from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base
from datetime import datetime

class UserRole(str, enum.Enum):
    """
    Перечисление ролей пользователей
    """
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"

class PhoneVerification(Base):
    """
    Модель для хранения кодов верификации номера телефона
    """
    __tablename__ = "phone_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), index=True, nullable=False)
    code = Column(String(6), nullable=False)  # 6-значный код подтверждения
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0)  # Количество попыток ввода кода

class User(Base):
    """
    Модель пользователя
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    phone_verified = Column(Boolean, default=False)  # Флаг проверки телефона
    role = Column(String(20), default=UserRole.BUYER.value)
    is_active = Column(Boolean, default=True)
    
    # Безопасность
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255), nullable=True)
    
    # Аватар пользователя
    avatar = Column(String(255), nullable=True)
    
    # Профиль продавца
    seller_rating = Column(Float, default=0.0)
    seller_description = Column(Text, nullable=True)
    
    # Система отслеживания
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Связи с другими таблицами
    products = relationship("Product", back_populates="seller")
    orders_as_buyer = relationship("Order", back_populates="buyer", foreign_keys="Order.buyer_id")
    orders_as_seller = relationship("Order", back_populates="seller", foreign_keys="Order.seller_id")
    reviews_given = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_id")
    reviews_received = relationship("Review", back_populates="seller", foreign_keys="Review.seller_id") 