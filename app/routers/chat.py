from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.order import Order
from app.models.chat import Chat, Message
from app.schemas.chat import (
    Chat as ChatSchema,
    ChatCreate,
    ChatDetail,
    Message as MessageSchema,
    MessageCreate
)
from app.security import get_current_user

router = APIRouter()

# Менеджер WebSocket-подключений
class ConnectionManager:
    def __init__(self):
        # Словарь активных соединений: {chat_id: {user_id: websocket}}
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int):
        await websocket.accept()
        
        # Инициализируем словарь для этого чата, если его еще нет
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = {}
        
        # Сохраняем соединение
        self.active_connections[chat_id][user_id] = websocket
    
    def disconnect(self, chat_id: int, user_id: int):
        # Удаляем соединение
        if chat_id in self.active_connections and user_id in self.active_connections[chat_id]:
            del self.active_connections[chat_id][user_id]
            
            # Если в чате не осталось активных пользователей, удаляем запись о чате
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]
    
    async def send_message(self, message: dict, chat_id: int, exclude_user_id: int = None):
        # Отправляем сообщение всем подключенным к чату, кроме исключенного пользователя
        if chat_id in self.active_connections:
            for user_id, connection in self.active_connections[chat_id].items():
                if exclude_user_id is None or user_id != exclude_user_id:
                    await connection.send_text(json.dumps(message))
    
    async def send_personal_message(self, message: dict, chat_id: int, user_id: int):
        # Отправляем сообщение конкретному пользователю в чате
        if chat_id in self.active_connections and user_id in self.active_connections[chat_id]:
            await self.active_connections[chat_id][user_id].send_text(json.dumps(message))

# Создаем экземпляр менеджера подключений
manager = ConnectionManager()

async def create_chat_for_order(order_id: int, db: Session):
    """
    Создание чата для заказа (вспомогательная функция)
    """
    # Проверка существования заказа
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None
    
    # Проверка, что чат для этого заказа еще не существует
    existing_chat = db.query(Chat).filter(Chat.order_id == order_id).first()
    if existing_chat:
        return existing_chat
    
    # Создаем новый чат
    db_chat = Chat(order_id=order_id)
    
    # Сохраняем чат в базу данных
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    
    return db_chat

@router.get("/", response_model=List[ChatSchema])
async def read_chats(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка чатов пользователя
    """
    if current_user.role == "admin":
        # Администраторы видят все чаты
        chats = db.query(Chat).offset(skip).limit(limit).all()
    else:
        # Обычные пользователи видят только свои чаты
        chats = db.query(Chat).join(Order).filter(
            (Order.buyer_id == current_user.id) | (Order.seller_id == current_user.id)
        ).offset(skip).limit(limit).all()
    
    return chats

@router.get("/{chat_id}", response_model=ChatDetail)
async def read_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации о чате по ID
    """
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    # Проверка прав доступа
    order = chat.order
    if current_user.role != "admin" and current_user.id != order.buyer_id and current_user.id != order.seller_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра этого чата"
        )
    
    return chat

@router.post("/messages", response_model=MessageSchema)
async def create_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создание нового сообщения в чате
    """
    # Проверка существования чата
    chat = db.query(Chat).filter(Chat.id == message_data.chat_id).first()
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    # Проверка прав доступа
    order = chat.order
    if current_user.role != "admin" and current_user.id != order.buyer_id and current_user.id != order.seller_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для отправки сообщения в этот чат"
        )
    
    # Создаем новое сообщение
    db_message = Message(
        chat_id=chat.id,
        sender_id=current_user.id,
        content=message_data.content
    )
    
    # Сохраняем сообщение в базу данных
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # Отправляем сообщение через WebSocket, если есть активные соединения
    message_data = {
        "id": db_message.id,
        "sender_id": db_message.sender_id,
        "content": db_message.content,
        "is_read": db_message.is_read,
        "created_at": db_message.created_at.isoformat(),
        "sender": {
            "id": current_user.id,
            "username": current_user.username
        }
    }
    
    # Асинхронно отправляем сообщение всем участникам чата, кроме отправителя
    try:
        await manager.send_message(message_data, chat.id, current_user.id)
    except:
        # Игнорируем ошибки отправки WebSocket (например, нет активных соединений)
        pass
    
    return db_message

@router.post("/messages/{message_id}/read", response_model=MessageSchema)
async def mark_message_as_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отметка сообщения как прочитанного
    """
    # Получаем сообщение
    db_message = db.query(Message).filter(Message.id == message_id).first()
    if db_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено"
        )
    
    # Проверка прав доступа
    chat = db_message.chat
    order = chat.order
    if current_user.role != "admin" and current_user.id != order.buyer_id and current_user.id != order.seller_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для чтения этого сообщения"
        )
    
    # Проверка, что пользователь не является отправителем сообщения
    if db_message.sender_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя отметить как прочитанное собственное сообщение"
        )
    
    # Отмечаем сообщение как прочитанное
    db_message.is_read = True
    db_message.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_message)
    
    return db_message

@router.websocket("/ws/{chat_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    chat_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket-соединение для чата
    """
    # Проверка токена и получение пользователя
    try:
        current_user = get_current_user(token, db)
    except HTTPException:
        # Если токен недействителен, закрываем соединение
        await websocket.close(code=1008)  # Policy Violation
        return
    
    # Проверка существования чата
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat is None:
        await websocket.close(code=1008)  # Policy Violation
        return
    
    # Проверка прав доступа
    order = chat.order
    if current_user.role != "admin" and current_user.id != order.buyer_id and current_user.id != order.seller_id:
        await websocket.close(code=1008)  # Policy Violation
        return
    
    # Подключаем пользователя к чату
    await manager.connect(websocket, chat_id, current_user.id)
    
    # Отправляем уведомление о подключении пользователя
    connection_message = {
        "type": "connection",
        "user_id": current_user.id,
        "username": current_user.username,
        "connected": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.send_message(connection_message, chat_id, current_user.id)
    
    try:
        while True:
            # Ожидаем сообщения от клиента
            data = await websocket.receive_text()
            
            try:
                # Парсим JSON-данные
                message_data = json.loads(data)
                content = message_data.get("content", "").strip()
                
                if not content:
                    continue
                
                # Создаем новое сообщение в БД
                db_message = Message(
                    chat_id=chat_id,
                    sender_id=current_user.id,
                    content=content
                )
                
                db.add(db_message)
                db.commit()
                db.refresh(db_message)
                
                # Формируем ответное сообщение
                response = {
                    "type": "message",
                    "id": db_message.id,
                    "chat_id": db_message.chat_id,
                    "sender_id": db_message.sender_id,
                    "content": db_message.content,
                    "is_read": db_message.is_read,
                    "created_at": db_message.created_at.isoformat(),
                    "sender": {
                        "id": current_user.id,
                        "username": current_user.username
                    }
                }
                
                # Отправляем сообщение всем участникам чата
                await manager.send_message(response, chat_id)
                
            except json.JSONDecodeError:
                # Игнорируем неправильно отформатированные сообщения
                continue
            
    except WebSocketDisconnect:
        # Обрабатываем отключение пользователя
        manager.disconnect(chat_id, current_user.id)
        
        # Отправляем уведомление об отключении пользователя
        disconnection_message = {
            "type": "connection",
            "user_id": current_user.id,
            "username": current_user.username,
            "connected": False,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await manager.send_message(disconnection_message, chat_id, current_user.id) 