# app.py - VERSIÓN FINAL CORREGIDA
import os
import sqlite3
import datetime
import json
import random
import string  # <--- ESTO FALTABA Y ERA EL ERROR
import smtplib
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
SECRET_KEY = "SUPER_SECRET_KEY_2025"

# TUS CREDENCIALES REALES
EMAIL_USER = "tomate0615@gmail.com" 
EMAIL_PASS = "vkrz jmuu zzpc ihts" 

DATABASE_NAME = "sitios.db"
BASE_DIR = Path(__file__).resolve().parent
SITE_OUTPUT_DIR = BASE_DIR / 'site_output'
TEMPLATE_BASE_DIR = BASE_DIR / 'template_base'

if not SITE_OUTPUT_DIR.exists(): SITE_OUTPUT_DIR.mkdir()
if not TEMPLATE_BASE_DIR.exists(): TEMPLATE_BASE_DIR.mkdir()

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# --- BASE DE DATOS ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'standard', is_verified BOOLEAN NOT NULL DEFAULT 0);""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS otp_codes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, code TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL, is_used BOOLEAN DEFAULT 0, type TEXT DEFAULT 'verify', FOREIGN KEY (user_id) REFERENCES users(id));""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, user_id INTEGER, action TEXT NOT NULL, details TEXT);""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS templates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT, base_path TEXT NOT NULL, is_active BOOLEAN DEFAULT 1);""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT NOT NULL, user_data_json TEXT, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_id INTEGER NOT NULL, template_id INTEGER NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (template_id) REFERENCES templates(id));""")
        
        # Plantillas Base
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

# --- UTILIDAD DE CORREO (HÍBRIDA) ---
def send_email(to_email, subject, body):
    print(f"\n--- Intentando enviar correo a {to_email} ---")
    try:
        # Intentar envío REAL
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        
        print("✅ ¡ÉXITO! Correo enviado correctamente.")
        return True

    except Exception as e:
        # Si falla, usar MODO RESPALDO (Consola)
        print(f"❌ Error enviando correo real: {e}")
        print("⚠️  ACTIVANDO MODO RESPALDO (Copia el código de aquí abajo):")
        print("█"*60)
        print(f"🔐 [CÓDIGO DE RESPALDO]")
        print(f"📨 Para: {to_email}")
        print(f"🔑 MENSAJE: {body}")
        print("█"*60 + "\n")
        return True 

# --- DECORADORES ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try: token = request.headers['Authorization'].split(" ")[1]
            except: return jsonify({"message": "Token mal"}), 401
        if not token: return jsonify({"message": "Falta token"}), 401
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
            return jsonify({"message": "Solo Admins"}), 403
        return f(current_user_id, *args, **kwargs)
    return decorated

