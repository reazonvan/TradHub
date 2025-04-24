import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_user_registration():
    # Успешная регистрация
    response = client.post(
        "/users/register",
        json={"username": "testuser", "password": "Tr@deHub2024"}
    )
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["username"] == "testuser"

    # Слабый пароль
    response = client.post(
        "/users/register",
        json={"username": "testuser2", "password": "weak"}
    )
    assert response.status_code == 400
    assert "Пароль должен" in response.json()["detail"]

    # Существующий пользователь
    response = client.post(
        "/users/register",
        json={"username": "testuser", "password": "Tr@deHub2024"}
    )
    assert response.status_code == 400
    assert "уже существует" in response.json()["detail"]

def test_user_login():
    # Регистрация тестового пользователя
    client.post(
        "/users/register",
        json={"username": "logintest", "password": "Tr@deHub2024"}
    )

    # Успешная аутентификация
    response = client.post(
        "/users/login",
        data={"username": "logintest", "password": "Tr@deHub2024"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

    # Неверный пароль
    response = client.post(
        "/users/login",
        data={"username": "logintest", "password": "wrong"}
    )
    assert response.status_code == 401
    assert "Неверные учетные данные" in response.json()["detail"]

    # Несуществующий пользователь
    response = client.post(
        "/users/login",
        data={"username": "nonexistent", "password": "Tr@deHub2024"}
    )
    assert response.status_code == 401
    assert "Неверные учетные данные" in response.json()["detail"] 