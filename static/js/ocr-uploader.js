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
    let pdfPageCount = 0;
    let stopSequentialOCR = false;

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

    async function handleFileSelected(file) {
        console.log('[OCR Uploader] Archivo seleccionado:', file.name);
        currentFile = file;
        pdfPageCount = 0;

        // Deshabilitar botones mientras analizamos
        if (btnProcessOCR) {
            btnProcessOCR.classList.add('d-none');
            btnProcessOCR.disabled = true;
        }

        // Si es PDF, mostrar estado de "analizando"
        if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
            dropZoneOCR.innerHTML = `
                <div class="text-accent mb-2">
                    <i class="fa-solid fa-sync fa-spin fa-2x"></i>
                </div>
                <div class="text-light">Analizando estructura del PDF...</div>
                <div class="small text-muted mt-1">${file.name}</div>
            `;
            await fetchPDFInfo(file);
        } else {
            // Imagen normal
            updateDropZoneWithFile(file);
        }

        // Mostrar botones de acción y habilitar
        const actionButtonsContainer = document.getElementById('ocr-action-buttons');
        if (actionButtonsContainer) {
            actionButtonsContainer.classList.remove('d-none');
        }
        if (btnProcessOCR) {
            btnProcessOCR.classList.remove('d-none');
            btnProcessOCR.disabled = false;
        }
        if (btnCancelOCR) btnCancelOCR.classList.remove('d-none');

        // AUTO-TRIGGER: Si es PDF, preguntar inmediatamente (independientemente del conteo para asegurar que salga)
        if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
            console.log('[OCR] PDF detectado, forzando activación de diálogo...');
            setTimeout(triggerOCRProcessing, 500);
        }
    }

    function updateDropZoneWithFile(file, extraInfo = '') {
        dropZoneOCR.innerHTML = `
            <div class="text-accent mb-2" style="font-size: 1.1rem;">
                <i class="fa-solid fa-file-pdf fa-2x"></i>
            </div>
            <div class="text-light mb-2" style="font-size: 1rem;">
                <strong>${file.name}</strong>
            </div>
            <div class="small text-muted">
                ${(file.size / (1024 * 1024)).toFixed(2)} MB ${extraInfo}
            </div>
            <div class="small text-accent mt-2 fw-bold">
                <i class="fa-solid fa-wand-magic-sparkles me-1"></i> LISTO PARA PROCESAR
            </div>
        `;
    }

    async function fetchPDFInfo(file) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            
            const response = await fetch('/api/ocr/pdf-info', {
                method: 'POST',
                headers: csrfToken ? { 'X-CSRFToken': csrfToken } : {},
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    pdfPageCount = data.pages;
                    console.log(`[OCR] PDF detectado con ${pdfPageCount} páginas`);
                    updateDropZoneWithFile(file, `| <span class="ocr-page-badge">${pdfPageCount} páginas</span>`);
                }
            }
        } catch (e) {
            console.error('[OCR] Error obteniendo info del PDF:', e);
        }
    }

    // ============================================================
    // PROCESAR DOCUMENTO
    // ============================================================


    // Siempre usar modo preciso (backend)
    function getSelectedOCRMode() {
        return 'backend';
    }

    // === PROCESAR DOCUMENTO (MODOS) ===
    // === FUNCIÓN PRINCIPAL DE PROCESAMIENTO ===
    async function triggerOCRProcessing() {
        if (!currentFile) {
            alert('No hay archivo seleccionado');
            return;
        }

        // Manejo de multi-página si es PDF (o forzar si es PDF y el conteo falló)
        const isPDF = currentFile.type === 'application/pdf' || currentFile.name.toLowerCase().endsWith('.pdf');
        
        if (isPDF) {
            // Si el conteo falló o es 0/1, intentamos preguntar de todos modos o dar opción manual
            const displayCount = pdfPageCount > 0 ? pdfPageCount : 'varias';
            
            const result = await Swal.fire({
                title: 'Documento PDF Detectado',
                text: `Se han detectado ${displayCount} páginas. ¿Cómo deseas proceder?`,
                icon: 'question',
                showConfirmButton: false,
                showCancelButton: true,
                cancelButtonText: 'Cancelar',
                background: '#1a1d21',
                color: '#fff',
                html: `
                    <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 15px;">
                        <button id="swal-btn-all-once" class="swal2-confirm swal2-styled" style="background-color: #ff9800; margin: 0; width: 100%;">Procesar todo (Un solo bloque)</button>
                        <button id="swal-btn-all-seq" class="swal2-confirm swal2-styled" style="background-color: #294a60; margin: 0; width: 100%;">Procesar todo (Secuencial)</button>
                        <button id="swal-btn-single" class="swal2-deny swal2-styled" style="background-color: #111; margin: 0; width: 100%; border: 1px solid #444;">Elegir página específica</button>
                    </div>
                `,
                didOpen: () => {
                    document.getElementById('swal-btn-all-once').onclick = () => {
                        window.swalOcrAction = 'all-once';
                        Swal.clickConfirm();
                    };
                    document.getElementById('swal-btn-all-seq').onclick = () => {
                        window.swalOcrAction = 'all-seq';
                        Swal.clickConfirm();
                    };
                    document.getElementById('swal-btn-single').onclick = () => {
                        window.swalOcrAction = 'single';
                        Swal.clickConfirm();
                    };
                },
                preConfirm: () => {
                    return window.swalOcrAction;
                }
            });

            const action = result.isConfirmed ? result.value : null;

            if (action === 'all-once') {
                // Procesar todo en una sola llamada (sin page_number)
                console.log('[OCR] Procesando documento completo en un bloque');
                await runOCR();
                return;
            } else if (action === 'all-seq') {
                // Procesar todo secuencialmente
                if (pdfPageCount === 0) pdfPageCount = 1; 
                await processSequentialOCR();
                return;
            } else if (action === 'single') {
                // Elegir página específica
                let page;
                if (pdfPageCount > 0) {
                    const inputOptions = {};
                    for (let i = 1; i <= pdfPageCount; i++) {
                        inputOptions[i] = `Página ${i}`;
                    }

                    const { value: selectedPage } = await Swal.fire({
                        title: 'Seleccionar Página',
                        html: `
                            <div style="margin-top: 15px; text-align: left;">
                                <label class="sirio-label" style="display: block; margin-bottom: 12px; color: #ff9800;">
                                    Haz clic en la página que deseas transcribir:
                                </label>
                                <div id="swal-page-list" class="custom-scrollbar" style="max-height: 250px; overflow-y: auto; background: #111; border: 1px solid #444; border-radius: 6px;">
                                    ${Array.from({length: pdfPageCount}, (_, i) => i + 1).map(i => `
                                        <div class="sirio-option" data-value="${i}" style="padding: 12px 15px; cursor: pointer; color: #ffd580; border-bottom: 1px solid #222;">
                                            <i class="fas fa-file-alt" style="margin-right: 10px; opacity: 0.5;"></i> Página ${i}
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `,
                        showCancelButton: true,
                        showConfirmButton: false, // El usuario elige al hacer clic
                        cancelButtonText: 'Cancelar',
                        background: '#1a1d21',
                        color: '#fff',
                        didOpen: () => {
                            const list = document.getElementById('swal-page-list');
                            list.querySelectorAll('.sirio-option').forEach(opt => {
                                opt.onclick = () => {
                                    window.selectedPageValue = opt.getAttribute('data-value');
                                    Swal.clickConfirm();
                                };
                            });
                        },
                        preConfirm: () => {
                            return window.selectedPageValue;
                        }
                    });
                    page = selectedPage;
                } else {
                    // Fallback manual si por algún motivo técnico no sabemos el total
                    const { value: manualPage } = await Swal.fire({
                        title: 'Seleccionar Página (Manual)',
                        input: 'number',
                        inputLabel: `No se pudo detectar el total de páginas. Introduce el número manualmente:`,
                        inputValue: 1,
                        inputAttributes: { min: 1, max: 999, step: 1 },
                        showCancelButton: true,
                        confirmButtonText: 'Extraer',
                        confirmButtonColor: '#ff9800',
                        background: '#1a1d21',
                        color: '#fff',
                        customClass: {
                            input: 'sirio-select',
                            label: 'sirio-label'
                        }
                    });
                    page = manualPage;
                }

                if (page) {
                    console.log(`[OCR] Solicitando extracción de página específica: ${page}`);
                    // Resetear estado anterior para asegurar una transcripción limpia
                    extractedData = null;
                    await runOCR(parseInt(page));
                }
                return;
            } else {
                return; // Cancelado o cerrado
            }
        }

        // Caso normal (Imagen o PDF de 1 página)
        await runOCR();
    }

    if (btnProcessOCR) {
        btnProcessOCR.addEventListener('click', triggerOCRProcessing);
    }

    async function runOCR(pageNumber = null) {
        try {
            // Ocultar botones, mostrar progreso
            if (btnProcessOCR) btnProcessOCR.classList.add('d-none');
            if (btnCancelOCR) btnCancelOCR.classList.add('d-none');
            if (ocrProgressContainer) ocrProgressContainer.classList.remove('d-none');
            
            // Reiniciar barra si es primera página o proceso único
            if (!pageNumber || pageNumber === 1) {
                if (ocrProgressBar) ocrProgressBar.style.width = '0%';
            }

            const pageInfo = pageNumber ? ` (Página ${pageNumber} de ${pdfPageCount})` : '';
            if (ocrProgressText) ocrProgressText.innerHTML = `<i class="fa-solid fa-microchip fa-spin me-2"></i>Iniciando Hibridación Deep Vision${pageInfo}...`;

            // Simulador de progreso para la página actual
            let currentProgress = 0;
            const progressInterval = setInterval(() => {
                if (currentProgress < 90) {
                    currentProgress += 5;
                    // Si es secuencial, el progreso base es de las páginas anteriores
                    let baseProgress = 0;
                    let pageWeight = 100;
                    
                    // Asegurar que pdfPageCount sea al menos 1 para evitar NaN/Infinity
                    const safeTotal = (pdfPageCount && pdfPageCount > 0) ? pdfPageCount : (pageNumber || 1);
                    
                    if (safeTotal > 1 && pageNumber) {
                        baseProgress = ((pageNumber - 1) / safeTotal) * 100;
                        pageWeight = (1 / safeTotal) * 100;
                    }
                    
                    const totalProgress = Math.min(100, baseProgress + (currentProgress / 100) * pageWeight);
                    if (ocrProgressBar) ocrProgressBar.style.width = `${totalProgress}%`;
                    
                    const totalDisplay = (pdfPageCount && pdfPageCount > 0) ? pdfPageCount : '?';
                    const pageInfo = pageNumber ? ` Pág. ${pageNumber}` : ' Documento';
                    const progressDisplay = pageNumber ? `(${pageNumber}/${totalDisplay})` : '';
                    
                    if (ocrProgressText) {
                        ocrProgressText.innerHTML = `
                            <i class="fa-solid fa-microchip fa-spin me-2"></i>
                            Procesando${pageInfo}... 
                            <span class="text-white ms-1">${Math.round(totalProgress)}%</span> 
                            <small class="text-muted">${progressDisplay}</small>
                        `;
                    }
                }
            }, 300);

            const formData = new FormData();
            formData.append('file', currentFile);
            
            // Validar y añadir número de página de forma segura
            if (pageNumber !== null && pageNumber !== undefined) {
                const pNum = parseInt(pageNumber);
                if (!isNaN(pNum)) {
                    formData.append('page_number', pNum.toString());
                    console.log(`[OCR] Enviando solicitud para página: ${pNum}`);
                }
            }

            const ocrModelSelect = document.getElementById('sel-potencia-ocr');
            if (ocrModelSelect) {
                formData.append('ocr_model', ocrModelSelect.value);
            }

            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            const headers = csrfToken ? { 'X-CSRFToken': csrfToken } : {};

            // DOBLE CANAL: Enviar por FormData y por Query Params para asegurar recepción
            let apiUrl = '/api/ocr/advanced';
            if (pageNumber) {
                apiUrl += `?page_number=${pageNumber}`;
            }

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: headers,
                body: formData
            });

            clearInterval(progressInterval);

            if (!response.ok) {
                let msg = 'Error en el OCR del servidor';
                try {
                    const errData = await response.json();
                    if (errData && errData.error) msg = `Error del servidor: ${errData.error}`;
                } catch (e) {}
                throw new Error(msg);
            }

            const data = await response.json();
            
            // Priorizar el texto corregido por la IA si existe
            const finalPageText = data.corrected_text || data.text || '';
            
            // Sincronizar el total de páginas si el cliente no lo sabía
            if (data.total_pages && (!pdfPageCount || pdfPageCount === 0)) {
                pdfPageCount = data.total_pages;
                console.log(`[OCR] Sincronizado total de páginas desde el servidor: ${pdfPageCount}`);
            }
            
            // Gestionar la acumulación de texto
            const pageHeader = pageNumber ? `\n\n--- [PÁGINA ${pageNumber}] ---\n\n` : '';
            
            if (extractedData && pageNumber && pageNumber > 1) {
                // Acumular si ya hay datos (modo secuencial)
                extractedData.text += pageHeader + finalPageText;
                if (data.metadata) {
                    extractedData.metadata = { ...extractedData.metadata, ...data.metadata };
                }
                extractedData.imageData = data.image_data;
            } else {
                // Primer proceso o página única
                extractedData = {
                    text: (pageNumber ? pageHeader : '') + finalPageText,
                    confidence: data.confidence || 0,
                    metadata: data.metadata || (data.metadatos ? data.metadatos : {}),
                    imageData: data.image_data
                };
            }

            // Marcar página actual como 100% (o el porcentaje correspondiente en el PDF)
            if (pdfPageCount > 1 && pageNumber) {
                const completedProgress = (pageNumber / pdfPageCount) * 100;
                if (ocrProgressBar) ocrProgressBar.style.width = `${completedProgress}%`;
            } else {
                if (ocrProgressBar) ocrProgressBar.style.width = '100%';
            }

            displayOCRResult(extractedData);
            
        } catch (error) {
            console.error('[OCR Uploader] Error:', error);
            alert(`Error al procesar el documento: ${error.message}`);
            resetOCRUI();
        }
    }

    async function processSequentialOCR() {
        extractedData = null; // Resetear para empezar de cero
        stopSequentialOCR = false;

        let p = 1;
        while (!stopSequentialOCR) {
            await runOCR(p);

            // ¿Hay más páginas?
            // Solo paramos automáticamente si estamos SEGUROS de que no hay más
            if (pdfPageCount > 1 && p >= pdfPageCount) {
                console.log(`[OCR] Fin del documento alcanzado (${p}/${pdfPageCount})`);
                break;
            }
            
            // Si el total es desconocido o solo se detectó 1 pero estamos en modo secuencial,
            // permitimos seguir hasta que el usuario diga basta o lleguemos al límite.
            if (p >= 100) {
                break;
            }

            // Si llegamos aquí, preguntamos si desea continuar con la siguiente
            const result = await Swal.fire({
                title: `Página ${p} extraída`,
                text: `¿Deseas continuar con la transcripción de la página ${p + 1}?`,
                icon: 'success',
                footer: pdfPageCount > 0 ? `<span class="text-muted">Página ${p} de ${pdfPageCount}</span>` : '<span class="text-warning">Total de páginas desconocido</span>',
                showCancelButton: true,
                confirmButtonText: 'Continuar a pág. ' + (p + 1),
                cancelButtonText: 'Terminar aquí',
                confirmButtonColor: '#ff9800',
                cancelButtonColor: '#294a60',
                background: '#1a1d21',
                color: '#fff'
            });

            if (result.isConfirmed) {
                p++;
            } else {
                stopSequentialOCR = true;
            }
        }
        if (extractedData && p > 1) {
            await performGlobalRefinement();
        }
        
        showNotification('✓ Extracción multi-página completada', 'success');
    }

    async function performGlobalRefinement() {
        if (!extractedData || !extractedData.text) return;

        Swal.fire({
            title: 'Refinamiento Global',
            text: 'La IA está perfeccionando el documento completo para asegurar coherencia entre páginas...',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            },
            background: '#1a1d21',
            color: '#fff'
        });

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            const response = await fetch('/api/ocr/corregir', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken || ''
                },
                body: JSON.stringify({
                    texto: extractedData.text,
                    metadatos: extractedData.metadata,
                    image_data: extractedData.imageData
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    extractedData.text = data.corrected_text || extractedData.text;
                    if (data.metadatos) {
                        extractedData.metadata = { ...extractedData.metadata, ...data.metadatos };
                    }
                    displayOCRResult(extractedData);
                    
                    Swal.fire({
                        icon: 'success',
                        title: 'Refinamiento Completado',
                        text: 'El documento ha sido optimizado integralmente por la IA.',
                        timer: 2000,
                        showConfirmButton: false,
                        background: '#1a1d21',
                        color: '#fff'
                    });
                } else {
                    console.warn('[OCR] El refinamiento devolvió un error:', data.error);
                    Swal.close();
                }
            } else {
                console.warn('[OCR] Falló la petición de refinamiento');
                Swal.close();
            }
        } catch (e) {
            console.error('[OCR] Error en refinamiento global:', e);
            Swal.close();
        }
    }

    // ============================================================
    // CANCELAR
    // ============================================================

    if (btnCancelOCR) {
        btnCancelOCR.addEventListener('click', () => {
            resetOCRUI();
        });
    }

    // --- NUEVO: Vincular imagen OCR como material adjunto ---
    const btnVincularImagenOCR = document.getElementById('btn-vincular-imagen-ocr');
    if (btnVincularImagenOCR) {
        btnVincularImagenOCR.addEventListener('click', () => {
            if (extractedData && extractedData.imageData) {
                const hiddenInput = document.getElementById('ocr_image_base64');
                if (hiddenInput) {
                    hiddenInput.value = extractedData.imageData;
                    
                    // NUEVO: Mostrar preview inmediato en el formulario principal
                    if (window.imageUploader && typeof window.imageUploader.addOCRPreview === 'function') {
                        window.imageUploader.addOCRPreview(extractedData.imageData);
                    }

                    Swal.fire({
                        icon: 'success',
                        title: 'Imagen vinculada',
                        text: 'La imagen se ha añadido al material adjunto y se guardará con la noticia.',
                        timer: 2000,
                        showConfirmButton: false,
                        background: '#1a1d21',
                        color: '#fff'
                    });
                    btnVincularImagenOCR.innerHTML = '<i class="fa-solid fa-check me-1"></i> Imagen vinculada correctamente';
                    btnVincularImagenOCR.classList.remove('btn-outline-info');
                    btnVincularImagenOCR.classList.add('btn-info');
                    btnVincularImagenOCR.disabled = true;
                }
            } else {
                Swal.fire({
                    icon: 'warning',
                    title: 'Sin imagen',
                    text: 'Primero debes procesar el documento con OCR.',
                    background: '#1a1d21',
                    color: '#fff'
                });
            }
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
            
            // Highlight paleographic markers
            let previewText = (result.text || 'No se extrajo texto');
            
            // === MEJORA: MAPA DE CALOR DE CONFIANZA ===
            if (result.words_data && result.words_data.length > 0) {
                console.log('[OCR] Generando mapa de calor de confianza...');
                let heatmapHTML = '';
                
                result.words_data.forEach(item => {
                    const word = item.word;
                    const conf = item.confidence;
                    
                    // Escapar palabra
                    let escapedWord = word.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    
                    if (conf !== -1 && conf < 85) {
                        // Resaltar si la confianza es baja (< 85%)
                        // Calculamos una opacidad basada en la duda
                        const opacity = (100 - conf) / 100;
                        heatmapHTML += `<span class="ocr-low-confidence" title="Confianza: ${conf}%" style="background: rgba(255, 152, 0, ${opacity * 0.4}); border-bottom: 1px dotted #ff9800;">${escapedWord}</span> `;
                    } else {
                        heatmapHTML += escapedWord + ' ';
                    }
                });
                
                previewText = heatmapHTML.trim();
                
                // Aplicar marcadores paleográficos sobre el heatmap (con cuidado de no romper el HTML)
                // Usamos una aproximación segura: solo si no están ya envueltos
                previewText = previewText.replace(/\[COLUMNA\s+(\d+)\]/gi, '<span class="ocr-marker-column">[COLUMNA $1]</span>');
                previewText = previewText.replace(/\[CABECERA\]/gi, '<span class="ocr-marker-header">[CABECERA]</span>');
                previewText = previewText.replace(/\[ANUNCIO\]/gi, '<span class="ocr-marker-column">[ANUNCIO]</span>');
                previewText = previewText.replace(/\[PÁGINA\s+(\d+)\]/gi, '<span class="ocr-marker-header">[PÁGINA $1]</span>');
                previewText = previewText.replace(/\[NOTICIA\]/gi, '<span class="ocr-marker-header">[NOTICIA]</span>');
            } else {
                // Fallback: texto plano con marcadores (lógica original)
                previewText = previewText.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                previewText = previewText.replace(/\[COLUMNA\s+(\d+)\]/gi, '<span class="ocr-marker-column">[COLUMNA $1]</span>');
                previewText = previewText.replace(/\[CABECERA\]/gi, '<span class="ocr-marker-header">[CABECERA]</span>');
                previewText = previewText.replace(/\[ANUNCIO\]/gi, '<span class="ocr-marker-column">[ANUNCIO]</span>');
                previewText = previewText.replace(/\[PÁGINA\s+(\d+)\]/gi, '<span class="ocr-marker-header">[PÁGINA $1]</span>');
                previewText = previewText.replace(/\[NOTICIA\]/gi, '<span class="ocr-marker-header">[NOTICIA]</span>');
                previewText = previewText.replace(/\[METADATOS:?.*?\]/gi, '<span class="ocr-marker-metadata">$&</span>');
            }

            ocrTextPreview.innerHTML = previewText;
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

            // --- LÓGICA DE BARRA DE PROGRESO SIMULADA ---
            const progContainer = document.getElementById('ai-progress-container');
            const progBar = document.getElementById('ai-progress-bar');
            const progText = document.getElementById('ai-progress-text');
            
            let progressInterval;
            if (progContainer && progBar) {
                progContainer.classList.remove('d-none');
                progBar.style.width = '0%';
                if (progText) progText.textContent = 'Iniciando conexión con motor de IA...';
                
                let width = 0;
                progressInterval = setInterval(() => {
                    if (width < 90) {
                        const increment = (95 - width) / 20;
                        width += increment;
                        progBar.style.width = width + '%';
                        
                        if (progText) {
                            if (width > 20 && width < 40) progText.textContent = 'Analizando estructura del documento...';
                            if (width > 40 && width < 70) progText.textContent = 'Refinando texto y metadatos...';
                            if (width > 70) progText.textContent = 'Finalizando corrección profunda...';
                        }
                    }
                }, 500);
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

            // Obtener imagen en Base64 (Prioridad: imagen de la página procesada, Fallback: archivo original si es imagen)
            let imageData = extractedData.imageData || null;
            
            if (!imageData && currentFile && currentFile.type.startsWith('image/')) {
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
            // --- FINALIZAR BARRA DE PROGRESO ---
            const progContainer = document.getElementById('ai-progress-container');
            const progBar = document.getElementById('ai-progress-bar');
            const progText = document.getElementById('ai-progress-text');
            
            if (progBar) {
                progBar.style.width = '100%';
                if (progText) progText.textContent = '¡Corrección completada!';
                setTimeout(() => {
                    if (progContainer) progContainer.classList.add('d-none');
                }, 1000);
            }

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

            // Mapeo de campos OCR → formulario (SOLO los solicitados por el usuario)
            const fieldMap = {
                'titulo': 'titulo'
            };

            // Aplicar valores básicos del mapa
            let appliedCount = 0;
            for (const [ocrField, formField] of Object.entries(fieldMap)) {
                if (metadata[ocrField]) {
                    const input = document.querySelector(`[name="${formField}"]`);
                    if (input) {
                        input.value = metadata[ocrField];
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        input.style.borderColor = '#4a7c2f';
                        setTimeout(() => { input.style.borderColor = ''; }, 2000);
                        appliedCount++;
                    }
                }
            }

            // Lógica especial para AUTOR (separar en Nombre y Apellido si es posible)
            if (metadata.autor) {
                const autorFull = metadata.autor.trim();
                let nombre = "";
                let apellido = "";

                // Intento de división simple por el último espacio para nombre/apellido
                const parts = autorFull.split(' ');
                if (parts.length > 1) {
                    apellido = parts.pop();
                    nombre = parts.join(' ');
                } else {
                    nombre = autorFull;
                }

                const inputNombre = document.querySelector('[name="nombre_autor"]');
                const inputApellido = document.querySelector('[name="apellido_autor"]');

                if (inputNombre && nombre) {
                    inputNombre.value = nombre;
                    inputNombre.dispatchEvent(new Event('change', { bubbles: true }));
                    inputNombre.style.borderColor = '#4a7c2f';
                    setTimeout(() => { inputNombre.style.borderColor = ''; }, 2000);
                    appliedCount++;
                }
                if (inputApellido && apellido) {
                    inputApellido.value = apellido;
                    inputApellido.dispatchEvent(new Event('change', { bubbles: true }));
                    inputApellido.style.borderColor = '#4a7c2f';
                    setTimeout(() => { inputApellido.style.borderColor = ''; }, 2000);
                    appliedCount++;
                }
            }

            // Copiar texto completo según selector de destino
            const destOriginal = document.getElementById('ocr-dest-original');
            const esIdiomaOriginal = destOriginal && destOriginal.checked;

            if (extractedData.text) {
                // Función interna para limpiar etiquetas de metadatos del OCR
                const cleanText = (txt) => {
                    if (!txt) return "";
                    // Regex para eliminar [PÁGINA ...], [COLUMNA ...], [GRABADO ...], [CABECERA ...], [PIE ...], etc.
                    return txt.replace(/\[(PÁGINA|COLUMNA|GRABADO|CABECERA|PAGE|COLUMN|HEADER|FOLL|FOLLE|PIE|PIE DE PÁGINA)[^\]]*\]/gi, "").trim();
                };

                const textToApply = cleanText(extractedData.text);

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
                        window.quillEditors.texto_original.setText(textToApply);
                        textoCopiado = true;
                        appliedCount++;
                    }

                    if (!textoCopiado && typeof tinymce !== 'undefined') {
                        const editor = tinymce.get('texto_original');
                        if (editor) {
                            // Para TinyMCE usamos un pre-wrap si es posible
                            editor.setContent('<pre style="font-family:inherit; white-space:pre-wrap;">' + textToApply + '</pre>');
                            textoCopiado = true;
                            appliedCount++;
                            editor.focus();
                        }
                    }

                    // Fallback a textarea nativo
                    if (!textoCopiado) {
                        const textareaOriginal = document.querySelector('textarea[name="texto_original"]');
                        if (textareaOriginal) {
                            textareaOriginal.value = textToApply;
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
                        window.quillEditors.contenido.setText(textToApply);
                        console.log('[OCR] ✓ Texto insertado en Quill (contenido)');
                        textoCopiado = true;
                        appliedCount++;
                    }

                    // MÉTODO 1: Intentar con TinyMCE (editor rico)
                    if (!textoCopiado && typeof tinymce !== 'undefined') {
                        const editor = tinymce.get('contenido');
                        console.log('[OCR] Editor TinyMCE encontrado:', !!editor);
                        if (editor) {
                            editor.setContent(textToApply.replace(/\n/g, '<br>'));
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
                            textareaContenido.value = textToApply;
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
