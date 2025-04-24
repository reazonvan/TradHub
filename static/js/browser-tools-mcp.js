// browser-tools-mcp.js
// MCP (Model-Control-Presenter) конфигурация для TradeHub

// Инициализация Browser Tools
const browserTools = (function() {
  // Настройки MCP
  const config = {
    serverHost: 'localhost',
    serverPort: 3025,
    disableDiscovery: true,
    projectName: 'TradeHub',
    debug: true
  };
  
  // Приватные переменные
  let connected = false;
  const eventQueue = [];
  let socket = null;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 5;
  
  // Инициализация WebSocket соединения
  const connect = function() {
    if (connected) return Promise.resolve();
    
    return new Promise((resolve, reject) => {
      try {
        console.log(`MCP: Попытка подключения к WebSocket на 0.0.0.0:3025`);
        
        // Прямое подключение к WebSocket
        socket = new WebSocket(`ws://localhost:3025`);
        
        socket.onopen = function() {
          connected = true;
          reconnectAttempts = 0;
          console.log('MCP: Соединение установлено');
          
          // Отправляем все события из очереди
          while (eventQueue.length > 0) {
            const event = eventQueue.shift();
            sendEvent(event.name, event.data);
          }
          
          resolve();
        };
        
        socket.onclose = function(event) {
          connected = false;
          console.log(`MCP: Соединение закрыто, код: ${event.code}, причина: ${event.reason}`);
          
          // Пытаемся переподключиться
          if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            console.log(`MCP: Попытка переподключения ${reconnectAttempts}/${maxReconnectAttempts}`);
            setTimeout(connect, 3000);
          }
        };
        
        socket.onerror = function(error) {
          console.error('MCP: Ошибка соединения', error);
        };
      } catch (err) {
        console.error('MCP: Не удалось создать соединение', err);
        reject(err);
      }
    });
  };
  
  // Проверка доступности сервера с использованием обычного подключения WebSocket
  const checkServerAvailability = function() {
    return new Promise((resolve) => {
      console.log('MCP: Проверка доступности сервера...');
      
      const testSocket = new WebSocket('ws://localhost:3025');
      
      testSocket.onopen = function() {
        console.log('MCP: Сервер доступен');
        testSocket.close();
        resolve(true);
      };
      
      testSocket.onerror = function() {
        console.warn('MCP: Сервер недоступен');
        resolve(false);
      };
      
      // Если нет ответа в течение 3 секунд, считаем сервер недоступным
      setTimeout(() => {
        if (testSocket.readyState !== WebSocket.OPEN) {
          console.warn('MCP: Сервер не отвечает (таймаут)');
          resolve(false);
        }
      }, 3000);
    });
  };
  
  // Отправка события
  const sendEvent = function(name, data) {
    if (!connected || !socket) {
      // Если соединение не установлено, добавляем в очередь
      eventQueue.push({ name, data });
      return;
    }
    
    try {
      const event = {
        type: 'event',
        name: name,
        data: data || {},
        timestamp: new Date().toISOString(),
        url: window.location.href
      };
      
      socket.send(JSON.stringify(event));
      if (config.debug) {
        console.log('MCP: Отправлено событие', event);
      }
    } catch (e) {
      console.error('MCP: Ошибка при отправке события', e);
      // Добавляем обратно в очередь при ошибке
      eventQueue.push({ name, data });
    }
  };
  
  // Отправка ошибки
  const logError = function(error) {
    const errorData = {
      type: 'error',
      message: error.message || error.toString(),
      stack: error.stack,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent
    };
    
    if (!connected || !socket) {
      eventQueue.push({ name: 'error', data: errorData });
      return;
    }
    
    try {
      socket.send(JSON.stringify(errorData));
      if (config.debug) {
        console.log('MCP: Отправлена ошибка', errorData);
      }
    } catch (e) {
      console.error('MCP: Ошибка при отправке ошибки', e);
      eventQueue.push({ name: 'error', data: errorData });
    }
  };
  
  // Отслеживание элементов DOM
  const trackElement = function(selector, events) {
    try {
      const elements = document.querySelectorAll(selector);
      if (elements.length === 0 && config.debug) {
        console.warn(`MCP: Элементы по селектору '${selector}' не найдены`);
      }
      
      elements.forEach(element => {
        for (const eventName in events) {
          element.addEventListener(eventName, function(event) {
            try {
              // Вызываем обработчик события
              events[eventName](element, event);
            } catch (err) {
              console.error(`MCP: Ошибка в обработчике события ${eventName}`, err);
              logError(err);
            }
          });
        }
      });
    } catch (err) {
      console.error('MCP: Ошибка при отслеживании элементов', err);
      logError(err);
    }
  };
  
  // Автоматическое отслеживание основных событий
  const setupAutoTracking = function() {
    try {
      // Отслеживание кликов по кнопкам
      trackElement('button', {
        click: (element) => {
          sendEvent('buttonClick', {
            id: element.id || '',
            text: element.textContent?.trim() || '',
            class: element.className || ''
          });
        }
      });
      
      // Отслеживание отправки форм
      trackElement('form', {
        submit: (element, event) => {
          sendEvent('formSubmit', {
            id: element.id || '',
            action: element.action || window.location.href,
            method: element.method || 'GET'
          });
        }
      });
      
      // Отслеживание навигации
      trackElement('a', {
        click: (element) => {
          sendEvent('navigation', {
            href: element.href || '',
            text: element.textContent?.trim() || ''
          });
        }
      });
      
      // Отслеживание глобальных ошибок
      window.addEventListener('error', (event) => {
        logError({
          message: event.message || 'Неизвестная ошибка',
          source: event.filename || '',
          line: event.lineno || 0,
          column: event.colno || 0,
          stack: event.error?.stack || ''
        });
      });
      
      // Отслеживание необработанных Promise-ошибок
      window.addEventListener('unhandledrejection', (event) => {
        logError({
          message: 'Unhandled Promise Rejection',
          reason: event.reason?.toString() || 'Нет данных',
          stack: event.reason?.stack || ''
        });
      });
      
      // Отслеживание изменений состояния страницы
      window.addEventListener('load', () => {
        sendEvent('pageLoad', {
          title: document.title,
          url: window.location.href,
          referrer: document.referrer,
          loadTime: performance.now()
        });
      });
      
      // Отслеживание ухода со страницы
      window.addEventListener('beforeunload', () => {
        sendEvent('pageExit', {
          title: document.title,
          url: window.location.href,
          timeSpent: performance.now()
        });
      });
      
      console.log('MCP: Автоматическое отслеживание настроено');
    } catch (err) {
      console.error('MCP: Ошибка при настройке отслеживания', err);
      logError(err);
    }
  };
  
  // Инициализация модуля
  const init = function() {
    console.log('MCP: Инициализация...');
    
    // Сначала проверяем доступность сервера
    checkServerAvailability()
      .then(isAvailable => {
        if (isAvailable) {
          return connect();
        } else {
          console.log('MCP: Сервер недоступен, работаем в автономном режиме');
          throw new Error('Сервер недоступен');
        }
      })
      .then(() => {
        setupAutoTracking();
        sendEvent('init', { timestamp: new Date().toISOString() });
        console.log('MCP: Успешная инициализация');
      })
      .catch((err) => {
        console.warn('MCP: Инициализация в автономном режиме', err);
        // Настраиваем отслеживание даже при ошибке подключения
        setupAutoTracking();
      });
  };
  
  // Публичный API
  return {
    connect: connect,
    logEvent: sendEvent,
    logError: logError,
    trackElement: trackElement,
    init: init,
    getStatus: function() {
      return {
        connected,
        queueLength: eventQueue.length,
        reconnectAttempts
      };
    }
  };
})();

