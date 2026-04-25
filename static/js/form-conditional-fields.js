/**
 * form-conditional-fields.js
 * Maneja campos condicionales en los formularios según el estado de otros campos
 * Incluye validación de números de referencia bibliográfica y auto-sugerencia
 * Sistema avanzado de campos según tipo de recurso
 */

class ConditionalFields {
    constructor() {
        this.incluidoRadios = document.getElementsByName('incluido');
        this.esReferenciaRadios = document.getElementsByName('es_referencia'); // Faltaba esta línea
        this.incluidoCheckbox = document.getElementById('checkIncluido'); // Soporte para versiones anteriores
        this.numeroReferenciaContainer = document.getElementById('numeroReferenciaContainer');
        this.numeroReferenciaInput = document.getElementById('numero_referencia') || document.getElementById('numeroReferencia');
        this.currentRecordId = this.getRecordId();
        this.tipoRecursoSelect = document.getElementById('selectRecurso') || document.querySelector('select[name="tipo_recurso"]');
        this.edicionesCache = {};

        // Mapeo de campos condicionales por tipo de recurso
        this.fieldsConfig = {
            'prensa': {
                show: ['publicacion', 'tipo_publicacion', 'periodicidad', 'edicion', 'fecha_original', 'anio', 'volumen', 'numero', 'pagina_inicio', 'pagina_fin', 'ciudad', 'pais_publicacion', 'idioma', 'issn', 'fuente'],
                hide: ['editorial', 'isbn', 'doi', 'lugar_publicacion'],
                required: ['publicacion', 'fecha_original'],
                hints: {
                    'publicacion': 'Nombre del periódico o revista',
                    'tipo_publicacion': 'Ej: Diario, Suplemento, Revista, Comic...',
                    'periodicidad': 'Ej: Diaria, Semanal, Mensual...',
                    'numero': 'Número de ejemplar',
                    'edicion': 'Edición (matutina, vespertina, etc.)'
                }
            },
            'folleto': {
                show: ['publicacion', 'tipo_publicacion', 'periodicidad', 'edicion', 'fecha_original', 'anio', 'volumen', 'numero', 'pagina_inicio', 'pagina_fin', 'ciudad', 'pais_publicacion', 'idioma', 'fuente'],
                hide: ['editorial', 'isbn', 'issn', 'doi', 'lugar_publicacion'],
                required: ['publicacion', 'fecha_original'],
                hints: {
                    'publicacion': 'Nombre del folleto o serie',
                    'tipo_publicacion': 'Tipo de folleto',
                    'periodicidad': 'Frecuencia de publicación si aplica'
                }
            },
            'libro': {
                show: ['publicacion', 'editorial', 'isbn', 'lugar_publicacion', 'fecha_original', 'pagina_inicio', 'pagina_fin', 'idioma', 'fuente', 'ciudad', 'pais_publicacion', 'edicion', 'numero', 'volumen'],
                hide: ['issn', 'doi', 'anio'],
                required: ['publicacion', 'editorial', 'fecha_original'],
                hints: {
                    'publicacion': 'Título del libro / Obra',
                    'editorial': 'Editorial que publicó el libro',
                    'isbn': 'Código ISBN (si existe)',
                    'lugar_publicacion': 'Ciudad de publicación'
                }
            },
            'articulo': {
                show: ['publicacion', 'volumen', 'numero', 'pagina_inicio', 'pagina_fin', 'doi', 'issn', 'anio', 'idioma', 'fuente', 'ciudad', 'pais_publicacion'],
                hide: ['editorial', 'isbn', 'fecha_original', 'edicion'],
                required: ['publicacion', 'volumen', 'anio'],
                hints: {
                    'publicacion': 'Nombre de la revista académica',
                    'volumen': 'Volumen de la revista',
                    'doi': 'DOI del artículo (si existe)'
                }
            },
            'tesis': {
                show: ['publicacion', 'editorial', 'lugar_publicacion', 'anio', 'idioma', 'fuente', 'edicion', 'pais_publicacion', 'ciudad'],
                hide: ['fecha_original', 'issn', 'isbn', 'doi', 'numero', 'volumen'],
                required: ['publicacion', 'editorial', 'anio'],
                hints: {
                    'publicacion': 'Título de la tesis / trabajo',
                    'editorial': 'Universidad / Institución',
                    'anio': 'Año de defensa'
                }
            },
            'fotografia': {
                show: ['publicacion', 'anio', 'lugar_publicacion', 'idioma', 'fuente', 'edicion', 'ciudad', 'pais_publicacion'],
                hide: ['editorial', 'issn', 'isbn', 'doi', 'numero', 'volumen', 'fecha_original'],
                required: ['publicacion', 'anio'],
                hints: {
                    'publicacion': 'Título / Descripción',
                    'anio': 'Año de la toma',
                    'lugar_publicacion': 'Sede Institución',
                    'fuente': 'Archivo / Colección'
                }
            },
            'obra_teatral': {
                show: ['publicacion', 'fecha_original', 'anio', 'ciudad', 'pais_publicacion', 'idioma', 'fuente', 'editorial', 'lugar_publicacion', 'seccion', 'volumen', 'palabras_clave', 'edicion', 'actos_totales', 'escenas_totales', 'reparto_total'],
                hide: ['isbn', 'issn', 'doi', 'numero', 'pagina_inicio', 'pagina_fin'],
                required: ['publicacion', 'fecha_original'],
                hints: {
                    'publicacion': 'Título de la Obra Teatral',
                    'editorial': 'Compañía Teatral / Productora',
                    'lugar_publicacion': 'Teatro / Recinto de representación',
                    'seccion': 'Acto(s) en este documento',
                    'volumen': 'Volumen o tomo',
                    'palabras_clave': 'Personajes principales y secundarios',
                    'fuente': 'Archivo / Colección / Fondo teatral',
                    'actos_totales': 'Número total de actos de la obra',
                    'escenas_totales': 'Número total de escenas de la obra',
                    'reparto_total': 'Reparto completo de la obra'
                }
            },
            'otros': {
                show: ['publicacion', 'anio', 'fecha_original', 'ciudad', 'pais_publicacion', 'idioma', 'fuente', 'edicion'],
                hide: [],
                required: ['publicacion'],
                hints: {}
            }
        };

        if ((this.esReferenciaRadios && this.esReferenciaRadios.length > 0) && this.numeroReferenciaContainer) {
            this.init();
        }
        
        this.setupInheritance();

        if (this.tipoRecursoSelect) {
            this.initTipoRecurso();
        }
    }

