/**
 * =========================================================
 * 🖋️ INITIALIZATION SCRIPT: QUILL EDITOR FOR NEWS/TEXTS
 * =========================================================
 * Maneja la inicialización de los editores enriquecidos,
 * la sincronización con el backend y la integración con IA.
 */

window.quillEditors = {};

class QuillFindReplace {
    constructor(quill) {
        this.quill = quill;
        this.matches = [];
        this.currentIndex = -1;
        this.findText = '';
        this.replaceText = '';
        this.caseSensitive = false;
        this.wholeWord = false;
        this.useRegex = false;
        
        this.createWidget();
    }
    
    createWidget() {
        const container = this.quill.container;
        const widget = document.createElement('div');
        widget.className = 'qfr-widget d-none';
        widget.innerHTML = `
            <div class="qfr-row-1">
                <div class="qfr-input-group">
                    <input type="text" class="qfr-find-input" placeholder="Buscar..." />
                    <div class="qfr-options">
                        <button type="button" class="qfr-opt-btn qfr-case-btn" title="Coincidir mayúsculas/minúsculas (Aa)">Aa</button>
                        <button type="button" class="qfr-opt-btn qfr-word-btn" title="Palabra completa (ab)">ab</button>
                        <button type="button" class="qfr-opt-btn qfr-regex-btn" title="Usar expresión regular (.*)">.*</button>
                    </div>
                </div>
                <span class="qfr-status">Sin resultados</span>
                <button type="button" class="qfr-nav-btn qfr-prev-btn" title="Anterior"><i class="fa-solid fa-arrow-up"></i></button>
                <button type="button" class="qfr-nav-btn qfr-next-btn" title="Siguiente"><i class="fa-solid fa-arrow-down"></i></button>
                <button type="button" class="qfr-close-btn" title="Cerrar"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="qfr-row-2">
                <input type="text" class="qfr-replace-input" placeholder="Reemplazar con..." />
                <button type="button" class="qfr-action-btn qfr-replace-btn">Reemplazar</button>
                <button type="button" class="qfr-action-btn qfr-replace-all-btn">Todo</button>
            </div>
        `;
        
        container.style.position = 'relative';
        container.appendChild(widget);
        this.widget = widget;
        this.bindEvents();
    }
    
    bindEvents() {
        const findInput = this.widget.querySelector('.qfr-find-input');
        const replaceInput = this.widget.querySelector('.qfr-replace-input');
        
        findInput.addEventListener('input', () => {
            this.findText = findInput.value;
            this.search();
        });

        findInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.next();
            }
        });
        
        replaceInput.addEventListener('input', () => {
            this.replaceText = replaceInput.value;
        });
        
        this.widget.querySelector('.qfr-case-btn').addEventListener('click', (e) => {
            e.preventDefault();
            this.caseSensitive = !this.caseSensitive;
            e.target.classList.toggle('active', this.caseSensitive);
            this.search();
        });
        
        this.widget.querySelector('.qfr-word-btn').addEventListener('click', (e) => {
            e.preventDefault();
            this.wholeWord = !this.wholeWord;
            e.target.classList.toggle('active', this.wholeWord);
            this.search();
        });
        
        this.widget.querySelector('.qfr-regex-btn').addEventListener('click', (e) => {
            e.preventDefault();
            this.useRegex = !this.useRegex;
            e.target.classList.toggle('active', this.useRegex);
            this.search();
        });
        
        this.widget.querySelector('.qfr-next-btn').addEventListener('click', (e) => { e.preventDefault(); this.next(); });
        this.widget.querySelector('.qfr-prev-btn').addEventListener('click', (e) => { e.preventDefault(); this.prev(); });
        this.widget.querySelector('.qfr-replace-btn').addEventListener('click', (e) => { e.preventDefault(); this.replace(); });
        this.widget.querySelector('.qfr-replace-all-btn').addEventListener('click', (e) => { e.preventDefault(); this.replaceAll(); });
        
        this.widget.querySelector('.qfr-close-btn').addEventListener('click', (e) => { e.preventDefault(); this.hide(); });
        
        this.widget.addEventListener('mousedown', (e) => {
            e.stopPropagation();
        });
    }
    
    show() {
        this.widget.classList.remove('d-none');
        const findInput = this.widget.querySelector('.qfr-find-input');
        findInput.focus();
        this.search();
    }
    
    hide() {
        this.widget.classList.add('d-none');
    }
    
    toggle() {
        if (this.widget.classList.contains('d-none')) {
            this.show();
        } else {
            this.hide();
        }
    }
    
    search() {
        this.matches = [];
        this.currentIndex = -1;
        
        if (!this.findText) {
            this.updateStatus();
            return;
        }
        
        const text = this.quill.getText();
        let regex;
        let flags = 'g';
        if (!this.caseSensitive) flags += 'i';
        
        try {
            if (this.useRegex) {
                regex = new RegExp(this.findText, flags);
            } else {
                let escaped = this.findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                if (this.wholeWord) {
                    escaped = '\\b' + escaped + '\\b';
                }
                regex = new RegExp(escaped, flags);
            }
            
            let match;
            while ((match = regex.exec(text)) !== null) {
                if (match[0].length === 0) {
                    regex.lastIndex++;
                    continue;
                }
                this.matches.push({
                    index: match.index,
                    length: match[0].length
                });
            }
        } catch (e) {
            // Error en regex
        }
        
        if (this.matches.length > 0) {
            this.currentIndex = 0;
        }
        
        this.updateStatus();
    }
    
    scrollToCurrent() {
        if (this.currentIndex >= 0 && this.currentIndex < this.matches.length) {
            const match = this.matches[this.currentIndex];
            this.quill.setSelection(match.index, match.length);
        }
    }
    
    next() {
        if (this.matches.length === 0) return;
        this.currentIndex = (this.currentIndex + 1) % this.matches.length;
        this.scrollToCurrent();
        this.updateStatus();
    }
    
    prev() {
        if (this.matches.length === 0) return;
        this.currentIndex = (this.currentIndex - 1 + this.matches.length) % this.matches.length;
        this.scrollToCurrent();
        this.updateStatus();
    }
    
    replace() {
        if (this.currentIndex < 0 || this.currentIndex >= this.matches.length) return;
        const match = this.matches[this.currentIndex];
        
        this.quill.deleteText(match.index, match.length);
        this.quill.insertText(match.index, this.replaceText);
        
        this.search();
    }
    
    replaceAll() {
        if (this.matches.length === 0) return;
        
        for (let i = this.matches.length - 1; i >= 0; i--) {
            const match = this.matches[i];
            this.quill.deleteText(match.index, match.length);
            this.quill.insertText(match.index, this.replaceText);
        }
        
        this.search();
    }
    
    updateStatus() {
        const statusEl = this.widget.querySelector('.qfr-status');
        if (this.matches.length === 0) {
            statusEl.textContent = 'Sin resultados';
            statusEl.className = 'qfr-status empty';
        } else {
            statusEl.textContent = `${this.currentIndex + 1} de ${this.matches.length}`;
            statusEl.className = 'qfr-status found';
        }
    }
}

