import sqlite3
import json
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import requests
from datetime import datetime
import re

VK_TOKEN = "vk1.a.6XR1Ly_CiS3mmbmxf0KHW6sEF0EVJuuLUlXhL1G8CQb9sLlYbiCCIJa07r0ujtVdx2xen_Tv78E_rMB6VppJqJnjFAtaPgwxHl2j06kt3BHOokcjZAEE83aIJrdIgiubeSj6gzKRDJY0le3jsp5pVqAjsOcZd3uucFQg8YbJERGE1_WMIGO7dBlojQ2jjq15WWNF0FcPqJmbgSGSC2cdDg"

user_survey_progress = {}  # Временное хранилище для анкет
DB_FILE = "bot_buttons.db"

# Функции для работы с базой данных
def execute_query(query, args=(), fetchone=False, commit=False):
    """Работа с базой данных."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(query, args)
    data = cursor.fetchone() if fetchone else cursor.fetchall()
    if commit:
        conn.commit()
    conn.close()
    return data

def get_buttons_by_parent_id(parent_id):
    """Получение кнопок по родительскому ID."""
    return execute_query("SELECT id, question, request_type, dop, media_url FROM buttons WHERE parent_id = ?", (parent_id,))

def get_response_by_text(user_text):
    """Получение ответа по тексту кнопки."""
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

# Проверка валидности ответа
def validate_answer(answer, answer_type):
    """
    Проверяет ответ пользователя в зависимости от ожидаемого типа.
    """
    if answer_type == 1:  # Текст
        return isinstance(answer, str) and len(answer) > 0
    elif answer_type == 2:  # Дата (формат YYYY-MM-DD)
        return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", answer))
    elif answer_type == 3:  # Число
        return answer.isdigit()
    elif answer_type == 4:  # Рисунок
        return answer.startswith("photo")  # Проверяем формат ID фото
    elif answer_type == 5:  # PDF
        return answer.endswith(".pdf")  # Проверяем формат URL
    return False

# Обработка анкет
def handle_survey_response(vk, user_id, survey, event):
    """
    Обрабатывает ответы пользователя в анкете.
    Проверяет ответ в зависимости от типа вопроса.
    """
    current_question = survey["questions"][survey["current_index"]]
    question_text = current_question["text"]
    answer_type = current_question["answer_type"]

    if event.attachments:
        if "photo"==event.attachments['attach1_type'] and answer_type == 4:
            # Обработка фото
            photo_id = event.attachments["photo"][0]
            survey["answers"].append(photo_id)
        elif "doc"==event.attachments['attach1_type'] and answer_type == 5:
            # Обработка PDF
            message_id = event.message_id
            message_data = vk.messages.getById(message_ids=message_id)["items"][0]
            document = message_data["attachments"][0]["doc"]
            if document["ext"] == "pdf":
                pdf_url = document["url"]
                survey["answers"].append(pdf_url)
            else:
                vk.messages.send(user_id=user_id, message="Пожалуйста, загрузите корректный PDF-документ.", random_id=0)
                return
        else:
            vk.messages.send(user_id=user_id, message="Неверный тип вложения.", random_id=0)
            return
    else:
        # Текстовые ответы
        user_answer = event.text
        if validate_answer(user_answer, answer_type):
            survey["answers"].append(user_answer)
        else:
            vk.messages.send(user_id=user_id, message=f"Неверный формат ответа. Повторите вопрос: {question_text}", random_id=0)
            return

    # Переход к следующему вопросу
    survey["current_index"] += 1
    if survey["current_index"] < len(survey["questions"]):
        next_question = survey["questions"][survey["current_index"]]["text"]
        vk.messages.send(user_id=user_id, message=next_question, random_id=0)
    else:
        # Завершение анкеты
        save_survey_result(user_id, survey["answers"], survey["survey_name"])
        del user_survey_progress[user_id]
        vk.messages.send(user_id=user_id, message="Спасибо за ответы! Анкета завершена.", random_id=0)

# Отправка сообщений
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

            # Если пользователь в процессе анкеты
            if user_id in user_survey_progress:
                survey = user_survey_progress[user_id]
                handle_survey_response(vk, user_id, survey, event)
                continue

            # Обработка кнопок
            response = get_response_by_text(event.text)
            if response:
                response_id, response_text, request_type, dop, media_url = response
                vk.messages.send(user_id=user_id, message=response_text, random_id=0)

                if request_type == 1:  # Режим анкеты
                    questions = json.loads(dop)
                    survey_name = questions[0]["text"]
                    user_survey_progress[user_id] = {
                        "questions": questions,
                        "current_index": 0,
                        "answers": [],
                        "survey_name": survey_name
                    }
                    vk.messages.send(user_id=user_id, message=questions[0]["text"], random_id=0)
                else:
                    # Получаем кнопки
                    buttons = get_buttons_by_parent_id(response_id)
                    if buttons:
                        send_message_with_keyboard(vk, user_id, "Выберите следующий шаг:", buttons)
                    else:
                        vk.messages.send(user_id=user_id, message="На этом всё!", random_id=0)
            else:
                # Показываем главное меню
                buttons = get_buttons_by_parent_id(0)
                send_message_with_keyboard(vk, user_id, "Я вас не понял. Вот главное меню:", buttons)

if __name__ == "__main__":
    main()
