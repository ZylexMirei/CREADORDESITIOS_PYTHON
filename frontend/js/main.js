// frontend/js/main.js - VERSIÓN COMPLETA (OTP + ADMIN + 7 PLANTILLAS)

const API_URL = 'http://127.0.0.1:5000/api';
let currentProjectId = null;
let templatesData = [];

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

// Wrapper para fetch con JWT
async function fetchAPI(endpoint, options = {}) {
    const token = localStorage.getItem('authToken');
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
    
    // Si el token expiró en una ruta protegida
    if (res.status === 401 && !endpoint.includes('/auth/')) {
        logout();
    }
    return res;
}

function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}

function checkAuth() {
    const token = localStorage.getItem('authToken');
    const path = window.location.pathname;
    
    // Si no hay token y no estamos en login/otp, sacar al usuario
    if (!token && !path.includes('index.html') && !path.includes('verify_otp.html')) {
        window.location.href = 'index.html';
        return false;
    }
    return true;
}

// --- INICIO DE LA APLICACIÓN ---
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    
    // 1. PANTALLA LOGIN/REGISTRO
    if (path.includes('index.html')) {
        setupAuthForms();
    } 
    // 2. PANTALLA OTP
    else if (path.includes('verify_otp.html')) {
        setupOTPForm();
    }
    // 3. DASHBOARD
    else if (path.includes('dashboard.html')) {
        if (checkAuth()) {
            setupDashboard();
            loadTemplates();
        }
    }
    // 4. ADMIN PAGE
    else if (path.includes('admin_page.html')) {
        if (checkAuth()) {
            const role = localStorage.getItem('role');
            if (role !== 'admin') {
                alert('Acceso denegado.');
                window.location.href = 'dashboard.html';
            } else {
                loadAdminLogs();
            }
        }
    }
    // 5. PÁGINA DE DESCARGA
    else if (path.includes('download_page.html')) {
        if (checkAuth()) setupDownloadPage();
    }
});

// --- LÓGICA DE FORMULARIOS (AUTH) ---
function setupAuthForms() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    // Alternar vistas
    document.getElementById('showRegister').onclick = () => {
        loginForm.style.display = 'none'; registerForm.style.display = 'block';
    };
    document.getElementById('showLogin').onclick = () => {
        registerForm.style.display = 'none'; loginForm.style.display = 'block';
    };

    // LOGIN
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const loginId = document.getElementById('loginId').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const res = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ login_id: loginId, password })
            });
            const data = await res.json();

            if (res.ok) {
                localStorage.setItem('authToken', data.token);
                localStorage.setItem('username', data.username);
                localStorage.setItem('role', data.role);
                window.location.href = 'dashboard.html';
            } else if (res.status === 403 && data.require_otp) {
                // Cuenta no verificada -> Enviar a OTP
                localStorage.setItem('tempUserId', data.user_id);
                window.location.href = 'verify_otp.html';
            } else {
                showMessage('message', data.message, 'error');
            }
        } catch (err) { showMessage('message', 'Error de conexión', 'error'); }
    });

    // REGISTRO
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;

        try {
            const res = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username, email, password })
            });
            const data = await res.json();

            if (res.ok) {
                localStorage.setItem('tempUserId', data.user_id); // Guardar ID temporalmente
                window.location.href = 'verify_otp.html'; // Ir a verificar
            } else {
                showMessage('message', data.message, 'error');
            }
        } catch (err) { showMessage('message', 'Error de conexión', 'error'); }
    });
}

// --- LÓGICA OTP ---
function setupOTPForm() {
    document.getElementById('otpForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const code = document.getElementById('otpCode').value;
        const userId = localStorage.getItem('tempUserId');

        try {
            const res = await fetch(`${API_URL}/auth/verify-otp`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId, code })
            });
            const data = await res.json();

            if (res.ok) {
                alert('¡Verificación exitosa! Por favor, inicia sesión.');
                window.location.href = 'index.html';
            } else {
                showMessage('message', data.message, 'error');
            }
        } catch (err) { showMessage('message', 'Error verificando código', 'error'); }
    });
}

// --- LÓGICA DASHBOARD ---
function setupDashboard() {
    const username = localStorage.getItem('username');
    const role = localStorage.getItem('role');
    
    document.getElementById('userDisplay').textContent = `${username} (${role})`;
    
    if (role === 'admin') {
        document.getElementById('adminLink').style.display = 'inline-block';
    }

    document.getElementById('saveBtn').addEventListener('click', async () => {
        const projectName = document.getElementById('projectName').value;
        const templateId = document.getElementById('templateSelect').value;
        
        if (!projectName || !templateId) {
            showMessage('projectMessage', 'Faltan datos obligatorios.', 'error');
            return;
        }

        // Recoger campos dinámicos
        const dynamicData = {};
        document.querySelectorAll('#dynamicFields input').forEach(input => {
            dynamicData[input.id] = input.value;
        });

        try {
            const res = await fetchAPI('/projects', {
                method: 'POST',
                body: JSON.stringify({
                    project_name: projectName,
                    template_id: templateId,
                    user_data_json: JSON.stringify(dynamicData)
                })
            });
            const data = await res.json();

            if (res.ok) {
                window.location.href = `download_page.html?id=${data.project_id}`;
            } else {
                showMessage('projectMessage', data.message, 'error');
            }
        } catch (err) { showMessage('projectMessage', 'Error al guardar', 'error'); }
    });
}

