// =========================================================
// 📊 INDICADOR DE PROGRESO DEL FORMULARIO
// =========================================================

class FormProgress {
    constructor() {
        // Detectar tipo de formulario
        const isPublicacion = window.location.pathname.includes('publicacion');

        if (isPublicacion) {
            // Campos para formularios de publicaciones
            this.requiredFields = ['nombre'];
            this.recommendedFields = ['ciudad', 'pais', 'descripcion', 'idioma'];
        } else {
            // Campos para formularios de referencias bibliográficas
            this.requiredFields = ['titulo'];
            this.recommendedFields = ['publicacion', 'fecha_original', 'anio', 'contenido', 'ciudad', 'autor'];
            this.optionalFields = ['numero_referencia', 'notas', 'temas', 'url'];
        }

        this.progressBar = null;

        this.init();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        // Verificar que estamos en una página con formulario
        const form = document.getElementById('form-ficha');
        if (!form) {
            console.log('[Form Progress] No se encontró formulario, módulo desactivado');
            return;
        }

        this.createProgressBar();
        this.attachListeners();
        this.updateProgress();
    }

    createProgressBar() {
        const bar = document.createElement('div');
        bar.className = 'form-progress-header';
        bar.innerHTML = `
            <div class="d-flex align-items-center justify-content-between mb-1">
                <span class="small text-uppercase fw-bold text-muted" style="font-size: 10px; letter-spacing: 0.5px;">✓ Progreso <span class="progress-percentage">0%</span></span>
            </div>
            <div class="progress" style="height: 4px; background: rgba(255,255,255,0.1);">
                <div class="progress-bar bg-success" role="progressbar" style="width: 0%; transition: width 0.4s ease;"></div>
            </div>
            <div class="progress-details mt-1 small"></div>
        `;

        // Intentar insertar en el slot de la cabecera (Nuevo diseño)
        const headerSlot = document.getElementById('header-progress-slot');
        if (headerSlot) {
            headerSlot.innerHTML = ''; // Limpiar
            headerSlot.appendChild(bar);
            headerSlot.classList.remove('d-none');
            this.progressBar = bar;
            return;
        }

        const materialAdjuntoCard = Array.from(document.querySelectorAll('.card-header-panel')).find(header =>
            header.textContent.includes('MATERIAL ADJUNTO')
        )?.closest('.card-panel');

        if (materialAdjuntoCard) {
            bar.className = 'form-progress-bar mt-3 mb-3 p-2 bg-dark rounded';
            materialAdjuntoCard.insertAdjacentElement('afterend', bar);
            this.progressBar = bar;
        } else {
            // Usar el formulario principal específico (ficha o nuevo) para evitar formas auxiliares en el header
            const mainForm = document.getElementById('form-ficha') || document.getElementById('form-nuevo') || document.querySelector('form');
            if (mainForm) {
                mainForm.insertBefore(bar, mainForm.firstChild);
                this.progressBar = bar;
            }
        }
    }

    attachListeners() {
        const allFields = [...this.requiredFields, ...this.recommendedFields];

        allFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.addEventListener('input', () => this.updateProgress());
                field.addEventListener('change', () => this.updateProgress());
            }
        });
    }

    updateProgress() {
        const filled = this.getFilledFields();
        const total = this.requiredFields.length + this.recommendedFields.length;
        const percentage = Math.round((filled.length / total) * 100);

        // Actualizar barra
        const progressBarEl = this.progressBar.querySelector('.progress-bar');
        progressBarEl.style.width = percentage + '%';

        // Actualizar texto
        const percentageEl = this.progressBar.querySelector('.progress-percentage');
        percentageEl.textContent = percentage + '%';

        // Detalles
        const detailsEl = this.progressBar.querySelector('.progress-details');
        if (!detailsEl) return; // Salir si no existe el elemento

        const missing = this.getMissingFields();

        if (missing.required.length > 0) {
            detailsEl.innerHTML = `
                <span class="text-danger">
                    <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
                        <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5" fill="none"/>
                        <path d="M8 4v4M8 10v.5" stroke="currentColor" stroke-width="1.5"/>
                    </svg>
                    Obligatorios faltantes: ${missing.required.join(', ')}
                </span>
            `;
        } else if (missing.recommended.length > 0) {
            detailsEl.innerHTML = `
                <span class="text-warning">Recomendados: ${missing.recommended.join(', ')}</span>
            `;
        } else {
            detailsEl.innerHTML = `
                <span class="text-success">
                    <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/>
                    </svg>
                    ¡Formulario completo!
                </span>
            `;
        }

        // Cambiar color según progreso
        progressBarEl.classList.remove('bg-danger', 'bg-warning', 'bg-success');
        if (percentage < 40) {
            progressBarEl.classList.add('bg-danger');
        } else if (percentage < 80) {
            progressBarEl.classList.add('bg-warning');
        } else {
            progressBarEl.classList.add('bg-success');
        }
    }

    getFilledFields() {
        const allFields = [...this.requiredFields, ...this.recommendedFields];
        return allFields.filter(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            return field && field.value.trim() !== '';
        });
    }

    getMissingFields() {
        const missing = {
            required: [],
            recommended: []
        };

        this.requiredFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (!field || field.value.trim() === '') {
                missing.required.push(this.getFieldLabel(fieldName));
            }
        });

        this.recommendedFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (!field || field.value.trim() === '') {
                missing.recommended.push(this.getFieldLabel(fieldName));
            }
        });

        return missing;
    }

    getFieldLabel(fieldName) {
        const labels = {
            // Referencias bibliográficas
            titulo: 'Título',
            publicacion: 'Publicación',
            fecha_original: 'Fecha',
            anio: 'Año',
            contenido: 'Contenido',
            ciudad: 'Ciudad',
            autor: 'Autor',
            numero_referencia: 'Nº Referencia',
            notas: 'Notas',
            temas: 'Temas',
            url: 'URL',

            // Publicaciones
            nombre: 'Nombre del Medio',
            pais: 'País',
            descripcion: 'Descripción',
            idioma: 'Idioma'
        };
        return labels[fieldName] || fieldName;
    }
}

// Inicializar
if (window.location.pathname.includes('/new') || window.location.pathname.includes('/editar/')) {
    const formProgress = new FormProgress();
}
