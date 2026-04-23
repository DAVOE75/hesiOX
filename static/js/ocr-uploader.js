/**
 * ========================================
 * OCR UPLOADER UI HANDLER
 * ========================================
 * Interfaz de usuario para carga de documentos
 * y auto-relleno de formulario con metadatos
 */

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[OCR Uploader] Inicializando...');

    // Elementos del DOM
    const dropZoneOCR = document.getElementById('dropZoneOCR');
    const fileInputOCR = document.getElementById('fileInputOCR');
    const btnProcessOCR = document.getElementById('btn-process-ocr');
    const btnCancelOCR = document.getElementById('btn-cancel-ocr');

    // Validar elementos críticos
    if (!dropZoneOCR || !fileInputOCR) {
        console.log('[OCR Uploader] Elementos OCR no encontrados, módulo desactivado');
        return;
    }
    const ocrProgressContainer = document.getElementById('ocr-progress-container');
    const ocrProgressText = document.getElementById('ocr-progress-text');
    const ocrProgressBar = document.getElementById('ocr-progress-bar');
    const ocrResultContainer = document.getElementById('ocr-result-container');
    const ocrTextPreview = document.getElementById('ocr-text-preview');
    const btnApplyMetadata = document.getElementById('btn-apply-ocr-text');

    // Si no hay botón de procesar, estamos en modo simplificado (solo uploader)
    const simplifiedMode = !btnProcessOCR;
    const btnDiscardOCR = document.getElementById('btn-discard-ocr');
    const btnMejorarIA = document.getElementById('btn-correct-gemini');

    // Verificar que existen los elementos (solo en formulario nuevo)
    if (!dropZoneOCR) {
        console.log('[OCR Uploader] No se encontró zona de OCR (no es formulario nuevo)');
        return;
    }

    let currentFile = null;
    let extractedData = null;
    let ocrProcessor = null;

    // Inicializar procesador
    ocrProcessor = new window.OCRProcessor();

    // ============================================================
    // DRAG & DROP
    // ============================================================

    dropZoneOCR.addEventListener('click', () => {
        fileInputOCR.click();
    });

    dropZoneOCR.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZoneOCR.style.borderColor = '#ff9800';
        dropZoneOCR.style.background = 'rgba(255, 152, 0, 0.1)';
    });

    dropZoneOCR.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZoneOCR.style.borderColor = '#6c757d';
        dropZoneOCR.style.background = 'rgba(33, 37, 41, 0.5)';
    });

    dropZoneOCR.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZoneOCR.style.borderColor = '#6c757d';
        dropZoneOCR.style.background = 'rgba(33, 37, 41, 0.5)';

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelected(files[0]);
        }
    });

    fileInputOCR.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelected(e.target.files[0]);
        }
    });

    // ============================================================
    // MANEJO DE ARCHIVO
    // ============================================================

    function handleFileSelected(file) {
        console.log('[OCR Uploader] Archivo seleccionado:', file.name);
        currentFile = file;

        // Actualizar UI
        dropZoneOCR.innerHTML = `
            <div class="text-warning mb-2" style="font-size: 1.1rem;">
                <svg width="32" height="32" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M14 4.5V14a2 2 0 0 1-2 2h-1v-1h1a1 1 0 0 0 1-1V4.5h-2A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v9H2V2a2 2 0 0 1 2-2h5.5L14 4.5z"/>
                    <path d="M1.5 11.5A1.5 1.5 0 0 1 3 10h10a1.5 1.5 0 0 1 1.5 1.5v2a1.5 1.5 0 0 1-1.5 1.5H3A1.5 1.5 0 0 1 1.5 13.5v-2z"/>
                </svg>
            </div>
            <div class="text-light mb-2" style="font-size: 1rem;">
                <strong>${file.name}</strong>
            </div>
            <div class="small text-info">
                ${(file.size / 1024).toFixed(2)} KB
            </div>
            <div class="small text-secondary mt-2">
                Haz click en "Procesar Documento" para extraer el texto
            </div>
        `;

        // Mostrar botones de acción
        const actionButtonsContainer = document.getElementById('ocr-action-buttons');
        if (actionButtonsContainer) {
            actionButtonsContainer.classList.remove('d-none');
        }
        if (btnProcessOCR) btnProcessOCR.classList.remove('d-none');
        if (btnCancelOCR) btnCancelOCR.classList.remove('d-none');
    }

    // ============================================================
    // PROCESAR DOCUMENTO
    // ============================================================


    // Siempre usar modo preciso (backend)
    function getSelectedOCRMode() {
        return 'backend';
    }

    // === PROCESAR DOCUMENTO (MODOS) ===
    if (btnProcessOCR) {
        btnProcessOCR.addEventListener('click', async () => {
            if (!currentFile) {
                alert('No hay archivo seleccionado');
                return;
            }


            // Siempre usar OCR BACKEND (FLASK)
            try {
                // Ocultar botones, mostrar progreso
                btnProcessOCR.classList.add('d-none');
                btnCancelOCR.classList.add('d-none');
                ocrProgressContainer.classList.remove('d-none');
                if (ocrProgressText) ocrProgressText.innerHTML = '<i class="fa-solid fa-microchip fa-spin me-2"></i>Iniciando Hibridación Deep Vision (IA)...';

                let result = null;
                // === OCR BACKEND (FLASK) ===
                const formData = new FormData();
                formData.append('file', currentFile);
                // Añadir el motor OCR seleccionado
                const ocrEngineSelect = document.getElementById('ocrEngineSelect');
                // Añadir el modelo de IA seleccionado para corrección automática
                const ocrModelSelect = document.getElementById('sel-potencia-ocr');
                if (ocrModelSelect) {
                    formData.append('ocr_model', ocrModelSelect.value);
                }

                // Obtener token CSRF del meta tag
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

                const headers = {};
                if (csrfToken) {
                    headers['X-CSRFToken'] = csrfToken;
                }

                const response = await fetch('/api/ocr/advanced', {
                    method: 'POST',
                    headers: headers,
                    body: formData
                });
                if (!response.ok) {
                    let msg = 'Error en el OCR del servidor';
                    try {
                        const errData = await response.json();
                        if (errData && errData.error) msg = `Error del servidor: ${errData.error}`;
                    } catch (e) {
                        console.error('Error parsing error response:', e);
                    }
                    console.error('[OCR Uploader] Server returned error:', msg);
                    alert(msg);
                    // Resetear UI
                    resetOCRUI();
                    return;
                }
                const data = await response.json();
                result = {
                    text: data.text || '',
                    confidence: data.confidence || 0,
                    metadata: {},
                    duration: 0
                };

                // CRÍTICO: Guardar datos extraídos de forma segura
                extractedData = {
                    text: result.text || '',
                    confidence: result.confidence || 0,
                    metadata: result.metadata || {},
                    duration: result.duration || 0
                };

                // Verificación de integridad
                console.log('[OCR Uploader] ✓ extractedData guardado:');
                console.log('  - text length:', extractedData.text.length);
                console.log('  - confidence:', extractedData.confidence);
                console.log('  - metadata keys:', Object.keys(extractedData.metadata));

                // Mostrar resultado
                displayOCRResult(extractedData);

                // ============================================
                // AUTO-CORRECCIÓN CON IA (AUTOMÁTICA)
                // ============================================
                console.log('[OCR] Iniciando corrección automática con IA...');
                await improveWithAI();

            } catch (error) {
                console.error('[OCR Uploader] Error:', error);
                alert(`Error al procesar el documento: ${error.message}`);
                // Resetear UI
                resetOCRUI();
            }
        });
    }

    // ============================================================
    // CANCELAR
    // ============================================================

    if (btnCancelOCR) {
        btnCancelOCR.addEventListener('click', () => {
            resetOCRUI();
        });
    }

    // ============================================================
    // MOSTRAR RESULTADO
    // ============================================================

    function displayOCRResult(result) {
        console.log('[OCR Uploader] Mostrando resultado:', result);

        // VALIDACIÓN: Asegurar que result.text existe
        if (!result.text || result.text.trim().length === 0) {
            console.warn('[OCR] ⚠️ ADVERTENCIA: No se extrajo texto del documento');
        }

        // Ocultar progreso
        ocrProgressContainer.classList.add('d-none');

        // Construir preview de metadatos (solo para mostrar)
        let metadataHTML = '';

        const metadata = result.metadata;
        const metadataLabels = {
            'titulo': 'Título',
            'autor': 'Autor',
            'publicacion': 'Publicación',
            'fecha_original': 'Fecha',
            'anio': 'Año',
            'ciudad': 'Ciudad',
            'pagina_inicio': 'Página Inicio',
            'pagina_fin': 'Página Fin'
        };

        let hasMetadata = false;
        for (const [key, label] of Object.entries(metadataLabels)) {
            if (metadata[key]) {
                hasMetadata = true;
                metadataHTML += `
                    <div class="col-md-6 mb-2">
                        <div class="p-2 bg-dark border border-secondary rounded">
                            <small class="text-secondary d-block mb-1" style="font-size: 0.7rem;">${label}</small>
                            <div class="text-warning" style="font-size: 0.85rem;">${metadata[key]}</div>
                        </div>
                    </div>
                `;
            }
        }

        // Contenedor de metadatos
        const metadataContainer = document.getElementById('ocr-metadata-preview');
        if (metadataContainer && hasMetadata) {
            metadataContainer.innerHTML = `
                <div class="mb-3 pb-3 border-bottom border-secondary">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <small class="text-muted text-uppercase fw-bold" style="font-size: 0.7rem;">
                            <i class="fa-solid fa-database me-1"></i> Metadatos Detectados
                        </small>
                        <span class="badge bg-dark border border-success text-success" style="font-size: 0.7rem;">
                            <i class="fa-solid fa-check-circle me-1"></i> ${result.confidence.toFixed(0)}% confianza
                        </span>
                    </div>
                    <div class="row g-2">
                        ${metadataHTML}
                    </div>
                </div>
            `;
        } else if (metadataContainer) {
            metadataContainer.innerHTML = '';
        }

        // IMPORTANTE: Guardar solo el texto puro en el preview (sin metadatos)
        if (ocrTextPreview) {
            // Guardar texto en atributo data para copiado
            ocrTextPreview.setAttribute('data-ocr-text', result.text || '');
            // Mostrar texto con formato
            ocrTextPreview.textContent = result.text || 'No se extrajo texto';
        }

        // Mostrar contenedor de resultado
        ocrResultContainer.classList.remove('d-none');

        // Scroll suave al resultado
        ocrResultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // ============================================================
    // 🤖 MEJORAR OCR CON IA (CLAUDE)
    // ============================================================

    // ============================================================
    // 🤖 MEJORAR OCR CON IA (CLAUDE/GEMINI)
    // ============================================================

    // Función reutilizable para mejorar con IA
    async function improveWithAI() {
        if (!extractedData) {
            console.warn('No hay datos de OCR para mejorar');
            return;
        }

        try {
            // Deshabilitar botón y mostrar estado de carga
            if (btnMejorarIA) {
                btnMejorarIA.disabled = true;
                btnMejorarIA.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                    Corrigiendo con IA...
                `;
            }

            // Obtener potencia (modelo) seleccionada
            const selPotencia = document.getElementById('sel-potencia-ocr');
            const potencia = selPotencia ? selPotencia.value : 'gemini:flash';

            console.log(`[IA] Enviando para corrección con modelo: ${potencia}...`);

            // Obtener token CSRF
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            const headers = {
                'Content-Type': 'application/json'
            };
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            // Convertir imagen a Base64 si existe
            let imageData = null;
            if (currentFile && currentFile.type.startsWith('image/')) {
                imageData = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = (e) => resolve(e.target.result);
                    reader.readAsDataURL(currentFile);
                });
            }

            // Llamar a endpoint de corrección avanzada
            const response = await fetch('/api/gemini/correct', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    texto: extractedData.text,
                    metadatos: extractedData.metadata,
                    image_data: imageData,
                    potencia: potencia // Enviar modelo seleccionado
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || data.mensaje || 'Error al procesar con IA');
            }

            if (!data.success) {
                throw new Error(data.error || 'Error desconocido');
            }

            console.log('[IA] ✓ Metadatos corregidos:', data.metadatos);

            // Actualizar metadatos con los corregidos por IA
            const textoOriginal = extractedData.text; // Guardar el texto antes de actualizar

            extractedData.metadata = {
                titulo: data.metadatos.titulo || extractedData.metadata.titulo,
                autor: data.metadatos.autor || extractedData.metadata.autor,
                fecha_original: data.metadatos.fecha_original || extractedData.metadata.fecha_original,
                anio: data.metadatos.anio || extractedData.metadata.anio,
                publicacion: data.metadatos.publicacion || extractedData.metadata.publicacion,
                ciudad: data.metadatos.ciudad || extractedData.metadata.ciudad,
                pagina_inicio: data.metadatos.pagina_inicio || extractedData.metadata.pagina_inicio,
                pagina_fin: data.metadatos.pagina_fin || extractedData.metadata.pagina_fin
            };

            // Actualizar confianza
            extractedData.confidence = data.metadatos.confianza || extractedData.confidence;

            // Actualizar texto si la IA lo corrigió
            if (data.corrected_text) {
                extractedData.text = data.corrected_text;
                console.log('[IA] Texto corregido actualizado');
            } else {
                // Si no hay correccion, mantener el original
                extractedData.text = textoOriginal;
            }

            // Regenerar preview con datos mejorados
            displayOCRResult(extractedData);

            // Mostrar correcciones realizadas
            if (data.metadatos.correcciones && data.metadatos.correcciones.length > 0) {
                const correccionesHTML = `
                    <div class="alert alert-success mt-3 small">
                        <h6 class="mb-2 fw-bold"><i class="fa-solid fa-check-double me-1"></i> Correcciones IA:</h6>
                        <ul class="mb-0 ps-3">
                            ${data.metadatos.correcciones.map(c => `<li>${c}</li>`).join('')}
                        </ul>
                    </div>
                `;
                if (ocrTextPreview) ocrTextPreview.insertAdjacentHTML('beforeend', correccionesHTML);
            }

            // Mostrar advertencias si las hay
            if (data.metadatos.advertencias && data.metadatos.advertencias.length > 0) {
                const advertenciasHTML = `
                    <div class="alert alert-warning mt-2 small">
                        <h6 class="mb-2 fw-bold"><i class="fa-solid fa-triangle-exclamation me-1"></i> Advertencias:</h6>
                        <ul class="mb-0 ps-3">
                            ${data.metadatos.advertencias.map(a => `<li>${a}</li>`).join('')}
                        </ul>
                    </div>
                `;
                if (ocrTextPreview) ocrTextPreview.insertAdjacentHTML('beforeend', advertenciasHTML);
            }

            // Notificación de éxito
            showNotification(`✓ IA (${potencia.split(':')[0]}): Texto y metadatos corregidos`, 'success');

            // Si el cálculo de progreso existe en esta página (editar.html/new.html), lo disparamos
            if (typeof calcularProgreso === 'function') {
                setTimeout(calcularProgreso, 200);
            }

        } catch (error) {
            console.error('[IA] Error:', error);

            let mensajeError = 'Error al mejorar con IA: ' + error.message;

            if (error.message.includes('API key')) {
                mensajeError = '⚠️ Configuración de IA no disponible.';
            }

            showNotification(mensajeError, 'danger');

        } finally {
            // Restaurar botón
            if (btnMejorarIA) {
                btnMejorarIA.disabled = false;
                btnMejorarIA.innerHTML = `
                    <i class="fa-solid fa-wand-magic-sparkles me-1"></i> Revisar con IA Seleccionada
                `;
            }
        }
    }

    // Event Listener manual (por si el usuario quiere reintentar)
    if (btnMejorarIA) {
        btnMejorarIA.addEventListener('click', improveWithAI);
    }

    // ============================================================
    // APLICAR METADATOS AL FORMULARIO
    // ============================================================

    if (btnApplyMetadata) {
        btnApplyMetadata.addEventListener('click', () => {
            if (!extractedData || !extractedData.metadata) {
                alert('No hay metadatos para aplicar');
                return;
            }

            // VALIDACIÓN CRÍTICA
            if (!extractedData.text || extractedData.text.trim().length === 0) {
                alert('⚠️ No hay texto extraído para aplicar.');
                return;
            }

            const metadata = extractedData.metadata;

            // Mapeo de campos OCR → formulario
            const fieldMap = {
                'titulo': 'titulo',
                'fecha_original': 'fecha_original',
                'anio': 'anio',
                'publicacion': 'publicacion',
                'ciudad': 'ciudad',
                'pagina_inicio': 'pagina_inicio',
                'pagina_fin': 'pagina_fin',
                'nombre_autor': 'nombre_autor',
                'apellido_autor': 'apellido_autor'
            };

            // Aplicar valores
            let appliedCount = 0;
            for (const [ocrField, formField] of Object.entries(fieldMap)) {
                if (metadata[ocrField]) {
                    const input = document.querySelector(`[name="${formField}"]`);
                    if (input) {
                        input.value = metadata[ocrField];

                        // Trigger change event para validación
                        input.dispatchEvent(new Event('change', { bubbles: true }));

                        // Highlight temporal
                        input.style.borderColor = '#4a7c2f';
                        setTimeout(() => {
                            input.style.borderColor = '';
                        }, 2000);

                        appliedCount++;
                    }
                }
            }

            // Copiar texto completo según selector de destino
            const destOriginal = document.getElementById('ocr-dest-original');
            const esIdiomaOriginal = destOriginal && destOriginal.checked;

            if (extractedData.text) {
                if (esIdiomaOriginal) {
                    // Pegar en campo "Texto original"

                    // Cambiar a la pestaña "Texto Original" PRIMERO
                    const tabOriginal = document.getElementById('original-tab');
                    if (tabOriginal) {
                        new bootstrap.Tab(tabOriginal).show();
                    }

                    // MÉTODO 0: Intentar con Quill (Especial para HesiOX News)
                    let textoCopiado = false;
                    if (window.quillEditors && window.quillEditors.texto_original) {
                        // USAR setText para preservar espacios y formato idéntico al OCR
                        window.quillEditors.texto_original.setText(extractedData.text);
                        textoCopiado = true;
                        appliedCount++;
                    }

                    if (!textoCopiado && typeof tinymce !== 'undefined') {
                        const editor = tinymce.get('texto_original');
                        if (editor) {
                            // Para TinyMCE usamos un pre-wrap si es posible
                            editor.setContent('<pre style="font-family:inherit; white-space:pre-wrap;">' + extractedData.text + '</pre>');
                            textoCopiado = true;
                            appliedCount++;
                            editor.focus();
                        }
                    }

                    // Fallback a textarea nativo
                    if (!textoCopiado) {
                        const textareaOriginal = document.querySelector('textarea[name="texto_original"]');
                        if (textareaOriginal) {
                            textareaOriginal.value = extractedData.text;
                            textareaOriginal.focus();
                            appliedCount++;
                        }
                    }
                } else {
                    // Pegar en campo "Contenido" (español)
                    console.log('[OCR] Intentando copiar a campo "contenido"...');

                    // Cambiar a la pestaña "Traducción/Español" PRIMERO
                    const tabTraduccion = document.getElementById('traduccion-tab');
                    if (tabTraduccion) {
                        const tab = new bootstrap.Tab(tabTraduccion);
                        tab.show();
                        console.log('[OCR] ✓ Pestaña "Traducción" activada');
                    }

                    // MÉTODO 0: Intentar con Quill (Especial para HesiOX News)
                    let textoCopiado = false;
                    if (window.quillEditors && window.quillEditors.contenido) {
                        // USAR setText para preservar espacios y formato idéntico al OCR
                        window.quillEditors.contenido.setText(extractedData.text);
                        console.log('[OCR] ✓ Texto insertado en Quill (contenido)');
                        textoCopiado = true;
                        appliedCount++;
                    }

                    // MÉTODO 1: Intentar con TinyMCE (editor rico)
                    if (!textoCopiado && typeof tinymce !== 'undefined') {
                        const editor = tinymce.get('contenido');
                        console.log('[OCR] Editor TinyMCE encontrado:', !!editor);
                        if (editor) {
                            editor.setContent(extractedData.text.replace(/\n/g, '<br>'));
                            console.log('[OCR] ✓ Texto insertado en TinyMCE (contenido)');
                            textoCopiado = true;
                            appliedCount++;

                            // Scroll al editor
                            setTimeout(() => {
                                const editorContainer = editor.getContainer();
                                if (editorContainer) {
                                    editorContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    editor.focus();
                                }
                            }, 100);
                        }
                    }

                    // MÉTODO 2: Fallback a textarea nativo (si TinyMCE no está activo)
                    if (!textoCopiado) {
                        const textareaContenido = document.querySelector('textarea[name="contenido"]');
                        console.log('[OCR] Textarea nativo encontrado:', !!textareaContenido);
                        if (textareaContenido) {
                            textareaContenido.value = extractedData.text;
                            textareaContenido.dispatchEvent(new Event('change', { bubbles: true }));
                            textareaContenido.style.borderColor = '#4a7c2f';
                            setTimeout(() => {
                                textareaContenido.style.borderColor = '';
                            }, 2000);
                            console.log('[OCR] ✓ Texto copiado a textarea nativo (contenido)');
                            appliedCount++;

                            // Scroll al campo
                            setTimeout(() => {
                                textareaContenido.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                textareaContenido.focus();
                            }, 100);
                        }
                    }
                }
            } else {
                console.warn('[OCR] ⚠️ No hay texto extraído para copiar');
            }

            // Notificación de éxito
            showNotification(`✓ ${appliedCount} campos completados`, 'success');

            // Resetear OCR UI
            resetOCRUI();
        });
    }

    // ============================================================
    // DESCARTAR
    // ============================================================

    if (btnDiscardOCR) {
        btnDiscardOCR.addEventListener('click', () => {
            if (confirm('¿Descartar los datos extraídos?')) {
                resetOCRUI();
            }
        });
    }

    // ============================================================
    // RESETEAR UI
    // ============================================================

    function resetOCRUI() {
        currentFile = null;
        extractedData = null;

        // Resetear drop zone
        dropZoneOCR.innerHTML = `
            <svg width="64" height="64" fill="currentColor" opacity="0.4" class="mb-3">
                <rect x="8" y="12" width="48" height="40" rx="3" stroke="currentColor" stroke-width="3" fill="none"/>
                <path d="M24 26 L32 18 L40 26" stroke="currentColor" stroke-width="3" fill="none"/>
                <line x1="32" y1="18" x2="32" y2="42" stroke="currentColor" stroke-width="3"/>
            </svg>
            <div class="text-light mb-2" style="font-size: 1.1rem;">
                <strong>📄 Arrastra un documento aquí</strong>
            </div>
            <div class="text-info mb-2">o haz click para seleccionar</div>
            <div class="small text-secondary">
                <span class="badge bg-secondary me-2">OCR automático</span>
                <span class="badge bg-secondary">Tamaño: 10 MB</span>
            </div>
            <div class="small text-warning mt-2">Formatos: PDF, JPG, PNG, TIFF</div>
        `;

        // Ocultar elementos
        btnProcessOCR.classList.add('d-none');
        btnCancelOCR.classList.add('d-none');
        ocrProgressContainer.classList.add('d-none');
        ocrResultContainer.classList.add('d-none');

        // Limpiar input
        fileInputOCR.value = '';
    }

    // ============================================================
    // NOTIFICACIÓN HELPER
    // ============================================================

    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '10000';
        notification.style.minWidth = '300px';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    console.log('[OCR Uploader] ✓ Sistema inicializado correctamente');
});