    getRecordId() {
        // Extraer ID del registro desde la URL (para edición)
        const match = window.location.pathname.match(/\/(?:edit|editar)\/(\d+)/);
        return match ? parseInt(match[1]) : null;
    }

    setupInheritance() {
        const inputPublicacion = document.getElementById('inputPublicacion');
        if (!inputPublicacion) return;

        inputPublicacion.addEventListener('change', async (e) => {
            const nombre = e.target.value.trim();
            if (!nombre) return;

            console.log(`[Inheritance] Fetching details for: ${nombre}`);
            try {
                const response = await fetch(`/api/publicacion/details/${encodeURIComponent(nombre)}`);
                if (!response.ok) return;

                const data = await response.json();
                if (data.error) return;

                console.log('[Inheritance] Data received:', data);

                // Solo autocompletar si el tipo de recurso es obra_teatral o si la publicación es obra_teatral
                const tipoActual = this.tipoRecursoSelect ? this.tipoRecursoSelect.value : '';
                
                if (data.tipo_recurso === 'obra_teatral') {
                    // Si la publicación es una obra teatral, forzamos el tipo de recurso a obra_teatral
                    if (this.tipoRecursoSelect && tipoActual !== 'obra_teatral') {
                        this.tipoRecursoSelect.value = 'obra_teatral';
                        this.applyFieldsConfig('obra_teatral');
                    }

                    // Rellenar campos globales si están vacíos
                    const campos = {
                        'actos_totales': data.actos_totales,
                        'escenas_totales': data.escenas_totales,
                        'reparto_total': data.reparto_total,
                        'tipo_publicacion': data.tipo_publicacion,
                        'periodicidad': data.periodicidad,
                        'lugar_publicacion': data.lugar_publicacion
                    };

                    Object.keys(campos).forEach(id => {
                        const field = document.querySelector(`[name="${id}"]`);
                        if (field && (!field.value || field.value.trim() === "")) {
                            field.value = campos[id];
                            field.style.backgroundColor = '#294a6022'; // Efecto sutil de autocompletado
                            setTimeout(() => field.style.backgroundColor = '', 2000);
                        }
                    });
                } else if (data.tipo_publicacion || data.periodicidad) {
                    // Si no es teatro pero tiene datos hemerográficos, rellenarlos también
                    const campos = {
                        'tipo_publicacion': data.tipo_publicacion,
                        'periodicidad': data.periodicidad,
                        'lugar_publicacion': data.lugar_publicacion
                    };
                    Object.keys(campos).forEach(id => {
                        const field = document.querySelector(`[name="${id}"]`);
                        if (field && (!field.value || field.value.trim() === "")) {
                            field.value = campos[id];
                            field.style.backgroundColor = '#294a6011';
                            setTimeout(() => field.style.backgroundColor = '', 2000);
                        }
                    });
                }
            } catch (err) {
                console.error('[Inheritance] Error:', err);
            }
        });
    }

