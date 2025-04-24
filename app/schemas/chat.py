from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class MessageBase(BaseModel):
    """
    Базовая схема сообщения
    """
    content: str = Field(..., min_length=1)
    
class MessageCreate(MessageBase):
    """
    Схема для создания сообщения
    """
    chat_id: int
    
class Message(MessageBase):
    """
    Схема сообщения для ответа API
    """
    id: int
    chat_id: int
    sender_id: int
    is_read: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        
class MessageDetail(Message):
    """
    Расширенная схема сообщения с информацией об отправителе
    """
    sender: 'UserInfo'  # Определим ниже
    
    class Config:
        orm_mode = True

class ChatBase(BaseModel):
    """
    Базовая схема чата
    """
    order_id: int
    
class ChatCreate(ChatBase):
    """
    Схема для создания чата
    """
    pass
    
class Chat(ChatBase):
    """
    Схема чата для ответа API
    """
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        
class ChatDetail(Chat):
    """
    Расширенная схема чата с сообщениями
    """
    messages: List[Message] = []
    order: 'OrderInfo'  # Определим ниже
    
    class Config:
        orm_mode = True

# Схемы для внешних ссылок
class UserInfo(BaseModel):
    id: int
    username: str
    
    class Config:
        orm_mode = True
        
class OrderInfo(BaseModel):
    id: int
    buyer_id: int
    seller_id: int
    
    class Config:
        orm_mode = True

# Обновление ссылок
MessageDetail.update_forward_refs()
ChatDetail.update_forward_refs() 