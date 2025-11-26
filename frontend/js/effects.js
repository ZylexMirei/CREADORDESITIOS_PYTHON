/* frontend/js/effects.js - CORREGIDO */

document.addEventListener('DOMContentLoaded', () => {

    // 1. Inicializar AOS (Animaciones) SOLO SI EXISTE
    // Esto evita el error "AOS is not defined"
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            once: true,
            offset: 50,
        });
    }

    // 2. Inicializar Particles.js (Fondo de Puntitos)
    if (document.getElementById('particles-js')) {
        particlesJS('particles-js', {
            "particles": {
                "number": { "value": 80, "density": { "enable": true, "value_area": 800 } },
                "color": { "value": "#E60023" }, /* Color Rojo de los puntos */
                "shape": { "type": "circle" },
                "opacity": { "value": 0.5, "random": true },
                "size": { "value": 3, "random": true },
                "line_linked": { "enable": false }, /* Sin líneas uniendo puntos */
                "move": {
                    "enable": true,
                    "speed": 1, /* Lento y elegante */
                    "direction": "none",
                    "random": false,
                    "out_mode": "out"
                }
            },
            "interactivity": {
                "detect_on": "canvas",
                "events": {
                    "onhover": { "enable": true, "mode": "repulse" },
                    "onclick": { "enable": true, "mode": "push" },
                    "resize": true
                }
            },
            "retina_detect": true
        });
    }
});