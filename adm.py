from flask import Flask, request, render_template, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
SUPERADMIN_USERNAME = os.getenv("SUPERADMIN_USERNAME", "superadmin")
SUPERADMIN_PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "superpassword")

# Конфигурация приложения
app = Flask(__name__)
app.secret_key = "your_secret_key"  # Замените на свой секретный ключ
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
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

# Главная страница
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    buttons = execute_query("SELECT id, question, response, parent_id, request_type, dop, media_url FROM buttons")
    return render_template("index.html", buttons=buttons)

# Регистрация пользователя (только для суперадмина)
@app.route("/manage_users", methods=["GET", "POST"])
def manage_users():
    if session.get("username") != SUPERADMIN_USERNAME:
        flash("Доступ запрещён.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            execute_query(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password),
                commit=True
            )
            flash("Пользователь успешно добавлен.", "success")
        except sqlite3.IntegrityError:
            flash("Пользователь с таким логином уже существует.", "danger")

    users = execute_query("SELECT id, username FROM users")
    return render_template("manage_users.html", users=users)

# Удаление пользователя (только для суперадмина)
@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if session.get("username") != SUPERADMIN_USERNAME:
        flash("Доступ запрещён.", "danger")
        return redirect(url_for("index"))

    execute_query("DELETE FROM users WHERE id = ?", (user_id,), commit=True)
    flash("Пользователь успешно удалён.", "success")
    return redirect(url_for("manage_users"))

# Авторизация пользователя
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == SUPERADMIN_USERNAME and password == SUPERADMIN_PASSWORD:
            session["user_id"] = -1  # Уникальный ID для суперадмина
            session["username"] = SUPERADMIN_USERNAME
            flash("Вы вошли как суперадмин!", "success")
            return redirect(url_for("index"))

        user = execute_query("SELECT * FROM users WHERE username = ?", (username,), fetchone=True)

        if user and user[2] == password:  # Прямая проверка пароля
            session["user_id"] = user[0]
            session["username"] = user[1]
            flash("Вы успешно вошли в систему!", "success")
            return redirect(url_for("index"))
        else:
            flash("Неверный логин или пароль.", "danger")

    return render_template("login.html")

# Выход из системы
@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("login"))

# Добавление новой кнопки
@app.route("/add", methods=["GET", "POST"])
def add_button():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        question = request.form["question"]
        response = request.form["response"]
        parent_id = int(request.form["parent_id"])
        request_type = int(request.form["request_type"])
        dop = request.form["dop"] if request.form["dop"] else None
        media_url = None

        if 'file' in request.files:
            file = request.files['file']
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                media_url = f"/uploads/{filename}"

        execute_query(
            '''
            INSERT INTO buttons (question, response, parent_id, request_type, dop, media_url)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (question, response, parent_id, request_type, dop, media_url),
            commit=True
        )
        return redirect(url_for("index"))

    buttons = execute_query("SELECT id, question FROM buttons")
    return render_template("add_button.html", buttons=buttons)

# Получение файлов из папки uploads
@app.route("/uploads/<path:filename>")
def get_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Удаление кнопки
@app.route("/delete/<int:button_id>")
def delete_button(button_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    execute_query("DELETE FROM buttons WHERE id = ?", (button_id,), commit=True)
    return redirect(url_for("index"))

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
