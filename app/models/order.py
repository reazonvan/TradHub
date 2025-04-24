from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum
from sqlalchemy.orm import relationship
import enum
from app.database import Base
from datetime import datetime

class OrderStatus(str, enum.Enum):
    """
    Перечисление статусов заказа
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class Order(Base):
    """
    Модель заказа
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    
    # Покупатель и продавец
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="orders_as_buyer")
    
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller = relationship("User", foreign_keys=[seller_id], back_populates="orders_as_seller")
    
    # Данные заказа
    status = Column(String(20), default=OrderStatus.PENDING.value)
    total_amount = Column(Float, nullable=False)
    
    # Дополнительная информация
    notes = Column(Text, nullable=True)
    
    # Система отслеживания
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Связи с другими таблицами
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    chat = relationship("Chat", back_populates="order", uselist=False, cascade="all, delete-orphan")

class OrderItem(Base):
    """
    Модель элемента заказа
    """
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Детали товара в заказе
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)  # Сохраняем цену на момент заказа
    
    # Связи
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="orders")

class Review(Base):
    """
    Модель отзыва
    """
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связи с пользователями
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")
    
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller = relationship("User", foreign_keys=[seller_id], back_populates="reviews_received")
    
    # Связь с товаром
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product = relationship("Product", back_populates="reviews")
    
    # Детали отзыва
    rating = Column(Integer, nullable=False)  # от 1 до 5
    comment = Column(Text, nullable=True)
    
    # Система отслеживания
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 