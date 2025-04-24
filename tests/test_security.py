import pytest
from app.security import check_password_strength

def test_password_strength():
    # Слабые пароли
    assert not check_password_strength("short")  # Слишком короткий
    assert not check_password_strength("password123")  # Нет заглавных букв и спецсимволов
    assert not check_password_strength("PASSWORD123")  # Нет строчных букв и спецсимволов
    assert not check_password_strength("Password123")  # Нет спецсимволов
    
    # Сильные пароли
    assert check_password_strength("Password123!")
    assert check_password_strength("Tr@deHub2024")
    assert check_password_strength("Secur3P@ssw0rd")
    assert check_password_strength("C0mpl3x!P@ss") 