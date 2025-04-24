#!/usr/bin/env python3
"""
Скрипт для инициализации директорий медиафайлов и загрузок
"""
import os
import shutil
from pathlib import Path

# Основные директории для создания
MEDIA_DIR = "media"
STATIC_DIR = "static"

# Поддиректории для медиафайлов
MEDIA_SUBDIRS = [
    "uploads",
    "uploads/avatars",
    "uploads/products",
    "uploads/temp"
]

# Поддиректории для статических файлов
STATIC_SUBDIRS = [
    "css",
    "js",
    "img",
    "fonts",
    "vendors"
]

def create_directories():
    """
    Создает основные директории для медиафайлов и статики
    """
    print("Создание директорий для медиафайлов и статики...")
    
    # Создаем корневые директории
    Path(MEDIA_DIR).mkdir(exist_ok=True)
    Path(STATIC_DIR).mkdir(exist_ok=True)
    
    # Создаем поддиректории для медиафайлов
    for subdir in MEDIA_SUBDIRS:
        path = Path(os.path.join(MEDIA_DIR, subdir))
        path.mkdir(exist_ok=True, parents=True)
        print(f"  ✓ Создана директория: {path}")
    
    # Создаем поддиректории для статических файлов
    for subdir in STATIC_SUBDIRS:
        path = Path(os.path.join(STATIC_DIR, subdir))
        path.mkdir(exist_ok=True, parents=True)
        print(f"  ✓ Создана директория: {path}")
    
    print("Директории успешно созданы!")

if __name__ == "__main__":
    create_directories() 