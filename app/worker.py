from celery import Celery
from app.config import settings
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("celery_worker")

# Настройка Celery
celery = Celery("tradehub")
celery.conf.broker_url = settings.REDIS_URL
celery.conf.result_backend = settings.REDIS_URL

# Задачи Celery
@celery.task(name="send_email_notification")
def send_email_notification(email, subject, message):
    """
    Асинхронная задача для отправки email-уведомлений
    В данной реализации просто логируем сообщение, но
    в реальном приложении здесь должна быть интеграция с SMTP
    """
    logger.info(f"Отправка email на {email}, тема: {subject}")
    logger.info(f"Сообщение: {message}")
    
    # Пример кода для отправки email через SMTP
    # (закомментирован, т.к. требуется настройка SMTP-сервера)
    """
    try:
        smtp_server = settings.SMTP_SERVER
        smtp_port = settings.SMTP_PORT
        smtp_username = settings.SMTP_USERNAME
        smtp_password = settings.SMTP_PASSWORD
        
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_FROM
        msg['To'] = email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            
        logger.info(f"Email успешно отправлен на {email}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке email: {str(e)}")
        return False
    """
    
    # Возвращаем успех для демо-версии
    return True

@celery.task(name="process_order_payments")
def process_order_payments(order_id):
    """
    Асинхронная задача для обработки платежей по заказу
    В данной реализации просто логируем действие, но
    в реальном приложении здесь должна быть интеграция с платежным шлюзом
    """
    logger.info(f"Обработка платежа для заказа {order_id}")
    
    # Здесь должен быть код для обработки платежа через платежный шлюз
    
    return True

@celery.task(name="update_order_status")
def update_order_status(order_id, new_status):
    """
    Асинхронная задача для обновления статуса заказа
    """
    from app.database import SessionLocal
    from app.models.order import Order
    
    logger.info(f"Обновление статуса заказа {order_id} на {new_status}")
    
    try:
        db = SessionLocal()
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if order:
            order.status = new_status
            
            if new_status == "completed":
                order.completed_at = datetime.utcnow()
                
            db.commit()
            logger.info(f"Статус заказа {order_id} успешно обновлен на {new_status}")
        else:
            logger.error(f"Заказ {order_id} не найден")
            
        db.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса заказа: {str(e)}")
        return False

@celery.task(name="periodic_cleanup")
def periodic_cleanup():
    """
    Периодическая задача для очистки временных данных и старых записей
    """
    from app.database import SessionLocal
    from app.models.order import Order, OrderStatus
    
    logger.info("Запуск периодической очистки данных")
    
    try:
        db = SessionLocal()
        
        # Пример: автоматическая отмена зависших заказов
        # Отменяем заказы, которые находятся в статусе "pending" более 3 дней
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        pending_orders = db.query(Order).filter(
            Order.status == OrderStatus.PENDING.value,
            Order.created_at < three_days_ago
        ).all()
        
        for order in pending_orders:
            order.status = OrderStatus.CANCELLED.value
            logger.info(f"Автоматическая отмена заказа {order.id} из-за истечения времени ожидания")
        
        db.commit()
        db.close()
        
        logger.info(f"Очистка завершена, отменено {len(pending_orders)} заказов")
        return True
    except Exception as e:
        logger.error(f"Ошибка при выполнении периодической очистки: {str(e)}")
        return False

# Настройка периодических задач
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Запуск задачи очистки каждый день в полночь
    sender.add_periodic_task(
        86400.0,  # 24 часа = 86400 секунд
        periodic_cleanup.s(),
        name="daily_cleanup"
    ) 