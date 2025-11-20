/* * effects.js
 * Configuración para Particles.js y AOS.js
 */

document.addEventListener('DOMContentLoaded', () => {

    // 1. Inicializar AOS (Animación al Hacer Scroll)
    AOS.init({
        duration: 800, // Duración de la animación en milisegundos
        once: true, // La animación solo ocurre una vez
        offset: 50, // Se activa 50px antes de que el elemento llegue
    });

    // 2. Inicializar Particles.js (Fondo Anmado)
    // Solo lo activamos si el elemento #particles-js existe (en landing.html)
    if (document.getElementById('particles-js')) {
        particlesJS('particles-js', {
            "particles": {
                "number": {
                    "value": 100, // Cantidad de partículas
                    "density": {
                        "enable": true,
                        "value_area": 800
                    }
                },
                "color": {
                    "value": "#E60023" // 🛑 Color Rojo
                },
                "shape": {
                    "type": "circle",
                    "stroke": {
                        "width": 0,
                        "color": "#000000"
                    }
                },
                "opacity": {
                    "value": 0.5, // Ligeramente transparentes
                    "random": true,
                    "anim": {
                        "enable": true,
                        "speed": 1,
                        "opacity_min": 0.1,
                        "sync": false
                    }
                },
                "size": {
                    "value": 3,
                    "random": true,
                    "anim": {
                        "enable": false,
                        "speed": 40,
                        "size_min": 0.1,
                        "sync": false
                    }
                },
                "line_linked": {
                    "enable": false, // Sin líneas entre ellas
                },
                "move": {
                    "enable": true,
                    "speed": 1, // Velocidad lenta
                    "direction": "none",
                    "random": false,
                    "straight": false,
                    "out_mode": "out",
                    "bounce": false,
                    "attract": {
                        "enable": false,
                        "rotateX": 600,
                        "rotateY": 1200
                    }
                }
            },
            "interactivity": {
                "detect_on": "canvas",
                "events": {
                    "onhover": {
                        "enable": true, // Activa la interactividad con el mouse
                        "mode": "repulse" // Las partículas huyen del mouse
                    },
                    "onclick": {
                        "enable": true,
                        "mode": "push" // Añade partículas al hacer clic
                    },
                    "resize": true
                },
                "modes": {
                    "repulse": {
                        "distance": 100,
                        "duration": 0.4
                    },
                    "push": {
                        "particles_nb": 4
                    }
                }
            },
            "retina_detect": true
        });
    }
});