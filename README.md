# Исходный код Бэкэнда(API) на FastAPI
## Автор - Искрин Артём

## Остальной код, ссылки для тестирования и видео работы:
  • Swagger UI: [https://energy-monitor-fastapi-production.up.railway.app/docs](https://energy-monitor-fastapi-production.up.railway.app/docs)  
  • Пользовательский сайт: [https://green-energy-reporter.netlify.app/](https://green-energy-reporter.netlify.app/)  
  • GitHub фронтенда: [https://github.com/deprotate/energy-monitor-frontend](https://github.com/deprotate/energy-monitor-frontend)  
  • GitHub Wemos: [https://github.com/deprotate/wemos-energy-monitor](https://github.com/deprotate/wemos-energy-monitor)  
• Видео работы: [https://disk.yandex.ru/d/vQEiWjrruTO2ig](https://disk.yandex.ru/d/vQEiWjrruTO2ig)

  

## Описание Бэкэнда(API)



- **Бэкенд (API)** – реализован на FastAPI с асинхронным программированием (Python 3.12, SQLAlchemy 2.0, asyncpg). Взаимодействует с базой данных PostgreSQL и предоставляет REST-эндпоинты для приёма данных с устройств (Wemos D1 Mini) и формирования отчётов.

---

###  Подробное описание файлов бэкенда

####  main.py

**Назначение:**  
Точка входа в приложение. Здесь происходит:

- Инициализация FastAPI.
- Настройка жизненного цикла приложения (через `asynccontextmanager`), что позволяет при запуске создать все таблицы в базе данных.
- Подключение CORS-мидлвэра для разрешения запросов с любых источников.
- Включение роутинга (подключение маршрутов из `api_v1/energy/views.py`).
- Определение эндпоинта `/`, возвращающего «OK» для проверки работоспособности API.

---

####  api_v1/energy/views.py

**Назначение:**  
Определяет REST-эндпоинты для работы с данными о энергии. Все маршруты используют асинхронную сессию базы данных, получаемую через зависимость `db_helper.session_dependency`.

**Основные эндпоинты:**

- **GET /energy/**  
  _Описание:_ Возвращает список всех записей о энергии.  
  _Метод из CRUD:_ `get_energy_list`

- **GET /energy/{energy_id}/**  
  _Описание:_ Возвращает конкретную запись по идентификатору.  
  _Метод из CRUD:_ `get_energy`

- **POST /create_energy/**  
  _Описание:_ Принимает данные в теле запроса для создания новой записи.  
  _Метод из CRUD:_ `create_energy`  
  _Пример запроса (JSON):_
  ```json
  {
    "type": 1,
    "value": 15
  }
  ```
  _Пример ответа (JSON):_
  ```json
  {
    "id": 101,
    "type": 1,
    "value": 15,
    "created_at": "14.02.2025 in 12.34.56"
  }
  ```

- **GET /report/**  
  _Описание:_ Формирует сводный отчёт, используя агрегирующие функции.  
  _Пример ответа (JSON):_
  ```json
  {
    "1": 150,
    "2": 120,
    "3": 30,
    "4": 0
  }
  ```
  Здесь:
  - `"1"` – суммарное значение потреблённой энергии.
  - `"2"` – суммарное значение произведённой энергии.
  - `"3"` – разница (если потребленная энергия больше произведенной).
  - `"4"` – обратная разница.

- **GET /report_by_date/**  
  _Описание:_ Позволяет получить отчёт за указанный диапазон дат. Принимает параметры:
  - `start_date` и `end_date` (формат `YYYY-MM-DD`);
  - необязательный параметр `group_by` (принимает значения: `day`, `month`, `year`).
  
  _Пример запроса без группировки (полный агрегат):_
  ```
  GET /report_by_date/?start_date=2025-02-10&end_date=2025-02-14
  ```
  _Пример ответа (JSON):_
  ```json
  {
    "1": 47,
    "2": 35,
    "3": 12,
    "4": 0
  }
  ```
  
  _Пример запроса с группировкой по дням:_
  ```
  GET /report_by_date/?start_date=2025-02-10&end_date=2025-02-15&group_by=day
  ```
  _Пример ответа (JSON):_
  ```json
  {
    "10.02.2025": {"1": 0, "2": 0, "3": 0, "4": 0},
    "11.02.2025": {"1": 0, "2": 0, "3": 0, "4": 0},
    "12.02.2025": {"1": 0, "2": 0, "3": 0, "4": 0},
    "13.02.2025": {"1": 15, "2": 10, "3": 5, "4": 0},
    "14.02.2025": {"1": 0, "2": 0, "3": 0, "4": 0},
    "15.02.2025": {"1": 0, "2": 0, "3": 0, "4": 0}
  }
  ```

---

####  api_v1/energy/crud.py

**Назначение:**  
Содержит бизнес-логику для работы с данными. Здесь реализуются функции для создания записей, выборки данных и формирования отчётов с использованием агрегатных SQL-запросов.

**Основные функции:**

- **create_energy(session, energy_data) → Energy**  
  Создаёт новую запись в таблице `energy`.  
  _Логика:_  
  1. Создание объекта модели `Energy` на основе данных, прошедших валидацию Pydantic-схемой `CreateEnergy`.
  2. Добавление объекта в сессию, выполнение commit и обновление объекта через `session.refresh`.

- **get_energy_list(session) → list**  
  Выполняет запрос для выборки всех записей и возвращает список объектов, представленных через схему `EnergyResponse`.

- **get_energy(session, energy_id) → EnergyResponse | None**  
  Выполняет выборку записи по `id` и возвращает объект, если запись найдена, иначе `None`.

- **report(session)**  
  Выполняет агрегирующий запрос для подсчёта суммарных значений по типам энергии (например, разницу между потреблённой и произведённой энергией).

- **get_report_by_range(session, start_date, end_date)**  
  Выполняет агрегирование данных за указанный диапазон дат без группировки по периодам.

- **get_report_by_date(session, start_date, end_date, group_by)**  
  Группирует данные по заданному периоду (день, месяц или год) с использованием SQL-функции `to_char`. Дополнительно генерируются все периоды в диапазоне, что позволяет заполнить отсутствующие значения нулями.

_Примечание:_  
Функция `generate_periods` внутри `get_report_by_date` отвечает за генерацию всех возможных периодов (с учётом типа группировки) и объединяет их с данными из БД.

---

#### api_v1/energy/schemas.py

**Назначение:**  
Определяет модели для валидации входящих запросов и формирования ответов. Использование Pydantic обеспечивает автоматическую проверку типов.

**Основные модели:**

- **CreateEnergy**  
  Модель для создания записи.  
  _Поля:_  
  - `type`: число, принимающее значения 1 (потребленная энергия) или 2 (произведенная энергия).
  - `value`: числовое значение энергии.

- **EnergyResponse**  
  Модель для возврата данных о записи.  
  _Поля:_  
  - `id`: идентификатор записи.
  - `type`: тип записи.
  - `value`: значение энергии.
  - `created_at`: дата и время создания, сериализуемые в формат «ДД.ММ.ГГГГ in ЧЧ.ММ.СС».

_Пример ответа:_  
При запросе записи может вернуться:
```json
{
  "id": 55,
  "type": 2,
  "value": 30,
  "created_at": "14.02.2025 in 12.34.56"
}
```

---

####  Конфигурация базы данных и модели

**api_v1/core/config.py**

- **Назначение:**  
  Содержит настройки приложения (хост, порт) и формирует URL для подключения к PostgreSQL. При необходимости производится замена префикса URL для использования асинхронного драйвера asyncpg.

**api_v1/core/DbHelper.py**

- **Назначение:**  
  Создаёт асинхронный SQLAlchemy-движок и фабрику сессий для работы с базой данных.  
  _Ключевые моменты:_  
  - Функция `session_dependency` используется как зависимость в эндпоинтах FastAPI для получения асинхронной сессии.
  - Метод `get_scopped_session` позволяет создавать сессии, привязанные к текущей задаче (scope).

**api_v1/core/models/Base.py**

- **Назначение:**  
  Определяет базовый класс для всех моделей SQLAlchemy. Автоматически генерирует имя таблицы на основе имени модели и включает общее поле `id`.

**api_v1/core/models/Energy.py**

- **Назначение:**  
  Определяет модель `Energy`, которая отражает записи о потреблённой и произведённой энергии.  
  _Поля модели:_  
  - `type`: целое число.
  - `value`: целое число.
  - `created_at`: дата и время создания записи, автоматически заполняемое через `func.now()`.

---
