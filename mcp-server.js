// mcp-server.js
// Скрипт для запуска MCP сервера для TradeHub (Упрощенная версия)

const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

// Версия MCP сервера
const MCP_VERSION = '1.0.1';
const PORT = 3025;
const HOST = 'localhost';

// Проверка наличия необходимых пакетов
const checkDependencies = () => {
  try {
    require.resolve('ws');
    console.log('✓ WebSocket модуль найден');
    return true;
  } catch (err) {
    console.log('✗ Отсутствует модуль ws');
    console.log('Установка ws...');
    
    const installProcess = spawnSync('npm', ['install', 'ws', '--save'], { 
      stdio: 'inherit',
      shell: true 
    });
    
    if (installProcess.status !== 0) {
      console.error('Ошибка при установке ws');
      return false;
    }
    
    console.log('✓ Модуль ws успешно установлен');
    return true;
  }
};

// Запуск встроенного MCP сервера
const startMcpServer = async () => {
  console.log(`Запуск TradeHub MCP сервера на порту ${PORT}...`);
  
  // Создаем HTTP сервер
  const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
      res.writeHead(204);
      res.end();
      return;
    }
    
    if (req.url === '/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ 
        status: 'ok',
        version: MCP_VERSION,
        timestamp: new Date().toISOString()
      }));
      return;
    }
    
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not found' }));
  });
  
  // Создаем WebSocket сервер
  const wss = new WebSocket.Server({ server });
  
  // Коллекция подключенных клиентов
  const clients = new Set();
  
  // Обработка WebSocket соединений
  wss.on('connection', (ws, req) => {
    const clientIp = req.socket.remoteAddress;
    console.log(`👤 Клиент подключен: ${clientIp}`);
    clients.add(ws);
    
    // Отправляем приветственное сообщение
    ws.send(JSON.stringify({
      type: 'system',
      message: 'Добро пожаловать в TradeHub MCP Server',
      version: MCP_VERSION,
      timestamp: new Date().toISOString()
    }));
    
    // Обработка сообщений от клиента
    ws.on('message', (message) => {
      try {
        const data = JSON.parse(message);
        console.log(`📥 Получено сообщение: тип=${data.type || 'неизвестно'}, ${data.name || ''}`);
        
        // Обработка различных типов сообщений
        if (data.type === 'event') {
          // Логирование событий
          const timestamp = new Date().toISOString();
          const logEntry = `[${timestamp}] EVENT: ${data.name} - ${JSON.stringify(data.data)}`;
          console.log(logEntry);
          
          // Сохранение событий в лог-файл
          fs.appendFile('mcp-events.log', logEntry + '\n', (err) => {
            if (err) console.error('Ошибка при записи в лог-файл:', err);
          });
        } else if (data.type === 'error') {
          // Логирование ошибок
          const timestamp = new Date().toISOString();
          const logEntry = `[${timestamp}] ERROR: ${data.message} - ${data.stack || 'No stack trace'}`;
          console.error(logEntry);
          
          // Сохранение ошибок в лог-файл
          fs.appendFile('mcp-errors.log', logEntry + '\n', (err) => {
            if (err) console.error('Ошибка при записи в лог-файл:', err);
          });
          
          console.error(`❌ Ошибка от клиента: ${data.message}`);
        }
      } catch (err) {
        console.error('Ошибка при обработке сообщения:', err);
      }
    });
    
    // Обработка закрытия соединения
    ws.on('close', () => {
      console.log(`👋 Клиент отключен: ${clientIp}`);
      clients.delete(ws);
    });
    
    // Обработка ошибок соединения
    ws.on('error', (err) => {
      console.error(`Ошибка WebSocket соединения с ${clientIp}:`, err);
      clients.delete(ws);
    });
  });
  
  // Запуск сервера
  server.listen(PORT, HOST, () => {
    console.log(`🚀 MCP сервер запущен на http://${HOST}:${PORT}`);
    console.log(`📊 WebSocket сервер запущен на ws://${HOST}:${PORT}`);
    
    // Периодическая отправка пинг-сообщений клиентам
    setInterval(() => {
      const timestamp = new Date().toISOString();
      
      if (clients.size > 0) {
        console.log(`📡 Отправка ping: ${timestamp} (активных клиентов: ${clients.size})`);
        
        clients.forEach((client) => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({
              type: 'ping',
              timestamp
            }));
          }
        });
      }
    }, 30000); // каждые 30 секунд
  });
  
  // Обработка ошибок сервера
  server.on('error', (err) => {
    console.error('Ошибка сервера:', err);
    process.exit(1);
  });
  
  // Обновление конфигурационного файла Cursor
  updateCursorConfig();
};

// Обновляем конфигурацию Cursor
const updateCursorConfig = () => {
  const mcpConfigPath = path.join(process.env.USERPROFILE || process.env.HOME, '.cursor', 'mcp.json');
  const mcpConfigDir = path.dirname(mcpConfigPath);
  
  if (!fs.existsSync(mcpConfigDir)) {
    try {
      fs.mkdirSync(mcpConfigDir, { recursive: true });
      console.log(`✓ Создана директория для конфигурации: ${mcpConfigDir}`);
    } catch (err) {
      console.error(`Ошибка при создании директории ${mcpConfigDir}:`, err);
      return;
    }
  }
  
  const mcpConfig = {
    mcpServers: {
      'browser-tools': {
        command: 'node mcp-server.js',
        browserToolsConfig: {
          serverHost: HOST,
          serverPort: PORT,
          disableDiscovery: true
        }
      }
    }
  };
  
  try {
    fs.writeFileSync(mcpConfigPath, JSON.stringify(mcpConfig, null, 2));
    console.log(`✓ Обновлен конфигурационный файл Cursor: ${mcpConfigPath}`);
  } catch (err) {
    console.error('Ошибка при обновлении конфигурационного файла Cursor:', err);
  }
};

// Обработка сигналов завершения
process.on('SIGINT', () => {
  console.log('\nЗавершение работы MCP сервера...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\nЗавершение работы MCP сервера...');
  process.exit(0);
});

// Основная функция
const main = async () => {
  console.log('=== TradeHub MCP Server ===');
  console.log(`Версия: ${MCP_VERSION}`);
  console.log('===========================');
  
  if (!checkDependencies()) {
    console.error('Не удалось установить необходимые зависимости');
    process.exit(1);
  }
  
  try {
    await startMcpServer();
  } catch (err) {
    console.error('Ошибка при запуске MCP сервера:', err);
    process.exit(1);
  }
};

// Старт программы
main();