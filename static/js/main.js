// Основной файл JavaScript для TradeHub

// Функция для инициализации функциональности сайта
function initTradeHub() {
    console.log('TradeHub: инициализация');
    
    // Инициализация всех компонентов
    initAnimations();
    initLazyLoading();
    initWebSockets();
    
    // Инициализация обработчиков событий
    document.addEventListener('DOMContentLoaded', function() {
        // Обработчики для фильтров на странице товаров
        initFilters();
        
        // Обработчики для модальных окон
        initModals();
        
        // Обработчики для форм
        initForms();
    });
}

// Инициализация анимаций
function initAnimations() {
    // Находим все элементы с анимациями
    const animatedElements = document.querySelectorAll('[data-animate]');
    
    if (animatedElements.length > 0) {
        console.log('TradeHub: инициализация анимаций');
        
        // Создаем наблюдатель за видимостью
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                // Если элемент стал видимым
                if (entry.isIntersecting) {
                    // Получаем тип анимации
                    const animationType = entry.target.dataset.animate;
                    // Добавляем класс для анимации
                    entry.target.classList.add(`animate-${animationType}`);
                    // Прекращаем наблюдение за этим элементом
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1 // Триггер при видимости 10% элемента
        });
        
        // Начинаем наблюдать за элементами
        animatedElements.forEach(element => {
            observer.observe(element);
        });
    }
}

// Ленивая загрузка изображений
function initLazyLoading() {
    const lazyImages = document.querySelectorAll('img[data-src]');
    
    if (lazyImages.length > 0) {
        console.log('TradeHub: инициализация ленивой загрузки');
        
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('fade-in');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    }
}

// Инициализация WebSocket для чата
function initWebSockets() {
    const chatContainer = document.getElementById('chat-container');
    
    if (chatContainer) {
        console.log('TradeHub: инициализация WebSocket для чата');
        
        const chatId = chatContainer.dataset.chatId;
        const token = chatContainer.dataset.token;
        
        if (chatId && token) {
            const socket = new WebSocket(`ws://${window.location.host}/chat/ws/${chatId}?token=${token}`);
            
            socket.onopen = function(e) {
                console.log('WebSocket соединение установлено');
                chatContainer.classList.remove('offline');
                chatContainer.classList.add('online');
            };
            
            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleChatMessage(data);
            };
            
            socket.onclose = function(event) {
                console.log('WebSocket соединение закрыто');
                chatContainer.classList.remove('online');
                chatContainer.classList.add('offline');
                
                // Попытка переподключения через 5 секунд
                setTimeout(initWebSockets, 5000);
            };
            
            socket.onerror = function(error) {
                console.error('WebSocket ошибка:', error);
            };
            
            // Сохраняем сокет в глобальной переменной
            window.chatSocket = socket;
            
            // Обработчик отправки сообщений
            const messageForm = document.getElementById('message-form');
            if (messageForm) {
                messageForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const input = this.querySelector('input[name="message"]');
                    const message = input.value.trim();
                    
                    if (message) {
                        // Отправка сообщения через WebSocket
                        socket.send(JSON.stringify({
                            content: message
                        }));
                        
                        // Очистка поля ввода
                        input.value = '';
                    }
                });
            }
        }
    }
}

