// frontend/js/main.js - VERSIÓN FINAL
const API_URL = 'http://127.0.0.1:5000/api';

function showMessage(id, text, type = 'success') {
    const el = document.getElementById(id);
    if (el) {
        el.style.display = 'block';
        el.className = `message ${type}`;
        el.innerHTML = text;
    }
}

async function fetchAPI(endpoint, options = {}) {
    const token = localStorage.getItem('authToken');
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(`${API_URL}${endpoint}`, { ...options, headers });
}

document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;

    // --- 1. LOGIN / REGISTRO ---
    if (path.includes('index.html')) {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');

        if(document.getElementById('showRegister')) {
            document.getElementById('showRegister').onclick = () => {
                loginForm.style.display = 'none'; registerForm.style.display = 'block';
            };
        }
        if(document.getElementById('showLogin')) {
            document.getElementById('showLogin').onclick = () => {
                registerForm.style.display = 'none'; loginForm.style.display = 'block';
            };
        }

        if(loginForm) {
            loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                try {
                    const res = await fetch(`${API_URL}/auth/login`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            login_id: document.getElementById('loginId').value,
                            password: document.getElementById('loginPassword').value
                        })
                    });
                    const data = await res.json();
                    
                    if (res.ok) {
                        localStorage.setItem('authToken', data.token);
                        localStorage.setItem('username', data.username);
                        localStorage.setItem('role', data.role);
                        window.location.href = 'dashboard.html';
                    } else if (res.status === 403) {
                        localStorage.setItem('tempUserId', data.user_id);
                        window.location.href = 'verify_otp.html';
                    } else {
                        showMessage('message', data.message, 'error');
                    }
                } catch(err) { showMessage('message', 'Error de conexión', 'error'); }
            });
        }

        if(registerForm) {
            registerForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                try {
                    const res = await fetch(`${API_URL}/auth/register`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            username: document.getElementById('registerUsername').value,
                            email: document.getElementById('registerEmail').value,
                            password: document.getElementById('registerPassword').value
                        })
                    });
                    const data = await res.json();
                    if (res.ok) {
                        localStorage.setItem('tempUserId', data.user_id);
                        window.location.href = 'verify_otp.html';
                    } else {
                        showMessage('message', data.message, 'error');
                    }
                } catch(err) { showMessage('message', 'Error de conexión', 'error'); }
            });
        }
    }

    // --- 2. VERIFICACIÓN OTP (CON REDIRECCIÓN AL DASHBOARD) ---
    else if (path.includes('verify_otp.html')) {
        const form = document.getElementById('otpForm');
        if(form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const userId = localStorage.getItem('tempUserId');
                const messageDiv = document.getElementById('message');
                const btn = e.target.querySelector('button');
                
                if (!userId) {
                    showMessage('message', 'Error: ID perdido. Regístrate de nuevo.', 'error');
                    return;
                }

                btn.textContent = "Entrando...";
                btn.disabled = true;

                try {
                    const res = await fetch(`${API_URL}/auth/verify-otp`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            user_id: userId,
                            code: document.getElementById('otpCode').value
                        })
                    });
                    
                    const data = await res.json();

                    if (res.ok) {
                        // GUARDAMOS EL TOKEN QUE NOS DA EL SERVIDOR
                        if (data.token) {
                            localStorage.setItem('authToken', data.token);
                            localStorage.setItem('username', data.username);
                            localStorage.setItem('role', data.role);
                            
                            // MENSAJE DE ÉXITO
                            form.style.display = 'none';
                            document.querySelector('.auth-container').innerHTML = `
                                <div style="text-align: center;">
                                    <h1 style="color: #4CAF50; font-size: 60px; margin: 10px 0;">✓</h1>
                                    <h2>¡Bienvenido!</h2>
                                    <p>Entrando al Dashboard...</p>
                                </div>
                            `;

                            // REDIRIGIR AL DASHBOARD
                            setTimeout(() => {
                                window.location.href = 'dashboard.html';
                            }, 1500);
                        } else {
                            showMessage('message', 'Error: Backend no envió token.', 'error');
                            btn.disabled = false;
                        }

                    } else {
                        showMessage('message', data.message || 'Código incorrecto', 'error');
                        btn.textContent = "Verificar";
                        btn.disabled = false;
                    }
                } catch(err) {
                    console.error(err);
                    showMessage('message', 'Error de conexión', 'error');
                    btn.textContent = "Verificar";
                    btn.disabled = false;
                }
            });
        }
    }

    // --- 3. DASHBOARD ---
    else if (path.includes('dashboard.html')) {
        const userDisplay = document.getElementById('userDisplay');
        if(userDisplay) userDisplay.textContent = localStorage.getItem('username');
        loadTemplates();
        
        document.getElementById('saveBtn').addEventListener('click', async () => {
            const inputs = document.querySelectorAll('#dynamicFields input');
            const data = {};
            inputs.forEach(i => data[i.id] = i.value);
            
            const res = await fetchAPI('/projects', {
                method: 'POST',
                body: JSON.stringify({
                    project_name: document.getElementById('projectName').value,
                    template_id: document.getElementById('templateSelect').value,
                    user_data_json: JSON.stringify(data)
                })
            });
            
            if(res.ok) {
                const d = await res.json();
                window.location.href = `download_page.html?id=${d.project_id}`;
            }
        });
    }
    
    // --- 4. DOWNLOAD ---
    else if (path.includes('download_page.html')) {
        const pid = new URLSearchParams(window.location.search).get('id');
        document.getElementById('finalDownloadBtn').onclick = async () => {
            const res = await fetchAPI(`/projects/${pid}/download`);
            if(res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = 'mi_sitio.zip'; a.click();
            }
        };
    }
});

async function loadTemplates() {
    const sel = document.getElementById('templateSelect');
    if(!sel) return;
    const res = await fetchAPI('/templates');
    const data = await res.json();
    
    sel.innerHTML = '<option>Selecciona...</option>';
    data.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.id;
        opt.textContent = t.name;
        opt.dataset.base = t.base_path;
        sel.appendChild(opt);
    });
    
    sel.addEventListener('change', () => {
        const base = sel.options[sel.selectedIndex].dataset.base;
        const container = document.getElementById('dynamicFields');
        container.innerHTML = '';
        const fields = ['Titulo', 'Descripcion', 'Contacto']; 
        fields.forEach(label => {
            const id = label.toUpperCase();
            container.innerHTML += `<label>${label}</label><input id="${id}" type="text">`;
        });
    });
}