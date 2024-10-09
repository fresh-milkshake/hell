# Техническое задание (ТЗ) - Обновленная версия

## Название проекта: 
Система управления Telegram-ботами и демонами с использованием HellAPI и Django

## Общая архитектура системы:
1. **HellAPI** — центральный API, управляющий системой "Hell". Реализован на основе FastAPI и предоставляет набор эндпоинтов для управления демонами, мониторинга состояния и работы с API-ключами. API должен быть спроектирован таким образом, чтобы обеспечить максимальную гибкость и возможность интеграции с различными приложениями.
2. **Django-приложение** — веб-интерфейс для пользователей, который взаимодействует с HellAPI для управления ботами и конфигурацией, а также предоставляет функции аутентификации и авторизации. Django-приложение полностью зависит от HellAPI и использует его для всех операций.

> **Замечание:** Django-приложение полностью изолировано от системы Hell и взаимодействует с ней только через API. HellAPI является центральным компонентом, который позволяет управлять системой "Hell" и взаимодействовать с любыми приложениями.

## Требования к функционалу

### 1. Оптимизация Hell и его API
- **Переход на асинхронное выполнение операций:**
  - Рассмотреть возможность переписывания класса `Hell` с использованием асинхронных подходов (например, с использованием `asyncio`), чтобы лучше интегрировать его с FastAPI и улучшить производительность.
  - Важно обеспечить, чтобы все операции по управлению демонами и обработке запросов API выполнялись асинхронно, чтобы избежать блокировки и повысить скорость работы системы.

- **Перепроектирование синглтона:**
  - Оптимизировать синглтон для класса `Hell` таким образом, чтобы он поддерживал асинхронное создание и управление экземплярами. Это может включать использование асинхронного инициализатора и контроллера состояния, который будет следить за состоянием экземпляра и управлять его доступом.

### 2. Расширенные API эндпоинты HellAPI
- **Основные эндпоинты:**
  1. `POST /api/hell/start` — Запуск системы "Hell".
  2. `POST /api/hell/stop` — Остановка системы "Hell".
  3. `POST /api/hell/restart` — Перезапуск системы "Hell".
  4. `GET /api/hell/metrics` — Получение метрик системы (состояние и производительность). Требуется API-ключ (`X-API-KEY`).

- **Эндпоинты для управления демонами:**
  1. `GET /api/daemons/` — Возвращает список всех демонов.
  2. `POST /api/daemon/start` — Запуск нового демона.
  3. `POST /api/daemon/stop` — Остановка демона.
  4. `POST /api/daemon/restart` — Перезапуск демона.
  5. `POST /api/daemons/create` — Создание нового демона.

- **Эндпоинты для управления API-ключами:**
  1. `POST /api/generate-api-key` — Генерация нового API-ключа на основе кода приглашения.
  2. `POST /api/create-invitation` — Создание нового кода приглашения.

> **Замечание:** Все запросы требуют аутентификации с использованием API-ключа, за исключением эндпоинтов для создания приглашений и генерации API-ключей.

### 3. Обновление кода Telegram-ботов
- **Способы обновления:**
  - Через репозиторий GitHub:
    - Полное клонирование проекта и замена всех файлов в директории бота на новые версии из репозитория.
  - Через загрузку архива:
    - Проверка сигнатур всех файлов. Обновляются только файлы, сигнатуры которых отличаются от текущих версий.
- **Доступность обновления:**
  - Обновление кода и файлов ботов доступно через интерфейс Django-приложения. Django отправляет запросы к HellAPI для выполнения этих операций.

### 4. Логи и Мониторинг
- **Централизованное логирование:**
  - Все логи (Django, FastAPI и Hell) собираются централизованно с использованием ELK или Grafana+Loki.
- **Метрики и мониторинг:**
  - Интеграция с Prometheus для сбора метрик о состоянии демонов, загрузке системы и состоянии API.
  - Настройка дашбордов в Grafana для визуализации метрик и мониторинга состояния системы.

### 5. Обработка ошибок и повторные попытки
- **Ретраи и глобальная обработка ошибок:**
  - В HellAPI используется библиотека Tenacity для повторных попыток в случае временных ошибок (например, при запуске демона).
  - Настройка глобального обработчика ошибок для логирования и уведомлений о критических проблемах.

### 6. Документация и тестирование API
- **Swagger/OpenAPI:**
  - HellAPI предоставляет документацию Swagger для всех эндпоинтов, что позволяет удобно тестировать API и интегрировать новые приложения.
- **Автоматизированные тесты:**
  - В Django и FastAPI реализуются тесты на основе pytest для проверки корректности взаимодействия с HellAPI и работы всех эндпоинтов.

### 7. Оптимизация работы с конфигурациями и автообнаружение устройств Hell
- **Автообнаружение Hell:**
  - HellAPI реализует механизм автообнаружения устройства Hell через mDNS или другой механизм.
  - В случае недоступности IP, Django автоматически ищет новое подключение.
- **API для управления конфигурациями:**
  - HellAPI предоставляет эндпоинты для загрузки и обновления конфигураций демонов, что позволяет легко менять параметры демонов и обновлять их настройки через веб-интерфейс Django.

## Технические требования:
1. **Языки и технологии:**
   - Python, FastAPI (HellAPI), Django (веб-интерфейс), Redis (кеширование и Pub/Sub), Prometheus и Grafana (мониторинг), Logstash/Elasticsearch/Kibana или Loki (логирование).
2. **Интеграция и взаимодействие:**
   - Вся система построена на взаимодействии через HellAPI, что обеспечивает гибкость и возможность масштабирования.

## Цель проекта
Обеспечить эффективное и безопасное управление Telegram-ботами и демонами с возможностью интеграции множества приложений через центральный API. Django выступает как один из интерфейсов взаимодействия, предоставляя веб-доступ и расширенные функции управления.

> Пожалуйста, ознакомьтесь с этим обновленным ТЗ и уточните, если есть дополнительные правки или замечания.