// Inyección de estilos CSS para el widget
const style = document.createElement('style');
style.innerHTML = `
    .qfr-widget {
        position: absolute;
        top: 10px;
        right: 10px;
        z-index: 1000;
        background: rgba(18, 18, 18, 0.95);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        color: #e0e0e0;
        width: 360px;
    }
    .qfr-row-1, .qfr-row-2 {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .qfr-row-2 {
        margin-top: 8px;
    }
    .qfr-input-group {
        display: flex;
        align-items: center;
        background: rgba(0, 0, 0, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 4px;
        padding-right: 4px;
        flex-grow: 1;
    }
    .qfr-find-input, .qfr-replace-input {
        background: transparent;
        border: none;
        color: #fff;
        padding: 4px 8px;
        font-size: 0.8rem;
        flex-grow: 1;
        outline: none;
    }
    .qfr-options {
        display: flex;
        gap: 2px;
    }
    .qfr-opt-btn {
        background: transparent;
        border: none;
        color: rgba(255,255,255,0.4);
        font-size: 0.75rem;
        padding: 2px 4px;
        border-radius: 2px;
        cursor: pointer;
        font-family: monospace;
    }
    .qfr-opt-btn:hover {
        color: rgba(255,255,255,0.8);
        background: rgba(255,255,255,0.05);
    }
    .qfr-opt-btn.active {
        color: var(--bs-primary, #ff9800);
        background: rgba(255, 152, 0, 0.15);
    }
    .qfr-status {
        font-size: 0.5rem;
        white-space: nowrap;
        min-width: 40px;
        text-align: center;
    }
    .qfr-status.empty {
        color: var(--bs-primary, #ff6b6b);
    }
    .qfr-status.found {
        color: var(--bs-primary, #ff9800);
    }
    .qfr-nav-btn, .qfr-close-btn {
        background: transparent;
        border: none;
        color: rgba(255,255,255,0.6);
        cursor: pointer;
        padding: 4px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .qfr-nav-btn:hover, .qfr-close-btn:hover {
        color: #fff;
        background: rgba(255,255,255,0.1);
    }
    .qfr-action-btn {
        background: rgba(255, 152, 0, 0.15);
        border: 1px solid var(--bs-primary, rgba(255, 152, 0, 0.3));
        color: var(--bs-primary, #ff9800);
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        cursor: pointer;
        white-space: nowrap;
    }
    .qfr-action-btn:hover {
        background: rgba(255, 152, 0, 0.3);
        color: #fff;
    }
    .ql-search-btn i {
        color: var(--bs-primary, #ff9800);
    }
    .ql-editor ::selection {
        background-color: rgba(255, 152, 0, 0.4) !important;
    }
    .ql-editor span, .ql-editor p {
        background-color: transparent !important;
    }

    /* Estilos para Modo Claro (Blanco y Azul) */
    [data-theme="light"] .ql-editor ::selection {
        background-color: rgba(41, 74, 96, 0.2) !important;
    }
    [data-theme="light"] .qfr-widget {
        background: rgba(255, 255, 255, 0.95);
        border: 1px solid rgba(41, 74, 96, 0.2);
        box-shadow: 0 10px 30px rgba(41, 74, 96, 0.15);
        color: #294A60;
    }
    [data-theme="light"] .qfr-input-group {
        background: rgba(41, 74, 96, 0.05);
        border: 1px solid rgba(41, 74, 96, 0.2);
    }
    [data-theme="light"] .qfr-find-input, 
    [data-theme="light"] .qfr-replace-input {
        color: #294A60;
    }
    [data-theme="light"] .qfr-opt-btn {
        color: rgba(41, 74, 96, 0.5);
    }
    [data-theme="light"] .qfr-opt-btn:hover {
        color: #294A60;
        background: rgba(41, 74, 96, 0.08);
    }
    [data-theme="light"] .qfr-opt-btn.active {
        color: #294A60;
        background: rgba(41, 74, 96, 0.15);
    }
    [data-theme="light"] .qfr-status.empty {
        color: #d9534f;
    }
    [data-theme="light"] .qfr-status.found {
        color: #294A60;
    }
    [data-theme="light"] .qfr-nav-btn, 
    [data-theme="light"] .qfr-close-btn {
        color: rgba(41, 74, 96, 0.6);
    }
    [data-theme="light"] .qfr-nav-btn:hover, 
    [data-theme="light"] .qfr-close-btn:hover {
        color: #294A60;
        background: rgba(41, 74, 96, 0.1);
    }
    [data-theme="light"] .qfr-action-btn {
        background: rgba(41, 74, 96, 0.1);
        border: 1px solid rgba(41, 74, 96, 0.3);
        color: #294A60;
    }
    [data-theme="light"] .qfr-action-btn:hover {
        background: rgba(41, 74, 96, 0.2);
        color: #294A60;
    }
    [data-theme="light"] .ql-search-btn i {
        color: #294A60;
    }
`;
document.head.appendChild(style);

