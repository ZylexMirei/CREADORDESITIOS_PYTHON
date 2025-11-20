# app.py - VERSIÓN FINAL PRO (OTP, Roles, Logs, 7 Plantillas)
import os
import sqlite3
import datetime
import json
import random
import string
import smtplib
from email.mime.text import MIMEText
from functools import wraps
from io import BytesIO
from zipfile import ZipFile
from pathlib import Path
import jwt

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from passlib.context import CryptContext

# --- CONFIGURACIÓN ---
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY_2025")
# Configuración de Email (Pon estos en tu .env idealmente)
EMAIL_USER = os.getenv("EMAIL_USER", "MI_CORREO") 
EMAIL_PASS = os.getenv("EMAIL_PASS", "MI_CONTRASEÑA_DE_APP") 

DATABASE_NAME = "sitios.db"
BASE_DIR = Path(__file__).resolve().parent
SITE_OUTPUT_DIR = BASE_DIR / 'site_output'
TEMPLATE_BASE_DIR = BASE_DIR / 'template_base'

if not SITE_OUTPUT_DIR.exists(): SITE_OUTPUT_DIR.mkdir()

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# --- DB ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tabla usuarios actualizada con verificación
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT NOT NULL DEFAULT 'standard',
                is_verified BOOLEAN NOT NULL DEFAULT 0
            );
        """)
        
        # Tabla OTP para control estricto
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otp_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                base_path TEXT NOT NULL,
                thumbnail_url TEXT,
                is_active BOOLEAN DEFAULT 1
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                user_data_json TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                template_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (template_id) REFERENCES templates(id)
            );
        """)
        
        # Semilla de 7 Plantillas
        cursor.execute("SELECT COUNT(*) FROM templates")
        if cursor.fetchone()[0] == 0:
            templates = [
                ('MinimalPortfolio', 'Portafolio elegante y minimalista (Mejorado).', 'MinimalPortfolio'),
                ('StartupLanding', 'Landing page moderna para productos (Mejorado).', 'StartupLanding'),
                ('TechDark', 'Tema oscuro ideal para desarrolladores.', 'TechDark'),
                ('RestoMenu', 'Elegancia para restaurantes y menús.', 'RestoMenu'),
                ('EventCountdown', 'Página de evento con cuenta regresiva.', 'EventCountdown'),
                ('BlogWriter', 'Enfoque en tipografía para escritores.', 'BlogWriter'),
                ('AgencyBold', 'Diseño audaz y corporativo.', 'AgencyBold')
            ]
            cursor.executemany("INSERT INTO templates (name, description, base_path) VALUES (?, ?, ?)", templates)

        conn.commit()
        conn.close()

# --- UTILIDADES ---
def log_action(user_id, action, details=None):
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO logs (timestamp, user_id, action, details) VALUES (?, ?, ?, ?)",
                     (datetime.datetime.now().isoformat(), user_id, action, details))
        conn.commit()
        conn.close()
    except: pass

def send_email_otp(to_email, otp_code):
    msg = MIMEText(f"Tu código de verificación es: {otp_code}\n\nExpira en 5 minutos.")
    msg['Subject'] = "Código de Verificación - Proyecto Isabella"
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
        print(f"Error enviando email: {e}")
        return False

