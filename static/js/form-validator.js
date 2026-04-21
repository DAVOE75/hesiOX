// =========================================================
// 📋 VALIDACIÓN EN TIEMPO REAL PARA FORMULARIOS
// =========================================================

class FormValidator {
    constructor() {
        this.rules = {
            // Campos de referencias bibliográficas
            titulo: { required: true, minLength: 3, maxLength: 500 },
            publicacion: { required: false, minLength: 2 },
            fecha_original: { required: false, pattern: /^\d{1,2}\/\d{1,2}\/\d{4}$/ },
            fecha_consulta: { required: false, pattern: /^\d{1,2}\/\d{1,2}\/\d{4}$/ },
            anio: { required: false, min: 1000, max: 2100 },
            url: { required: false, pattern: /^https?:\/\/.+/ },
            pagina_inicio: { required: false, pattern: /^\d+$/ },
            pagina_fin: { required: false, pattern: /^\d+$/ },
            contenido: { required: false, minLength: 10 },
            numero_referencia: { required: false, min: 1, max: 9999, pattern: /^\d+$/ },

            // Campos de publicaciones (medios)
            nombre: { required: true, minLength: 2, maxLength: 200 },
            ciudad: { required: false, minLength: 2, maxLength: 100 },
            pais: { required: false, minLength: 2, maxLength: 100 },
            pais_publicacion: { required: false, minLength: 2, maxLength: 100 },
            descripcion: { required: false, minLength: 10, maxLength: 5000 },
            idioma: { required: false, minLength: 2, maxLength: 50 },
            licencia: { required: false, minLength: 3 },
        };

        this.init();
    }

    init() {
        // Esperar a que el DOM esté listo
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.attachValidators());
        } else {
            this.attachValidators();
        }
    }

    attachValidators() {
        // Validar todos los campos con reglas definidas
        Object.keys(this.rules).forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field) {
                // Validar mientras escribe (con debounce)
                let timeout;
                field.addEventListener('input', () => {
                    clearTimeout(timeout);
                    timeout = setTimeout(() => this.validateField(field, fieldName), 300);
                });

                // Validar al perder foco
                field.addEventListener('blur', () => this.validateField(field, fieldName));
            }
        });

        // Validar páginas (inicio <= fin)
        const pagIni = document.querySelector('[name="pagina_inicio"]');
        const pagFin = document.querySelector('[name="pagina_fin"]');
        if (pagIni && pagFin) {
            pagIni.addEventListener('input', () => this.validatePageRange(pagIni, pagFin));
            pagFin.addEventListener('input', () => this.validatePageRange(pagIni, pagFin));
        }
    }

    validateField(field, fieldName) {
        const rule = this.rules[fieldName];
        const value = field.value.trim();
        let isValid = true;
        let message = '';

        // Required
        if (rule.required && !value) {
            isValid = false;
            message = 'Campo obligatorio';
        }

        // MinLength
        if (value && rule.minLength && value.length < rule.minLength) {
            isValid = false;
            message = `Mínimo ${rule.minLength} caracteres`;
        }

        // MaxLength
        if (value && rule.maxLength && value.length > rule.maxLength) {
            isValid = false;
            message = `Máximo ${rule.maxLength} caracteres`;
        }

        // Pattern (regex)
        if (value && rule.pattern && !rule.pattern.test(value)) {
            isValid = false;
            if (fieldName.includes('fecha')) {
                message = 'Formato: DD/MM/AAAA';
            } else if (fieldName === 'url') {
                message = 'URL inválida (debe empezar con http:// o https://)';
            } else if (fieldName.includes('pagina')) {
                message = 'Solo números';
            } else if (fieldName === 'numero_referencia') {
                message = 'Solo números enteros positivos';
            } else {
                message = 'Formato inválido';
            }
        }

        // Min/Max (numbers)
        if (value && rule.min !== undefined && Number(value) < rule.min) {
            isValid = false;
            message = `Mínimo ${rule.min}`;
        }
        if (value && rule.max !== undefined && Number(value) > rule.max) {
            isValid = false;
            message = `Máximo ${rule.max}`;
        }

        this.updateFieldUI(field, isValid, message);
        return isValid;
    }

    validatePageRange(pagIni, pagFin) {
        const ini = parseInt(pagIni.value);
        const fin = parseInt(pagFin.value);

        if (ini && fin && ini > fin) {
            this.updateFieldUI(pagFin, false, 'Debe ser mayor o igual a la página inicial');
            return false;
        } else {
            this.updateFieldUI(pagIni, true, '');
            this.updateFieldUI(pagFin, true, '');
            return true;
        }
    }

    updateFieldUI(field, isValid, message) {
        // Remover clases previas
        field.classList.remove('is-valid', 'is-invalid');

        // Buscar o crear feedback element
        let feedback = field.parentElement.querySelector('.invalid-feedback, .valid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'feedback-message';
            field.parentElement.appendChild(feedback);
        }

        // Si el campo está vacío y no es required, no mostrar nada
        const rule = this.rules[field.name];
        if (!field.value.trim() && (!rule || !rule.required)) {
            feedback.textContent = '';
            feedback.className = 'feedback-message';
            return;
        }

        // Aplicar estilos
        if (isValid) {
            field.classList.add('is-valid');
            feedback.className = 'feedback-message valid-feedback';
            feedback.textContent = '';
        } else {
            field.classList.add('is-invalid');
            feedback.className = 'feedback-message invalid-feedback';
            feedback.textContent = message;
        }
    }

    validateForm() {
        let allValid = true;
        Object.keys(this.rules).forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field) {
                const isValid = this.validateField(field, fieldName);
                if (!isValid && this.rules[fieldName].required) {
                    allValid = false;
                }
            }
        });
        return allValid;
    }
}

// Inicializar validador
const formValidator = new FormValidator();
