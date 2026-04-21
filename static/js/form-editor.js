// =========================================================
// 📝 EDITOR DE TEXTO RICO (TinyMCE)
// =========================================================

class RichTextEditor {
    constructor() {
        this.config = {
            // Campos que tendrán editor rico
            fields: [
                'contenido',           // Traducción/Español
                'texto_original'       // Texto Original
                // 'descripcion', 'descripcion_publicacion', 'resumen_corpus' - Removidos (textarea simple)
            ],

            // Configuración TinyMCE
            commonConfig: {
                height: 400,
                menubar: false,
                skin: 'oxide-dark',
                content_css: 'dark',
                plugins: [
                    'advlist', 'autolink', 'lists', 'link', 'charmap', 'preview',
                    'searchreplace', 'visualblocks', 'code', 'fullscreen',
                    'insertdatetime', 'table', 'wordcount', 'quickbars'
                ],
                toolbar: 'undo redo | formatselect | bold italic underline strikethrough | ' +
                    'forecolor backcolor | alignleft aligncenter alignright alignjustify | ' +
                    'bullist numlist outdent indent | link table charmap | ' +
                    'removeformat code fullscreen',
                quickbars_selection_toolbar: 'bold italic | quicklink h2 h3 blockquote',
                contextmenu: 'link table',

                // Estilos personalizados para tema dark tech
                content_style: `
                    body {
                        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        font-size: 14px;
                        line-height: 1.6;
                        color: #e0e0e0;
                        background-color: #0d0d0d;
                        padding: 15px;
                    }
                    p { margin-bottom: 1em; }
                    h1, h2, h3 { 
                        color: #ff9800; 
                        font-family: 'Roboto Condensed', sans-serif;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        text-shadow: 0 0 10px rgba(255, 152, 0, 0.15);
                    }
                    blockquote {
                        border-left: 4px solid #ff9800;
                        padding-left: 1em;
                        margin-left: 0;
                        font-style: italic;
                        color: #ccc;
                        background: rgba(255, 152, 0, 0.05);
                        padding: 10px 15px;
                    }
                    a {
                        color: #ff9800;
                        text-decoration: none;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                    table {
                        border-collapse: collapse;
                        width: 100%;
                        border: 1px solid #333;
                    }
                    table th {
                        background: rgba(255, 152, 0, 0.1);
                        color: #ff9800;
                        border: 1px solid #333;
                        padding: 8px;
                    }
                    table td {
                        border: 1px solid #333;
                        padding: 8px;
                    }
                    code {
                        background: #1e1e1e;
                        border: 1px solid #333;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-family: 'JetBrains Mono', monospace;
                        color: #ff9800;
                    }
                    pre {
                        background: #1e1e1e;
                        border: 1px solid #333;
                        padding: 10px;
                        border-radius: 4px;
                        overflow-x: auto;
                    }
                `,

                // Formatos de párrafo
                block_formats: 'Párrafo=p; Encabezado 1=h1; Encabezado 2=h2; Encabezado 3=h3; Cita=blockquote; Preformateado=pre',

                // Configuración de tabla
                table_default_attributes: {
                    border: '1'
                },
                table_default_styles: {
                    'border-collapse': 'collapse',
                    'width': '100%'
                },

                // Evento de cambio para activar validación
                setup: (editor) => {
                    editor.on('change keyup', () => {
                        editor.save(); // Sincronizar con textarea

                        // Trigger validación si existe
                        const textarea = document.getElementById(editor.id);
                        if (textarea && window.formValidator) {
                            textarea.dispatchEvent(new Event('input'));
                        }
                    });

                    // Personalizar color del editor
                    editor.on('init', () => {
                        const editorContainer = editor.getContainer();
                        if (editorContainer) {
                            editorContainer.style.borderColor = '#333';
                        }
                    });
                }
            }
        };

        this.init();
    }