# --- RUTAS ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    email, password, username = data.get('email'), data.get('password'), data.get('username')
    conn = get_db_connection()
    try:
        if conn.execute("SELECT id FROM users WHERE email=? OR username=?", (email, username)).fetchone():
            return jsonify({"message": "Usuario ya existe"}), 409
        
        # El primero es admin
        role = 'admin' if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0 else 'standard'
        hashed = pwd_context.hash(password)
        cur = conn.execute("INSERT INTO users (email, password_hash, username, role) VALUES (?, ?, ?, ?)", (email, hashed, username, role))
        uid = cur.lastrowid
        
        otp = ''.join(random.choices(string.digits, k=6))
        exp = datetime.datetime.now() + datetime.timedelta(minutes=10)
        conn.execute("INSERT INTO otp_codes (user_id, code, expires_at, type) VALUES (?, ?, ?, 'verify')", (uid, otp, exp))
        conn.commit()
        
        send_email(email, "Verifica tu cuenta", f"Tu código de verificación es: {otp}")
        return jsonify({"message": "Registrado", "user_id": uid}), 201
    finally: conn.close()

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    uid, code, type_ = data.get('user_id'), data.get('code'), data.get('type', 'verify')
    conn = get_db_connection()
    try:
        rec = conn.execute("SELECT * FROM otp_codes WHERE user_id=? AND code=? AND is_used=0 AND type=? ORDER BY id DESC LIMIT 1", (uid, code, type_)).fetchone()
        if not rec: return jsonify({"message": "Código incorrecto"}), 400
        
        conn.execute("UPDATE otp_codes SET is_used=1 WHERE id=?", (rec['id'],))
        if type_ == 'verify': conn.execute("UPDATE users SET is_verified=1 WHERE id=?", (uid,))
        conn.commit()
        return jsonify({"message": "Éxito"}), 200
    finally: conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    lid, pwd = data.get('login_id'), data.get('password')
    conn = get_db_connection()
    u = conn.execute("SELECT * FROM users WHERE email=? OR username=?", (lid, lid)).fetchone()
    
    if not u or not pwd_context.verify(pwd, u['password_hash']):
        conn.close()
        return jsonify({"message": "Datos incorrectos"}), 401
        
    if not u['is_verified']:
        # REENVIAR CÓDIGO SI NO ESTÁ VERIFICADO
        new_otp = ''.join(random.choices(string.digits, k=6))
        exp = datetime.datetime.now() + datetime.timedelta(minutes=10)
        conn.execute("INSERT INTO otp_codes (user_id, code, expires_at, type) VALUES (?, ?, ?, 'verify')", (u['id'], new_otp, exp))
        conn.commit()
        conn.close()
        send_email(u['email'], "Código de Verificación", f"Tu código es: {new_otp}")
        return jsonify({"message": "Cuenta no verificada. Código reenviado.", "user_id": u['id'], "require_otp": True}), 403
    
    conn.close()
    token = jwt.encode({'user_id': u['id'], 'role': u['role'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, SECRET_KEY, algorithm="HS256")
    return jsonify({"token": token, "username": u['username'], "role": u['role']}), 200

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
        send_email(email, "Recuperar Password", f"Tu código de recuperación es: {otp}")
        conn.close()
        return jsonify({"message": "Enviado", "user_id": u['id']}), 200
    conn.close()
    return jsonify({"message": "Enviado"}), 200

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    uid, code, new_pass = data.get('user_id'), data.get('code'), data.get('new_password')
    conn = get_db_connection()
    rec = conn.execute("SELECT * FROM otp_codes WHERE user_id=? AND code=? AND is_used=0 AND type='reset' ORDER BY id DESC LIMIT 1", (uid, code)).fetchone()
    if not rec:
        conn.close()
        return jsonify({"message": "Código inválido"}), 400
    
    hashed = pwd_context.hash(new_pass)
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hashed, uid))
    conn.execute("UPDATE otp_codes SET is_used=1 WHERE id=?", (rec['id'],))
    conn.commit()
    conn.close()
    return jsonify({"message": "Contraseña actualizada"}), 200

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users(uid):
    conn = get_db_connection()
    users = conn.execute("SELECT id, username, email, role, is_verified FROM users").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route('/api/admin/upload-template', methods=['POST'])
@admin_required
def upload(uid):
    if 'file' not in request.files: return jsonify({"message": "Falta archivo"}), 400
    file = request.files['file']
    name = request.form.get('name')
    desc = request.form.get('description')
    
    safe_name = secure_filename(name).replace(" ", "_")
    path = TEMPLATE_BASE_DIR / safe_name
    try:
        with ZipFile(file, 'r') as z: z.extractall(path)
        conn = get_db_connection()
        conn.execute("INSERT INTO templates (name, description, base_path) VALUES (?, ?, ?)", (name, desc, safe_name))
        conn.commit()
        conn.close()
        return jsonify({"message": "Subido"}), 201
    except Exception as e: return jsonify({"message": str(e)}), 500

@app.route('/api/templates', methods=['GET'])
@token_required
def list_templates(uid):
    conn = get_db_connection()
    t = conn.execute("SELECT * FROM templates WHERE is_active=1").fetchall()
    conn.close()
    return jsonify([dict(row) for row in t])

@app.route('/api/projects', methods=['POST'])
@token_required
def create_proj(uid):
    data = request.json
    conn = get_db_connection()
    cur = conn.execute("INSERT INTO projects (project_name, template_id, user_id, user_data_json) VALUES (?, ?, ?, ?)", (data['project_name'], data['template_id'], uid, data['user_data_json']))
    conn.commit()
    conn.close()
    return jsonify({"project_id": cur.lastrowid}), 201

@app.route('/api/projects/<int:pid>/download', methods=['GET'])
@token_required
def download_proj(uid, pid):
    conn = get_db_connection()
    p = conn.execute("SELECT p.*, t.base_path FROM projects p JOIN templates t ON p.template_id=t.id WHERE p.id=? AND p.user_id=?", (pid, uid)).fetchone()
    conn.close()
    if not p: return jsonify({"message": "Error"}), 404
    
    path = TEMPLATE_BASE_DIR / p['base_path']
    if not path.exists(): return jsonify({"message": "Plantilla no existe en disco"}), 500
    
    user_data = json.loads(p['user_data_json'])
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zf:
        for f in path.rglob('*'):
            if f.is_file():
                content = f.read_bytes()
                if f.suffix in ['.html', '.css', '.js']:
                    text = content.decode('utf-8', errors='ignore')
                    for k, v in user_data.items():
                        if v: text = text.replace(f"[[{k}]]", str(v))
                    content = text.encode('utf-8')
                zf.writestr(f.name, content)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/zip', as_attachment=True, download_name=f"{p['project_name']}.zip")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)