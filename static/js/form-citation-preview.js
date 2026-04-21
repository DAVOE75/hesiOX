// =========================================================
// 📚 VISTA PREVIA DE CITA BIBLIOGRÁFICA (v3.0 - Integrado)
// =========================================================

class CitationPreview {
    constructor() {
        this.previewPanel = null;
        this.generator = null;
        this.currentFormat = ''; // Sin formato seleccionado por defecto

        console.log('[Citation Preview] Inicializando v3.0...');
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
        // Esperar a que CitationGenerator esté disponible (máximo 5 segundos)
        if (!window.CitationGenerator) {
            this.retryCount = (this.retryCount || 0) + 1;
            if (this.retryCount > 50) {
                console.log('[Citation Preview] CitationGenerator no disponible, módulo desactivado');
                return;
            }
            setTimeout(() => this.setup(), 100);
            return;
        }

        // Crear instancia del generador
        this.generator = new CitationGenerator();

        // Crear panel integrado
        this.createPreviewPanel();

        // Observar cambios en todos los campos del formulario
        this.watchFormChanges();

        // Actualización inicial
        this.updatePreview();

        console.log('[Citation Preview] ✅ Sistema listo');
    }

    createPreviewPanel() {
        // Buscar la sección de Material Adjunto (compatible con .card-header y .card-header-panel)
        const headers = Array.from(document.querySelectorAll('.card-header, .card-header-panel'));
        const materialAdjuntoCard = headers.find(header =>
            header.textContent.toUpperCase().includes('MATERIAL ADJUNTO')
        )?.closest('.card, .card-panel');

        if (!materialAdjuntoCard) {
            console.warn('[Citation Preview] No se encontró sección Material Adjunto');
            return;
        }

        // Crear panel
        this.previewPanel = document.createElement('div');
        this.previewPanel.className = 'citation-preview-integrated card-panel mt-3';
        this.previewPanel.style.flex = 'none'; // EVITAR QUE SE ESTIRE EN EL EDITOR

        // Generar opciones de formato
        const formats = this.generator.getFormats();
        const formatOptions = '<option value="">-- Selecciona un formato --</option>' +
            Object.entries(formats).map(([key, label]) =>
                `<option value="${key}"${key === this.currentFormat ? ' selected' : ''}>${label}</option>`
            ).join('');

        this.previewPanel.innerHTML = `
            <div class="card-header-panel d-flex justify-content-between cursor-pointer" onclick="document.getElementById('citation-preview-body').classList.toggle('d-none'); this.querySelector('i.fa-caret-down').classList.toggle('fa-rotate-180');">
                <span><i class="fa-solid fa-quote-right me-2"></i> Generador de Citas</span>
                <i class="fa-solid fa-caret-down transition-transform"></i>
            </div>
            
            <div id="citation-preview-body" class="p-3">
                <div class="citation-inner">
                    <div class="mb-3">
                        <label class="form-label-sirio">Formato de Cita</label>
                        <select id="citation-format-select" class="form-select form-control-sirio" style="width: 100%;">
                            ${formatOptions}
                        </select>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label-sirio">Vista Previa</label>
                        <div class="citation-text p-3 bg-black border border-secondary rounded text-light" style="font-family: 'JetBrains Mono', monospace; font-size: 0.9em; min-height: 60px;"></div>
                    </div>

                    <button type="button" class="btn btn-sirio-primary w-100 justify-content-center citation-copy-btn" onclick="citationPreview.copyCitation()">
                        <i class="fa-regular fa-copy"></i> Copiar Cita
                    </button>
                </div>
            </div>
        `;

        // Insertar después de Material Adjunto
        materialAdjuntoCard.insertAdjacentElement('afterend', this.previewPanel);

        // Configurar eventos
        setTimeout(() => {
            const select = document.getElementById('citation-format-select');
            if (select) {
                select.addEventListener('change', (e) => {
                    this.currentFormat = e.target.value;
                    this.updatePreview();
                });
            }
        }, 200);
    }

    watchFormChanges() {
        // Campos relevantes para citas
        const relevantFields = [
            'autor', 'nombre_autor', 'apellido_autor',
            'titulo', 'publicacion', 'ciudad',
            'fecha_original', 'anio', 'numero', 'paginas',
            'editorial', 'isbn', 'volumen', 'doi', 'issn',
            'lugar_publicacion', 'url', 'tipo_recurso'
        ];

        relevantFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.addEventListener('input', () => {
                    // Debounce: esperar 300ms después del último cambio
                    clearTimeout(this.updateTimeout);
                    this.updateTimeout = setTimeout(() => this.updatePreview(), 300);
                });

                // Para selects, actualizar inmediatamente
                if (field.tagName === 'SELECT') {
                    field.addEventListener('change', () => this.updatePreview());
                }
            }
        });

        console.log('[Citation Preview] Observando', relevantFields.length, 'campos');
    }

    updatePreview() {
        if (!this.generator || !this.previewPanel) return;

        const citationDiv = this.previewPanel.querySelector('.citation-text');

        // Si no hay formato seleccionado, mostrar mensaje de ayuda
        if (!this.currentFormat) {
            citationDiv.innerHTML = '<em class="text-muted">Selecciona un formato de cita para generar la vista previa...</em>';
            return;
        }

        const citation = this.generator.generate(this.currentFormat);

        if (citation && citation.trim().length > 10) {
            citationDiv.innerHTML = citation;
        } else {
            citationDiv.innerHTML = '<em class="text-muted">Completa los campos (Autor, Título, Publicación) para generar la cita...</em>';
        }
    }

    copyCitation() {
        if (!this.generator) return;

        const citation = this.generator.generate(this.currentFormat);

        // Crear elemento temporal para copiar (eliminar HTML)
        const temp = document.createElement('div');
        temp.innerHTML = citation;
        const plainText = temp.textContent || temp.innerText || '';

        // Copiar al portapapeles
        navigator.clipboard.writeText(plainText).then(() => {
            // Feedback visual
            const btn = this.previewPanel.querySelector('.citation-copy-btn');
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-check"></i> ¡Copiado!';
            btn.classList.add('btn-success');
            btn.classList.remove('btn-sirio-primary');

            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.classList.remove('btn-success');
                btn.classList.add('btn-sirio-primary');
            }, 2000);
        }).catch(err => {
            console.error('[Citation Preview] Error al copiar:', err);
            alert('No se pudo copiar. Tu navegador no soporta esta función.');
        });
    }
}

// Inicializar automáticamente
let citationPreview;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        citationPreview = new CitationPreview();
    });
} else {
    citationPreview = new CitationPreview();
}

console.log('[Citation Preview] ✅ Módulo cargado correctamente');
