document.addEventListener('DOMContentLoaded', () => {
    // Evitar error AOS
    if (typeof AOS !== 'undefined') {
        AOS.init({ duration: 800, once: true, offset: 50 });
    }
    // Iniciar Partículas
    if (document.getElementById('particles-js')) {
        particlesJS('particles-js', {
            "particles": {
                "number": { "value": 80 },
                "color": { "value": "#E60023" }, /* Color Rojo */
                "shape": { "type": "circle" },
                "opacity": { "value": 0.5, "random": true },
                "size": { "value": 3, "random": true },
                "line_linked": { "enable": false },
                "move": { "enable": true, "speed": 1 }
            },
            "interactivity": {
                "detect_on": "canvas",
                "events": { "onhover": { "enable": true, "mode": "repulse" } }
            }
        });
    }
});