    init() {
        // Listener para el cambio del checkbox de "Incluir en estudio" (Legacy)
        // Ya NO afecta al número de referencia directamente en la nueva lógica,
        // pero lo mantenemos por si acaso hay dependencias externas ocultas.
        if (this.incluidoCheckbox) {
            this.incluidoCheckbox.addEventListener('change', async () => {
                // await this.toggleNumeroReferencia(this.incluidoCheckbox.checked); // Deshabilitado para la nueva lógica
            });
        }

        // Listener para los radios "Incluir en estudio" (Actual)
        if (this.incluidoRadios && this.incluidoRadios.length > 0) {
            this.incluidoRadios.forEach(radio => {
                radio.addEventListener('change', async () => {
                    // if (radio.checked) {
                    //     await this.toggleNumeroReferencia(radio.value === 'si'); // Deshabilitado para la nueva lógica
                    // }
                });
            });
        }

        // Listener para los radios "Incluir Ref. Bibliográfica" (Actual)
        if (this.esReferenciaRadios && this.esReferenciaRadios.length > 0) {
            this.esReferenciaRadios.forEach(radio => {
                radio.addEventListener('change', async () => {
                    // Solo ejecutar si este radio específico está marcado tras el cambio
                    if (radio.checked) {
                        console.log('[Conditional Fields] Radio cambiado:', radio.name, radio.value);
                        await this.toggleNumeroReferencia(radio.value === 'si');
                    }
                });
            });
        }

        // Listener para validación en tiempo real
        if (this.numeroReferenciaInput) {
            this.numeroReferenciaInput.addEventListener('blur', () => {
                this.validateNumeroReferencia();
            });

            this.numeroReferenciaInput.addEventListener('input', () => {
                this.clearValidationMessage();
            });
        }

        // Ejecución inicial según estado
        const currentIsRef = this.isReference();
        if (currentIsRef) {
            this.toggleNumeroReferencia(true, false); // true=show, false=noAnimation
        }

        console.log('[Conditional Fields] Inicializado con separación de Referencia/Estudio');
    }

    isIncluded() {
        if (this.incluidoCheckbox) return this.incluidoCheckbox.checked;
        if (this.incluidoRadios && this.incluidoRadios.length > 0) {
            const siRadio = Array.from(this.incluidoRadios).find(r => r.value === 'si');
            return siRadio ? siRadio.checked : false;
        }
        return false;
    }

    isReference() {
        if (this.esReferenciaRadios && this.esReferenciaRadios.length > 0) {
            const siRadio = Array.from(this.esReferenciaRadios).find(r => r.value === 'si');
            return siRadio ? siRadio.checked : false;
        }
        // Fallback: si no existe el radio (versiones antiguas), usamos incluido
        return this.isIncluded();
    }

    async toggleNumeroReferencia(show, animate = true) {
        if (show) {
            // Mostrar el campo
            this.numeroReferenciaContainer.style.display = 'block';
            this.numeroReferenciaContainer.classList.remove('d-none');

            if (animate) {
                this.numeroReferenciaContainer.style.opacity = '0';
                this.numeroReferenciaContainer.style.transform = 'translateY(-10px)';
                this.numeroReferenciaContainer.offsetHeight; // Reflow
                this.numeroReferenciaContainer.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                this.numeroReferenciaContainer.style.opacity = '1';
                this.numeroReferenciaContainer.style.transform = 'translateY(0)';
            } else {
                this.numeroReferenciaContainer.style.opacity = '1';
                this.numeroReferenciaContainer.style.transform = 'translateY(0)';
            }

            // Auto-sugerir número si el campo está vacío
            if (this.numeroReferenciaInput && !this.numeroReferenciaInput.value) {
                await this.suggestNextNumber();
            }
        } else {
            // Ocultar
            if (animate) {
                this.numeroReferenciaContainer.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
                this.numeroReferenciaContainer.style.opacity = '0';
                this.numeroReferenciaContainer.style.transform = 'translateY(-10px)';
                setTimeout(() => {
                    this.numeroReferenciaContainer.style.display = 'none';
                    this.numeroReferenciaContainer.classList.add('d-none');
                }, 200);
            } else {
                this.numeroReferenciaContainer.style.display = 'none';
                this.numeroReferenciaContainer.classList.add('d-none');
            }
        }

        console.log(`[Conditional Fields] Número de referencia ${show ? 'visible' : 'oculto'}`);
    }