document.addEventListener('DOMContentLoaded', function() {
    console.log('[Quill News] Inicializando editores...');

    const toolbarOptions = [
        [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
        ['bold', 'italic', 'underline', 'strike'],
        ['blockquote', 'code-block'],
        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
        [{ 'script': 'sub'}, { 'script': 'super' }],
        [{ 'indent': '-1'}, { 'indent': '+1' }],
        [{ 'direction': 'rtl' }],
        [{ 'color': [] }, { 'background': [] }],
        [{ 'align': [] }],
        ['link', 'image'],
        ['clean']
    ];

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

        if (textarea.value) {
            const val = textarea.value.trim();
            if (val.startsWith('<p') || val.startsWith('<div') || val.includes('<br')) {
                quill.root.innerHTML = val;
            } else {
                const html = val.split('\n').map(line => line.trim() ? `<p>${line}</p>` : '<p><br></p>').join('');
                quill.root.innerHTML = html;
            }
        }

        quill.on('text-change', function() {
            textarea.value = quill.root.innerHTML;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        });

        const qfr = new QuillFindReplace(quill);
        
        setTimeout(() => {
            const toolbar = quill.getModule('toolbar');
            if (toolbar && toolbar.container) {
                const searchBtn = document.createElement('button');
                searchBtn.type = 'button';
                searchBtn.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i>';
                searchBtn.title = "Buscar y Reemplazar";
                searchBtn.classList.add('ql-search-btn');
                searchBtn.style.float = 'right';
                searchBtn.style.padding = '3px 8px';
                searchBtn.style.marginTop = '2px';
                searchBtn.style.background = 'transparent';
                searchBtn.style.border = 'none';
                
                searchBtn.onclick = function(e) {
                    e.preventDefault();
                    qfr.toggle();
                };
                
                toolbar.container.appendChild(searchBtn);
            }
        }, 100);

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
        btn.innerHTML = '<i class="fa-solid fa-brain fa-spin me-1"></i> Revisando...';

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

            let data;
            try {
                data = await response.json();
            } catch (jsonErr) {
                console.error('[IA] Error parsing JSON:', jsonErr);
                throw new Error('El servidor devolvió un error inesperado (posible error 500). Por favor, intenta de nuevo.');
            }
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
