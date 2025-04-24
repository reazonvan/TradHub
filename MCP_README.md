# TradeHub MCP (Model-Control-Presenter)

## Описание

MCP (Model-Control-Presenter) - модуль для TradeHub, обеспечивающий аналитику, отладку и тестирование веб-приложения. Он предоставляет:

- Отслеживание взаимодействия пользователей с сайтом
- Логирование ошибок и исключений
- Аналитику использования функций
- Отладку в режиме реального времени
- Возможность автоматизированного тестирования

## Установка

1. Убедитесь, что в системе установлен Node.js
2. Установите зависимости:

```bash
npm install
```

## Запуск MCP сервера

```bash
npm run start-mcp
```

MCP сервер запустится на порту 3025 и будет готов к подключению из браузера.

## Использование в коде

### Отслеживание событий

```javascript
// Отправка события в MCP
browserTools.logEvent('customEvent', { 
  property1: 'value1',
  property2: 'value2'
});
```

### Отслеживание ошибок

```javascript
try {
  // Ваш код
} catch (error) {
  browserTools.logError(error);
}
```

### Отслеживание элементов DOM

```javascript
// Отслеживание кликов по определенным элементам
browserTools.trackElement('.my-button', {
  click: (element) => {
    console.log('Кнопка нажата:', element);
    // Ваша логика
  }
});
```

## Доступные методы API

### browserTools

- `logEvent(name, data)` - логирует событие с указанным именем и данными
- `logError(error)` - логирует ошибку
- `trackElement(selector, events)` - отслеживает события на DOM-элементах
- `connect()` - принудительно подключается к MCP серверу
- `init()` - инициализирует MCP

### dataService

Модуль для работы с данными, который интегрирован с MCP для отслеживания ошибок:

- `products.getAll()` - получает все продукты
- `products.getById(id)` - получает продукт по ID
- `products.search(query)` - поиск продуктов
- `user.getCurrent()` - получает текущего пользователя
- `user.getCart()` - получает корзину пользователя
- `user.getOrders()` - получает заказы пользователя
- `cart.addItem(productId, quantity)` - добавляет товар в корзину
- `cart.removeItem(itemId)` - удаляет товар из корзины
- `cart.updateQuantity(itemId, quantity)` - обновляет количество товара в корзине

## Структура файлов MCP

- `static/js/browser-tools-mcp.js` - основной клиентский модуль MCP
- `mcp-server.js` - серверная часть MCP
- `package.json` - зависимости и скрипты для запуска MCP
- `MCP_README.md` - документация по MCP

## Настройка

Настройки MCP находятся в начале файла `static/js/browser-tools-mcp.js`:

```javascript
const config = {
  serverHost: '127.0.0.1',
  serverPort: 3025,
  disableDiscovery: false,
  projectName: 'TradeHub',
  debug: false
};
```

Вы можете изменить эти настройки в соответствии с вашими потребностями. 