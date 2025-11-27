/* frontend/js/main.js - VERSIÓN FINAL */
const API_URL = 'http://127.0.0.1:5000/api';

function showMessage(id, text, type = 'success') {
    const el = document.getElementById(id);
    if (el) { el.textContent = text; el.className = `message ${type}`; el.style.display = 'block'; setTimeout(() => el.style.display = 'none', 5000); }
}

function logout() {
    if(confirm("¿Cerrar sesión?")) { localStorage.clear(); window.location.href = 'index.html'; }
}

async function fetchAPI(endpoint, options = {}) {
    const token = localStorage.getItem('authToken');
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
    if (res.status === 401 && !endpoint.includes('/auth/')) logout();
    return res;
}

document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    if (path.includes('index.html')) setupAuthForms();
    else if (path.includes('verify_otp.html')) setupOTPForm();
    else if (path.includes('dashboard.html')) { checkAuth(); setupDashboard(); }
    else if (path.includes('admin_page.html')) { checkAuth(); if (localStorage.getItem('role') !== 'admin') window.location.href = 'dashboard.html'; }
});

function checkAuth() { if (!localStorage.getItem('authToken')) window.location.href = 'index.html'; }

function setupAuthForms() {
    const showReg = document.getElementById('showRegister');
    const showLog = document.getElementById('showLogin');
    const formLog = document.getElementById('loginForm');
    const formReg = document.getElementById('registerForm');

    if(showReg) showReg.onclick = () => { formLog.style.display='none'; formReg.style.display='block'; };
    if(showLog) showLog.onclick = () => { formReg.style.display='none'; formLog.style.display='block'; };

    if(formLog) formLog.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const res = await fetch(`${API_URL}/auth/login`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ login_id: document.getElementById('loginId').value, password: document.getElementById('loginPassword').value }) });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('authToken', data.token); localStorage.setItem('username', data.username); localStorage.setItem('role', data.role);
                window.location.href = 'dashboard.html';
            } else if (res.status === 403 && data.require_otp) {
                localStorage.setItem('tempUserId', data.user_id); alert(data.message); window.location.href = 'verify_otp.html';
            } else showMessage('message', data.message || 'Error', 'error');
        } catch (err) { showMessage('message', 'Error de conexión', 'error'); }
    });

    if(formReg) formReg.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const res = await fetch(`${API_URL}/auth/register`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ username: document.getElementById('registerUsername').value, email: document.getElementById('registerEmail').value, password: document.getElementById('registerPassword').value }) });
            const data = await res.json();
            if (res.ok) { localStorage.setItem('tempUserId', data.user_id); alert('Registro exitoso. Verifique su correo.'); window.location.href = 'verify_otp.html'; }
            else showMessage('message', data.message, 'error');
        } catch (err) { showMessage('message', 'Error de conexión', 'error'); }
    });
}

function setupOTPForm() {
    const form = document.getElementById('otpForm');
    if(form) form.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const res = await fetch(`${API_URL}/auth/verify-otp`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ user_id: localStorage.getItem('tempUserId'), code: document.getElementById('otpCode').value }) });
            const data = await res.json();
            if (res.ok) { alert('Cuenta Verificada. Inicia sesión.'); localStorage.removeItem('tempUserId'); window.location.replace('index.html'); }
            else showMessage('message', data.message, 'error');
        } catch (err) { showMessage('message', 'Error', 'error'); }
    });
}

function setupDashboard() {
    const uDis = document.getElementById('userDisplay');
    const aLink = document.getElementById('adminLink');
    if(uDis) uDis.innerHTML = `<i class="fa-solid fa-user"></i> ${localStorage.getItem('username')}`;
    if(aLink && localStorage.getItem('role') === 'admin') aLink.style.display = 'inline-block';
}