from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)

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
        media_url = request.form["media_url"] if request.form["media_url"] else None

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

# Редактирование кнопки
@app.route("/edit/<int:button_id>", methods=["GET", "POST"])
def edit_button(button_id):
    if request.method == "POST":
        question = request.form["question"]
        response = request.form["response"]
        parent_id = int(request.form["parent_id"])
        request_type = int(request.form["request_type"])
        dop = request.form["dop"] if request.form["dop"] else None
        media_url = request.form["media_url"] if request.form["media_url"] else None

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
@app.route("/results")
def survey_results():
    results = execute_query("SELECT id, user_id, answers, survey_name, created_at, file_url FROM survey_results")
    return render_template("survey_results.html", results=results)

# Запуск приложения
if __name__ == "__main__":
    app.run(debug=True)
