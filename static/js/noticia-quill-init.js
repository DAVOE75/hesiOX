/**
 * =========================================================
 * 🖋️ INITIALIZATION SCRIPT: QUILL EDITOR FOR NEWS/TEXTS
 * =========================================================
 * Maneja la inicialización de los editores enriquecidos,
 * la sincronización con el backend y la integración con IA.
 */

window.quillEditors = {};

document.addEventListener('DOMContentLoaded', function() {
    console.log('[Quill News] Inicializando editores...');

    // Opciones de la barra de herramientas (ql-toolbar)
    const toolbarOptions = [
        [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
        ['bold', 'italic', 'underline', 'strike'],        // negrita, cursiva, subrayado, tachado
        ['blockquote', 'code-block'],
        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
        [{ 'script': 'sub'}, { 'script': 'super' }],      // subíndice/superíndice
        [{ 'indent': '-1'}, { 'indent': '+1' }],          // sangría
        [{ 'direction': 'rtl' }],                         // dirección del texto
        [{ 'color': [] }, { 'background': [] }],          // color y fondo
        [{ 'align': [] }],
        ['link', 'image'],                                // enlaces e imágenes
        ['clean']                                         // eliminar formato
    ];

    /**
     * Inicializa una instancia de Quill
     * @param {string} editorId - ID del contenedor div del editor
     * @param {string} textareaId - ID del textarea oculto para sync
     * @param {string} toolbarId - ID del contenedor de la toolbar (si aplica)
     * @param {string} placeholder - Texto de ayuda
     */
    function setupEditor(editorId, textareaId, toolbarId, placeholder) {
        const editorContainer = document.getElementById(editorId);
        const textarea = document.getElementById(textareaId);

        if (!editorContainer || !textarea) {
            console.warn(`[Quill News] No se encontró el editor o textarea para: ${editorId}`);
            return null;
        }

        const quill = new Quill(`#${editorId}`, {
            modules: {
                toolbar: toolbarOptions
            },
            placeholder: placeholder,
            theme: 'snow'
        });

        // Carga inicial de contenido respetando saltos de línea (Compatibilidad con datos viejos)
        if (textarea.value) {
            const val = textarea.value.trim();
            if (val.startsWith('<p') || val.startsWith('<div') || val.includes('<br')) {
                // Es HTML, cargar directamente
                quill.root.innerHTML = val;
            } else {
                // Es texto plano (viejo), convertir saltos a párrafos para Quill
                const html = val.split('\n').map(line => line.trim() ? `<p>${line}</p>` : '<p><br></p>').join('');
                quill.root.innerHTML = html;
            }
        }

        // Sincronización Quill -> Textarea (cada vez que cambia el texto)
        quill.on('text-change', function() {
            textarea.value = quill.root.innerHTML;
            // Disparar evento input para que otros scripts (como CharacterCounter) se enteren
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        });

        console.log(`[Quill News] ✓ Editor '${editorId}' inicializado.`);
        return quill;
    }

    // Inicializar los dos editores principales
    window.quillEditors.contenido = setupEditor(
        'contenido-editor', 
        'contenido', 
        'toolbar-contenido', 
        'Escribe aquí la versión en español o traducción...'
    );

    window.quillEditors.texto_original = setupEditor(
        'texto_original_editor', 
        'texto_original', 
        'toolbar-texto_original', 
        'Pega aquí el texto original (paleográfico/idioma nativo)...'
    );

    window.quillEditors.contenido_diplomatico = setupEditor(
        'contenido_diplomatico_editor', 
        'contenido_diplomatico', 
        'toolbar-contenido_diplomatico', 
        'Transcripción diplomática (literal, respetando abreviaturas y grafías)...'
    );

    window.quillEditors.contenido_critico = setupEditor(
        'contenido_critico_editor', 
        'contenido_critico', 
        'toolbar-contenido_critico', 
        'Edición crítica (anotada, modernizada, con aparato crítico)...'
    );

    // =========================================================
    // 🛠️ PARCHEO DE BOTONES EXISTENTES (IA / LIMPIEZA)
    // =========================================================

    /**
     * Re-vincula la lógica de los botones para que actúen sobre Quill
     * en lugar de sobre el textarea plano.
     */
    function patchActionButtons() {
        // IDs de botones y sus editores correspondientes
        const mappings = [
            { btn: 'btnLimpiarManual', editorKey: 'contenido' },
            { btn: 'btnLimpiarManual-orig', editorKey: 'texto_original' },
            { btn: 'btn-correct-txt-gemini', editorKey: 'contenido' },
            { btn: 'btn-correct-txt-gemini-orig', editorKey: 'texto_original' }
        ];

        mappings.forEach(map => {
            const btn = document.getElementById(map.btn);
            const quill = window.quillEditors[map.editorKey];

            if (btn && quill) {
                // Clonar el botón para eliminar listeners anteriores
                const newBtn = btn.cloneNode(true);
                btn.parentNode.replaceChild(newBtn, btn);

                newBtn.addEventListener('click', async function() {
                    // Acción dependiendo del botón
                    if (map.btn.includes('Limpiar')) {
                        await runCleaningAction(quill, map.editorKey);
                    } else if (map.btn.includes('correct')) {
                        await runAIGeminiAction(quill, map.editorKey, newBtn);
                    }
                });
            }
        });
    }

    /**
     * Acción de Limpieza (Spacy)
     */
    async function runCleaningAction(quill, fieldId) {
        const text = quill.getText().trim();
        if (text.length < 5) {
            alert('Texto insuficiente para limpiar.');
            return;
        }

        const btn = document.getElementById(fieldId === 'contenido' ? 'btnLimpiarManual' : 'btnLimpiarManual-orig');
        const originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Limpiando...';

        try {
            const response = await fetch('/api/spacy/clean2', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                },
                body: JSON.stringify({ text: text })
            });

            if (response.ok) {
                const data = await response.json();
                const cleanText = data.clean_text || '';
                // Convertir saltos de línea en párrafos para mantener estructura en Quill
                const formattedContent = cleanText.split('\n').map(line => line.trim() ? `<p>${line}</p>` : '<p><br></p>').join('');
                quill.root.innerHTML = formattedContent;
            } else {
                throw new Error('Error en el servidor');
            }
        } catch (err) {
            console.error('Error limpieza:', err);
            alert('Error al limpiar el texto.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }
    }

    /**
     * Acción de IA Gemini
     */
    async function runAIGeminiAction(quill, fieldId, btn) {
        const text = quill.getText().trim();
        if (text.length < 10) {
            alert('Texto insuficiente para revisión IA.');
            return;
        }

        const originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-brain fa-spin me-1"></i> Corrigiendo...';

        // --- LÓGICA DE BARRA DE PROGRESO SIMULADA ---
        const progContainer = document.getElementById('ai-progress-container');
        const progBar = document.getElementById('ai-progress-bar');
        const progText = document.getElementById('ai-progress-text');
        
        let progressInterval;
        if (progContainer && progBar) {
            progContainer.classList.remove('d-none');
            progBar.style.width = '0%';
            progText.textContent = 'Iniciando conexión con motor de IA...';
            
            let width = 0;
            progressInterval = setInterval(() => {
                if (width < 92) {
                    // Crecimiento asintótico: más lento a medida que se acerca al final
                    const increment = (95 - width) / 15;
                    width += increment;
                    progBar.style.width = width + '%';
                    
                    if (width > 20 && width < 40) progText.textContent = 'Analizando estructura del documento...';
                    if (width > 40 && width < 70) progText.textContent = 'Corrigiendo errores de OCR y paleografía...';
                    if (width > 70) progText.textContent = 'Finalizando reconstrucción de metadatos...';
                }
            }, 500);
        }

        try {
            const selPotencia = document.getElementById('sel-potencia-ocr');
            const potencia = selPotencia ? selPotencia.value : 'gemini:flash';

            const response = await fetch('/api/gemini/correct', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                },
                body: JSON.stringify({
                    text: text,
                    potencia: potencia
                })
            });

            const data = await response.json();
            if (data.clean_text || data.corrected_text) {
                const corrected = data.clean_text || data.corrected_text;
                // Convertir saltos de línea en párrafos
                const formattedContent = corrected.split('\n').map(line => line.trim() ? `<p>${line}</p>` : '<p><br></p>').join('');
                quill.root.innerHTML = formattedContent;
                const provider = potencia.split(':')[0].toUpperCase();
                // Notificación no intrusiva (Toast o similar si existiera, usamos alert por ahora)
                console.log(`[Quill News] ✓ Revisión IA (${provider}) completada.`);
            } else {
                throw new Error(data.error || 'Error desconocido');
            }
        } catch (error) {
            console.error('Error IA:', error);
            alert('Error en revisión IA: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHTML;

            // --- FINALIZAR BARRA DE PROGRESO ---
            if (progressInterval) clearInterval(progressInterval);
            if (progBar) {
                progBar.style.width = '100%';
                if (progText) progText.textContent = '¡Corrección completada!';
                setTimeout(() => {
                    if (progContainer) progContainer.classList.add('d-none');
                    progBar.style.width = '0%';
                }, 1500);
            }
        }
    }

    // Ejecutar parcheo de botones
    patchActionButtons();

    // =========================================================
    // 🔍 INTEGRACIÓN CON OCR (COMPATIBILIDAD)
    // =========================================================
    
    /**
     * Sobrescribimos el método de aplicación de texto si el script OCR ya cargó
     * O escuchamos cambios en los textareas si se actualizan por fallback
     */
    window.updateQuillFromOCR = function(fieldId, text) {
        const quill = window.quillEditors[fieldId];
        if (quill) {
            console.log(`[Quill News] Inyectando texto desde OCR a: ${fieldId}`);
            quill.root.innerHTML = text.replace(/\n/g, '<br>');
        }
    };

    /**
     * Recupera una versión histórica de la noticia
     */
    window.cargarVersion = function(versionId) {
        if (!confirm('¿Estás seguro de que deseas recuperar esta versión? Los cambios actuales no guardados se perderán.')) return;
        
        fetch(`/api/versiones/${versionId}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    if (window.quillEditors.contenido) window.quillEditors.contenido.root.innerHTML = data.version.contenido || '';
                    if (window.quillEditors.contenido_diplomatico) window.quillEditors.contenido_diplomatico.root.innerHTML = data.version.contenido_diplomatico || '';
                    if (window.quillEditors.contenido_critico) window.quillEditors.contenido_critico.root.innerHTML = data.version.contenido_critico || '';
                    
                    // Notificar al usuario
                    Swal.fire({
                        icon: 'success',
                        title: 'Versión Recuperada',
                        text: 'Se han cargado los contenidos de la versión seleccionada.',
                        timer: 2000,
                        showConfirmButton: false,
                        toast: true,
                        position: 'top-end'
                    });
                    
                    // Cambiar a la pestaña de contenido normalizado
                    document.getElementById('traduccion-tab').click();
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(err => console.error('Error al recuperar versión:', err));
    };
});
