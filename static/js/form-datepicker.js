// =========================================================
// 📅 CALENDARIO DESPLEGABLE PARA FECHAS (FLATPICKR)
// =========================================================

class DatePicker {
    constructor() {
        this.init();
    }

    init() {
        // Cargar Flatpickr desde CDN
        this.loadFlatpickr().then(() => {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.setup());
            } else {
                this.setup();
            }
        });
    }

    loadFlatpickr() {
        return new Promise((resolve, reject) => {
            // Verificar si ya está cargado
            if (window.flatpickr) {
                resolve();
                return;
            }

            // Cargar CSS
            const css = document.createElement('link');
            css.rel = 'stylesheet';
            css.href = 'https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css';
            document.head.appendChild(css);

            // Cargar tema dark
            const cssDark = document.createElement('link');
            cssDark.rel = 'stylesheet';
            cssDark.href = 'https://cdn.jsdelivr.net/npm/flatpickr/dist/themes/dark.css';
            document.head.appendChild(cssDark);

            // Cargar JS principal
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/flatpickr';
            script.onload = () => {
                // DESPUÉS cargar idioma español
                const scriptEs = document.createElement('script');
                scriptEs.src = 'https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/es.js';
                scriptEs.onload = resolve; // Resolver cuando el idioma esté listo
                scriptEs.onerror = resolve; // Si falla, continuar sin idioma
                document.head.appendChild(scriptEs);
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    setup() {
        if (!window.flatpickr) {
            console.warn('Flatpickr no se cargó correctamente');
            return;
        }

        // Configurar locale español
        if (window.flatpickr.l10ns && window.flatpickr.l10ns.es) {
            window.flatpickr.localize(window.flatpickr.l10ns.es);
        }

        // Campos de fecha
        const dateFields = [
            { selector: '[name="fecha_original"]', allowInput: true },
            { selector: '[name="fecha_consulta"]', allowInput: true },
            { selector: '[name="fecha_nacimiento"]', allowInput: true },
            { selector: '[name="fecha_defuncion"]', allowInput: true }
        ];

        dateFields.forEach(field => {
            const inputs = document.querySelectorAll(field.selector);
            
            inputs.forEach(input => {
                // Evitar doble inicialización
                if (input.classList.contains('flatpickr-input') || input._flatpickr) return;

                // Configurar Flatpickr
                flatpickr(input, {
                    dateFormat: 'd/m/Y',
                    allowInput: field.allowInput,
                    locale: 'es',
                    theme: 'dark',
                    // Permitir fechas históricas
                    minDate: '01/01/1000',
                    maxDate: new Date(),
                    // Iconos personalizados
                    prevArrow: '<svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M11.354 1.646a.5.5 0 0 1 0 .708L5.707 8l5.647 5.646a.5.5 0 0 1-.708.708l-6-6a.5.5 0 0 1 0-.708l6-6a.5.5 0 0 1 .708 0z"/></svg>',
                    nextArrow: '<svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M4.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708L10.293 8 4.646 2.354a.5.5 0 0 1 0-.708z"/></svg>',
                    // Actualizar año automáticamente
                    onChange: (selectedDates, dateStr, instance) => {
                        if (selectedDates.length > 0 && field.selector === '[name="fecha_original"]') {
                            const year = selectedDates[0].getFullYear();
                            const yearInput = document.querySelector('[name="anio"]');
                            if (yearInput && !yearInput.value) {
                                yearInput.value = year;
                            }
                        }
                    },
                    // Agregar botón "hoy"
                    onReady: (selectedDates, dateStr, instance) => {
                        const todayBtn = document.createElement('button');
                        todayBtn.type = 'button';
                        todayBtn.className = 'flatpickr-today-btn';
                        todayBtn.textContent = 'Hoy';
                        todayBtn.onclick = () => {
                            instance.setDate(new Date(), true);
                        };

                        const calendar = instance.calendarContainer;
                        if (calendar) {
                            calendar.appendChild(todayBtn);
                        }
                    }
                });

                // Agregar icono de calendario al input
                this.addCalendarIcon(input);
            });
        });
        
        // Exponer globalmente para re-inicialización manual si es necesario
        window.reinitDatePickers = () => this.setup();
    }

    addCalendarIcon(input) {
        // Buscar el label asociado
        let label = input.parentElement.querySelector('label');
        
        if (!label) {
            // Buscar en el contenedor de nivel superior (para campos agrupados como en la biografía)
            const container = input.closest('.col-md-6, .col-md-9, .mb-3, .form-group');
            if (container) label = container.querySelector('label');
        }

        // Si no hay label o ya tiene icono, salir
        if (!label || label.querySelector('.calendar-icon')) return;

        const icon = document.createElement('span');
        icon.className = 'calendar-icon me-2 text-warning'; // Agregamos color y margen
        icon.innerHTML = `
            <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5zM1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4H1z"/>
            </svg>
        `;

        // Insertar el icono al principio del label
        label.prepend(icon);
    }
}

// Inicializar
const datePicker = new DatePicker();
