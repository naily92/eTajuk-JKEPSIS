# e-Tajuk@JKEPSIS

This is a simple Flask app for searching student project titles and abstracts, with an admin CSV upload.

## Quickstart (local)

1. Create virtual environment:
   python -m venv venv
   source venv/bin/activate  # on Windows: venv\Scripts\activate

2. Install:
   pip install -r requirements.txt

3. Run:
   python app.py

Admin login: admin / admin123

CSV format (header): title,year,abstract,supervisor,student
