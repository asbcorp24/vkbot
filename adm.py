from flask import Flask, render_template, request, redirect, url_for,send_from_directory
import sqlite3
import json
from datetime import datetime
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}



# Проверка разрешённого расширения файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DB_FILE = "bot_buttons.db"

# Вспомогательные функции
def execute_query(query, args=(), fetchone=False, commit=False):
    """Функция для работы с базой данных."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(query, args)
    data = cursor.fetchone() if fetchone else cursor.fetchall()
    if commit:
        conn.commit()
    conn.close()
    return data

# Главная страница: список кнопок
@app.route("/")
def index():
    buttons = execute_query("SELECT id, question, response, parent_id, request_type, dop, media_url FROM buttons")
    return render_template("index.html", buttons=buttons)

# Добавление новой кнопки
@app.route("/add", methods=["GET", "POST"])
def add_button():
    if request.method == "POST":
        question = request.form["question"]
        response = request.form["response"]
        parent_id = int(request.form["parent_id"])
        request_type = int(request.form["request_type"])
        dop = request.form["dop"] if request.form["dop"] else None
        media_url = None

        # Обработка файла
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                media_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        execute_query(
            '''
            INSERT INTO buttons (question, response, parent_id, request_type, dop, media_url)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (question, response, parent_id, request_type, dop, media_url),
            commit=True
        )
        return redirect(url_for("index"))

    # Получаем список кнопок для выбора родительского ID
    buttons = execute_query("SELECT id, question FROM buttons")
    return render_template("add_button.html", buttons=buttons)


@app.route("/uploads/<path:filename>")
def get_uploaded_file(filename):
    """
    Возвращает файл из папки uploads.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Редактирование кнопки
@app.route("/edit/<int:button_id>", methods=["GET", "POST"])
def edit_button(button_id):
    if request.method == "POST":
        question = request.form["question"]
        response = request.form["response"]
        parent_id = int(request.form["parent_id"])
        request_type = int(request.form["request_type"])
        dop = request.form["dop"] if request.form["dop"] else None
        media_url = request.form["media_url"]

        # Обработка нового файла
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                media_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        execute_query(
            '''
            UPDATE buttons
            SET question = ?, response = ?, parent_id = ?, request_type = ?, dop = ?, media_url = ?
            WHERE id = ?
            ''',
            (question, response, parent_id, request_type, dop, media_url, button_id),
            commit=True
        )
        return redirect(url_for("index"))

    button = execute_query("SELECT * FROM buttons WHERE id = ?", (button_id,), fetchone=True)
    return render_template("edit_button.html", button=button)

# Удаление кнопки
@app.route("/delete/<int:button_id>")
def delete_button(button_id):
    execute_query("DELETE FROM buttons WHERE id = ?", (button_id,), commit=True)
    return redirect(url_for("index"))

# Просмотр результатов анкет
@app.route("/results", methods=["GET"])
def survey_results():
    # Получение уникальных названий анкет
    survey_names = [row[0] for row in execute_query("SELECT DISTINCT survey_name FROM survey_results")]

    # Получение фильтров из параметров запроса
    survey_name = request.args.get("survey_name", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    # Базовый запрос
    query = "SELECT id, user_id, answers, survey_name, created_at, file_url FROM survey_results WHERE 1=1"
    params = []

    # Добавление фильтра по названию анкеты
    if survey_name:
        query += " AND survey_name = ?"
        params.append(survey_name)

    # Добавление фильтра по дате начала
    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)

    # Добавление фильтра по дате окончания
    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)

    # Выполнение запроса
    raw_results = execute_query(query, params)

    # Парсим ответы из JSON
    results = []
    for row in raw_results:
        try:
            # Преобразование строки JSON в список словарей
            answers = json.loads(row[2]) if row[2] else []
        except json.JSONDecodeError:
            answers = []  # Если парсинг не удался
        parsed_answers = []
        for answer in answers:
            if isinstance(answer, dict):  # Убедимся, что ответ — это словарь
                parsed_answers.append(answer)
            else:
                parsed_answers.append({"question": "Неизвестный вопрос", "answer": answer})  # На случай строки
        results.append((row[0], row[1], parsed_answers, row[3], row[4], row[5]))

    return render_template("survey_results.html", results=results, survey_names=survey_names)
from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)
DB_FILE = "bot_buttons.db"

# Работа с базой данных
def execute_query(query, args=(), fetchone=False, commit=False):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(query, args)
    data = cursor.fetchone() if fetchone else cursor.fetchall()
    if commit:
        conn.commit()
    conn.close()
    return data

@app.route("/results", methods=["GET"])
def survey_results():
    # Получение уникальных названий анкет
    survey_names = [row[0] for row in execute_query("SELECT DISTINCT survey_name FROM survey_results")]

    # Получение фильтров из параметров запроса
    survey_name = request.args.get("survey_name", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    # Базовый запрос
    query = "SELECT id, user_id, answers, survey_name, created_at, file_url FROM survey_results WHERE 1=1"
    params = []

    # Добавление фильтра по названию анкеты
    if survey_name:
        query += " AND survey_name = ?"
        params.append(survey_name)

    # Добавление фильтра по дате начала
    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)

    # Добавление фильтра по дате окончания
    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)

    # Выполнение запроса
    raw_results = execute_query(query, params)

    # Парсим ответы из JSON
    results = []
    for row in raw_results:
        try:
            answers = json.loads(row[2]) if row[2] else []
        except json.JSONDecodeError:
            answers = []  # Если парсинг не удался
        parsed_answers = []
        for answer in answers:
            if isinstance(answer, dict):
                parsed_answers.append(answer)
            else:
                parsed_answers.append({"question": "Неизвестный вопрос", "answer": answer})
        results.append((row[0], row[1], parsed_answers, row[3], row[4], row[5]))

    return render_template("survey_results.html", results=results, survey_names=survey_names)

@app.route("/delete_result/<int:result_id>", methods=["POST"])
def delete_result(result_id):
    # Удаление записи из базы данных
    execute_query("DELETE FROM survey_results WHERE id = ?", (result_id,), commit=True)
    return redirect(url_for("survey_results"))




# Запуск приложения
if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run()
