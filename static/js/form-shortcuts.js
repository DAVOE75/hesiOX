// =========================================================
// ⌨️ ATAJOS DE TECLADO PARA FORMULARIOS
// =========================================================

class KeyboardShortcuts {
    constructor() {
        this.shortcuts = {
            'ctrl+s': { action: 'save', description: 'Guardar formulario' },
            'ctrl+enter': { action: 'submit', description: 'Enviar formulario' },
            'escape': { action: 'cancel', description: 'Cancelar y volver' },
            'ctrl+shift+p': { action: 'preview', description: 'Ver vista previa' }
        };

        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));
        this.showShortcutsHelp();
    }

    handleKeyPress(e) {
        const key = this.getKeyCombo(e);
        const shortcut = this.shortcuts[key];

        if (!shortcut) return;

        // Prevenir comportamiento por defecto
        e.preventDefault();

        // Ejecutar acción
        this[shortcut.action]();

        // Mostrar feedback
        this.showActionFeedback(shortcut.description);
    }

    getKeyCombo(e) {
        const parts = [];
        if (e.ctrlKey) parts.push('ctrl');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');

        const key = (e.key || '').toLowerCase();
        if (!['control', 'shift', 'alt'].includes(key)) {
            parts.push(key);
        }

        return parts.join('+');
    }

    save() {
        // Trigger autoguardado manual
        if (window.autosave) {
            window.autosave.saveDraft();
        }
        console.log('💾 Borrador guardado');
    }

    submit() {
        const form = document.querySelector('form');
        if (form) {
            form.submit();
        }
    }

    cancel() {
        const cancelBtn = document.querySelector('a[href="/"], a[href*="volver"]');
        if (cancelBtn) {
            window.location.href = cancelBtn.href;
        } else {
            window.history.back();
        }
    }

    preview() {
        const previewPanel = document.getElementById('citation-preview');
        if (previewPanel) {
            previewPanel.classList.toggle('minimized');
        }
    }

    showActionFeedback(description) {
        let feedback = document.getElementById('keyboard-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.id = 'keyboard-feedback';
            feedback.className = 'keyboard-feedback';
            document.body.appendChild(feedback);
        }

        feedback.textContent = description;
        feedback.classList.add('show');

        setTimeout(() => {
            feedback.classList.remove('show');
        }, 1500);
    }

    showShortcutsHelp() {
        // Si ya existe un botón manual en el HTML, lo usamos
        const existingBtn = document.getElementById('btn-keyboard-help');
        if (existingBtn) {
            existingBtn.onclick = () => this.toggleHelp();
            return;
        }

        // Crear botón de ayuda flotante solo si no hay uno manual
        const helpBtn = document.createElement('button');
        helpBtn.className = 'keyboard-help-btn';
        helpBtn.title = 'Atajos de teclado (?)';
        helpBtn.innerHTML = '?';
        helpBtn.onclick = () => this.toggleHelp();

        document.body.appendChild(helpBtn);
    }

    toggleHelp() {
        let helpPanel = document.getElementById('shortcuts-help');

        if (helpPanel) {
            helpPanel.remove();
            return;
        }

        helpPanel = document.createElement('div');
        helpPanel.id = 'shortcuts-help';
        helpPanel.className = 'shortcuts-help';
        helpPanel.innerHTML = `
            <div class="shortcuts-header">
                <strong>⌨️ Atajos de Teclado</strong>
                <button onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="shortcuts-list">
                ${Object.entries(this.shortcuts).map(([key, data]) => `
                    <div class="shortcut-item">
                        <kbd>${key.replace(/\+/g, ' + ').toUpperCase()}</kbd>
                        <span>${data.description}</span>
                    </div>
                `).join('')}
            </div>
        `;

        document.body.appendChild(helpPanel);
    }
}

// Inicializar
const keyboardShortcuts = new KeyboardShortcuts();