    init() {
        // Cargar TinyMCE desde CDN
        this.loadTinyMCE().then(() => {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.setup());
            } else {
                this.setup();
            }
        }).catch(error => {
            console.warn('TinyMCE no se pudo cargar, usando textarea estándar:', error);
        });
    }

    loadTinyMCE() {
        return new Promise((resolve, reject) => {
            // Verificar si ya está cargado
            if (window.tinymce) {
                resolve();
                return;
            }

            // Cargar script desde CDN público (jsDelivr)
            const script = document.createElement('script');
            // Usar la versión 6.8.2 que sabemos que funciona con la configuración actual
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/tinymce/6.8.2/tinymce.min.js';
            script.referrerpolicy = 'origin';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    setup() {
        if (!window.tinymce) {
            console.error('❌ TinyMCE no está disponible');
            return;
        }

        console.log('✓ TinyMCE cargado, inicializando editores...');

        // Inicializar editores para cada campo
        this.config.fields.forEach(fieldName => {
            const textarea = document.querySelector(`textarea[name="${fieldName}"], textarea#${fieldName}`);

            if (!textarea) {
                console.log(`⚠️ Campo ${fieldName} no encontrado en esta página`);
                return;
            }

            // Si es texto_original y está en una pestaña oculta, retrasar inicialización
            if (fieldName === 'texto_original') {
                const tabPane = textarea.closest('.tab-pane');
                if (tabPane && !tabPane.classList.contains('active')) {
                    console.log(`⏳ ${fieldName} está en pestaña oculta, retrasando inicialización`);
                    this.setupDelayedEditor(fieldName, textarea);
                    return;
                }
            }

            console.log(`✓ Inicializando editor para: ${fieldName}`);

            // Asegurar que tenga ID
            if (!textarea.id) {
                textarea.id = fieldName;
            }

            // Configuración específica por campo
            const editorConfig = {
                ...this.config.commonConfig,
                selector: '#' + textarea.id
            };

            // Ajustes específicos por tipo de campo
            if (fieldName === 'contenido') {
                // Contenido principal: altura 100% para llenar espacio
                console.log('🔧 Configurando contenido con altura 100%');
                editorConfig.height = '100%';
                editorConfig.toolbar = 'undo redo | formatselect | bold italic underline | bullist numlist | link | removeformat code';
            } else if (fieldName === 'texto_original') {
                // Texto original: fuente monoespaciada y más técnico
                editorConfig.content_style = `
                    body {
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 14px;
                        line-height: 1.5;
                        color: #80d4ff;
                        background-color: #0a0a0a;
                        padding: 15px;
                    }
                    h1, h2, h3 {
                        color: #ff9800;
                        font-family: 'JetBrains Mono', monospace;
                    }
                    blockquote {
                        border-left: 4px solid #ff9800;
                        padding-left: 1em;
                        background: rgba(255, 152, 0, 0.05);
                        padding: 10px 15px;
                    }
                `;
                editorConfig.toolbar = 'undo redo | formatselect | bold italic underline | bullist numlist | link | removeformat code fullscreen';
                editorConfig.menubar = false;
            } else if (fieldName.includes('descripcion')) {
                // Descripciones: altura fija 200px
                console.log('🔧 Configurando descripcion con altura 200px');
                editorConfig.height = 200;
                editorConfig.min_height = 200;
                editorConfig.max_height = 600;
                editorConfig.resize = 'both';
                editorConfig.toolbar = 'undo redo | bold italic | bullist numlist | link | removeformat code';
            }

            // Inicializar TinyMCE
            tinymce.init(editorConfig).then(editors => {
                console.log(`✅ Editor rico activado para: ${fieldName} (height: ${editorConfig.height}px)`);

                // Marcar campo como enriquecido
                textarea.classList.add('has-rich-editor');

                // Agregar indicador visual
                this.addEditorBadge(textarea);

                // Personalizar colores después de la carga
                if (editors && editors.length > 0) {
                    const editor = editors[0];
                    this.customizeEditorTheme(editor);
                }
            }).catch(error => {
                console.error(`Error al inicializar editor para ${fieldName}:`, error);
            });
        });

        // Sincronizar con formulario antes de enviar (todos los formularios)
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', () => {
                if (window.tinymce) {
                    console.log('📝 Sincronizando TinyMCE antes de enviar formulario:', form.id || 'sin-id');
                    try {
                        tinymce.triggerSave();
                    } catch (e) {
                        console.error('Error al sincronizar TinyMCE:', e);
                    }
                }
            });
        });
    }

    addEditorBadge(textarea) {
        const parent = textarea.parentElement;
        if (!parent) return;

        // Buscar label asociado
        const label = parent.querySelector('label');
        if (!label || label.querySelector('.editor-badge')) return;

        const badge = document.createElement('span');
        badge.className = 'editor-badge';
        badge.innerHTML = `
            <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16" style="margin-left: 8px;">
                <path d="M12.854.146a.5.5 0 0 0-.707 0L10.5 1.793 14.207 5.5l1.647-1.646a.5.5 0 0 0 0-.708l-3-3zm.646 6.061L9.793 2.5 3.293 9H3.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.207l6.5-6.5zm-7.468 7.468A.5.5 0 0 1 6 13.5V13h-.5a.5.5 0 0 1-.5-.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.5-.5V10h-.5a.499.499 0 0 1-.175-.032l-.179.178a.5.5 0 0 0-.11.168l-2 5a.5.5 0 0 0 .65.65l5-2a.5.5 0 0 0 .168-.11l.178-.178z"/>
            </svg>
            <span style="font-size: 0.75rem; color: #ff9800; font-weight: normal;">Editor Rico</span>
        `;

        label.appendChild(badge);
    }

    customizeEditorTheme(editor) {
        editor.on('init', () => {
            const container = editor.getContainer();
            if (container) {
                // Borde oscuro por defecto
                container.style.borderColor = '#333';
                container.style.borderWidth = '1px';
                container.style.borderRadius = '2px';
                container.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';

                // Toolbar
                const toolbar = container.querySelector('.tox-toolbar, .tox-toolbar__primary');
                if (toolbar) {
                    toolbar.style.background = '#1a1a1a';
                    toolbar.style.borderBottom = '1px solid #2a2a2a';
                }

                // Statusbar
                const statusbar = container.querySelector('.tox-statusbar');
                if (statusbar) {
                    statusbar.style.background = '#141414';
                    statusbar.style.borderTop = '1px solid #2a2a2a';
                    statusbar.style.color = '#777';
                }
            }
        });

        // Efecto Focus (Borde Naranja Sirio)
        editor.on('focus', () => {
            const container = editor.getContainer();
            if (container) {
                container.style.borderColor = '#ff9800';
                container.style.boxShadow = '0 0 0 1px #ff9800';
            }
        });

        editor.on('blur', () => {
            const container = editor.getContainer();
            if (container) {
                container.style.borderColor = '#333';
                container.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
            }
        });
    }

    setupDelayedEditor(fieldName, textarea) {
        // Esperar a que la pestaña se active por primera vez
        const tabPane = textarea.closest('.tab-pane');
        if (!tabPane) return;

        const tabId = tabPane.id;
        const tabButton = document.querySelector(`[data-bs-target="#${tabId}"]`);

        if (!tabButton) return;

        let initialized = false;

        const initEditor = () => {
            if (initialized) return;
            initialized = true;

            console.log(`✓ Pestaña activada, inicializando editor para: ${fieldName}`);

            // Asegurar que tenga ID
            if (!textarea.id) {
                textarea.id = fieldName;
            }

            // Configuración específica por campo
            const editorConfig = {
                ...this.config.commonConfig,
                selector: '#' + textarea.id
            };

            // Texto original: fuente monoespaciada y más técnico
            editorConfig.content_style = `
                body {
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 14px;
                    line-height: 1.5;
                    color: #80d4ff;
                    background-color: #0a0a0a;
                    padding: 15px;
                }
                h1, h2, h3 {
                    color: #ff9800;
                    font-family: 'JetBrains Mono', monospace;
                }
                blockquote {
                    border-left: 4px solid #ff9800;
                    padding-left: 1em;
                    background: rgba(255, 152, 0, 0.05);
                    padding: 10px 15px;
                }
            `;
            editorConfig.toolbar = 'undo redo | formatselect | bold italic underline | bullist numlist | link | removeformat code fullscreen';
            editorConfig.menubar = false;
            editorConfig.height = 400;

            // Inicializar TinyMCE
            tinymce.init(editorConfig).then(editors => {
                console.log(`✅ Editor rico activado para: ${fieldName}`);

                // Marcar campo como enriquecido
                textarea.classList.add('has-rich-editor');

                // Agregar indicador visual
                this.addEditorBadge(textarea);

                // Personalizar colores después de la carga
                if (editors && editors.length > 0) {
                    const editor = editors[0];
                    this.customizeEditorTheme(editor);
                }
            }).catch(error => {
                console.error(`Error al inicializar editor para ${fieldName}:`, error);
            });
        };

        // Escuchar cuando la pestaña se muestre
        tabButton.addEventListener('shown.bs.tab', initEditor, { once: true });
    }

    // Método para obtener contenido limpio (sin HTML) si es necesario
    getPlainText(fieldName) {
        const editor = tinymce.get('editor-' + fieldName);
        if (editor) {
            return editor.getContent({ format: 'text' });
        }
        return '';
    }

    // Método para destruir editores (útil para modales)
    destroy() {
        if (window.tinymce) {
            tinymce.remove();
        }
    }
}

// =========================================================
// INICIALIZACIÓN AUTOMÁTICA
// =========================================================
(function () {
    const editorPaths = [
        // '/nueva', '/new', '/editar/', '/edit/'  <-- DESACTIVADO POR PROBLEMAS DE STANDARDS MODE
        // Publicaciones y Hemerotecas usan textarea simple, no requieren editor
        // '/nueva_publicacion', '/editar_publicacion/',
        // '/nueva_hemeroteca', '/editar_hemeroteca'
    ];
    const currentPath = window.location.pathname;
    const shouldInit = editorPaths.some(path => currentPath.includes(path));

    console.log('🔍 TinyMCE Editor v3.1');
    console.log('   Ruta:', currentPath);
    console.log('   Inicializar:', shouldInit);

    if (shouldInit) {
        console.log('✓ Cargando RichTextEditor...');
        // Asegurar que no se duplique
        if (!window.richTextEditor) {
            const editor = new RichTextEditor();
            window.richTextEditor = editor;
        }
    } else {
        console.log('⚠️ Ruta no requiere editor');
    }
})();
