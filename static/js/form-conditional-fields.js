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
                show: ['publicacion', 'ciudad', 'pais_publicacion', 'idioma', 'fecha_original', 'numero', 'edicion', 'pagina_inicio', 'pagina_fin', 'issn', 'fuente'],
                hide: ['editorial', 'isbn', 'volumen', 'doi', 'lugar_publicacion'],
                required: ['publicacion', 'fecha_original'],
                hints: {
                    'publicacion': 'Nombre del periódico o revista',
                    'numero': 'Número de ejemplar',
                    'edicion': 'Edición (matutina, vespertina, etc.)'
                }
            },
            'libro': {
                show: ['publicacion', 'editorial', 'isbn', 'lugar_publicacion', 'anio', 'pagina_inicio', 'pagina_fin', 'idioma', 'fuente', 'ciudad', 'pais_publicacion', 'edicion', 'numero', 'volumen'],
                hide: ['issn', 'doi', 'fecha_original'],
                required: ['publicacion', 'editorial', 'anio'],
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
                show: ['publicacion', 'anio', 'fecha_original', 'lugar_publicacion', 'idioma', 'fuente', 'edicion', 'ciudad', 'pais_publicacion'],
                hide: ['editorial', 'issn', 'isbn', 'doi', 'numero', 'volumen'],
                required: ['publicacion', 'anio'],
                hints: {
                    'publicacion': 'Título o descripción de la imagen',
                    'fuente': 'Archivo / Colección'
                }
            },
            'obra_teatral': {
                show: ['publicacion', 'fecha_original', 'anio', 'ciudad', 'pais_publicacion', 'idioma', 'fuente', 'editorial', 'lugar_publicacion', 'seccion', 'volumen', 'palabras_clave', 'edicion'],
                hide: ['isbn', 'issn', 'doi', 'numero', 'pagina_inicio', 'pagina_fin'],
                required: ['publicacion', 'fecha_original'],
                hints: {
                    'publicacion': 'Título de la Obra Teatral',
                    'editorial': 'Compañía Teatral / Productora',
                    'lugar_publicacion': 'Teatro / Recinto de representación',
                    'seccion': 'Número de Actos',
                    'volumen': 'Número de escenas o cuadros',
                    'palabras_clave': 'Personajes principales y secundarios',
                    'fuente': 'Archivo / Colección / Fondo teatral'
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

        if (this.tipoRecursoSelect) {
            this.initTipoRecurso();
        }
    }

    getRecordId() {
        // Extraer ID del registro desde la URL (para edición)
        const match = window.location.pathname.match(/\/(?:edit|editar)\/(\d+)/);
        return match ? parseInt(match[1]) : null;
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
            padding: 6px 12px;
            font-size: 0.75rem;
            background: rgba(74, 222, 128, 0.15);
            border: 1px solid #4ade80;
            border-radius: 4px;
            color: #4ade80;
            white-space: nowrap;
            animation: fadeIn 0.3s ease;
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

        // Aplicar visibilidad
        allFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            const container = this.getFieldContainer(field);
            if (!container) return;

            if (config.show.includes(fieldName)) {
                // Mostrar campo
                container.style.display = '';
                field.disabled = false;
                this.addFieldAnimation(container, 'show');
            } else if (config.hide.includes(fieldName)) {
                // Ocultar campo
                container.style.display = 'none';
                field.disabled = true;
                field.value = ''; // Limpiar valor al ocultar
            }
        });

        // Actualizar campos requeridos
        this.updateRequiredFields(config.required);

        // Actualizar hints
        this.updateFieldHints(config.hints);

        // Actualizar etiquetas contextuales
        this.updateContextualLabels(tipoRecurso);

        // Actualizar opciones de edición
        this.updateEditionOptions(tipoRecurso);

        // Disparar evento personalizado
        document.dispatchEvent(new CustomEvent('tipoRecursoChanged', {
            detail: { tipo: tipoRecurso, config: config }
        }));

        console.log(`[Conditional Fields] Configuración aplicada para tipo: ${tipoRecurso}`);
    }

    getFieldContainer(field) {
        // Intentar diferentes contenedores comunes
        return field.closest('.col-6') ||
            field.closest('.col-4') ||
            field.closest('.col-3') ||
            field.closest('.col-5') ||
            field.closest('.mb-3') ||
            field.closest('div[class*="col"]') ||
            field.parentElement;
    }

    addFieldAnimation(container, type) {
        if (type === 'show') {
            container.style.animation = 'fadeIn 0.3s ease';
        }
    }

    updateRequiredFields(requiredFields) {
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
            if (field && !field.disabled) {
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
                'pagina_inicio': 'Pág. Inicial'
            },
            'libro': {
                'publicacion': 'Publicación / Fuente',
                'anio': 'Año de Publicación',
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
                'editorial': 'Compañía / Productora',
                'lugar_publicacion': 'Teatro / Recinto',
                'seccion': 'Sección / Actos',
                'volumen': 'Volumen / Tomo / Escenas',
                'palabras_clave': 'Reparto / Personajes',
                'fuente': 'Archivo / Fondo'
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
            .then(options => {
                // Si no hay opciones para este tipo, intentar con 'prensa' como fallback
                if (options.length === 0 && tipoRecurso !== 'prensa') {
                    console.warn(`[Conditional Fields] No hay ediciones para ${tipoRecurso}, usando prensa.`);
                    this.updateEditionOptions('prensa');
                    return;
                }

                this.edicionesCache[tipoRecurso] = options;
                this.renderEdiciones(edicionSelect, options, currentValue);
            })
            .catch(error => {
                console.error('[Conditional Fields] Error fetching editions:', error);
            });
    }

    renderEdiciones(select, options, currentValue) {
        // Verificar si existe una instancia de Choices.js para este select
        const choicesInstance = window.choicesInstances ? window.choicesInstances['selectEdicion'] : null;

        if (choicesInstance && typeof choicesInstance.setChoices === 'function') {
            const choices = options.map(opt => ({
                value: opt.value,
                label: opt.text,
                selected: opt.value === currentValue
            }));
            choicesInstance.clearChoices();
            choicesInstance.setChoices(choices, 'value', 'label', true);
        } else {
            select.innerHTML = '';
            options.forEach(opt => {
                const row = document.createElement('option');
                row.value = opt.value;
                row.textContent = opt.text;
                if (opt.value === currentValue) row.selected = true;
                select.appendChild(row);
            });
        }
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