# --- DECORADORES ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try: token = request.headers['Authorization'].split(" ")[1]
            except: return jsonify({"message": "Token mal formateado."}), 401
        if not token: return jsonify({"message": "Token faltante."}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user_id = data['user_id']
            # Validar rol admin si es necesario
            request.user_role = data.get('role')
        except: return jsonify({"message": "Token inválido o expirado."}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    @token_required
    def decorated(current_user_id, *args, **kwargs):
        if request.user_role != 'admin':
            return jsonify({"message": "Acceso denegado. Solo Admins."}), 403
        return f(current_user_id, *args, **kwargs)
    return decorated

# --- RUTAS AUTH & OTP ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    email, password, username = data.get('email'), data.get('password'), data.get('username')
    
    if not all([email, password, username]): return jsonify({"message": "Datos incompletos"}), 400

    conn = get_db_connection()
    try:
        if conn.execute("SELECT id FROM users WHERE email=? OR username=?", (email, username)).fetchone():
            return jsonify({"message": "Usuario ya existe"}), 409
        
        # Rol admin para el primero
        role = 'admin' if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0 else 'standard'
        hashed = pwd_context.hash(password)
        
        cur = conn.execute("INSERT INTO users (email, password_hash, username, role, is_verified) VALUES (?, ?, ?, ?, 0)",
                           (email, hashed, username, role))
        user_id = cur.lastrowid
        
        # Generar OTP
        otp = ''.join(random.choices(string.digits, k=6))
        expires = datetime.datetime.now() + datetime.timedelta(minutes=5)
        
        conn.execute("INSERT INTO otp_codes (user_id, code, expires_at) VALUES (?, ?, ?)",
                     (user_id, otp, expires))
        conn.commit()
        
        if send_email_otp(email, otp):
            log_action(user_id, 'REGISTER_INIT', 'OTP enviado')
            return jsonify({"message": "Usuario registrado. Verifique su email.", "user_id": user_id}), 201
        else:
            return jsonify({"message": "Error enviando email, pero usuario creado."}), 500
            
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    finally: conn.close()

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    user_id, code = data.get('user_id'), data.get('code')
    
    conn = get_db_connection()
    try:
        # Buscar OTP válido y no usado
        record = conn.execute("""
            SELECT * FROM otp_codes 
            WHERE user_id=? AND code=? AND is_used=0 
            ORDER BY created_at DESC LIMIT 1
        """, (user_id, code)).fetchone()
        
        if not record:
            log_action(user_id, 'OTP_FAIL', 'Código incorrecto o no encontrado')
            return jsonify({"message": "Código inválido."}), 400
            
        # Chequear expiración (formato string sqlite)
        exp = datetime.datetime.fromisoformat(record['expires_at'])
        if datetime.datetime.now() > exp:
            log_action(user_id, 'OTP_EXPIRED', 'Código expirado intentado')
            return jsonify({"message": "El código ha expirado."}), 400
            
        # Éxito
        conn.execute("UPDATE otp_codes SET is_used=1 WHERE id=?", (record['id'],))
        conn.execute("UPDATE users SET is_verified=1 WHERE id=?", (user_id,))
        conn.commit()
        
        log_action(user_id, 'VERIFIED', 'Cuenta verificada exitosamente')
        return jsonify({"message": "Cuenta verificada. Puede iniciar sesión."}), 200
        
    finally: conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    login_id, password = data.get('login_id'), data.get('password')
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email=? OR username=?", (login_id, login_id)).fetchone()
    conn.close()
    
    if not user or not pwd_context.verify(password, user['password_hash']):
        return jsonify({"message": "Credenciales inválidas"}), 401
    
    if not user['is_verified']:
        return jsonify({"message": "Cuenta no verificada", "user_id": user['id'], "require_otp": True}), 403

    token = jwt.encode({
        'user_id': user['id'],
        'role': user['role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, SECRET_KEY, algorithm="HS256")
    
    log_action(user['id'], 'LOGIN', 'Login exitoso')
    return jsonify({"token": token, "username": user['username'], "role": user['role']}), 200

# --- RUTAS PROYECTOS (Resumen) ---
@app.route('/api/templates', methods=['GET'])
@token_required
def get_templates(uid):
    conn = get_db_connection()
    tpls = conn.execute("SELECT * FROM templates WHERE is_active=1").fetchall()
    conn.close()
    return jsonify([dict(t) for t in tpls]), 200

@app.route('/api/projects', methods=['POST'])
@token_required
def create_project(uid):
    data = request.json
    # ... (Lógica de creación idéntica a tu versión anterior) ...
    conn = get_db_connection()
    try:
        cur = conn.execute("INSERT INTO projects (project_name, template_id, user_id, user_data_json) VALUES (?, ?, ?, ?)",
                           (data['project_name'], data['template_id'], uid, data['user_data_json']))
        conn.commit()
        return jsonify({"message": "Creado", "project_id": cur.lastrowid}), 201
    except Exception as e: return jsonify({"message": str(e)}), 500
    finally: conn.close()

@app.route('/api/projects/<int:pid>/download', methods=['GET'])
@token_required
def download(uid, pid):
    conn = get_db_connection()
    proj = conn.execute("SELECT p.*, t.base_path FROM projects p JOIN templates t ON p.template_id=t.id WHERE p.id=? AND p.user_id=?", (pid, uid)).fetchone()
    conn.close()
    
    if not proj: return jsonify({"message": "No encontrado"}), 404
    
    # Generación ZIP
    user_data = json.loads(proj['user_data_json'])
    files = generate_site_content(proj['base_path'], user_data)
    
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zf:
        for name, content in files: zf.writestr(name, content)
    zip_buffer.seek(0)
    
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name=f"{proj['project_name']}.zip")

# Función auxiliar para leer plantillas
def generate_site_content(base_path, data):
    path = TEMPLATE_BASE_DIR / base_path
    if not path.exists(): return []
    
    files = []
    # Intenta leer index.html y style.css
    for fname in ['index.html', 'style.css']:
        fpath = path / fname
        if fpath.exists():
            content = fpath.read_text(encoding='utf-8')
            for k, v in data.items(): content = content.replace(f"[[{k}]]", str(v))
            files.append((fname, content))
    return files

# --- ADMIN ---
@app.route('/api/admin/logs', methods=['GET'])
@admin_required
def get_logs(uid):
    conn = get_db_connection()
    logs = conn.execute("SELECT l.*, u.username FROM logs l LEFT JOIN users u ON l.user_id=u.id ORDER BY l.timestamp DESC LIMIT 100").fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)