    async suggestNextNumber() {
        if (!this.numeroReferenciaInput) return;

        console.log('[Conditional Fields] Solicitando sugerencia de número. RecordID:', this.currentRecordId);

        // Mostrar estado de carga en el input
        const originalBg = this.numeroReferenciaInput.style.backgroundColor;
        this.numeroReferenciaInput.style.backgroundColor = 'rgba(255, 193, 7, 0.1)';
        this.numeroReferenciaInput.placeholder = '...';

        try {
            const response = await fetch('/api/siguiente_numero_referencia');

            if (!response.ok) {
                console.error('[Conditional Fields] Error en respuesta de API:', response.status, response.statusText);
                this.showValidationError('Error al conectar con el servidor para sugerir número.');
                return;
            }

            const data = await response.json();
            console.log('[Conditional Fields] Datos recibidos:', data);

            if (data.siguiente_numero !== undefined) {
                this.numeroReferenciaInput.value = data.siguiente_numero;
                this.numeroReferenciaInput.style.backgroundColor = 'rgba(74, 222, 128, 0.15)';
                this.numeroReferenciaInput.style.borderColor = '#4ade80';

                // Mostrar tooltip con sugerencia
                this.showSuggestionTooltip(data.siguiente_numero, data.total_referencias);

                setTimeout(() => {
                    this.numeroReferenciaInput.style.backgroundColor = '';
                    this.numeroReferenciaInput.style.borderColor = '';
                }, 1500);
            } else if (data.error) {
                console.warn('[Conditional Fields] API devolvió un error:', data.error);
                this.showValidationError('No se pudo sugerir número: ' + data.error);
            }
        } catch (error) {
            console.error('[Conditional Fields] Error crítico al obtener siguiente número:', error);
            this.showValidationError('Error de red al intentar sugerir número.');
        } finally {
            this.numeroReferenciaInput.placeholder = '';
        }
    }

    showSuggestionTooltip(numero, total) {
        const existing = document.getElementById('numero-ref-tooltip');
        if (existing) existing.remove();

        const tooltip = document.createElement('div');
        tooltip.id = 'numero-ref-tooltip';
        tooltip.className = 'alert alert-success';
        tooltip.style.cssText = `
            position: absolute;
            top: -45px;
            left: 0;
            z-index: 1000;
            padding: 5px 10px;
            font-size: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            width: auto !important;
            border-radius: 4px;
            white-space: nowrap;
        `;
        tooltip.innerHTML = `
            <svg width="12" height="12" fill="currentColor" style="vertical-align: text-bottom; margin-right: 4px;">
                <path d="M10 3l-6 6-2-2"/>
            </svg>
            Número sugerido: <strong>${numero}</strong> (${total} referencias existentes)
        `;

        this.numeroReferenciaContainer.style.position = 'relative';
        this.numeroReferenciaContainer.appendChild(tooltip);

        setTimeout(() => {
            tooltip.style.opacity = '0';
            tooltip.style.transition = 'opacity 0.3s ease';
            setTimeout(() => tooltip.remove(), 300);
        }, 3000);
    }

    async validateNumeroReferencia() {
        const numero = parseInt(this.numeroReferenciaInput.value);

        if (!numero || numero < 1) {
            return;
        }

        try {
            const params = new URLSearchParams({ numero: numero });
            if (this.currentRecordId) {
                params.append('exclude_id', this.currentRecordId);
            }

            const response = await fetch(`/api/validar_numero_referencia?${params}`);
            const data = await response.json();

            if (data.en_uso) {
                this.showValidationError(
                    `El número ${numero} ya está asignado a: "${data.titulo}" (ID: ${data.id})`
                );
                this.numeroReferenciaInput.style.borderColor = '#ef4444';
                this.numeroReferenciaInput.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
            } else {
                this.clearValidationMessage();
                this.numeroReferenciaInput.style.borderColor = '#4ade80';
                this.numeroReferenciaInput.style.backgroundColor = 'rgba(74, 222, 128, 0.1)';

                setTimeout(() => {
                    this.numeroReferenciaInput.style.borderColor = '';
                    this.numeroReferenciaInput.style.backgroundColor = '';
                }, 1500);
            }
        } catch (error) {
            console.error('[Conditional Fields] Error al validar número:', error);
        }
    }

    showValidationError(message) {
        this.clearValidationMessage();

        const errorDiv = document.createElement('div');
        errorDiv.id = 'numero-ref-error';
        errorDiv.className = 'alert alert-danger';
        errorDiv.style.cssText = `
            margin-top: 8px;
            padding: 8px 12px;
            font-size: 0.75rem;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid #ef4444;
            border-radius: 4px;
            color: #ef4444;
        `;
        errorDiv.innerHTML = `
            <svg width="14" height="14" fill="currentColor" style="vertical-align: text-bottom; margin-right: 4px;">
                <circle cx="7" cy="7" r="6" stroke="currentColor" fill="none"/>
                <text x="7" y="11" text-anchor="middle" font-size="12" font-weight="bold">!</text>
            </svg>
            ${message}
            <br>
            <small style="opacity: 0.8; margin-left: 18px;">Usa otro número o mantén este si quieres reutilizar la misma referencia</small>
        `;

        this.numeroReferenciaContainer.appendChild(errorDiv);
    }

