from app.schemas.user import (
    User, UserCreate, UserUpdate, UserInDB, UserLogin,
    Token, TokenData
)
from app.schemas.product import (
    Product, ProductCreate, ProductUpdate, ProductDetail,
    Category, CategoryCreate, CategoryWithChildren,
    ProductImage, ProductImageCreate
)
from app.schemas.order import (
    Order, OrderCreate, OrderUpdate, OrderDetail,
    OrderItem, OrderItemCreate,
    Review, ReviewCreate, ReviewUpdate, ReviewDetail
)
from app.schemas.chat import (
    Chat, ChatCreate, ChatDetail,
    Message, MessageCreate, MessageDetail
)

# Для удобного импорта: from app.schemas import User, Product, ...
__all__ = [
    # User
    "User", "UserCreate", "UserUpdate", "UserInDB", "UserLogin",
    "Token", "TokenData",
    
    # Product
    "Product", "ProductCreate", "ProductUpdate", "ProductDetail",
    "Category", "CategoryCreate", "CategoryWithChildren",
    "ProductImage", "ProductImageCreate",
    
    # Order
    "Order", "OrderCreate", "OrderUpdate", "OrderDetail",
    "OrderItem", "OrderItemCreate",
    "Review", "ReviewCreate", "ReviewUpdate", "ReviewDetail",
    
    # Chat
    "Chat", "ChatCreate", "ChatDetail",
    "Message", "MessageCreate", "MessageDetail"
] 