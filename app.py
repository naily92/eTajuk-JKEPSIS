from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import nltk
from nltk.corpus import wordnet

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_synonyms(keyword):
    synonyms = set()
    for syn in wordnet.synsets(keyword):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().lower())
    return list(synonyms)

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    years = []
    keyword = ''
    selected_year = ''

    conn = sqlite3.connect('projects.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT tahun FROM projects ORDER BY tahun DESC')
    years = [row[0] for row in cursor.fetchall()]

    if request.method == 'POST':
        keyword = request.form['keyword'].lower()
        selected_year = request.form.get('tahun')

        synonyms = get_synonyms(keyword)
        synonyms.append(keyword)

        query = "SELECT * FROM projects WHERE "
        conditions = []
        params = []

        for syn in synonyms:
            conditions.append("(LOWER(tajuk) LIKE ? OR LOWER(abstrak) LIKE ?)")
            params.extend([f"%{syn}%", f"%{syn}%"])

        if selected_year:
            query += "(" + " OR ".join(conditions) + ") AND tahun = ?"
            params.append(selected_year)
        else:
            query += " OR ".join(conditions)

        cursor.execute(query, params)
        results = cursor.fetchall()

    conn.close()
    return render_template('index.html', results=results, years=years, keyword=keyword, selected_year=selected_year)

if __name__ == '__main__':
    app.run(debug=True)

from flask import flash
import csv
import os

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['admin'] = True
            return redirect(url_for('upload'))
        else:
            return render_template('login.html', message="Login gagal.")
    return render_template('login.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('admin'):
        return redirect(url_for('login'))

    message = ''
    if request.method == 'POST':
        file = request.files['csvfile']
        if file and file.filename.endswith('.csv'):
            filepath = os.path.join('uploads', file.filename)
            os.makedirs('uploads', exist_ok=True)
            file.save(filepath)

            conn = sqlite3.connect('projects.db')
            cursor = conn.cursor()
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if len(row) == 5:
                        cursor.execute("INSERT INTO projects (tajuk, tahun, abstrak, penyelia, pelajar) VALUES (?, ?, ?, ?, ?)", row)
            conn.commit()
            conn.close()
            message = "Fail CSV berjaya dimuat naik dan dimasukkan ke pangkalan data."
        else:
            message = "Sila muat naik fail CSV yang sah."
    return render_template('upload.html', message=message)
