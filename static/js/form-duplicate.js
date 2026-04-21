// =========================================================
// 🔄 BOTÓN DUPLICAR ÚLTIMO REGISTRO
// =========================================================

class DuplicateRecord {
    constructor() {
        this.init();
    }
    
    init() {
        // Solo en página de nuevo registro
        if (!window.location.pathname.includes('/new')) return;
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }
    
    setup() {
        this.createButton();
    }
    
    createButton() {
        const header = document.querySelector('.d-flex.justify-content-between.align-items-center');
        if (!header) return;
        
        const cancelBtn = header.querySelector('a[href="/"]');
        if (!cancelBtn) return;
        
        // Crear botón
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-outline-info btn-sm';
        btn.innerHTML = `
            <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16" style="margin-right: 5px;">
                <rect x="5" y="5" width="9" height="9" rx="1" stroke="currentColor" stroke-width="1.5" fill="none"/>
                <path d="M3 1h8a2 2 0 0 1 2 2v8" stroke="currentColor" stroke-width="1.5" fill="none"/>
                <line x1="7" y1="8" x2="11" y2="8" stroke="currentColor" stroke-width="1"/>
                <line x1="9" y1="6" x2="9" y2="10" stroke="currentColor" stroke-width="1"/>
            </svg>
            Copiar del Último
        `;
        btn.onclick = () => this.duplicateLastRecord();
        
        // Insertar antes del botón cancelar
        cancelBtn.parentElement.insertBefore(btn, cancelBtn);
    }
    
    async duplicateLastRecord() {
        try {
            const response = await fetch('/api/ultimo_registro');
            if (!response.ok) {
                this.showNotification('No hay registros previos', 'warning');
                return;
            }
            
            const data = await response.json();
            
            // Llenar campos
            this.fillField('publicacion', data.publicacion);
            this.fillField('ciudad', data.ciudad);
            this.fillField('pais_publicacion', data.pais_publicacion);
            this.fillField('idioma', data.idioma);
            this.fillField('tipo_recurso', data.tipo_recurso);
            this.fillField('fuente', data.fuente);
            this.fillField('formato_fuente', data.formato_fuente);
            this.fillField('licencia', data.licencia);
            this.fillField('edicion', data.edicion);
            this.fillField('anio', data.anio);
            
            // Trigger autocompletado de publicación
            const pubInput = document.querySelector('[name="publicacion"]');
            if (pubInput) {
                pubInput.dispatchEvent(new Event('change'));
            }
            
            this.showNotification('Datos copiados del último registro', 'success');
            
        } catch (error) {
            console.error('Error duplicating record:', error);
            this.showNotification('Error al copiar datos', 'danger');
        }
    }
    
    fillField(fieldName, value) {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (!field || !value) return;
        
        // Solo llenar si está vacío
        if (field.value && field.value.trim()) return;
        
        field.value = value;
        
        // Trigger validation si existe
        if (window.formValidator) {
            field.dispatchEvent(new Event('input'));
        }
    }
    
    showNotification(message, type) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show duplicate-notification`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(alert, container.firstChild);
            
            // Auto-dismiss after 3 seconds
            setTimeout(() => {
                alert.classList.remove('show');
                setTimeout(() => alert.remove(), 150);
            }, 3000);
        }
    }
}

// Inicializar
const duplicateRecord = new DuplicateRecord();
