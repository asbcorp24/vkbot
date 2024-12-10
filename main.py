import sqlite3
import json
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import requests
from datetime import datetime

# Ваш токен VK API
VK_TOKEN = "vk1.a.6XR1Ly_CiS3mmbmxf0KHW6sEF0EVJuuLUlXhL1G8CQb9sLlYbiCCIJa07r0ujtVdx2xen_Tv78E_rMB6VppJqJnjFAtaPgwxHl2j06kt3BHOokcjZAEE83aIJrdIgiubeSj6gzKRDJY0le3jsp5pVqAjsOcZd3uucFQg8YbJERGE1_WMIGO7dBlojQ2jjq15WWNF0FcPqJmbgSGSC2cdDg"

# Временное хранилище для анкет
user_survey_progress = {}

# Файл базы данных
DB_FILE = "bot_buttons.db"

# Вспомогательные функции для работы с базой данных
def execute_query(query, args=(), fetchone=False, commit=False):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(query, args)
    data = cursor.fetchone() if fetchone else cursor.fetchall()
    if commit:
        conn.commit()
    conn.close()
    return data

def get_buttons_by_parent_id(parent_id):
    """Получает кнопки по родительскому ID."""
    return execute_query("SELECT id, question, request_type, dop, media_url FROM buttons WHERE parent_id = ?", (parent_id,))

def get_response_by_text(user_text):
    """Получает ответ по тексту кнопки."""
    return execute_query("SELECT id, response, request_type, dop, media_url FROM buttons WHERE question LIKE ?", (f"%{user_text}%",), fetchone=True)

def save_survey_result(user_id, answers, survey_name, file_url=None):
    """Сохраняет результаты анкеты."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_query(
        '''
        INSERT INTO survey_results (user_id, answers, file_url, survey_name, created_at)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (user_id, json.dumps(answers), file_url, survey_name, created_at),
        commit=True
    )

# Загрузка медиафайлов
def upload_photo(vk, user_id, photo_path):
    """Загружает фото на сервер VK и возвращает вложение."""
    upload_url = vk.photos.getMessagesUploadServer()["upload_url"]
    with open(photo_path, "rb") as file:
        response = requests.post(upload_url, files={"photo": file}).json()
    photo = vk.photos.saveMessagesPhoto(
        photo=response["photo"],
        server=response["server"],
        hash=response["hash"]
    )[0]
    return f"photo{photo['owner_id']}_{photo['id']}"

def upload_document(vk, user_id, doc_path, doc_title="document"):
    """Загружает документ на сервер VK и возвращает вложение."""
    upload_url = vk.docs.getMessagesUploadServer(type="doc", peer_id=user_id)["upload_url"]
    with open(doc_path, "rb") as file:
        response = requests.post(upload_url, files={"file": file}).json()
    document = vk.docs.save(file=response["file"], title=doc_title)["doc"]
    return f"doc{document['owner_id']}_{document['id']}"

def send_message_with_media(vk, user_id, message, media_path=None, media_type="photo"):
    """Отправляет сообщение с медиаматериалом."""
    attachment = None
    if media_path:
        if media_type == "photo":
            attachment = upload_photo(vk, user_id, media_path)
        elif media_type == "document":
            attachment = upload_document(vk, user_id, media_path)
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=0,
        attachment=attachment
    )

# Отправка сообщений с кнопками
def send_message_with_keyboard(vk, user_id, message, buttons):
    """Отправляет сообщение с кнопками."""
    keyboard = VkKeyboard(one_time=True)
    for i, (button_id, button_text, request_type, dop, media_url) in enumerate(buttons):
        keyboard.add_button(button_text, color=VkKeyboardColor.PRIMARY)
        if i < len(buttons) - 1:
            keyboard.add_line()
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=0,
        keyboard=keyboard.get_keyboard()
    )

# Основная логика бота
def main():
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    print("Бот запущен...")

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            user_message = event.text   #.lower()

            # Если пользователь в процессе анкеты
            if user_id in user_survey_progress:
                survey = user_survey_progress[user_id]
                current_question = survey["questions"][survey["current_index"]]
                survey["answers"].append(user_message)

                # Переход к следующему вопросу
                survey["current_index"] += 1
                if survey["current_index"] < len(survey["questions"]):
                    next_question = survey["questions"][survey["current_index"]]
                    vk.messages.send(user_id=user_id, message=next_question, random_id=0)
                else:
                    # Завершение анкеты
                    save_survey_result(user_id, survey["answers"], survey["survey_name"])
                    del user_survey_progress[user_id]
                    vk.messages.send(user_id=user_id, message="Спасибо за ответы! Анкета завершена.", random_id=0)
                continue

            # Обработка кнопок и ответов
            response = get_response_by_text(user_message)
            if response:
                response_id, response_text, request_type, dop, media_url = response
                send_message_with_media(vk, user_id, response_text, media_path=media_url, media_type="photo" if media_url and media_url.endswith((".jpg", ".png")) else "document")
                print(response_text);
                if request_type == 1:  # Режим анкеты
                    questions = json.loads(dop)
                    survey_name = questions[0]
                    user_survey_progress[user_id] = {
                        "questions": questions,
                        "current_index": 0,
                        "answers": [],
                        "survey_name": survey_name
                    }
                    vk.messages.send(user_id=user_id, message=questions[0], random_id=0)
                else:
                    # Получаем кнопки
                    buttons = get_buttons_by_parent_id(response_id)
                    if buttons:
                        send_message_with_keyboard(vk, user_id, "Выберите следующий шаг:", buttons)
                    else:
                        vk.messages.send(user_id=user_id, message="На этом всё!", random_id=0)
            else:
                # Показать главное меню, если текст не распознан
                buttons = get_buttons_by_parent_id(0)
                send_message_with_keyboard(vk, user_id, "Я вас не понял. Вот главное меню:", buttons)

if __name__ == "__main__":
    main()
