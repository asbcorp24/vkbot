import sqlite3

def create_database():
    conn = sqlite3.connect("bot_buttons.db")
    cursor = conn.cursor()

    # Таблица для кнопок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,            -- Текст вопроса или кнопки
            response TEXT NOT NULL,            -- Ответ на кнопку
            parent_id INTEGER DEFAULT 0,       -- Родительский ID
            request_type INTEGER DEFAULT 0,    -- Тип запроса (0 = стандартный, 1 = анкета)
            dop TEXT DEFAULT NULL,             -- Дополнительные данные (например, JSON для анкет)
            media_url TEXT DEFAULT NULL        -- Ссылка на медиа (картинка или документ)
        )
    ''')

    # Таблица для результатов анкет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS survey_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,          -- ID пользователя, заполнившего анкету
            answers TEXT NOT NULL,             -- Ответы в формате JSON
            file_url TEXT DEFAULT NULL,        -- Ссылка на загруженный файл (если есть)
            survey_name TEXT DEFAULT NULL,     -- Название анкеты
            created_at TEXT DEFAULT NULL       -- Дата и время заполнения анкеты
        )
    ''')

    conn.commit()
    conn.close()
    print("База данных успешно создана!")

def seed_database():
    conn = sqlite3.connect("bot_buttons.db")
    cursor = conn.cursor()

    # Пример данных для кнопок
    buttons = [
        (1, "Главное меню", "Выберите опцию:", 0, 0, None, None),
        (2, "Расписание", "Вот ваше расписание на сегодня:\n1. Математика\n2. Физика", 1, 0, None, None),
        (3, "Помощь", "Я могу помочь с расписанием, информацией о школе и ответами на вопросы.", 1, 0, None, None),
        (4, "Контакты", "Контакты:\n- Администрация: 123-456\n- Секретарь: 789-012", 3, 0, None, None),
        (5, "Анкета", "Пожалуйста, ответьте на следующие вопросы:", 1, 1, '["Ваше имя?", "Ваш возраст?", "Ваш любимый предмет?"]', None)
    ]

    cursor.executemany('''
        INSERT INTO buttons (id, question, response, parent_id, request_type, dop, media_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', buttons)

    conn.commit()
    conn.close()
    print("Примерные данные добавлены в базу!")

# Создаем базу данных и добавляем данные
create_database()
seed_database()
