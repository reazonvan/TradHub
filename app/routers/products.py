from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
import os
from uuid import uuid4

from app.database import get_db
from app.models.user import User
from app.models.product import Product, Category, ProductImage, ProductStatus
from app.schemas.product import (
    Product as ProductSchema,
    ProductCreate,
    ProductUpdate,
    ProductDetail,
    Category as CategorySchema,
    CategoryCreate,
    CategoryWithChildren
)
from app.security import get_current_user, get_current_seller, get_current_admin
from app.config import settings

router = APIRouter()

# Эндпоинты для категорий
@router.get("/categories", response_model=List[CategorySchema])
async def read_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Получение списка категорий товаров
    """
    categories = db.query(Category).filter(Category.parent_id == None).offset(skip).limit(limit).all()
    return categories

@router.get("/categories/{category_id}", response_model=CategoryWithChildren)
async def read_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """
    Получение информации о категории по ID
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    return category

@router.post("/categories", response_model=CategorySchema)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Создание новой категории (только для администраторов)
    """
    # Проверка уникальности slug
    db_category = db.query(Category).filter(Category.slug == category_data.slug).first()
    if db_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория с таким slug уже существует"
        )
    
    # Проверка родительской категории, если она указана
    if category_data.parent_id:
        parent_category = db.query(Category).filter(Category.id == category_data.parent_id).first()
        if not parent_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Родительская категория не найдена"
            )
    
    # Создаем новую категорию
    db_category = Category(
        name=category_data.name,
        slug=category_data.slug,
        description=category_data.description,
        parent_id=category_data.parent_id
    )
    
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    return db_category

# Эндпоинты для товаров
@router.get("/", response_model=List[ProductSchema])
async def read_products(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    seller_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Получение списка товаров с возможностью фильтрации
    """
    query = db.query(Product).filter(Product.status == ProductStatus.ACTIVE.value)
    
    # Фильтрация по категории
    if category_id:
        query = query.filter(Product.categories.any(Category.id == category_id))
    
    # Фильтрация по продавцу
    if seller_id:
        query = query.filter(Product.seller_id == seller_id)
    
    # Фильтрация по цене
    if min_price:
        query = query.filter(Product.price >= min_price)
    if max_price:
        query = query.filter(Product.price <= max_price)
    
    # Поиск по названию и описанию
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Product.title.ilike(search_term),
                Product.description.ilike(search_term)
            )
        )
    
    products = query.offset(skip).limit(limit).all()
    return products

@router.get("/{product_id}", response_model=ProductDetail)
async def read_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Получение информации о товаре по ID
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар не найден"
        )
    
    if product.status != ProductStatus.ACTIVE.value:
        # Для неактивных товаров нужны права
        try:
            current_user = get_current_user(db=db)
            if current_user.id != product.seller_id and current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав для просмотра этого товара"
                )
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Товар не найден"
            )
    
    return product

@router.post("/", response_model=ProductDetail)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_seller)
):
    """
    Создание нового товара (только для продавцов)
    """
    # Проверка существования категорий
    categories = []
    if product_data.category_ids:
        for category_id in product_data.category_ids:
            category = db.query(Category).filter(Category.id == category_id).first()
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Категория с ID {category_id} не найдена"
                )
            categories.append(category)
    
    # Создаем новый товар
    db_product = Product(
        title=product_data.title,
        description=product_data.description,
        price=product_data.price,
        quantity=product_data.quantity,
        thumbnail=product_data.thumbnail,
        status=ProductStatus.MODERATION.value,  # Новые товары сначала проходят модерацию
        seller_id=current_user.id
    )
    
    # Добавляем категории
    db_product.categories = categories
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return db_product

@router.put("/{product_id}", response_model=ProductDetail)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_seller)
):
    """
    Обновление товара (только для владельца товара или администратора)
    """
    # Получаем товар
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар не найден"
        )
    
    # Проверка прав
    if db_product.seller_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для редактирования этого товара"
        )
    
    # Проверка и обновление категорий
    if product_data.category_ids is not None:
        categories = []
        for category_id in product_data.category_ids:
            category = db.query(Category).filter(Category.id == category_id).first()
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Категория с ID {category_id} не найдена"
                )
            categories.append(category)
        db_product.categories = categories
    
    # Обновляем поля товара
    update_data = product_data.dict(exclude_unset=True, exclude={"category_ids"})
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    # Если товар был изменен, он снова должен пройти модерацию
    if db_product.status == ProductStatus.ACTIVE.value:
        db_product.status = ProductStatus.MODERATION.value
    
    db.commit()
    db.refresh(db_product)
    
    return db_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_seller)
):
    """
    Удаление товара (только для владельца товара или администратора)
    """
    # Получаем товар
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар не найден"
        )
    
    # Проверка прав
    if db_product.seller_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления этого товара"
        )
    
    # Изменяем статус товара на удаленный
    db_product.status = ProductStatus.DELETED.value
    db.commit()
    
    return None

@router.post("/{product_id}/images", response_model=ProductDetail)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_seller)
):
    """
    Загрузка изображения товара
    """
    # Получаем товар
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар не найден"
        )
    
    # Проверка прав
    if db_product.seller_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для редактирования этого товара"
        )
    
    # Проверка размера файла
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Размер файла превышает максимально допустимый ({settings.MAX_UPLOAD_SIZE} байт)"
        )
    
    # Проверка типа файла
    content_type = file.content_type
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Файл должен быть изображением"
        )
    
    # Создаем директорию для загрузок, если она не существует
    upload_dir = os.path.join(settings.UPLOAD_DIR, "products")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Создаем уникальное имя файла
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    # Если изображение отмечено как основное, снимаем отметку с других изображений
    if is_primary:
        for image in db_product.images:
            image.is_primary = False
    
    # Создаем запись в базе данных
    relative_path = os.path.join("products", unique_filename)
    db_image = ProductImage(
        product_id=db_product.id,
        image_url=relative_path,
        is_primary=is_primary
    )
    
    # Если это первое изображение или оно отмечено как основное, 
    # устанавливаем его как миниатюру товара
    if is_primary or not db_product.thumbnail:
        db_product.thumbnail = relative_path
    
    db.add(db_image)
    db.commit()
    db.refresh(db_product)
    
    return db_product 