async function loadTemplates() {
    try {
        const res = await fetchAPI('/templates');
        const templates = await res.json();
        templatesData = templates; // Guardar cache

        const select = document.getElementById('templateSelect');
        select.innerHTML = '<option value="" disabled selected>Selecciona una plantilla...</option>';
        
        templates.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.id;
            opt.textContent = t.name;
            opt.dataset.base = t.base_path;
            select.appendChild(opt);
        });

        select.addEventListener('change', renderDynamicFields);
    } catch (err) { console.error(err); }
}

function renderDynamicFields() {
    const select = document.getElementById('templateSelect');
    const baseName = select.options[select.selectedIndex].dataset.base;
    const container = document.getElementById('dynamicFields');
    container.innerHTML = '';

    let fields = [];

    // Lógica para seleccionar los campos según la plantilla
    switch (baseName) {
        case 'MinimalPortfolio':
            fields = [
                { id: 'NOMBRE_COMPLETO', label: 'Nombre Completo' },
                { id: 'TITULO_PAGINA', label: 'Título Profesional' },
                { id: 'EMAIL_CONTACTO', label: 'Email de Contacto' },
                { id: 'DESCRIPCION_CORTA', label: 'Sobre mí (Breve)' },
                { id: 'LINK_PORTAFOLIO', label: 'Enlace a Trabajos' }
            ];
            break;
        case 'StartupLanding':
            fields = [
                { id: 'PRODUCTO_NOMBRE', label: 'Nombre del Producto' },
                { id: 'TITULAR_PRINCIPAL', label: 'Titular Principal' },
                { id: 'SUBTITULAR', label: 'Slogan / Subtítulo' },
                { id: 'CTA_TEXT', label: 'Texto Botón Acción' }
            ];
            break;
        case 'TechDark':
            fields = [
                { id: 'NOMBRE_DEV', label: 'Tu Nickname o Nombre' },
                { id: 'ROL_DEV', label: 'Rol (ej: Full Stack Dev)' },
                { id: 'BIO_CORTA', label: 'Línea de comando (Bio)' },
                { id: 'LINK_GITHUB', label: 'Enlace a GitHub' }
            ];
            break;
        case 'RestoMenu':
            fields = [
                { id: 'NOMBRE_RESTAURANTE', label: 'Nombre del Restaurante' },
                { id: 'ESPECIALIDAD', label: 'Especialidad (Tagline)' },
                { id: 'DESCRIPCION_PLATO', label: 'Plato Destacado' },
                { id: 'LINK_RESERVA', label: 'Link de Reservas/WhatsApp' }
            ];
            break;
        case 'EventCountdown':
            fields = [
                { id: 'NOMBRE_EVENTO', label: 'Nombre del Evento' },
                { id: 'FECHA_EVENTO', label: 'Fecha (Texto)' },
                { id: 'DESCRIPCION_EVENTO', label: 'Descripción corta' },
                { id: 'LINK_REGISTRO', label: 'Link de Registro' }
            ];
            break;
        case 'BlogWriter':
            fields = [
                { id: 'TITULO_BLOG', label: 'Título del Blog' },
                { id: 'NOMBRE_AUTOR', label: 'Nombre del Autor' },
                { id: 'INTRODUCCION_POST', label: 'Introducción (Texto)' },
                { id: 'LINK_REDES', label: 'Enlace a Redes' }
            ];
            break;
        case 'AgencyBold':
            fields = [
                { id: 'NOMBRE_AGENCIA', label: 'Nombre de la Agencia' },
                { id: 'SLOGAN_AGENCIA', label: 'Slogan de impacto' },
                { id: 'SERVICIOS_DESC', label: 'Descripción de Servicios' },
                { id: 'LINK_CONTACTO', label: 'Link de Contacto' }
            ];
            break;
        default:
            fields = [{ id: 'GENERICO', label: 'Dato Genérico' }];
    }

    fields.forEach(f => {
        const div = document.createElement('div');
        div.innerHTML = `<label>${f.label}</label><input type="text" id="${f.id}" required>`;
        container.appendChild(div);
    });
}
// --- LÓGICA DESCARGA ---
function setupDownloadPage() {
    const params = new URLSearchParams(window.location.search);
    const pid = params.get('id');
    const btn = document.getElementById('finalDownloadBtn');

    if (pid) {
        btn.onclick = async () => {
            try {
                const res = await fetchAPI(`/projects/${pid}/download`);
                if (res.ok) {
                    const blob = await res.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `proyecto_${pid}.zip`;
                    a.click();
                } else { alert('Error descargando'); }
            } catch (err) { alert('Error de red'); }
        };
    }
}

// --- LÓGICA ADMIN ---
async function loadAdminLogs() {
    const container = document.getElementById('logsContainer');
    try {
        const res = await fetchAPI('/admin/logs');
        const logs = await res.json();
        
        let html = `<table class="logs-table"><thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Detalles</th></tr></thead><tbody>`;
        logs.forEach(l => {
            html += `<tr>
                <td>${new Date(l.timestamp).toLocaleString()}</td>
                <td>${l.username || 'N/A'}</td>
                <td>${l.action}</td>
                <td>${l.details || '-'}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (err) { container.textContent = 'Error cargando logs.'; }
}