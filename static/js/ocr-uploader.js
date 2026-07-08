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
    let currentRangeEnd = null;

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
    let isProcessingOCR = false;

    async function triggerOCRProcessing() {
        if (!currentFile) {
            alert('No hay archivo seleccionado');
            return;
        }

        if (isProcessingOCR) {
            console.warn('[OCR] Ya hay un proceso en marcha');
            return;
        }

        isProcessingOCR = true;
        try {
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
                        <button id="swal-btn-range" class="swal2-confirm swal2-styled" style="background-color: #8e44ad; margin: 0; width: 100%;">Procesar rango de páginas</button>
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
                    document.getElementById('swal-btn-range').onclick = () => {
                        window.swalOcrAction = 'range';
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
            } else if (action === 'range') {
                // Procesar rango de páginas
                const { value: rangeValues } = await Swal.fire({
                    title: 'Definir Rango de Páginas',
                    html: `
                        <div class="row g-3" style="margin-top:10px;">
                            <div class="col-6 text-start">
                                <label class="sirio-label mb-2">Página Inicio</label>
                                <input id="swal-range-start" type="number" class="swal2-input m-0 w-100" value="1" min="1" max="${pdfPageCount || 999}">
                            </div>
                            <div class="col-6 text-start">
                                <label class="sirio-label mb-2">Página Fin</label>
                                <input id="swal-range-end" type="number" class="swal2-input m-0 w-100" value="${pdfPageCount || 1}" min="1" max="${pdfPageCount || 999}">
                            </div>
                        </div>
                    `,
                    focusConfirm: false,
                    showCancelButton: true,
                    confirmButtonText: 'Procesar Rango',
                    confirmButtonColor: '#8e44ad',
                    background: '#1a1d21',
                    color: '#fff',
                    preConfirm: () => {
                        const start = parseInt(document.getElementById('swal-range-start').value);
                        const end = parseInt(document.getElementById('swal-range-end').value);
                        if (!start || !end || start > end) {
                            Swal.showValidationMessage('El rango no es válido');
                            return false;
                        }
                        return { start, end };
                    }
                });

                if (rangeValues) {
                    await processSequentialOCR(rangeValues.start, rangeValues.end);
                }
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
            }
        } else {
            // Caso normal (Imagen o PDF de 1 página)
            await runOCR();
        }
    } finally {
        isProcessingOCR = false;
    }
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
                // Si llegamos al 90%, entramos en un modo de avance ultra-lento para indicar actividad
                if (currentProgress < 90) {
                    currentProgress += (currentProgress < 70) ? 5 : 2;
                } else if (currentProgress < 99) {
                    currentProgress += 0.1; // Creep ultra-lento hasta el 99%
                }
                
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
                    // Mostrar decimales si el progreso total es muy bajo (ej: muchas páginas) para ver movimiento
                    const displayPercent = (safeTotal > 20) ? totalProgress.toFixed(1) : Math.round(totalProgress);
                    
                    ocrProgressText.innerHTML = `
                        <i class="fa-solid fa-microchip fa-spin me-2"></i>
                        Procesando${pageInfo}... 
                        <span class="text-white ms-1">${displayPercent}%</span> 
                        <small class="text-muted">${progressDisplay}</small>
                    `;
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

            const ocrEngineSelect = document.getElementById('ocrEngineSelect');
            if (ocrEngineSelect) {
                formData.append('ocr_engine', ocrEngineSelect.value);
                console.log(`[OCR] Usando motor: ${ocrEngineSelect.value}`);
                
                // Si es motor híbrido, forzar reconciliación en el backend
                if (ocrEngineSelect.value === 'hybrid') {
                    formData.append('reconcile_hybrid', 'true');
                }
            }

            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            const headers = csrfToken ? { 'X-CSRFToken': csrfToken } : {};

            // DOBLE CANAL: Enviar por FormData y por Query Params para asegurar recepción
            let apiUrl = '/api/ocr/advanced';
            if (pageNumber) {
                apiUrl += `?page_number=${pageNumber}`;
                // Asegurar que también esté en FormData
                formData.set('page_number', pageNumber.toString());
            }

            // [NUEVO] Asegurar que el archivo esté presente en CADA petición secuencial
            if (currentFile) {
                formData.set('file', currentFile);
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
            let finalPageText = data.corrected_text || data.text || '';
            
            // [CLIENT-SIDE DEDUPLICATION v3] - Optimizado para documentos largos
            if (finalPageText.length > 200) {
                const lines = finalPageText.split('\n');
                const uniqueLines = [];
                const seenNormThisPage = new Set();

                lines.forEach(line => {
                    const l = line.trim();
                    if (!l) {
                        uniqueLines.push("");
                        return;
                    }
                    const norm = l.toLowerCase().replace(/[^a-z0-9]+/g, '');
                    
                    // Solo deduplicar si la línea es significativa (evitar borrar "El", "De", etc.)
                    if (norm.length > 20) {
                        if (seenNormThisPage.has(norm)) return;
                        seenNormThisPage.add(norm);
                    }

                    uniqueLines.push(line);
                });
                finalPageText = uniqueLines.join('\n').replace(/\n{3,}/g, '\n\n');
            }
            
            // Sincronizar el total de páginas si el cliente no lo sabía
            if (data.total_pages && (!pdfPageCount || pdfPageCount === 0)) {
                pdfPageCount = data.total_pages;
                console.log(`[OCR] Sincronizado total de páginas desde el servidor: ${pdfPageCount}`);
            }
            
            // Gestionar la acumulación de texto
            const pageHeader = pageNumber ? `\n\n--- [PÁGINA ${pageNumber}] ---\n\n` : '';
            
            // Log para depurar acumulación
            console.log(`[OCR] Procesando acumulación para página ${pageNumber}. Estado previo: ${extractedData ? 'existe' : 'null'}`);

            if (extractedData && pageNumber && pageNumber > 1) {
                // Acumular si ya hay datos (modo secuencial)
                // Evitar duplicar el header si el backend ya lo incluye (heurística simple)
                const cleanFinalText = finalPageText.trim();
                const alreadyHasHeader = cleanFinalText.includes(`--- [PÁGINA ${pageNumber}] ---`) || 
                                       cleanFinalText.startsWith(`[PÁGINA ${pageNumber}]`);
                
                const textToAppend = alreadyHasHeader ? `\n\n${cleanFinalText}` : `${pageHeader}${cleanFinalText}`;
                extractedData.text += textToAppend;
                
                console.log(`[OCR] Texto acumulado. Nueva longitud: ${extractedData.text.length}`);

                if (data.metadata) {
                    extractedData.metadata = { ...extractedData.metadata, ...data.metadata };
                }
                extractedData.imageData = data.image_data;
                // Acumular mapa de coordenadas (etiquetando por página)
                if (data.words_data) {
                    if (!extractedData.ocrMap) extractedData.ocrMap = [];
                    // Añadir info de página a cada palabra
                    const wordsWithPage = data.words_data.map(w => ({...w, p: pageNumber}));
                    extractedData.ocrMap = extractedData.ocrMap.concat(wordsWithPage);
                }
            } else {
                // Primer proceso o página única
                // Evitar doble header inicial para pág 1
                const alreadyHasHeader = finalPageText.includes(`--- [PÁGINA 1] ---`) || 
                                       finalPageText.startsWith(`[PÁGINA 1]`);
                
                extractedData = {
                    text: (alreadyHasHeader ? '' : (pageNumber ? pageHeader : '')) + finalPageText,
                    confidence: data.confidence || 0,
                    metadata: data.metadata || (data.metadatos ? data.metadatos : {}),
                    imageData: data.image_data,
                    ocrMap: data.words_data ? data.words_data.map(w => ({...w, p: w.p || pageNumber || 1})) : []
                };
                console.log(`[OCR] Primer bloque creado. Longitud: ${extractedData.text.length}`);
            }

            // Marcar página actual con el porcentaje correspondiente
            const totalToProcess = currentRangeEnd || pdfPageCount || pageNumber || 1;
            if (totalToProcess > 1 && pageNumber) {
                const completedProgress = (pageNumber / totalToProcess) * 100;
                if (ocrProgressBar) ocrProgressBar.style.width = `${completedProgress}%`;
            } else {
                if (ocrProgressBar) ocrProgressBar.style.width = '100%';
            }

            // AUTO-VINCULACIÓN: Vinculamos la imagen procesada automáticamente al uploader general
            if (data && data.image_data) {
                // Pasamos el mapa específico de esta página, no el acumulado
                vincularImagenOCRAutomaticamente(data.image_data, data.words_data);
            }

            displayOCRResult(extractedData);
            
        } catch (error) {
            console.error('[OCR Uploader] Error:', error);
            alert(`Error al procesar el documento: ${error.message}`);
            resetOCRUI();
        }
    }

    async function processSequentialOCR(startPage = 1, endPage = null) {
        extractedData = null; // Resetear para empezar de cero
        stopSequentialOCR = false;
        currentRangeEnd = endPage;
        
        // Reiniciar barra de progreso visualmente al inicio del proceso por lotes/rango
        if (ocrProgressBar) ocrProgressBar.style.width = '0%';

        // Bloquear UI para evitar interrupciones durante el proceso de rango

        let p = startPage;
        const targetEnd = endPage || pdfPageCount || 100;

        while (!stopSequentialOCR) {
            await runOCR(p);

            // ¿Hay más páginas dentro del rango?
            if (p >= targetEnd) {
                console.log(`[OCR] Fin del rango alcanzado (${p}/${targetEnd})`);
                break;
            }

            // Siguiente página
            const nextP = p + 1;

            // Si es un proceso automático de rango (endPage definido), seguimos directamente
            if (endPage) {
                // Verificar si hemos excedido el rango por error de redondeo o lógica
                if (nextP > targetEnd) {
                    console.log(`[OCR] Se ha intentado exceder el rango final (${nextP} > ${targetEnd}). Deteniendo.`);
                    break;
                }
                p = nextP;
                continue;
            }
            
            // Si llegamos aquí (modo secuencial sin rango fijo), preguntamos si desea continuar
            const result = await Swal.fire({
                title: `Página ${p} extraída`,
                text: `¿Deseas continuar con la transcripción de la página ${nextP}?`,
                icon: 'success',
                footer: pdfPageCount > 0 ? `<span class="text-muted">Página ${p} de ${pdfPageCount}</span>` : '<span class="text-warning">Total de páginas desconocido</span>',
                showCancelButton: true,
                confirmButtonText: 'Continuar a pág. ' + nextP,
                cancelButtonText: 'Terminar aquí',
                confirmButtonColor: '#ff9800',
                cancelButtonColor: '#294a60',
                background: '#1a1d21',
                color: '#fff'
            });

            if (result.isConfirmed) {
                p = nextP;
            } else {
                stopSequentialOCR = true;
            }
        }
        
        // Finalizar proceso: cerramos flags y actualizamos UI final
        stopSequentialOCR = true;
        currentRangeEnd = null;
        
        // Asegurar que la barra llegue al 100% al terminar
        if (ocrProgressBar) ocrProgressBar.style.width = '100%';
        if (ocrProgressText) ocrProgressText.innerHTML = '<i class="fa-solid fa-check-double me-2"></i>¡Proceso Completado! Finalizando...';
        
        displayOCRResult(extractedData);
        
        // Ocultar barra con un pequeño delay para que el usuario vea el 100%
        setTimeout(() => {
            if (ocrProgressContainer) ocrProgressContainer.classList.add('d-none');
            showNotification('✓ Extracción multi-página completada', 'success');
        }, 1500);
        
        if (extractedData && p > 1) {
            await performGlobalRefinement();
        }
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

    // --- NUEVO: Vincular imágenes OCR como material adjunto ---
    const btnVincularImagenOCR = document.getElementById('btn-vincular-imagen-ocr');
    if (btnVincularImagenOCR) {
        btnVincularImagenOCR.addEventListener('click', () => {
            if (extractedData && extractedData.imageData) {
                // NUEVO: Mostrar preview inmediato en el formulario principal
                // El preview ahora gestiona su propio input oculto para persistencia múltiple
                if (window.imageUploader && typeof window.imageUploader.addOCRPreview === 'function') {
                    window.imageUploader.addOCRPreview(extractedData.imageData, extractedData.ocrMap);

                    Swal.fire({
                        icon: 'success',
                        title: 'Imagen vinculada',
                        text: 'La imagen se ha añadido al material adjunto y se guardará con la noticia.',
                        timer: 2000,
                        showConfirmButton: false,
                        background: '#1a1d21',
                        color: '#fff'
                    });
                    btnVincularImagenOCR.innerHTML = '<i class="fa-solid fa-check me-1"></i> Imagen vinculada';
                    btnVincularImagenOCR.classList.remove('btn-outline-info');
                    btnVincularImagenOCR.classList.add('btn-info');
                    btnVincularImagenOCR.disabled = true;
                } else {
                    console.warn('[OCR] imageUploader no disponible para vinculación');
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

    // --- NUEVO: Preview Espacial (Indizado) ---
    // Usamos delegación de eventos para asegurar que funcione incluso si el DOM se refresca
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('#btn-preview-spatial');
        if (btn) {
            console.log('[OCR Preview] Click detectado en botón de indexación');
            const hasMap = extractedData && extractedData.ocrMap && extractedData.ocrMap.length > 0;
            
            if (extractedData && extractedData.imageData && hasMap) {
                console.log('[OCR Preview] Lanzando modal de preview espacial con', extractedData.ocrMap.length, 'cajas');
                showSpatialPreview(extractedData.imageData, extractedData.ocrMap);
            } else {
                console.warn('[OCR Preview] No hay datos suficientes para el preview:', {
                    hasData: !!extractedData,
                    hasImage: extractedData ? !!extractedData.imageData : false,
                    hasMap: hasMap
                });
                
                let warningText = 'El proceso de OCR no generó un mapa de coordenadas para este documento.';
                if (extractedData && (!extractedData.ocrMap || extractedData.ocrMap.length === 0)) {
                    warningText = 'Este motor de OCR (o el documento actual) no ha proporcionado coordenadas espaciales para el indizado.';
                }

                Swal.fire({
                    icon: 'warning',
                    title: 'Sin datos de indexación',
                    text: warningText,
                    footer: '<small class="text-muted">Prueba a procesar con "Tesseract (local)" o "Híbrido" para obtener coordenadas.</small>',
                    background: '#1a1d21',
                    color: '#fff'
                });
            }
        }
    });

    /**
     * Muestra un modal con el canvas renderizando los bounding boxes
     */
    function showSpatialPreview(base64Image, ocrMap) {
        Swal.fire({
            title: '<i class="fa-solid fa-eye me-2 text-warning"></i>Preview de Indizado Espacial',
            html: `
                <div id="spatial-preview-loader" class="p-5 text-center">
                    <i class="fas fa-circle-notch fa-spin fa-2x text-warning"></i>
                    <p class="mt-2 text-muted">Renderizando coordenadas sobre la imagen...</p>
                </div>
                <div id="spatial-preview-container" class="d-none" style="max-height: 70vh; overflow: auto; background: #000; border: 1px solid #444; border-radius: 4px;">
                    <canvas id="preview-canvas" style="max-width: 100%; height: auto; cursor: crosshair;"></canvas>
                </div>
                <div class="mt-3 text-start small text-muted p-2 bg-dark rounded border border-secondary" style="font-size: 0.75rem;">
                    <i class="fa-solid fa-info-circle me-1 text-info"></i> 
                    Los recuadros naranja translúcidos representan las <b>${ocrMap.length} zonas</b> detectadas e indizadas. 
                    En el Modo Lector, el sistema podrá resaltar estas palabras individualmente.
                </div>
            `,
            width: '90%',
            showCloseButton: true,
            showConfirmButton: false,
            background: '#1a1d21',
            color: '#fff',
            didOpen: () => {
                const img = new Image();
                img.onload = () => {
                    const previewCanvas = document.getElementById('preview-canvas');
                    if (!previewCanvas) return;
                    
                    const previewCtx = previewCanvas.getContext('2d');
                    
                    // Dimensiones reales de la imagen
                    previewCanvas.width = img.width;
                    previewCanvas.height = img.height;
                    
                    // Dibujar imagen de fondo
                    previewCtx.drawImage(img, 0, 0);
                    
                    // Configurar estilo de los recuadros de indexación
                    previewCtx.strokeStyle = '#ff9800'; // Naranja puro
                    previewCtx.fillStyle = 'rgba(255, 152, 0, 0.4)'; // Resaltado visible
                    previewCtx.lineWidth = Math.max(2, img.width / 1000);
                    
                    // Dibujar cada caja del mapa (normalizadas o relativas)
                    ocrMap.forEach(item => {
                        let x, y, w, h;
                        
                        // Formato BBOX (Gemini 0-1000: [ymin, xmin, ymax, xmax])
                        if (item.bbox && Array.isArray(item.bbox) && item.bbox.length === 4) {
                            const [ymin, xmin, ymax, xmax] = item.bbox;
                            x = (xmin / 1000) * img.width;
                            y = (ymin / 1000) * img.height;
                            w = ((xmax - xmin) / 1000) * img.width;
                            h = ((ymax - ymin) / 1000) * img.height;
                        } 
                        // Formato BOX_2D (Gemini alternate 0-1000)
                        else if (item.box_2d && Array.isArray(item.box_2d) && item.box_2d.length === 4) {
                            const [ymin, xmin, ymax, xmax] = item.box_2d;
                            x = (xmin / 1000) * img.width;
                            y = (ymin / 1000) * img.height;
                            w = ((xmax - xmin) / 1000) * img.width;
                            h = ((ymax - ymin) / 1000) * img.height;
                        }
                        // Formato Porcentual (OCR.space 0-100)
                        else if (item.x !== undefined && item.y !== undefined) {
                            x = (item.x / 100) * img.width;
                            y = (item.y / 100) * img.height;
                            w = (item.w / 100) * img.width;
                            h = (item.h / 100) * img.height;
                        }
                        
                        // Dibujar si se pudo calcular
                        if (x !== undefined && w > 0 && h > 0) {
                            previewCtx.fillRect(x, y, w, h);
                            previewCtx.strokeRect(x, y, w, h);
                        }
                    });
                    
                    // Mostrar contenedor y ocultar loader
                    document.getElementById('spatial-preview-loader').classList.add('d-none');
                    document.getElementById('spatial-preview-container').classList.remove('d-none');
                };
                img.src = base64Image.startsWith('data:') ? base64Image : `data:image/jpeg;base64,${base64Image}`;
            }
        });
    }

    // ============================================================
    // MOSTRAR RESULTADO
    // ============================================================

    function displayOCRResult(result) {
        console.log('[OCR Uploader] Mostrando resultado:', result);

        // Si ocrProgressContainer existe, lo mantenemos visible si stopSequentialOCR es false.
        // Si es true, NO lo ocultamos inmediatamente aquí, dejamos que el flujo principal (processSequentialOCR)
        // lo haga con su propio delay para mejor UX, A MENOS que sea un OCR de una sola página.
        if (ocrProgressContainer) {
             if (!stopSequentialOCR) {
                 ocrProgressContainer.classList.remove('d-none');
             }
        }

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
            'numero': 'Número',
            'volumen': 'Volumen',
            'edicion': 'Edición',
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

        // NOTIFICACIÓN DE ÉXITO PREMIUM
        const hasMap = (result.ocrMap && result.ocrMap.length > 0);
        const mapIcon = hasMap ? 'fa-location-dot' : 'fa-font';
        const mapText = hasMap ? 'con Indizado Espacial' : 'completado';

        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'success',
                title: `<span style="color: #ff9800; font-family: 'Outfit', sans-serif;">OCR ${mapText}</span>`,
                html: `
                    <div class="text-start small">
                        <p class="mb-2"><i class="fa-solid ${mapIcon} me-2 text-accent"></i>Se han extraído <b>${result.text.split(/\s+/).length}</b> palabras correctamente.</p>
                        <div class="p-2 bg-dark rounded border border-success" style="background: rgba(40,167,69,0.1) !important;">
                            <i class="fa-solid fa-link me-1 text-success"></i> 
                            <b>Éxito:</b> La imagen procesada se ha vinculado automáticamente para el Lector.
                        </div>
                    </div>
                `,
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 6000,
                timerProgressBar: true,
                background: '#1a1d21',
                color: '#fff',
                didOpen: (toast) => {
                    toast.addEventListener('mouseenter', Swal.stopTimer)
                    toast.addEventListener('mouseleave', Swal.resumeTimer)
                }
            });
        }
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

            // RE-VERIFICACIÓN TRAS AWAIT: El usuario pudo haber cancelado durante la subida
            if (!extractedData) {
                console.warn('[IA] Operación abortada: Los datos de OCR ya no existen.');
                return;
            }

            let data;
            try {
                data = await response.json();
            } catch (jsonError) {
                console.error('[IA] Error al parsear JSON:', jsonError);
                throw new Error('El servidor devolvió una respuesta inválida (posible error 500). Por favor, intenta de nuevo o con un fragmento más pequeño.');
            }

            if (!response.ok) {
                throw new Error(data.error || data.mensaje || 'Error al procesar con IA');
            }

            if (!data.success) {
                throw new Error(data.error || 'Error desconocido');
            }

            console.log('[IA] ✓ Metadatos corregidos:', data.metadatos);

            // RE-VERIFICACIÓN TRAS LOGS/PROCESAMIENTO: Seguridad extra
            if (!extractedData) return;

            // Actualizar metadatos con los corregidos por IA (Fusión total)
            const correctedMetadata = data.metadatos || {};
            const textoOriginal = extractedData.text; 

            extractedData.metadata = {
                ...extractedData.metadata,
                ...correctedMetadata
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
                    <i class="fa-solid fa-wand-magic-sparkles me-1"></i> Revisión por IA
                `;
            }
        }
    }

    // Event Listener manual (por si el usuario quiere reintentar)
    if (btnMejorarIA) {
        btnMejorarIA.addEventListener('click', improveWithAI);
    }

    // Botón Descartar: Limpiar todo el estado de OCR
    if (btnDiscardOCR) {
        btnDiscardOCR.addEventListener('click', () => {
            resetOCRUI();
            console.log('[OCR] Datos descartados por el usuario');
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'info',
                    title: 'OCR Descartado',
                    text: 'Se han limpiado los datos extraídos y se ha reseteado el cargador.',
                    toast: true,
                    position: 'top-end',
                    showConfirmButton: false,
                    timer: 3000,
                    background: '#1a1d21',
                    color: '#fff'
                });
            }
        });
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

            // --- NUEVO: Aplicar Spatial Index (ocr_map) ---
            const inputOcrMap = document.getElementById('input_ocr_map');
            if (inputOcrMap && extractedData.ocrMap) {
                console.log('[OCR] Aplicando Spatial Index (ocr_map) al formulario...', extractedData.ocrMap.length, 'palabras');
                inputOcrMap.value = JSON.stringify(extractedData.ocrMap);
            }

            // Mapeo de campos OCR → formulario
            const fieldMap = {
                'titulo': 'titulo',
                'publicacion': 'publicacion',
                'fecha_original': 'fecha_original',
                'anio': 'anio',
                'ciudad': 'ciudad',
                'numero': 'numero',
                'volumen': 'volumen',
                'edicion': 'edicion',
                'pagina_inicio': 'pagina_inicio',
                'pagina_fin': 'pagina_fin',
                'lugar_publicacion': 'lugar_publicacion',
                'editorial': 'editorial'
            };

            let appliedCount = 0;
            for (const [ocrField, formField] of Object.entries(fieldMap)) {
                if (metadata[ocrField]) {
                    const input = document.querySelector(`[name="${formField}"]`);
                    if (input) {
                        input.value = metadata[ocrField];
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        appliedCount++;
                    }
                }
            }

            // Lógica para AUTORES (HesiOX usa filas dinámicas)
            if (metadata.autor) {
                const autorFull = metadata.autor.trim();
                if (typeof window.addAutorRow === 'function') {
                    let nombre = ""; let apellido = "";
                    const parts = autorFull.split(' ');
                    if (parts.length > 1) {
                        apellido = parts.pop();
                        nombre = parts.join(' ');
                    } else { nombre = autorFull; }
                    window.addAutorRow(nombre, apellido, 'firmado', false);
                    appliedCount++;
                }
            }

            // Aplicar también el contenido principal (CON DEDUPLICACIÓN)
            autoAplicarTextoCompleto();

            // Vincular imagen y OCR map
            vincularImagenOCRAutomaticamente();

            // Usar la función existente en el proyecto
            showNotification(`Se han aplicado ${appliedCount} campos y el contenido de la noticia.`, 'success');
        });
    }

    // ============================================================

    function vincularImagenOCRAutomaticamente(specificImageData = null, specificOcrMap = null) {
        const imageData = specificImageData || (extractedData ? extractedData.imageData : null);
        const mapData = specificOcrMap || (extractedData ? extractedData.ocrMap : null);
        
        if (imageData) {
            // Mostrar preview inmediato en el formulario principal si el uploader está disponible
            // El preview ahora contiene el input oculto para soportar múltiples imágenes
            if (window.imageUploader && typeof window.imageUploader.addOCRPreview === 'function') {
                window.imageUploader.addOCRPreview(imageData, mapData);
                console.log('[OCR] Imagen vinculada automáticamente al uploader general');
            }

            // Actualizar estado del botón de vinculación si existe
            const btnVincular = document.getElementById('btn-vincular-imagen-ocr');
            if (btnVincular) {
                btnVincular.innerHTML = '<i class="fa-solid fa-check me-1"></i> Imagen vinculada (Auto)';
                btnVincular.classList.remove('btn-outline-info');
                btnVincular.classList.add('btn-info');
                btnVincular.disabled = true;
            }
        }
    }

    // ============================================================
    // AUTO-APLICAR TEXTO AL FORMULARIO (MODO RANGO)
    // ============================================================

    function autoAplicarTextoCompleto() {
        if (!extractedData || !extractedData.text) return;
        
        console.log("[OCR] Aplicando texto al formulario...");

        // Función interna para limpiar etiquetas de metadatos del OCR
        const cleanText = (txt) => {
            if (!txt) return "";
            // Eliminamos las etiquetas y ruidos constantes detectados en Rodrigo Jiménez de Rada
            return txt.replace(/-*\s*\[(PÁGINA|COLUMNA|GRABADO|CABECERA|PAGE|COLUMN|HEADER|FOLL|FOLLE|PIE|PIE DE PÁGINA|DATOS CABECERA|BORRADOR BASE)[^\]]*\]\s*-*/gi, "")
                      .replace(/\d+\s+\d+\s+Rodrigo\s+Jiménez\s+de\s+Rada/gi, "")
                      .replace(/Rodrigo\s+Jiménez\s+de\s+Rada/gi, "")
                      .replace(/\s\d+\s(?=\s[a-zñ])/gi, " ") // Números aislados antes de palabra (contadores)
                      .replace(/HF\s+o\s*!|o\s+o\s*!/gi, "")
                      .trim();
        };

        let textToApply = cleanText(extractedData.text);
        
        // --- DEDUPLICACIÓN AGRESIVA (Anti-Hybrid) ---
        // 1. Detección de bloques híbridos marcados por el motor
        if (textToApply.includes('[BORRADOR BASE]') && textToApply.includes('[DATOS CABECERA]')) {
             console.log("[OCR] Detectado formato híbrido duplicado. Limpiando...");
             const parts = textToApply.split(/\[BORRADOR BASE\]|\[DATOS CABECERA\]/);
             if (parts.length >= 3) {
                 const base = parts[1].trim();
                 const header = parts[2].trim();
                 
                 // Similitud normalizada (sin números)
                 const normBase = base.toLowerCase().replace(/[^a-zñ]/g, '');
                 const normHeader = header.toLowerCase().replace(/[^a-zñ]/g, '');
                 
                 if (normBase.includes(normHeader) || normHeader.includes(normBase) || Math.abs(normBase.length - normHeader.length) < 50) {
                     textToApply = parts[0] + "\n" + (base.length >= header.length ? base : header);
                 }
             }
        }

        // --- EVITAR DUPLICIDAD GLOBAL Y ECOS DE LÍNEA (Normalización Extrema) ---
        if (textToApply.length > 150) {
            const blocks = textToApply.split(/\n\s*\n/);
            const uniqueBlocks = [];
            let seenNormalized = "";
            let duplicateCount = 0;

            for (let block of blocks) {
                // Normalización extrema: solo letras minúsculas (sin números ni puntuación)
                const normalized = block.toLowerCase().replace(/[^a-zñ]/g, '');
                
                if (normalized.length < 10) {
                    uniqueBlocks.push(block);
                    continue;
                }

                // A. Check exacto en el historial acumulado
                if (seenNormalized.includes(normalized)) {
                    duplicateCount++;
                    continue;
                }

                // B. Check por fragmentos (si el 60% del bloque ya existe en piezas de 20 letras)
                let pieceMatches = 0;
                let pieces = [];
                for (let i = 0; i < normalized.length; i += 20) {
                    const piece = normalized.substring(i, i + 20);
                    if (piece.length >= 18) {
                        pieces.push(piece);
                        if (seenNormalized.includes(piece)) pieceMatches++;
                    }
                }

                if (pieces.length > 0 && (pieceMatches / pieces.length) >= 0.6) {
                    duplicateCount++;
                    continue;
                }

                uniqueBlocks.push(block);
                seenNormalized += " [SEP] " + normalized;
            }

            if (duplicateCount > 0) {
                console.warn(`[OCR] Detectados ${duplicateCount} bloques duplicados. Limpiando...`);
                textToApply = uniqueBlocks.join('\n\n');
            }
        }

        const destOriginal = document.getElementById('ocr-dest-original');
        const destDiplomatica = document.getElementById('ocr-dest-diplomatica');
        const destCritica = document.getElementById('ocr-dest-critica');
        
        const esIdiomaOriginal = destOriginal && destOriginal.checked;
        const esDiplomatica = destDiplomatica && destDiplomatica.checked;
        const esCritica = destCritica && destCritica.checked;

        // Cambiar pestañas automáticamente
        if (esIdiomaOriginal) {
            const tab = document.getElementById('original-tab');
            if (tab) new bootstrap.Tab(tab).show();
        } else if (esDiplomatica) {
            const tab = document.getElementById('diplomatica-tab');
            if (tab) new bootstrap.Tab(tab).show();
        } else if (esCritica) {
            const tab = document.getElementById('critica-tab');
            if (tab) new bootstrap.Tab(tab).show();
        } else {
            const tab = document.getElementById('traduccion-tab');
            if (tab) new bootstrap.Tab(tab).show();
        }

        let aplicado = false;
        let targetField = 'contenido';
        if (esIdiomaOriginal) targetField = 'texto_original';
        if (esDiplomatica) targetField = 'contenido_diplomatico';
        if (esCritica) targetField = 'contenido_critico';
        
        // 1. Intentar con Quill
        if (window.quillEditors && window.quillEditors[targetField]) {
            window.quillEditors[targetField].setText(''); // Limpiar antes
            window.quillEditors[targetField].setText(textToApply);
            aplicado = true;
        }

        // 2. Intentar con TinyMCE
        if (!aplicado && typeof tinymce !== 'undefined') {
            const editor = tinymce.get(targetField);
            if (editor) {
                editor.setContent(textToApply.replace(/\n/g, '<br>'));
                aplicado = true;
            }
        }

        // 3. Fallback a Textarea
        if (!aplicado) {
            const textarea = document.querySelector(`textarea[name="${targetField}"]`);
            if (textarea) {
                textarea.value = textToApply;
                textarea.dispatchEvent(new Event('change', { bubbles: true }));
                aplicado = true;
            }
        }

        if (aplicado) {
            console.log(`[OCR] Texto aplicado con éxito a ${targetField}`);
            // Scroll suave al editor
            const el = document.getElementsByName(targetField)[0] || document.getElementById(targetField);
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    // ============================================================
    // RESETEAR UI
    // ============================================================

    function resetOCRUI() {
        currentFile = null;
        extractedData = null;
        // Resetear botones
        const btnVincular = document.getElementById('btn-vincular-imagen-ocr');
        if (btnVincular) {
            btnVincular.innerHTML = '<i class="fa-solid fa-link me-1"></i> Vincular imagen procesada';
            btnVincular.classList.add('btn-outline-info');
            btnVincular.classList.remove('btn-info');
            btnVincular.disabled = false;
        }

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
