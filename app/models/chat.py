from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Chat(Base):
    """
    Модель чата между покупателем и продавцом
    """
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связи с заказом
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    order = relationship("Order", back_populates="chat")
    
    # Система отслеживания
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи с сообщениями
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    """
    Модель сообщения в чате
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связи с чатом
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    chat = relationship("Chat", back_populates="messages")
    
    # Связи с отправителем
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender = relationship("User")
    
    # Содержимое сообщения
    content = Column(Text, nullable=False)
    
    # Статус сообщения
    is_read = Column(Boolean, default=False)
    
    # Система отслеживания
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 