    clearValidationMessage() {
        const error = document.getElementById('numero-ref-error');
        if (error) error.remove();
    }

    // ===== SISTEMA DE CAMPOS CONDICIONALES POR TIPO DE RECURSO =====

    initTipoRecurso() {
        // Aplicar configuración inicial con un pequeño delay para asegurar que Choices.js (en base_desktop.html) esté listo
        setTimeout(() => {
            const tipoInicial = this.tipoRecursoSelect.value;
            if (tipoInicial) {
                console.log('[Conditional Fields] Aplicando configuración inicial para:', tipoInicial);
                this.applyFieldsConfig(tipoInicial);
            }
        }, 200);

        // Escuchar cambios
        this.tipoRecursoSelect.addEventListener('change', (e) => {
            this.applyFieldsConfig(e.target.value);
        });

        console.log('[Conditional Fields] Sistema de tipo recurso inicializado');
    }

    applyFieldsConfig(tipoRecurso) {
        const config = this.fieldsConfig[tipoRecurso] || this.fieldsConfig['otros'];

        // Obtener todos los nombres de campo únicos
        const allFields = new Set();
        Object.values(this.fieldsConfig).forEach(c => {
            c.show.forEach(f => allFields.add(f));
            c.hide.forEach(f => allFields.add(f));
        });

        // Campos que siempre deben estar visibles (Datos Hemerográficos / Publicación)
        const HEMERO_FIELDS = [
            'publicacion', 'tipo_publicacion', 'periodicidad', 'edicion', 'fecha_original', 'anio', 
            'volumen', 'numero', 'pagina_inicio', 'pagina_fin', 'ciudad', 'pais_publicacion', 
            'idioma', 'issn', 'isbn', 'doi', 'fuente', 'lugar_publicacion', 'editorial'
        ];

        // Aplicar visibilidad
        allFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            const container = this.getFieldContainer(field);
            if (!container) return;

            // Prioridad 1: Si está en la lista de HIDE, lo ocultamos sí o sí
            if (config.hide.includes(fieldName)) {
                container.style.display = 'none';
                return;
            }

            // Prioridad 2: Si está en la lista de SHOW, lo mostramos
            if (config.show.includes(fieldName)) {
                container.style.display = '';
                this.addFieldAnimation(container, 'show');
                return;
            }

            // Prioridad 3: Si es un campo hemerográfico base, lo mostramos (si no se ocultó antes)
            if (HEMERO_FIELDS.includes(fieldName)) {
                container.style.display = '';
                return;
            }
        });

        // Actualizar campos requeridos
        this.updateRequiredFields(config);

        // Actualizar hints
        this.updateFieldHints(config.hints);

        // Actualizar etiquetas contextuales
        this.updateContextualLabels(tipoRecurso);

        // Actualizar opciones de edición
        this.updateEditionOptions(tipoRecurso);

        // Actualizar opciones de tipo de publicación
        this.updateTipoPublicacionOptions(tipoRecurso);

        // Ajustar anchos de columnas dinámicamente según visibilidad
        this.finalizeLayout(tipoRecurso);

        // Disparar evento personalizado
        document.dispatchEvent(new CustomEvent('tipoRecursoChanged', {
            detail: { tipo: tipoRecurso, config: config }
        }));

        console.log(`[Conditional Fields] Configuración aplicada para tipo: ${tipoRecurso}`);
    }

    finalizeLayout(tipoRecurso) {
        // Ajustes específicos para que los campos "encajen bien" cuando hay ocultos
        const row1 = document.querySelector('input[name="fecha_original"]')?.closest('.row');
        if (row1) {
            const fechaCol = document.querySelector('input[name="fecha_original"]')?.closest('[class*="col-"]');
            const anioCol = document.querySelector('input[name="anio"]')?.closest('[class*="col-"]');
            const lugarCol = document.querySelector('input[name="lugar_publicacion"]')?.closest('[class*="col-"]');

            if (tipoRecurso === 'libro') {
                // En Libro ocultamos Año (col-3), repartimos el espacio
                if (fechaCol) { fechaCol.className = 'col-md-4'; }
                if (lugarCol) { lugarCol.className = 'col-md-8'; }
            } else if (tipoRecurso === 'articulo') {
                // En Artículo ocultamos Fecha (col-4), repartimos el espacio
                if (anioCol) { anioCol.className = 'col-md-4'; }
                if (lugarCol) { lugarCol.className = 'col-md-8'; }
            } else if (tipoRecurso === 'obra_teatral') {
                // En Obra Teatral, ajustar los 3 para que llenen bien (4, 3, 5 base está ok, pero 4, 2, 6 mejor?)
                if (fechaCol) { fechaCol.className = 'col-md-4'; }
                if (anioCol) { anioCol.className = 'col-md-3'; }
                if (lugarCol) { lugarCol.className = 'col-md-5'; }
            } else if (tipoRecurso === 'tesis' || tipoRecurso === 'fotografia') {
                // En Tesis y Foto ocultamos Fecha (col-4), repartimos el espacio
                if (anioCol) { anioCol.className = 'col-md-4'; }
                if (lugarCol) { lugarCol.className = 'col-md-8'; }
            } else if (tipoRecurso === 'prensa') {
                // En Prensa, Fecha y Año (4 y 3 base), hacemos Fecha más ancha (6 y 6)
                if (fechaCol) { fechaCol.className = 'col-md-6'; }
                if (anioCol) { anioCol.className = 'col-md-6'; }
            } else {
                // Reset a base
                if (fechaCol) { fechaCol.className = 'col-md-4'; }
                if (anioCol) { anioCol.className = 'col-md-3'; }
                if (lugarCol) { lugarCol.className = 'col-md-5'; }
            }
        }

        const row2 = document.querySelector('select[name="edicion"]')?.closest('.row');
        if (row2) {
            const edicionCol = document.querySelector('select[name="edicion"]')?.closest('[class*="col-"]');
            const volumenCol = document.querySelector('input[name="volumen"]')?.closest('[class*="col-"]');
            const numeroCol = document.querySelector('input[name="numero"]')?.closest('[class*="col-"]');

            if (tipoRecurso === 'articulo') {
                // En Artículo ocultamos Edición, repartimos Volumen y Número
                if (volumenCol) { volumenCol.className = 'col-md-6'; }
                if (numeroCol) { numeroCol.className = 'col-md-6'; }
            } else if (tipoRecurso === 'tesis' || tipoRecurso === 'obra_teatral') {
                // Ocultamos Volumen y Número (en tesis), Edición al 100% o repartir? 
                // En Tesis solo queda Edición en esta fila
                if (edicionCol) { edicionCol.className = 'col-md-12'; }
            } else {
                if (edicionCol) { edicionCol.className = 'col-md-4'; }
                if (volumenCol) { volumenCol.className = 'col-md-4'; }
                if (numeroCol) { numeroCol.className = 'col-md-4'; }
            }
        }

        const row3 = document.querySelector('input[name="editorial"]')?.closest('.row');
        if (row3) {
            const editorialCol = document.querySelector('input[name="editorial"]')?.closest('[class*="col-"]');
            const paginasCol = document.querySelector('input[name="pagina_inicio"]')?.closest('[class*="col-"]');

            if (tipoRecurso === 'articulo') {
                // En Artículo ocultamos Editorial, Páginas al 100% (o 6 y dejar hueco si se prefiere, pero 12 es más cuadrado)
                if (paginasCol) { paginasCol.className = 'col-md-12'; }
            } else {
                if (editorialCol) { editorialCol.className = 'col-md-6'; }
                if (paginasCol) { paginasCol.className = 'col-md-6'; }
            }
        }
    }

    getFieldContainer(field) {
        // 1. Priorizar el contenedor de columna (col-X) si existe
        // Esto evita que campos que comparten fila (.row.mb-3) se pisen entre sí
        const col = field.closest('[class*="col-"]:not(.row)');
        if (col) return col;

        // 2. Si no hay columna, buscar el envoltorio específico de campo
        const specificWrapper = field.closest('.mb-3, .mb-2, .form-group, .field-wrapper');
        if (specificWrapper) return specificWrapper;

        return field.parentElement;
    }

    addFieldAnimation(container, type) {
        if (type === 'show') {
            container.style.animation = 'fadeIn 0.3s ease';
        }
    }

    updateRequiredFields(config) {
        const requiredFields = config.required || [];
        // Quitar asteriscos de todos los labels
        document.querySelectorAll('label').forEach(label => {
            if (label.innerHTML.includes('*')) {
                label.innerHTML = label.innerHTML.replace(/ <span class="text-danger">\*<\/span>/g, '').replace(/\*/g, '');
            }
        });

        // Quitar atributo required de todos los campos
        document.querySelectorAll('input, select, textarea').forEach(field => {
            if (field.name !== 'titulo' && field.name !== 'csrf_token') {
                field.removeAttribute('required');
            }
        });

        // Añadir required a campos específicos
        requiredFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            // Solo añadir si el campo está en la lista de 'show' para este tipo
            if (field && config.show && config.show.includes(fieldName)) {
                field.setAttribute('required', 'required');

                // Añadir asterisco al label
                const container = this.getFieldContainer(field);
                const label = container?.querySelector('label');
                if (label && !label.textContent.includes('*')) {
                    label.innerHTML = label.innerHTML + ' <span class="text-danger">*</span>';
                }
            }
        });
    }

    updateFieldHints(hints) {
        Object.keys(hints).forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.placeholder = hints[fieldName];
                field.title = hints[fieldName];
            }
        });
    }

    updateContextualLabels(tipoRecurso) {
        const labelMap = {
            'prensa': {
                'fecha_original': 'Fecha de Publicación',
                'publicacion': 'Publicación / Medio',
                'pagina_inicio': 'PÁGINA/AS'
            },
            'libro': {
                'publicacion': 'Publicación / Fuente',
                'fecha_original': 'MES/AÑO',
                'pagina_inicio': 'Páginas'
            },
            'articulo': {
                'publicacion': 'Revista Académica',
                'anio': 'Año de Publicación'
            },
            'tesis': {
                'publicacion': 'Título de Tesis',
                'editorial': 'Universidad',
                'anio': 'Año de Defensa',
                'lugar_publicacion': 'Sede Institución'
            },
            'fotografia': {
                'publicacion': 'Título / Descripción',
                'fuente': 'Archivo / Colección',
                'anio': 'Año de la Toma'
            },
            'obra_teatral': {
                'publicacion': 'Título de la Obra',
                'fecha_original': 'Fecha de Estreno',
                'anio': 'Año',
                'lugar_publicacion': 'Teatro / Recinto'
            },
            'otros': {
                'publicacion': 'Título / Referencia'
            }
        };

        const labels = labelMap[tipoRecurso];
        if (!labels) return;

        Object.keys(labels).forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field) {
                const container = this.getFieldContainer(field);
                const label = container?.querySelector('label');
                if (label) {
                    const hasAsterisk = label.innerHTML.includes('*');
                    const asterisk = hasAsterisk ? ' <span class="text-danger">*</span>' : '';
                    label.innerHTML = labels[fieldName] + asterisk;
                }
            }
        });
    }

    updateEditionOptions(tipoRecurso) {
        const edicionSelect = document.getElementById('selectEdicion') || document.querySelector('select[name="edicion"]');
        if (!edicionSelect) return;

        // Guardar valor actual para intentar restaurarlo
        const currentValue = edicionSelect.getAttribute('data-value') || edicionSelect.value;

        // Limpiar el tipo de recurso por si viene con ID (ej: libro:1)
        const cleanTipo = tipoRecurso.split(':')[0];
        console.log(`[Conditional Fields] Solicitando ediciones para: ${cleanTipo} (original: ${tipoRecurso})`);

        // Fetch desde la API del blueprint noticias
        fetch(`/api/ediciones/${cleanTipo}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const contentType = response.headers.get("content-type");
                if (!contentType || !contentType.includes("application/json")) {
                    throw new TypeError("Oops, we haven't got JSON!");
                }
                return response.json();
            })
            .then(data => {
                // Si no hay opciones para este tipo, intentar con 'prensa' como fallback
                if (data.length === 0 && tipoRecurso !== 'prensa') {
                    console.warn(`[Conditional Fields] No hay ediciones para ${tipoRecurso}, usando prensa.`);
                    this.updateEditionOptions('prensa');
                    return;
                }

                // Filtrar duplicados por valor (insensible a mayúsculas)
                const seen = new Set();
                const options = data.filter(ed => {
                    // El API retorna {value, text} según EdicionTipoRecurso.to_dict()
                    const val = ed.value || ed.valor;
                    if (val === undefined || val === null) return false;
                    const key = String(val).toLowerCase();
                    if (seen.has(key)) return false;
                    seen.add(key);
                    return true;
                }).map(ed => ({ 
                    value: ed.value || ed.valor, 
                    text: ed.text || ed.etiqueta || ed.value || ed.valor 
                }));

                this.edicionesCache[tipoRecurso] = options;
                this.renderSelectOptions(edicionSelect, options, currentValue);
            })
            .catch(error => {
                console.error('[Conditional Fields] Error fetching editions:', error);
            });
    }

    renderSelectOptions(select, options, currentValue) {
        if (!select) return;

        // Detectar instancia de Choices.js de forma robusta
        let choicesInstance = null;
        if (window.choicesInstances && select.id && window.choicesInstances[select.id]) {
            choicesInstance = window.choicesInstances[select.id];
        } else if (select._choices) {
            choicesInstance = select._choices;
        }

        // Si tenemos Choices.js, usamos su API para evitar mutaciones que disparen otros scripts
        if (choicesInstance && typeof choicesInstance.setChoices === 'function') {
            try {
                const choices = options.map(opt => ({
                    value: opt.value || '',
                    label: opt.text || opt.value || '',
                    selected: String(opt.value) === String(currentValue),
                    disabled: false
                }));

                // Siempre incluimos la opción por defecto si no está en los datos
                if (!choices.some(c => c.value === '')) {
                    choices.unshift({ value: '', label: '(Seleccionar)', selected: !currentValue });
                }

                choicesInstance.clearChoices();
                choicesInstance.setChoices(choices, 'value', 'label', true);
                
                // Refuerzo: Asegurar que el select original permanezca oculto y no interactuable
                select.style.display = 'none';
                select.style.visibility = 'hidden';
                select.style.height = '0';
                select.setAttribute('aria-hidden', 'true');
                select.tabIndex = -1;
                
                // Si el contenedor de Choices existe pero no se ve, forzar display
                const container = select.closest('.choices');
                if (container) {
                    container.style.display = 'block';
                }

                return;
            } catch (err) {
                console.warn('[Conditional Fields] Error en Choices.js, reintentando modo estándar:', err);
            }
        }

        // Modo estándar: Solo si NO hay Choices.js activo
        if (select.closest('.choices')) {
            console.warn('[Conditional Fields] Select bajo Choices.js pero sin instancia detectada.');
            return;
        }

        select.innerHTML = '';
        const defaultOpt = document.createElement('option');
        defaultOpt.value = "";
        defaultOpt.textContent = "(Seleccionar)";
        if (!currentValue) defaultOpt.selected = true;
        select.appendChild(defaultOpt);

        options.forEach(opt => {
            const row = document.createElement('option');
            row.value = opt.value || '';
            row.textContent = opt.text || opt.value || '';
            if (String(opt.value) === String(currentValue)) row.selected = true;
            select.appendChild(row);
        });
    }

    updateTipoPublicacionOptions(tipoRecurso) {
        const tipoSelect = document.getElementById('selectTipoPublicacion') || document.querySelector('select[name="tipo_publicacion"]');
        if (!tipoSelect) return;

        // Guardar valor actual para intentar restaurarlo
        const currentValue = tipoSelect.getAttribute('data-value') || tipoSelect.value;
        const cleanTipo = tipoRecurso.split(':')[0];

        // Mapeo de tipos de publicación según el recurso principal
        const config = {
            'prensa': [
                { value: 'Periódico', text: 'Periódico' },
                { value: 'Diario', text: 'Diario' },
                { value: 'Semanario', text: 'Semanario' },
                { value: 'Revista', text: 'Revista' },
                { value: 'Magazine', text: 'Magazine' },
                { value: 'Suplemento', text: 'Suplemento' },
                { value: 'Cómic', text: 'Cómic / Tebeo' },
                { value: 'Hoja suelta', text: 'Hoja suelta' },
                { value: 'Boletín', text: 'Boletín' },
                { value: 'Gaceta', text: 'Gaceta' },
                { value: 'Anuario', text: 'Anuario' },
                { value: 'Otros', text: 'Otros' }
            ],
            'folleto': [
                { value: 'Panfleto', text: 'Panfleto' },
                { value: 'Programa', text: 'Programa (Teatro/Evento)' },
                { value: 'Libelo', text: 'Libelo' },
                { value: 'Manifiesto', text: 'Manifiesto' },
                { value: 'Catálogo', text: 'Catálogo' },
                { value: 'Circular', text: 'Circular' }
            ],
            'libro': [
                { value: 'Monografía', text: 'Monografía' },
                { value: 'Ensayo', text: 'Ensayo' },
                { value: 'Antología', text: 'Antología' },
                { value: 'Manual', text: 'Manual' },
                { value: 'Tratado', text: 'Tratado' }
            ],
            'obra_teatral': [
                { value: 'Drama', text: 'Drama' },
                { value: 'Comedia', text: 'Comedia' },
                { value: 'Tragedia', text: 'Tragedia' },
                { value: 'Sainete', text: 'Sainete' },
                { value: 'Auto sacramental', text: 'Auto sacramental' },
                { value: 'Libreto', text: 'Libreto' },
                { value: 'Zarzuela', text: 'Zarzuela' },
                { value: 'Entremés', text: 'Entremés' }
            ],
            'articulo': [
                { value: 'Artículo original', text: 'Artículo original' },
                { value: 'Revisión', text: 'Revisión' },
                { value: 'Nota técnica', text: 'Nota técnica' },
                { value: 'Reseña', text: 'Reseña' }
            ],
            'tesis': [
                { value: 'Doctoral', text: 'Tesis Doctoral' },
                { value: 'Maestría', text: 'Tesis de Maestría' },
                { value: 'Licenciatura', text: 'Tesis de Licenciatura' }
            ]
        };

        const options = config[cleanTipo] || [{ value: 'Otro', text: 'Otro' }];
        
        // Reutilizamos el renderizador de opciones
        this.renderSelectOptions(tipoSelect, options, currentValue);
    }
}

// Integración con otros módulos
document.addEventListener('tipoRecursoChanged', (e) => {
    if (window.formProgress) window.formProgress.updateProgress();
    if (window.formValidator) window.formValidator.validateAll();
});

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.conditionalFields = new ConditionalFields();
    });
} else {
    window.conditionalFields = new ConditionalFields();
}
