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
            dop TEXT DEFAULT NULL,             -- Дополнительные данные (JSON для анкеты)
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

    # Пример стандартных кнопок
    buttons = [
        (1, "Главное меню", "Выберите опцию:", 0, 0, None, None),
        (2, "Расписание", "Вот ваше расписание:\n1. Математика\n2. Физика", 1, 0, None, None),
        (3, "Контакты", "Контакты школы:\nТелефон: 123-456-789\nE-mail: school@example.com", 1, 0, None, None),
        (4, "Анкета", "Пожалуйста, заполните анкету:", 1, 1, '''
        [
            {"text": "Ваше имя?", "answer_type": 1},
            {"text": "Введите вашу дату рождения (YYYY-MM-DD):", "answer_type": 2},
            {"text": "Введите ваш возраст:", "answer_type": 3},
            {"text": "Загрузите ваше фото:", "answer_type": 4},
            {"text": "Загрузите документ в формате PDF:", "answer_type": 5}
        ]
        ''', None)
    ]

    cursor.executemany('''
        INSERT INTO buttons (id, question, response, parent_id, request_type, dop, media_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', buttons)

    conn.commit()
    conn.close()
    print("Демо-данные успешно добавлены!")

if __name__ == "__main__":
    create_database()
    seed_database()
