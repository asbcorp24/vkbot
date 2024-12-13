import os
import json
import sqlite3
from flask import Flask, request, jsonify
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime

# Загрузка переменных окружения
load_dotenv()
VK_TOKEN = os.getenv("VK_TOKEN")
CONFIRMATION_TOKEN = os.getenv("CONFIRMATION_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
UPLOAD_FOLDER = "uploads"

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Глобальные переменные
user_survey_progress = {}
DB_FILE = "bot_buttons.db"

# Вспомогательные функции
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
    return execute_query("SELECT id, question, request_type, dop, media_url FROM buttons WHERE parent_id = ?", (parent_id,))

def get_response_by_text(user_text):
    return execute_query("SELECT id, response, request_type, dop, media_url FROM buttons WHERE question LIKE ?", (f"%{user_text}%",), fetchone=True)

def save_survey_result(user_id, answers, survey_name):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_query(
        '''INSERT INTO survey_results (user_id, answers, survey_name, created_at) VALUES (?, ?, ?, ?)''',
        (user_id, json.dumps(answers), survey_name, created_at),
        commit=True
    )

def send_message(vk, user_id, message, media_url=None):
    attachment = None
    if media_url:
        attachment = upload_media(vk, media_url)
    vk.messages.send(user_id=user_id, message=message, random_id=0, attachment=attachment)

def upload_media(vk, media_url):
    # Логика загрузки медиа (добавьте реализацию, если потребуется)
    return None

def send_message_with_keyboard(vk, user_id, message, buttons):
    keyboard = VkKeyboard(one_time=True)
    for i, (button_id, button_text, request_type, dop, media_url) in enumerate(buttons):
        keyboard.add_button(button_text, color=VkKeyboardColor.PRIMARY)
        if i < len(buttons) - 1:
            keyboard.add_line()
    vk.messages.send(user_id=user_id, message=message, random_id=0, keyboard=keyboard.get_keyboard())

# Обработка анкет
def handle_survey_response(vk, user_id, survey, event):
    current_question = survey["questions"][survey["current_index"]]
    user_answer = event.text

    survey["answers"].append({"question": current_question["text"], "answer": user_answer})
    survey["current_index"] += 1

    if survey["current_index"] < len(survey["questions"]):
        next_question = survey["questions"][survey["current_index"]]
        vk.messages.send(user_id=user_id, message=next_question["text"], random_id=0)
    else:
        save_survey_result(user_id, survey["answers"], survey["survey_name"])
        del user_survey_progress[user_id]
        vk.messages.send(user_id=user_id, message="Спасибо за ответы! Анкета завершена.", random_id=0)

# Flask Callback API
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return "No data", 400

    if data.get("type") == "confirmation":
        return CONFIRMATION_TOKEN

    if data.get("type") == "message_new":
        event = data["object"]["message"]
        user_id = event["from_id"]
        text = event["text"]

        vk_session = vk_api.VkApi(token=VK_TOKEN)
        vk = vk_session.get_api()

        if user_id in user_survey_progress:
            survey = user_survey_progress[user_id]
            handle_survey_response(vk, user_id, survey, event)
        else:
            response = get_response_by_text(text)
            if response:
                response_id, response_text, request_type, dop, media_url = response
                send_message(vk, user_id, response_text, media_url)

                if request_type == 1:
                    questions = json.loads(dop)
                    survey_name = "Анкета"
                    user_survey_progress[user_id] = {
                        "questions": questions,
                        "current_index": 0,
                        "answers": [],
                        "survey_name": survey_name
                    }
                    vk.messages.send(user_id=user_id, message=questions[0]["text"], random_id=0)
                else:
                    buttons = get_buttons_by_parent_id(response_id)
                    if buttons:
                        send_message_with_keyboard(vk, user_id, "Выберите следующий шаг:", buttons)
            else:
                buttons = get_buttons_by_parent_id(0)
                send_message_with_keyboard(vk, user_id, "Я вас не понял. Вот главное меню:", buttons)

    return "ok", 200

# LongPoll API
def longpoll_listener():
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id

            if user_id in user_survey_progress:
                survey = user_survey_progress[user_id]
                handle_survey_response(vk, user_id, survey, event)
                continue

            response = get_response_by_text(event.text)
            if response:
                response_id, response_text, request_type, dop, media_url = response
                send_message(vk, user_id, response_text, media_url)

                if request_type == 1:
                    questions = json.loads(dop)
                    survey_name = "Анкета"
                    user_survey_progress[user_id] = {
                        "questions": questions,
                        "current_index": 0,
                        "answers": [],
                        "survey_name": survey_name
                    }
                    vk.messages.send(user_id=user_id, message=questions[0]["text"], random_id=0)
                else:
                    buttons = get_buttons_by_parent_id(response_id)
                    if buttons:
                        send_message_with_keyboard(vk, user_id, "Выберите следующий шаг:", buttons)
            else:
                buttons = get_buttons_by_parent_id(0)
                send_message_with_keyboard(vk, user_id, "Я вас не понял. Вот главное меню:", buttons)

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Запуск Flask сервера
    from threading import Thread
    thread = Thread(target=longpoll_listener)
    thread.start()

    app.run(host="0.0.0.0", port=5000)
