
import os, re, csv, sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from markupsafe import Markup
import nltk
from nltk.corpus import wordnet
from werkzeug.utils import secure_filename

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "your_secret_key")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"csv"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        year TEXT,
        abstract TEXT,
        supervisor TEXT,
        student TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("session_text", "Data updated up to Sesi Jun 2025"))
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    conn.close()

def get_synonyms(word):
    syns = set([word.lower()])
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            syns.add(lemma.name().replace("_", " ").lower())
    return sorted(syns)

def highlight_text(text, keywords):
    import re
    if not text or not keywords:
        return text or ""
    kws = sorted(set([k for k in keywords if k.strip()]), key=len, reverse=True)
    patt = r"(" + "|".join(re.escape(k) for k in kws) + r")"
    return re.sub(patt, lambda m: f"<mark>{m.group(0)}</mark>", text, flags=re.IGNORECASE)

def build_exact_query(words, year=None):
    clauses, params = [], []
    for w in words:
        clauses.append("(title LIKE ? OR abstract LIKE ?)")
        params.extend((f"%{w}%", f"%{w}%"))
    where = " AND ".join(clauses) if clauses else "1=1"
    if year:
        where = f"({where}) AND year=?"
        params.append(year)
    sql = f"SELECT title, year, abstract, supervisor, student FROM projects WHERE {where}"
    return sql, params

def build_smart_query(words, year=None):
    groups, params = [], []
    for w in words:
        syns = get_synonyms(w)
        subs = []
        for s in syns:
            subs.append("(title LIKE ? OR abstract LIKE ?)")
            params.extend((f"%{s}%", f"%{s}%"))
        groups.append("(" + " OR ".join(subs) + ")") if subs else groups.append("(1=1)")
    where = " AND ".join(groups) if groups else "1=1"
    if year:
        where = f"({where}) AND year=?"
        params.append(year)
    sql = f"SELECT title, year, abstract, supervisor, student FROM projects WHERE {where}"
    return sql, params

def execute_query(sql, params):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    seen, uniq = set(), []
    for r in rows:
        key = (r[0], r[1], r[2])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq

@app.route("/", methods=["GET"])
def index():
    import re
    query = request.args.get("query", "").strip()
    year = request.args.get("year", "").strip()
    mode = request.args.get("mode", "smart")
    session_text = get_setting("session_text", "")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    years = [r[0] for r in cur.execute("SELECT DISTINCT year FROM projects ORDER BY year DESC").fetchall()]
    conn.close()

    results = []
    exact_count = smart_count = 0
    smart_terms_display = []

    if query:
        words = [w for w in re.split(r"\s+", query) if w]

        ex_sql, ex_params = build_exact_query(words, year if year else None)
        exact_rows = execute_query(ex_sql, ex_params)
        exact_count = len(exact_rows)

        sm_sql, sm_params = build_smart_query(words, year if year else None)
        smart_rows = execute_query(sm_sql, sm_params)
        smart_count = len(smart_rows)

        rows = smart_rows if mode == "smart" else exact_rows

        if mode == "smart":
            syn_union = set()
            for w in words:
                syn_union.update(get_synonyms(w))
            highlight_keys = syn_union
            smart_terms_display = sorted(syn_union)
        else:
            highlight_keys = set(words)

        processed = []
        for title, y, abstract, sv, st in rows:
            ht = Markup(highlight_text(title or "", highlight_keys))
            ha = highlight_text(abstract or "", highlight_keys)
            short = ha[:300] + ("..." if len(ha) > 300 else "")
            processed.append((ht, y, Markup(ha), Markup(short), sv or "", st or ""))
        results = processed

    return render_template("index.html",
                           query=query, years=years, selected_year=year, mode=mode,
                           results=results, exact_count=exact_count, smart_count=smart_count,
                           smart_terms=smart_terms_display, session_text=session_text)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == "admin" and p == "eTajukJKEPSIS25":
            session["username"] = u
            return redirect(url_for("admin"))
        flash("Invalid login", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("username") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        if "file" in request.files and request.files["file"].filename:
            f = request.files["file"]
            if allowed_file(f.filename):
                fname = secure_filename(f.filename)
                path = os.path.join(UPLOAD_FOLDER, fname)
                f.save(path)
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                with open(path, newline="", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        cur.execute("""INSERT INTO projects (title, year, abstract, supervisor, student)
                                       VALUES (?, ?, ?, ?, ?)""",
                                       (row.get("title",""), row.get("year",""), row.get("abstract",""),
                                        row.get("supervisor",""), row.get("student","")))
                conn.commit()
                conn.close()
                flash("CSV successfuly uploaded", "success")
                return redirect(url_for("admin"))
            else:
                flash("Please choose a valid CSV file", "danger")
                return redirect(url_for("admin"))

        new_text = request.form.get("session_text", "").strip()
        set_setting("session_text", new_text)
        flash("Session details successfully updated", "success")
        return redirect(url_for("admin"))

    current_text = get_setting("session_text", "")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    conn.close()
    return render_template("admin.html", session_text=current_text, total=total)

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
