from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum, Table
from sqlalchemy.orm import relationship
import enum
from app.database import Base
from datetime import datetime

# Связующая таблица для категорий товаров
product_category = Table(
    "product_category",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True)
)

class ProductStatus(str, enum.Enum):
    """
    Перечисление статусов товара
    """
    DRAFT = "draft"
    ACTIVE = "active"
    MODERATION = "moderation"
    HIDDEN = "hidden"
    DELETED = "deleted"

class ModerationAction(str, enum.Enum):
    """
    Перечисление действий модерации
    """
    APPROVE = "approve"
    REJECT = "reject"
    BLOCK = "block"
    UNBLOCK = "unblock"
    REVIEW = "review"

class Product(Base):
    """
    Модель товара
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    
    # Дополнительные поля товара
    thumbnail = Column(String(255), nullable=True)
    status = Column(String(20), default=ProductStatus.DRAFT.value)
    quantity = Column(Integer, default=1)
    
    # Связи с пользователем-продавцом
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller = relationship("User", back_populates="products")
    
    # Система отслеживания
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи с другими таблицами
    categories = relationship("Category", secondary=product_category, back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    orders = relationship("OrderItem", back_populates="product")
    reviews = relationship("Review", back_populates="product")
    moderation_history = relationship("ModerationHistory", back_populates="product")

class Category(Base):
    """
    Модель категории товаров
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Связи
    parent = relationship("Category", remote_side=[id], backref="subcategories")
    products = relationship("Product", secondary=product_category, back_populates="categories")
    
    # Система отслеживания
    created_at = Column(DateTime, default=datetime.utcnow)

class ProductImage(Base):
    """
    Модель изображения товара
    """
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    image_url = Column(String(255), nullable=False)
    is_primary = Column(Boolean, default=False)
    
    # Связи
    product = relationship("Product", back_populates="images")

class ModerationHistory(Base):
    """
    Модель истории модерации товара
    """
    __tablename__ = "moderation_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    admin_id = Column(Integer, ForeignKey("users.id"))
    action = Column(Enum(ModerationAction), index=True)
    reason = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    product = relationship("Product", back_populates="moderation_history")
    admin = relationship("User", backref="moderation_actions") 