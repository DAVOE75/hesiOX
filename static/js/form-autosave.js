// =========================================================
// 💾 AUTOGUARDADO DE BORRADOR EN LOCALSTORAGE
// =========================================================

class FormAutosave {
    constructor(formSelector, saveInterval = 5000) {
        this.form = document.querySelector(formSelector);
        if (!this.form) return;

        this.saveInterval = saveInterval;
        this.storageKey = 'draft_' + window.location.pathname;
        this.saveTimer = null;

        this.init();
    }

    init() {
        // Cargar borrador al iniciar
        this.loadDraft();

        // Detectar cambios en cualquier campo
        this.form.addEventListener('input', () => {
            this.scheduleSave();
        });

        // Guardar antes de salir
        window.addEventListener('beforeunload', () => {
            this.saveDraft();
        });

        // Limpiar borrador al enviar
        this.form.addEventListener('submit', () => {
            this.clearDraft();
        });

        // Mostrar notificación si hay borrador
        this.showDraftNotification();
    }

    scheduleSave() {
        clearTimeout(this.saveTimer);
        this.saveTimer = setTimeout(() => {
            this.saveDraft();
        }, this.saveInterval);
    }

    saveDraft() {
        const formData = new FormData(this.form);
        const data = {};

        formData.forEach((value, key) => {
            // No guardar archivos
            if (value instanceof File) return;
            data[key] = value;
        });

        // Guardar timestamp
        data._saved_at = new Date().toISOString();

        try {
            localStorage.setItem(this.storageKey, JSON.stringify(data));
            this.showSaveIndicator();
        } catch (e) {
            console.error('Error al guardar borrador:', e);
        }
    }

    loadDraft() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (!saved) return;

            const data = JSON.parse(saved);

            // Cargar valores en el formulario
            Object.keys(data).forEach(key => {
                if (key === '_saved_at') return;

                const field = this.form.querySelector(`[name="${key}"]`);
                if (!field) return;

                // Solo cargar si el campo está vacío
                if (field.value) return;

                if (field.type === 'checkbox') {
                    field.checked = data[key] === 'si' || data[key] === 'on';
                } else if (field.tagName === 'SELECT') {
                    field.value = data[key];
                } else {
                    field.value = data[key];
                }
            });

        } catch (e) {
            console.error('Error al cargar borrador:', e);
        }
    }

    clearDraft() {
        try {
            localStorage.removeItem(this.storageKey);
        } catch (e) {
            console.error('Error al limpiar borrador:', e);
        }
    }

    showSaveIndicator() {
        // Mostrar "Guardado automáticamente" temporalmente
        let indicator = document.getElementById('autosave-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'autosave-indicator';
            indicator.className = 'autosave-indicator';
            indicator.innerHTML = `
                <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16" style="margin-right: 5px;">
                    <path d="M2 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H9.5a1 1 0 0 0-1 1v7.293l2.646-2.647a.5.5 0 0 1 .708.708l-3.5 3.5a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L7.5 9.293V2a2 2 0 0 1 2-2H14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h2.5a.5.5 0 0 1 0 1H2z"/>
                </svg>
                Borrador guardado
            `;
            document.body.appendChild(indicator);
        }

        indicator.classList.add('show');
        setTimeout(() => {
            indicator.classList.remove('show');
        }, 2000);
    }

    showDraftNotification() {
        const saved = localStorage.getItem(this.storageKey);
        if (!saved) return;

        const data = JSON.parse(saved);
        const savedAt = new Date(data._saved_at);
        const now = new Date();
        const diff = now - savedAt;

        // Solo mostrar si el borrador tiene menos de 24 horas
        if (diff > 24 * 60 * 60 * 1000) {
            this.clearDraft();
            return;
        }

        const timeAgo = this.formatTimeAgo(diff);

        const notification = document.createElement('div');
        notification.className = 'draft-notification';
        notification.innerHTML = `
            <div class="d-flex align-items-center justify-content-between">
                <div>
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16" style="margin-right: 8px;">
                        <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                        <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
                    </svg>
                    <strong>Borrador recuperado</strong> - Guardado hace ${timeAgo}
                </div>
                <button type="button" class="btn-close-draft" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;

        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(notification, container.firstChild);
        }
    }

    formatTimeAgo(ms) {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) return `${hours}h`;
        if (minutes > 0) return `${minutes}min`;
        return `${seconds}s`;
    }
}

// Inicializar autoguardado (solo en formularios new/editar/publicaciones)
const formPaths = ['/new', '/editar/', '/nueva_publicacion', '/editar_publicacion/'];
const shouldAutoSave = formPaths.some(path => window.location.pathname.includes(path));

if (shouldAutoSave) {
    const autosave = new FormAutosave('form', 5000); // Guardar cada 5 segundos
    // Hacer accesible globalmente para atajos de teclado
    window.autosave = autosave;
}