// Инициализация после загрузки DOM
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', browserTools.init);
} else {
  browserTools.init();
}

// Модуль для работы с данными
const dataService = (function() {
  const fetchJson = async (url, options = {}) => {
    try {
      console.log(`MCP: Отправка запроса к ${url}`, options);
      const response = await fetch(url, options);
      
      if (!response.ok) {
        const error = new Error(`HTTP error! Status: ${response.status}`);
        error.status = response.status;
        error.statusText = response.statusText;
        error.url = url;
        browserTools.logError(error);
        throw error;
      }
      
      return await response.json();
    } catch (error) {
      console.error(`MCP: Ошибка запроса к ${url}`, error);
      browserTools.logError(error);
      throw error;
    }
  };
  
  return {
    products: {
      getAll: () => fetchJson('/products/api'),
      getById: (id) => fetchJson(`/products/api/${id}`),
      search: (query) => fetchJson(`/products/search?q=${query}`)
    },
    user: {
      getCurrent: () => fetchJson('/users/me'),
      getCart: () => fetchJson('/cart/api'),
      getOrders: () => fetchJson('/orders/api')
    },
    cart: {
      addItem: (productId, quantity = 1) => fetchJson('/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, quantity })
      }),
      removeItem: (itemId) => fetchJson(`/cart/remove/${itemId}`, {
        method: 'DELETE'
      }),
      updateQuantity: (itemId, quantity) => fetchJson(`/cart/update/${itemId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity })
      })
    }
  };
})();

// Экспорт для использования с Node.js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { browserTools, dataService };
} 