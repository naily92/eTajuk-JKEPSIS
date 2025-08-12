from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import csv
import os
import nltk
from nltk.corpus import wordnet
from werkzeug.utils import secure_filename

# Attempt to download wordnet if not present
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

basedir = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(basedir, 'database.db')

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('FLASK_SECRET', 'your_secret_key')
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        year TEXT,
                        abstract TEXT,
                        supervisor TEXT,
                        student TEXT
                    )''')
    conn.commit()
    conn.close()

def get_synonyms(word):
    synonyms = set([word])
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace('_', ' '))
    return list(synonyms)

@app.route('/', methods=['GET'])
def index():
    query = request.args.get('query', '').strip()
    year = request.args.get('year', '').strip()
    results = []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if query:
        synonyms = get_synonyms(query)
        # build WHERE clauses
        clauses = []
        params = []
        for w in synonyms:
            clauses.append("(title LIKE ? OR abstract LIKE ?)")
            params.extend((f"%{w}%", f"%{w}%"))
        where = " OR ".join(clauses)
        if year:
            where = f"({where}) AND year = ?"
            params.append(year)
        sql = f"SELECT title, year, abstract, supervisor, student FROM projects WHERE {where}"
        cursor.execute(sql, params)
        results = cursor.fetchall()
    else:
        if year:
            cursor.execute("SELECT title, year, abstract, supervisor, student FROM projects WHERE year = ? ORDER BY id DESC", (year,))
        else:
            cursor.execute("SELECT title, year, abstract, supervisor, student FROM projects ORDER BY id DESC")
        results = cursor.fetchall()

    # fetch distinct years
    cursor.execute("SELECT DISTINCT year FROM projects ORDER BY year DESC")
    years = [r[0] for r in cursor.fetchall()]

    conn.close()
    return render_template('index.html', results=results, query=query, years=years, selected_year=year)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','')
        password = request.form.get('password','')
        if username == 'admin' and password == 'admin123':
            session['username'] = username
            return redirect(url_for('admin'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('username') != 'admin':
        return redirect(url_for('login'))
    message = ''
    if request.method == 'POST':
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # expect columns: title, year, abstract, supervisor, student
                    cursor.execute('''INSERT INTO projects (title, year, abstract, supervisor, student)
                                      VALUES (?, ?, ?, ?, ?)''',
                                   (row.get('title',''), row.get('year',''), row.get('abstract',''),
                                    row.get('supervisor',''), row.get('student','')))
            conn.commit()
            conn.close()
            flash('CSV uploaded and data inserted.', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Please upload a valid CSV file.', 'danger')
    return render_template('admin.html')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    # debug should be False in production; keep False here
    app.run(host='0.0.0.0', port=port, debug=False)
