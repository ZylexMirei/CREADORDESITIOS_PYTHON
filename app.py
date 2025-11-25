# app.py - VERSIÓN ULTIMATE (Admin Total + Recovery + Uploads)
import os
import sqlite3
import datetime
import json
import random
import string
import smtplib
import shutil
from email.mime.text import MIMEText
from functools import wraps
from io import BytesIO
from zipfile import ZipFile
from pathlib import Path
import jwt
from werkzeug.utils import secure_filename

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from passlib.context import CryptContext

# --- CONFIGURACIÓN ---
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY_2025")
EMAIL_USER = os.getenv("EMAIL_USER", "tucorreo@gmail.com") 
EMAIL_PASS = os.getenv("EMAIL_PASS", "tucontraseñadeaplicacion") 

DATABASE_NAME = "sitios.db"
BASE_DIR = Path(__file__).resolve().parent
SITE_OUTPUT_DIR = BASE_DIR / 'site_output'
TEMPLATE_BASE_DIR = BASE_DIR / 'template_base'

if not SITE_OUTPUT_DIR.exists(): SITE_OUTPUT_DIR.mkdir()
if not TEMPLATE_BASE_DIR.exists(): TEMPLATE_BASE_DIR.mkdir()

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# --- DB & UTILS (Mismas funciones base, agregamos logica admin) ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()
        # Tablas existentes...
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, full_name TEXT, role TEXT NOT NULL DEFAULT 'standard', is_verified BOOLEAN NOT NULL DEFAULT 0);""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS otp_codes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, code TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL, is_used BOOLEAN DEFAULT 0, type TEXT DEFAULT 'verify', FOREIGN KEY (user_id) REFERENCES users(id));""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, user_id INTEGER, action TEXT NOT NULL, details TEXT);""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS templates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT, base_path TEXT NOT NULL, is_active BOOLEAN DEFAULT 1);""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT NOT NULL, user_data_json TEXT, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_id INTEGER NOT NULL, template_id INTEGER NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (template_id) REFERENCES templates(id));""")
        
        # Plantillas base si está vacío
        cursor.execute("SELECT COUNT(*) FROM templates")
        if cursor.fetchone()[0] == 0:
            templates = [
                ('MinimalPortfolio', 'Portafolio elegante.', 'MinimalPortfolio'),
                ('StartupLanding', 'Landing page producto.', 'StartupLanding'),
                ('TechDark', 'Tema oscuro dev.', 'TechDark'),
                ('RestoMenu', 'Menú restaurante.', 'RestoMenu'),
                ('EventCountdown', 'Evento cuenta atrás.', 'EventCountdown'),
                ('BlogWriter', 'Blog simple.', 'BlogWriter'),
                ('AgencyBold', 'Agencia creativa.', 'AgencyBold')
            ]
            cursor.executemany("INSERT INTO templates (name, description, base_path) VALUES (?, ?, ?)", templates)
        conn.commit()
        conn.close()

def log_action(user_id, action, details=None):
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO logs (timestamp, user_id, action, details) VALUES (?, ?, ?, ?)", (datetime.datetime.now().isoformat(), user_id, action, details))
        conn.commit()
        conn.close()
    except: pass

def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = to_email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# --- DECORATORS ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try: token = request.headers['Authorization'].split(" ")[1]
            except: return jsonify({"message": "Token mal"}), 401
        if not token: return jsonify({"message": "Token faltante"}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user_id = data['user_id']
            request.user_role = data.get('role')
        except: return jsonify({"message": "Token inválido"}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    @token_required
    def decorated(current_user_id, *args, **kwargs):
        if request.user_role != 'admin':
            return jsonify({"message": "Acceso Denegado"}), 403
        return f(current_user_id, *args, **kwargs)
    return decorated

# --- AUTH ROUTES ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    email, password, username = data.get('email'), data.get('password'), data.get('username')
    conn = get_db_connection()
    try:
        if conn.execute("SELECT id FROM users WHERE email=? OR username=?", (email, username)).fetchone():
            return jsonify({"message": "Usuario existe"}), 409
        
        role = 'admin' if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0 else 'standard'
        hashed = pwd_context.hash(password)
        cur = conn.execute("INSERT INTO users (email, password_hash, username, role) VALUES (?, ?, ?, ?)", (email, hashed, username, role))
        uid = cur.lastrowid
        
        otp = ''.join(random.choices(string.digits, k=6))
        exp = datetime.datetime.now() + datetime.timedelta(minutes=10)
        conn.execute("INSERT INTO otp_codes (user_id, code, expires_at, type) VALUES (?, ?, ?, 'verify')", (uid, otp, exp))
        
        if send_email(email, "Verifica tu cuenta", f"Tu código es: {otp}"):
            conn.commit()
            return jsonify({"message": "Registrado. Verifica tu email.", "user_id": uid}), 201
        else:
            conn.rollback()
            return jsonify({"message": "Error email"}), 500
    finally: conn.close()

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    uid, code, type_ = data.get('user_id'), data.get('code'), data.get('type', 'verify')
    conn = get_db_connection()
    try:
        rec = conn.execute("SELECT * FROM otp_codes WHERE user_id=? AND code=? AND is_used=0 AND type=? ORDER BY id DESC LIMIT 1", (uid, code, type_)).fetchone()
        if not rec or datetime.datetime.fromisoformat(str(rec['expires_at'])) < datetime.datetime.now():
            return jsonify({"message": "Código inválido o expirado"}), 400
        
        conn.execute("UPDATE otp_codes SET is_used=1 WHERE id=?", (rec['id'],))
        if type_ == 'verify':
            conn.execute("UPDATE users SET is_verified=1 WHERE id=?", (uid,))
        conn.commit()
        return jsonify({"message": "Éxito"}), 200
    finally: conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    lid, pwd = data.get('login_id'), data.get('password')
    conn = get_db_connection()
    u = conn.execute("SELECT * FROM users WHERE email=? OR username=?", (lid, lid)).fetchone()
    conn.close()
    
    if not u or not pwd_context.verify(pwd, u['password_hash']): return jsonify({"message": "Credenciales mal"}), 401
    if not u['is_verified']: return jsonify({"message": "No verificado", "user_id": u['id'], "require_otp": True}), 403
    
    token = jwt.encode({'user_id': u['id'], 'role': u['role'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, SECRET_KEY, algorithm="HS256")
    return jsonify({"token": token, "username": u['username'], "role": u['role']}), 200

# --- FORGOT PASSWORD ROUTES ---
@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    conn = get_db_connection()
    u = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    
    if u:
        otp = ''.join(random.choices(string.digits, k=6))
        exp = datetime.datetime.now() + datetime.timedelta(minutes=10)
        conn.execute("INSERT INTO otp_codes (user_id, code, expires_at, type) VALUES (?, ?, ?, 'reset')", (u['id'], otp, exp))
        conn.commit()
        send_email(email, "Restablecer Contraseña", f"Usa este código para cambiar tu contraseña: {otp}")
        conn.close()
        return jsonify({"message": "Si el correo existe, se envió el código.", "user_id": u['id']}), 200
    conn.close()
    return jsonify({"message": "Si el correo existe, se envió el código."}), 200 # Seguridad: no revelar si existe

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    uid, code, new_pass = data.get('user_id'), data.get('code'), data.get('new_password')
    conn = get_db_connection()
    
    # Verificar OTP de tipo 'reset'
    rec = conn.execute("SELECT * FROM otp_codes WHERE user_id=? AND code=? AND is_used=0 AND type='reset' ORDER BY id DESC LIMIT 1", (uid, code)).fetchone()
    if not rec or datetime.datetime.fromisoformat(str(rec['expires_at'])) < datetime.datetime.now():
        conn.close()
        return jsonify({"message": "Código inválido o expirado"}), 400
    
    hashed = pwd_context.hash(new_pass)
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hashed, uid))
    conn.execute("UPDATE otp_codes SET is_used=1 WHERE id=?", (rec['id'],))
    conn.commit()
    conn.close()
    return jsonify({"message": "Contraseña actualizada"}), 200

# --- ADMIN ROUTES ---
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users(uid):
    conn = get_db_connection()
    users = conn.execute("SELECT id, username, email, role, is_verified FROM users").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route('/api/admin/logs', methods=['GET'])
@admin_required
def get_logs(uid):
    conn = get_db_connection()
    logs = conn.execute("SELECT l.*, u.username FROM logs l LEFT JOIN users u ON l.user_id=u.id ORDER BY l.timestamp DESC LIMIT 100").fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])

@app.route('/api/admin/upload-template', methods=['POST'])
@admin_required
def upload_template(uid):
    if 'file' not in request.files: return jsonify({"message": "No file"}), 400
    file = request.files['file']
    name = request.form.get('name')
    desc = request.form.get('description')
    
    if not file.filename.endswith('.zip'): return jsonify({"message": "Solo ZIPs"}), 400
    
    # Guardar y extraer
    safe_name = secure_filename(name).replace(" ", "_")
    extract_path = TEMPLATE_BASE_DIR / safe_name
    
    try:
        with ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Registrar en DB
        conn = get_db_connection()
        conn.execute("INSERT INTO templates (name, description, base_path) VALUES (?, ?, ?)", (name, desc, safe_name))
        conn.commit()
        conn.close()
        log_action(uid, 'UPLOAD_TEMPLATE', f"Plantilla {name} subida")
        return jsonify({"message": "Plantilla subida exitosamente"}), 201
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# --- PROJECT ROUTES (Igual que antes) ---
@app.route('/api/templates', methods=['GET'])
@token_required
def get_templates(uid):
    conn = get_db_connection()
    tpls = conn.execute("SELECT * FROM templates WHERE is_active=1").fetchall()
    conn.close()
    return jsonify([dict(t) for t in tpls])

@app.route('/api/projects', methods=['POST'])
@token_required
def create_project(uid):
    data = request.json
    conn = get_db_connection()
    cur = conn.execute("INSERT INTO projects (project_name, template_id, user_id, user_data_json) VALUES (?, ?, ?, ?)", (data['project_name'], data['template_id'], uid, data['user_data_json']))
    conn.commit()
    conn.close()
    return jsonify({"project_id": cur.lastrowid}), 201

@app.route('/api/projects/<int:pid>/download', methods=['GET'])
@token_required
def download(uid, pid):
    conn = get_db_connection()
    proj = conn.execute("SELECT p.*, t.base_path FROM projects p JOIN templates t ON p.template_id=t.id WHERE p.id=? AND p.user_id=?", (pid, uid)).fetchone()
    conn.close()
    if not proj: return jsonify({"message": "No encontrado"}), 404
    
    path = TEMPLATE_BASE_DIR / proj['base_path']
    if not path.exists(): return jsonify({"message": "Error archivos base"}), 500

    user_data = json.loads(proj['user_data_json'])
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zf:
        for fpath in path.rglob('*'):
            if fpath.is_file():
                content = fpath.read_bytes()
                if fpath.suffix in ['.html', '.css', '.js']:
                    text = content.decode('utf-8', errors='ignore')
                    for k, v in user_data.items():
                        if v: text = text.replace(f"[[{k}]]", str(v))
                    content = text.encode('utf-8')
                zf.writestr(fpath.name, content)
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name=f"{proj['project_name']}.zip")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)