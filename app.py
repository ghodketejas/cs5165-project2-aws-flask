from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'CHANGE_THIS_TO_A_RANDOM_STRING_12345'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'users.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_FILENAME = 'limerick.txt'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL UNIQUE,
                  password TEXT NOT NULL,
                  firstname TEXT,
                  lastname TEXT,
                  email TEXT,
                  address TEXT,
                  limerick_filename TEXT)''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', error=None)

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not password:
        return render_template('login.html', error="Both fields are required.")

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username=? AND password=?", (username, password))
    row = c.fetchone()
    conn.close()

    if row:
        session['user'] = username
        return redirect(url_for('profile', username=username))
    else:
        return render_template('login.html', error="Invalid username or password.")

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    firstname = request.form.get('firstname', '').strip()
    lastname = request.form.get('lastname', '').strip()
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()

    if not username or not password:
        return "Username and Password are required.", 400

    init_db()

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO users (username, password, firstname, lastname, email, address)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (username, password, firstname, lastname, email, address))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Username already exists. Please choose another.", 400

    conn.close()
    session['user'] = username
    return redirect(url_for('profile', username=username))

@app.route('/profile/<username>')
def profile(username):
    if session.get('user') != username:
        return redirect(url_for('login'))

    init_db()
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""SELECT username, firstname, lastname, email, address, limerick_filename
                 FROM users WHERE username = ?""", (username,))
    user = c.fetchone()
    conn.close()

    if not user:
        return "User not found.", 404

    # Word count logic (only if file exists)
    word_count = None
    can_download = False

    filename = user[5]
    if filename:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            can_download = True
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
                word_count = len(text.split())

    return render_template('profile.html', user=user, word_count=word_count, can_download=can_download)

@app.route('/upload/<username>', methods=['POST'])
def upload(username):
    if session.get('user') != username:
        return redirect(url_for('login'))

    if 'file' not in request.files:
        return "No file part.", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file.", 400

    filename = secure_filename(file.filename).lower()

    # Require exactly Limerick.txt (case-insensitive)
    if filename != ALLOWED_FILENAME:
        return "Please upload Limerick.txt only.", 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    # Save filename to DB for this user
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET limerick_filename=? WHERE username=?", (filename, username))
    conn.commit()
    conn.close()

    return redirect(url_for('profile', username=username))

@app.route('/download/<username>')
def download(username):
    if session.get('user') != username:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT limerick_filename FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return "No file uploaded for this user.", 404

    filename = row[0]
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found on server.", 404

    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
