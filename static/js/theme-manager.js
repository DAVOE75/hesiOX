/**
 * Theme Manager JS
 * Maneja la lógica del modal de gestión de temas y sincronización con Choices.js
 */

const ThemeManager = {
    config: {
        baseUrl: '/api/temas',
        renameUrl: '/api/temas/renombrar',
        deleteUrl: '/api/temas/eliminar',
        createUrl: '/api/temas/crear',
        themeInputId: 'inputTemas'
    },
    
    get swal() {
        return window.Swal || null;
    },
    
    init(customConfig = {}) {
        this.config = { ...this.config, ...customConfig };
        const modalEl = document.getElementById('modalGestorTemas');
        if (!modalEl) return;

        console.log("ThemeManager initialized on modal:", modalEl);

        modalEl.addEventListener('show.bs.modal', () => {
            this.loadTemas();
        });

        const filterInput = document.getElementById('filterTemasInput');
        if (filterInput) {
            filterInput.addEventListener('input', (e) => {
                this.filterTable(e.target.value);
            });
        }

        const btnCrear = document.getElementById('btnNuevoTemaStandalone');
        if (btnCrear) {
            console.log("Wiring up btnNuevoTemaStandalone");
            btnCrear.addEventListener('click', () => this.startCreate());
        }
    },

    async loadTemas() {
        const tableBody = document.getElementById('temasTableBody');
        tableBody.innerHTML = `
            <tr>
                <td colspan="3" class="text-center py-4">
                    <div class="spinner-border text-info" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                </td>
            </tr>
        `;

        try {
            const response = await fetch(this.config.baseUrl);
            if (!response.ok) throw new Error('Error al cargar temas');
            this.allThemes = await response.json();
            this.renderTable(this.allThemes);
        } catch (error) {
            console.error(error);
            tableBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger py-4">Error al cargar temas</td></tr>`;
        }
    },

    escapeJS(str) {
        return str.replace(/'/g, "\\'");
    },

    renderTable(temas) {
        const tableBody = document.getElementById('temasTableBody');
        if (temas.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="3" class="text-center py-4 opacity-50">No hay temas que coincidan</td></tr>`;
            return;
        }

        tableBody.innerHTML = temas.map(t => {
            const escapedName = this.escapeJS(t.nombre);
            const escapedId = t.nombre.replace(/\s+/g, '-');
            return `
                <tr data-tema="${t.nombre}" id="row-tema-${escapedId}" class="theme-row">
                    <td class="ps-3 align-middle">
                        <div class="theme-name-container d-flex align-items-center">
                            <span class="tema-nombre fw-semibold text-white">${t.nombre}</span>
                        </div>
                    </td>
                    <td class="text-center align-middle">
                        <span class="badge rounded-pill bg-info text-dark opacity-75 px-3">${t.cantidad}</span>
                    </td>
                    <td class="pe-3 text-end align-middle">
                        <div class="action-buttons-view d-flex gap-2 justify-content-end align-items-center">
                            <button class="btn btn-sirio btn-sirio-sm px-2" onclick="ThemeManager.startRenameInline('${escapedName}')" title="Renombrar">
                                <i class="fa-solid fa-pen-to-square text-warning"></i>
                            </button>
                            <button class="btn btn-sirio-danger btn-sirio-sm px-2" onclick="ThemeManager.deleteTema('${escapedName}')" title="Eliminar">
                                <i class="fa-solid fa-trash-can"></i>
                            </button>
                        </div>
                        <div class="action-buttons-edit d-none d-flex gap-2 justify-content-end align-items-center">
                            <button class="btn btn-sirio-primary btn-sirio-sm px-3" onclick="ThemeManager.saveRenameInline('${escapedName}')">
                                <i class="fa-solid fa-check me-1"></i>Guardar
                            </button>
                            <button class="btn btn-sirio btn-sirio-sm px-2" onclick="ThemeManager.cancelRenameInline('${escapedName}')">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    },

    filterTable(query) {
        const filtered = this.allThemes.filter(t => t.nombre.toLowerCase().includes(query.toLowerCase()));
        this.renderTable(filtered);
    },

    startCreate() {
        this.startCreateInline();
    },

    startCreateInline() {
        const tableBody = document.getElementById('temasTableBody');
        if (!tableBody) {
            console.error("No se encontró temasTableBody");
            return;
        }

        // Check if there's already a creation row
        if (document.getElementById('row-new-theme')) {
            document.getElementById('input-new-theme').focus();
            return;
        }

        const newRow = document.createElement('tr');
        newRow.id = 'row-new-theme';
        newRow.className = 'theme-row bg-panel-sirio-alt';
        newRow.innerHTML = `
            <td class="ps-3 align-middle">
                <div class="theme-name-container d-flex align-items-center">
                    <input type="text" id="input-new-theme" class="form-control form-control-sirio-sm" 
                           placeholder="Nuevo tema..."
                           onkeyup="if(event.key==='Enter') ThemeManager.saveCreateInline()"
                           onkeydown="if(event.key==='Escape') ThemeManager.cancelCreateInline()">
                </div>
            </td>
            <td class="text-center align-middle">
                <span class="badge rounded-pill bg-secondary opacity-50 px-3">0</span>
            </td>
            <td class="pe-3 text-end align-middle">
                <div class="d-flex gap-2 justify-content-end align-items-center">
                    <button class="btn btn-sirio-primary btn-sirio-sm px-3" onclick="ThemeManager.saveCreateInline()">
                        <i class="fa-solid fa-check me-1"></i>Crear
                    </button>
                    <button class="btn btn-sirio-danger btn-sirio-sm px-2" onclick="ThemeManager.cancelCreateInline()">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </td>
        `;

        // Check if "No hay temas" message exists
        if (tableBody.innerHTML.includes('No hay temas')) {
            tableBody.innerHTML = '';
        }
        
        tableBody.insertBefore(newRow, tableBody.firstChild);
        
        const input = document.getElementById('input-new-theme');
        input.focus();
    },

    cancelCreateInline() {
        const row = document.getElementById('row-new-theme');
        if (row) row.remove();
        
        // If table is empty, reload to show "No hay temas" message
        const tableBody = document.getElementById('temasTableBody');
        if (tableBody && tableBody.children.length === 0) {
            this.loadTemas();
        }
    },

    async saveCreateInline() {
        const input = document.getElementById('input-new-theme');
        if (!input) return;
        
        const newName = input.value.trim();
        if (!newName) {
            this.cancelCreateInline();
            return;
        }

        try {
            const response = await fetch(this.config.createUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ tema_new: newName })
            });

            const result = await response.json();
            if (result.success) {
                if (this.swal) {
                    this.swal.fire({
                        icon: 'success',
                        title: 'Tema creado',
                        timer: 1500,
                        showConfirmButton: false,
                        customClass: {
                            popup: 'swal2-sirio-popup',
                            title: 'swal2-sirio-title'
                        }
                    });
                }
                this.loadTemas();
                
                // Sync with Choices if it exists
                const temasEl = document.getElementById(this.config.themeInputId);
                if (temasEl && window.choicesInstances && window.choicesInstances[this.config.themeInputId]) {
                    const choices = window.choicesInstances[this.config.themeInputId];
                    choices.setChoices([{ value: newName, label: newName, selected: true }], 'value', 'label', false);
                }
            } else {
                throw new Error(result.error || 'Error al crear tema');
            }
        } catch (error) {
            if (this.swal) this.swal.fire('Error', error.message, 'error');
            this.cancelCreateInline();
        }
    },

    startRenameInline(oldName) {
        const escapedId = oldName.replace(/\s+/g, '-');
        const row = document.getElementById(`row-tema-${escapedId}`);
        if (!row) return;

        // Cambiar a modo edición
        const nameContainer = row.querySelector('.theme-name-container');
        const currentName = nameContainer.querySelector('.tema-nombre').textContent;
        
        nameContainer.innerHTML = `
            <input type="text" class="form-control form-control-sirio-sm input-rename-inline" 
                   value="${this.escapeJS(currentName)}" 
                   onkeyup="if(event.key==='Enter') ThemeManager.saveRenameInline('${this.escapeJS(oldName)}')"
                   onkeydown="if(event.key==='Escape') ThemeManager.cancelRenameInline('${this.escapeJS(oldName)}')"
                   autofocus>
        `;
        
        row.querySelector('.action-buttons-view').classList.add('d-none');
        row.querySelector('.action-buttons-edit').classList.remove('d-none');
        
        const input = nameContainer.querySelector('input');
        input.focus();
        input.select();
    },

    cancelRenameInline(oldName) {
        const escapedId = oldName.replace(/\s+/g, '-');
        const row = document.getElementById(`row-tema-${escapedId}`);
        if (!row) return;

        const nameContainer = row.querySelector('.theme-name-container');
        nameContainer.innerHTML = `<span class="tema-nombre fw-semibold text-white">${oldName}</span>`;
        
        row.querySelector('.action-buttons-view').classList.remove('d-none');
        row.querySelector('.action-buttons-edit').classList.add('d-none');
    },

    async saveRenameInline(oldName) {
        const escapedId = oldName.replace(/\s+/g, '-');
        const row = document.getElementById(`row-tema-${escapedId}`);
        if (!row) return;

        const input = row.querySelector('.input-rename-inline');
        const newName = input.value.trim();

        if (!newName || newName === oldName) {
            this.cancelRenameInline(oldName);
            return;
        }

        try {
            const response = await fetch(this.config.renameUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ tema_old: oldName, tema_new: newName })
            });

            const result = await response.json();
            if (result.success) {
                if (this.swal) {
                    this.swal.fire({
                        icon: 'success',
                        title: 'Renombrado correctamente',
                        timer: 1500,
                        showConfirmButton: false,
                        customClass: {
                            popup: 'swal2-sirio-popup',
                            title: 'swal2-sirio-title'
                        }
                    });
                }
                this.loadTemas();
                this.syncChoicesInstance(oldName, newName);
            } else {
                throw new Error(result.error || 'Error al renombrar');
            }
        } catch (error) {
            if (this.swal) this.swal.fire('Error', error.message, 'error');
            this.cancelRenameInline(oldName);
        }
    },

    async deleteTema(name) {
        if (!this.swal) return;
        const confirm = await this.swal.fire({
            title: '¿Eliminar tema?',
            text: `Se quitará "${name}" de todos los registros del proyecto. Esta acción es irreversible.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar',
            customClass: {
                popup: 'swal2-sirio-popup',
                title: 'swal2-sirio-title',
                htmlContainer: 'swal2-sirio-html',
                confirmButton: 'swal2-sirio-confirm btn-sirio-danger',
                cancelButton: 'swal2-sirio-cancel',
                actions: 'swal2-sirio-actions'
            },
            buttonsStyling: false
        });

        if (confirm.isConfirmed) {
            try {
                const response = await fetch(this.config.deleteUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({ tema_old: name })
                });

                const result = await response.json();
                if (result.success) {
                    if (this.swal) {
                        this.swal.fire({
                            icon: 'success',
                            title: 'Eliminado correctamente',
                            timer: 2000,
                            showConfirmButton: false,
                            background: '#1a1a2e',
                            color: '#fff'
                        });
                    }
                    this.loadTemas();
                    this.syncChoicesInstance(name, null);
                } else {
                    throw new Error(result.error || 'Error desconocido');
                }
            } catch (error) {
                if (this.swal) this.swal.fire('Error', error.message, 'error');
            }
        }
    },

    syncChoicesInstance(oldValue, newValue) {
        // Buscar la instancia de Choices para el campo 'temas'
        // Según _choices_includes.html, se guardan en window.choicesInstances[id]
        const temasEl = document.getElementById('inputTemas');
        if (!temasEl || !window.choicesInstances || !window.choicesInstances['inputTemas']) return;

        const choices = window.choicesInstances['inputTemas'];
        
        // Obtener valores actuales
        let currentValues = choices.getValue(true);
        
        if (newValue) {
            // Renombrar: si el viejo estaba seleccionado, cambiarlo por el nuevo
            if (currentValues.includes(oldValue)) {
                choices.removeActiveItemsByValue(oldValue);
                choices.setChoices([{ value: newValue, label: newValue, selected: true }], 'value', 'label', true);
            }
        } else {
            // Eliminar: quitar si estaba seleccionado
            if (currentValues.includes(oldValue)) {
                choices.removeActiveItemsByValue(oldValue);
            }
        }
    },

    getCSRFToken() {
        // Intentar meta tag primero (estándar en hesiOX base.html)
        const metaToken = document.querySelector('meta[name="csrf-token"]')?.content;
        if (metaToken) return metaToken;
        
        // Luego input oculto (Flask-WTF)
        return document.querySelector('input[name="csrf_token"]')?.value || '';
    }
};

// Exponer globalmente para que funcionen los onclick dinámicos
window.ThemeManager = ThemeManager;

document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
