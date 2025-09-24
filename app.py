import os, re, csv
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash, Markup
import nltk
from nltk.corpus import wordnet
from werkzeug.utils import secure_filename

# Ensure wordnet exists
try:
    nltk.data.find("corpora/wordnet")
except LookupError:
    nltk.download("wordnet")

# Flask setup
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "your_secret_key")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"csv"}

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Init tables
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        title TEXT,
        year TEXT,
        abstract TEXT,
        short_abstract TEXT,
        supervisor TEXT,
        student TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    cur.execute("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
                ("session_text", "Data updated up to Sesi Jun 2025"))
    conn.commit()
    cur.close()
    conn.close()

# Settings helpers
def get_setting(key, default=""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key=%s", (key,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO settings (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
    """, (key, value))
    conn.commit()
    cur.close()
    conn.close()

# Search helpers
def get_synonyms(word):
    syns = set([word.lower()])
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            syns.add(lemma.name().replace("_", " ").lower())
    return sorted(syns)

def highlight_text(text, keywords):
    if not text or not keywords:
        return text or ""
    kws = sorted(set([k for k in keywords if k.strip()]), key=len, reverse=True)
    patt = r"(" + "|".join(re.escape(k) for k in kws) + r")"
    return re.sub(patt, lambda m: f"<mark>{m.group(0)}</mark>", text, flags=re.IGNORECASE)

def execute_query(sql, params):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# Routes
@app.route("/", methods=["GET"])
def index():
    query = request.args.get("query", "").strip()
    year = request.args.get("year", "").strip()
    mode = request.args.get("mode", "smart")
    session_text = get_setting("session_text", "")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT year FROM projects ORDER BY year DESC")
    years = [r["year"] for r in cur.fetchall() if r["year"]]
    cur.close()
    conn.close()

    results, exact_count, smart_count, smart_terms_display = [], 0, 0, []

    if query:
        words = [w for w in re.split(r"\s+", query) if w]

        # exact search
        ex_clauses, ex_params = [], []
        for w in words:
            ex_clauses.append("(title ILIKE %s OR abstract ILIKE %s)")
            ex_params.extend((f"%{w}%", f"%{w}%"))
        ex_where = " AND ".join(ex_clauses) if ex_clauses else "TRUE"
        if year:
            ex_where += " AND year=%s"
            ex_params.append(year)
        ex_sql = f"SELECT * FROM projects WHERE {ex_where}"
        exact_rows = execute_query(ex_sql, ex_params)
        exact_count = len(exact_rows)

        # smart search
        sm_clauses, sm_params = [], []
        for w in words:
            syns = get_synonyms(w)
            subs = []
            for s in syns:
                subs.append("(title ILIKE %s OR abstract ILIKE %s)")
                sm_params.extend((f"%{s}%", f"%{s}%"))
            if subs:
                sm_clauses.append("(" + " OR ".join(subs) + ")")
        sm_where = " AND ".join(sm_clauses) if sm_clauses else "TRUE"
        if year:
            sm_where += " AND year=%s"
            sm_params.append(year)
        sm_sql = f"SELECT * FROM projects WHERE {sm_where}"
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
        for row in rows:
            ht = Markup(highlight_text(row["title"] or "", highlight_keys))
            ha = highlight_text(row["abstract"] or "", highlight_keys)
            processed.append((ht, row["year"], Markup(ha),
                              Markup(row["short_abstract"] or ""),
                              row.get("supervisor",""), row.get("student","")))
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
        admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
        if u == "admin" and p == admin_pass:
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
            if f and f.filename.endswith(".csv"):
                fname = secure_filename(f.filename)
                path = os.path.join(UPLOAD_FOLDER, fname)
                f.save(path)
                conn = get_conn()
                cur = conn.cursor()
                with open(path, newline="", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        short = (row.get("abstract","")[:300] + "...") if row.get("abstract") else ""
                        cur.execute("""INSERT INTO projects (title, year, abstract, short_abstract, supervisor, student)
                                       VALUES (%s, %s, %s, %s, %s, %s)""",
                                       (row.get("title",""), row.get("year",""), row.get("abstract",""),
                                        short, row.get("supervisor",""), row.get("student_name","")))
                conn.commit()
                cur.close()
                conn.close()
                flash("CSV dimuat naik & data dimasukkan", "success")
                return redirect(url_for("admin"))
            else:
                flash("Sila pilih fail CSV yang sah", "danger")
                return redirect(url_for("admin"))

        new_text = request.form.get("session_text", "").strip()
        set_setting("session_text", new_text)
        flash("Maklumat sesi dikemaskini", "success")
        return redirect(url_for("admin"))

    current_text = get_setting("session_text", "")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM projects")
    total = cur.fetchone()["count"]
    cur.close()
    conn.close()
    return render_template("admin.html", session_text=current_text, total=total)

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