// Обработка сообщений чата
function handleChatMessage(data) {
    const messagesContainer = document.getElementById('chat-messages');
    
    if (messagesContainer) {
        if (data.type === 'message') {
            // Создаем новый элемент сообщения
            const messageElement = document.createElement('div');
            messageElement.className = 'p-3 rounded-lg mb-2';
            
            // Добавляем классы в зависимости от отправителя
            if (data.sender_id === parseInt(messagesContainer.dataset.userId)) {
                messageElement.classList.add('bg-accent-teal/10', 'ml-auto');
            } else {
                messageElement.classList.add('bg-gray-100');
            }
            
            // Формируем содержимое сообщения
            messageElement.innerHTML = `
                <div class="flex items-start">
                    <div class="flex-1">
                        <div class="flex items-center mb-1">
                            <span class="font-semibold">${data.sender.username}</span>
                            <span class="text-xs text-gray-500 ml-2">${new Date(data.created_at).toLocaleTimeString()}</span>
                        </div>
                        <p>${data.content}</p>
                    </div>
                </div>
            `;
            
            // Добавляем сообщение в контейнер
            messagesContainer.appendChild(messageElement);
            
            // Прокручиваем чат к последнему сообщению
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } else if (data.type === 'connection') {
            // Обрабатываем уведомления о подключении/отключении
            const statusElement = document.createElement('div');
            statusElement.className = 'text-center text-sm text-gray-500 my-2';
            
            statusElement.textContent = data.connected 
                ? `${data.username} подключился к чату` 
                : `${data.username} вышел из чата`;
            
            messagesContainer.appendChild(statusElement);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
}

// Инициализация фильтров
function initFilters() {
    const filterForm = document.getElementById('filter-form');
    
    if (filterForm) {
        console.log('TradeHub: инициализация фильтров');
        
        // HTMX уже обрабатывает отправку формы, просто добавляем вспомогательную логику
        
        // Сброс фильтров
        const resetButton = document.getElementById('reset-filters');
        if (resetButton) {
            resetButton.addEventListener('click', function() {
                const inputs = filterForm.querySelectorAll('input:not([type="hidden"]), select');
                inputs.forEach(input => {
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        input.checked = false;
                    } else {
                        input.value = '';
                    }
                });
                
                // Триггерим событие изменения для HTMX
                filterForm.dispatchEvent(new Event('change'));
            });
        }
        
        // Мобильные фильтры
        const mobileFilterToggle = document.getElementById('mobile-filter-toggle');
        const filterSidebar = document.getElementById('filter-sidebar');
        
        if (mobileFilterToggle && filterSidebar) {
            mobileFilterToggle.addEventListener('click', function() {
                filterSidebar.classList.toggle('hidden');
                filterSidebar.classList.toggle('block');
            });
        }
    }
}

// Инициализация модальных окон
function initModals() {
    // Модальные окна обычно управляются Alpine.js, но мы можем добавить дополнительную логику
    
    // Обработчик для закрытия модальных окон по клавише Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('[x-data][data-modal]');
            modals.forEach(modal => {
                // Вызываем Alpine.js метод закрытия модального окна
                if (typeof Alpine !== 'undefined') {
                    Alpine.dispatchEvent(modal, 'close-modal');
                }
            });
        }
    });
}

// Инициализация форм
function initForms() {
    // Находим все формы на странице
    const forms = document.querySelectorAll('form:not([data-no-enhance])');
    
    forms.forEach(form => {
        // Добавляем проверку на заполнение обязательных полей
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let hasErrors = false;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    hasErrors = true;
                    
                    // Добавляем класс ошибки
                    field.classList.add('border-red-500');
                    
                    // Добавляем сообщение об ошибке, если его еще нет
                    const errorId = `${field.id}-error`;
                    if (!document.getElementById(errorId)) {
                        const errorElement = document.createElement('p');
                        errorElement.id = errorId;
                        errorElement.className = 'text-red-500 text-sm mt-1';
                        errorElement.textContent = 'Это поле обязательно для заполнения';
                        
                        field.parentNode.appendChild(errorElement);
                    }
                } else {
                    // Удаляем класс ошибки и сообщение, если поле заполнено
                    field.classList.remove('border-red-500');
                    
                    const errorElement = document.getElementById(`${field.id}-error`);
                    if (errorElement) {
                        errorElement.remove();
                    }
                }
            });
            
            // Если есть ошибки, предотвращаем отправку формы
            if (hasErrors) {
                e.preventDefault();
            }
        });
    });
}

// Запускаем инициализацию при загрузке страницы
initTradeHub(); 