/* frontend/js/main.js - VERSIÓN DEFINITIVA */

const API_URL = 'http://127.0.0.1:5000/api';

// --- UTILIDADES ---
function showMessage(id, text, type = 'success') {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = text;
        el.className = `message ${type}`;
        el.style.display = 'block';
        setTimeout(() => el.style.display = 'none', 5000);
    }
}

// Función para cerrar sesión (Logout)
function logout() {
    if(confirm("¿Estás seguro de que quieres salir?")) {
        localStorage.clear(); // Borra todo: token, usuario, ids temporales
        window.location.href = 'index.html';
    }
}

// Wrapper para conectar con el Backend (Fetch con Token)
async function fetchAPI(endpoint, options = {}) {
    const token = localStorage.getItem('authToken');
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
    
    // Si el token expiró, sacar al usuario
    if (res.status === 401 && !endpoint.includes('/auth/')) {
        alert("Tu sesión ha expirado.");
        logout();
    }
    return res;
}

// --- LÓGICA DE INICIO (Se ejecuta al cargar la página) ---
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;

    // 1. PANTALLA DE LOGIN / REGISTRO (index.html)
    if (path.includes('index.html')) {
        setupAuthForms();
    } 
    // 2. PANTALLA DE VERIFICACIÓN OTP (verify_otp.html)
    else if (path.includes('verify_otp.html')) {
        setupOTPForm();
    }
    // 3. DASHBOARD (dashboard.html)
    else if (path.includes('dashboard.html')) {
        checkAuth();
        setupDashboard(); // Cargar nombre de usuario, etc.
    }
    // 4. ADMIN (admin_page.html)
    else if (path.includes('admin_page.html')) {
        checkAuth();
        if (localStorage.getItem('role') !== 'admin') {
            alert('Acceso denegado. No eres Admin.');
            window.location.href = 'dashboard.html';
        }
    }
});

// --- FUNCIONES ESPECÍFICAS ---

function checkAuth() {
    if (!localStorage.getItem('authToken')) {
        window.location.href = 'index.html';
    }
}

function setupAuthForms() {
    // Botones para cambiar entre Login y Registro
    const showReg = document.getElementById('showRegister');
    const showLog = document.getElementById('showLogin');
    const formLog = document.getElementById('loginForm');
    const formReg = document.getElementById('registerForm');

    if(showReg) showReg.onclick = () => { formLog.style.display='none'; formReg.style.display='block'; };
    if(showLog) showLog.onclick = () => { formReg.style.display='none'; formLog.style.display='block'; };

    // LOGIN
    if(formLog) formLog.addEventListener('submit', async (e) => {
        e.preventDefault();
        const loginId = document.getElementById('loginId').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const res = await fetch(`${API_URL}/auth/login`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ login_id: loginId, password })
            });
            const data = await res.json();

            if (res.ok) {
                localStorage.setItem('authToken', data.token);
                localStorage.setItem('username', data.username);
                localStorage.setItem('role', data.role);
                window.location.href = 'dashboard.html';
            } else if (res.status === 403 && data.require_otp) {
                // Cuenta existe pero no verificada -> Guardar ID y mandar a verificar
                localStorage.setItem('tempUserId', data.user_id);
                alert("Cuenta no verificada. Por favor ingresa el código.");
                window.location.href = 'verify_otp.html';
            } else {
                showMessage('message', data.message || 'Error al entrar', 'error');
            }
        } catch (err) { showMessage('message', 'Error de conexión', 'error'); }
    });

    // REGISTRO
    if(formReg) formReg.addEventListener('submit', async (e) => {
        e.preventDefault();
        const u = document.getElementById('registerUsername').value;
        const em = document.getElementById('registerEmail').value;
        const p = document.getElementById('registerPassword').value;

        try {
            const res = await fetch(`${API_URL}/auth/register`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username: u, email: em, password: p })
            });
            const data = await res.json();

            if (res.ok) {
                // ¡IMPORTANTE! Guardamos el ID temporal para la verificación
                localStorage.setItem('tempUserId', data.user_id); 
                alert('¡Registro exitoso! Revisa la terminal/correo para el código.');
                window.location.href = 'verify_otp.html';
            } else {
                showMessage('message', data.message || 'Error al registrar', 'error');
            }
        } catch (err) { showMessage('message', 'Error de conexión', 'error'); }
    });
}

function setupOTPForm() {
    const form = document.getElementById('otpForm');
    if(form) form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const code = document.getElementById('otpCode').value;
        // Recuperamos el ID que guardamos en el paso anterior
        const userId = localStorage.getItem('tempUserId');

        if (!userId) {
            alert("Error: No se encontró el usuario. Regístrate de nuevo.");
            window.location.href = 'index.html';
            return;
        }

        try {
            const res = await fetch(`${API_URL}/auth/verify-otp`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId, code: code })
            });
            const data = await res.json();

            if (res.ok) {
                alert('¡Verificación exitosa! Ahora inicia sesión.');
                localStorage.removeItem('tempUserId'); // Limpieza
                window.location.href = 'index.html';
            } else {
                showMessage('message', data.message || 'Código incorrecto', 'error');
            }
        } catch (err) { showMessage('message', 'Error al verificar', 'error'); }
    });
}

function setupDashboard() {
    const userDisplay = document.getElementById('userDisplay');
    const adminLink = document.getElementById('adminLink');
    const uName = localStorage.getItem('username');
    const role = localStorage.getItem('role');

    if(userDisplay) userDisplay.innerHTML = `<i class="fa-solid fa-user"></i> ${uName}`;
    if(adminLink && role === 'admin') adminLink.style.display = 'inline-block';
}