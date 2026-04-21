// =========================================================
// 🔢 CONTADOR DE CARACTERES PARA TEXTAREAS
// =========================================================

class CharacterCounter {
    constructor() {
        this.limits = {
            // Campos de referencias
            titulo: { recommended: 200, max: 500 },
            contenido: { recommended: 5000, max: 150000 },
            texto_original: { recommended: 5000, max: 150000 },
            notas: { recommended: 500, max: 2000 },

            // Campos de publicaciones
            nombre: { recommended: 100, max: 200 },
            descripcion: { recommended: 1000, max: 5000 },
            descripcion_publicacion: { recommended: 500, max: 2000 }
        };

        this.init();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.attachCounters());
        } else {
            this.attachCounters();
        }
    }

    attachCounters() {
        Object.keys(this.limits).forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            // Crear contador
            const counter = this.createCounter(fieldName);

            // Insertar después del campo o en contenedor específico si existe
            const customContainer = document.getElementById(`counter-${fieldName}`);
            if (customContainer) {
                // Usar el contenedor existente y añadir el contador al principio (antes de los botones)
                customContainer.prepend(counter);
                // Ajustar estilos para modo toolbar
                counter.classList.remove('mt-1');
                counter.classList.add('me-auto'); // Empujar botones a la derecha si es flex
                counter.style.marginTop = '0';
            } else {
                field.parentElement.appendChild(counter);
            }

            // Actualizar contador
            const updateCounter = () => {
                const length = field.value.length;
                const limit = this.limits[fieldName];

                counter.textContent = `${length.toLocaleString()} caracteres`;

                // Cambiar color según límite
                counter.classList.remove('text-success', 'text-warning', 'text-danger');

                if (length > limit.max) {
                    counter.classList.add('text-danger');
                    counter.textContent += ` (excede máximo de ${limit.max.toLocaleString()})`;
                } else if (length > limit.recommended) {
                    counter.classList.add('text-warning');
                    counter.textContent += ` (recomendado: ${limit.recommended.toLocaleString()})`;
                } else if (length > 0) {
                    counter.classList.add('text-success');
                }
            };

            // Eventos
            field.addEventListener('input', updateCounter);
            field.addEventListener('paste', () => setTimeout(updateCounter, 10));

            // Actualizar inicial
            updateCounter();
        });
    }

    createCounter(fieldName) {
        const counter = document.createElement('div');
        counter.className = 'char-counter small mt-1';
        counter.style.fontFamily = "'JetBrains Mono', monospace";
        counter.style.fontSize = '0.75rem';
        return counter;
    }
}

// Inicializar contador
const charCounter = new CharacterCounter();
