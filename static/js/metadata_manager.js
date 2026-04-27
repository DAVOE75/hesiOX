/**
 * MetadataManager.js
 * Gestión dinámica de opciones para selectores (Género, Subgénero, Frecuencia)
 */

const MetadataManager = {
    currentCategory: null,
    targetSelectId: null,
    modal: null,

    init() {
        this.modal = new bootstrap.Modal(document.getElementById('modalMetadataManager'));
        this.setupEventListeners();
    },

    setupEventListeners() {
        const form = document.getElementById('metadata-option-form');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveOption();
        });

        document.getElementById('btn-cancel-edit-metadata').addEventListener('click', () => {
            this.resetForm();
        });
    },

    /**
     * Abre el modal para una categoría específica
     * @param {string} category - ID de la categoría (tipo_recurso, tipo_publicacion, frecuencia)
     * @param {string} selectId - ID del select que se debe actualizar al terminar
     * @param {string} title - Título amigable para el modal
     */
    open(category, selectId, title) {
        this.currentCategory = category;
        this.targetSelectId = selectId;
        
        document.getElementById('metadata-category-title').textContent = title;
        document.getElementById('metadata-categoria').value = category;
        
        this.loadOptions();
        this.resetForm();
        this.modal.show();
    },

    async loadOptions() {
        const listContainer = document.getElementById('metadata-options-list');
        listContainer.innerHTML = '<tr><td colspan="5" class="text-center p-4 text-muted italic">Cargando...</td></tr>';

        try {
            const response = await fetch(`/api/metadata/${this.currentCategory}`);
            const options = await response.json();
            
            if (options.length === 0) {
                listContainer.innerHTML = '<tr><td colspan="5" class="text-center p-4 text-muted">No hay opciones configuradas.</td></tr>';
            } else {
                listContainer.innerHTML = options.map(opt => `
                    <tr>
                        <td class="font-monospace">${opt.orden}</td>
                        <td><span class="fw-bold">${opt.etiqueta}</span></td>
                        <td><code class="xsmall text-muted">${opt.valor}</code></td>
                        <td>${opt.grupo || '-'}</td>
                        <td class="text-end">
                            <button class="btn btn-xs btn-outline-info me-1" onclick="MetadataManager.editOption(${JSON.stringify(opt).replace(/"/g, '&quot;')})">
                                <i class="fa-solid fa-pencil"></i>
                            </button>
                            <button class="btn btn-xs btn-outline-danger" onclick="MetadataManager.deleteOption(${opt.id})">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        } catch (error) {
            console.error('Error loading metadata options:', error);
            listContainer.innerHTML = '<tr><td colspan="5" class="text-center p-4 text-danger">Error al cargar datos.</td></tr>';
        }
    },

    async saveOption() {
        const id = document.getElementById('metadata-id').value;
        const data = {
            etiqueta: document.getElementById('metadata-etiqueta').value,
            valor: document.getElementById('metadata-valor').value,
            grupo: document.getElementById('metadata-grupo').value,
            orden: parseInt(document.getElementById('metadata-orden').value) || 0
        };

        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/metadata/option/${id}` : `/api/metadata/${this.currentCategory}`;
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                this.loadOptions();
                this.resetForm();
                this.refreshTargetSelect();
                
                // Si es un add nuevo, podemos mostrar un toast o aviso
                if (!id) {
                    console.log('Opción añadida con éxito');
                }
            } else {
                const err = await response.json();
                alert('Error: ' + (err.error || 'No se pudo guardar la opción'));
            }
        } catch (error) {
            console.error('Error saving metadata option:', error);
            alert('Error de conexión al guardar.');
        }
    },

    editOption(opt) {
        document.getElementById('metadata-id').value = opt.id;
        document.getElementById('metadata-etiqueta').value = opt.etiqueta;
        document.getElementById('metadata-valor').value = opt.valor;
        document.getElementById('metadata-grupo').value = opt.grupo || '';
        document.getElementById('metadata-orden').value = opt.orden;
        
        document.getElementById('metadata-form-title').textContent = 'Editar Opción';
        document.getElementById('btn-save-metadata').innerHTML = '<i class="fa-solid fa-check me-1"></i> ACTUALIZAR';
        document.getElementById('btn-cancel-edit-metadata').classList.remove('d-none');
    },

    async deleteOption(id) {
        if (!confirm('¿Estás seguro de eliminar esta opción? Los registros existentes que la usen conservarán el valor, pero no aparecerá en el desplegable.')) return;

        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
        try {
            const response = await fetch(`/api/metadata/option/${id}`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrfToken }
            });

            if (response.ok) {
                this.loadOptions();
                this.refreshTargetSelect();
            }
        } catch (error) {
            console.error('Error deleting metadata option:', error);
        }
    },

    async refreshTargetSelect() {
        if (!this.targetSelectId) return;
        const select = document.getElementById(this.targetSelectId);
        if (!select) return;

        const currentValue = select.value;
        const choicesInstance = window.choicesInstances ? window.choicesInstances[this.targetSelectId] : null;

        try {
            const response = await fetch(`/api/metadata/${this.currentCategory}`);
            const options = await response.json();
            
            // Reconstruir el select
            if (choicesInstance) {
                choicesInstance.clearChoices();
                
                const formattedChoices = options.map(opt => ({
                    value: opt.valor,
                    label: opt.etiqueta,
                    selected: opt.valor === currentValue,
                    customProperties: { grupo: opt.grupo }
                }));
                
                choicesInstance.setChoices(formattedChoices, 'value', 'label', true);
            } else {
                // Select nativo
                let html = '<option value="">Seleccionar...</option>';
                
                // Agrupar por grupo si existe
                const grouped = {};
                options.forEach(opt => {
                    const g = opt.grupo || '';
                    if (!grouped[g]) grouped[g] = [];
                    grouped[g].push(opt);
                });

                for (const [group, opts] of Object.entries(grouped)) {
                    if (group) html += `<optgroup label="${group}">`;
                    opts.forEach(opt => {
                        html += `<option value="${opt.valor}" ${opt.valor === currentValue ? 'selected' : ''}>${opt.etiqueta}</option>`;
                    });
                    if (group) html += `</optgroup>`;
                }
                
                select.innerHTML = html;
            }
        } catch (error) {
            console.error('Error refreshing select:', error);
        }
    },

    resetForm() {
        document.getElementById('metadata-id').value = '';
        document.getElementById('metadata-option-form').reset();
        document.getElementById('metadata-form-title').textContent = 'Añadir Nueva Opción';
        document.getElementById('btn-save-metadata').innerHTML = '<i class="fa-solid fa-plus me-1"></i> GUARDAR';
        document.getElementById('btn-cancel-edit-metadata').classList.add('d-none');
    }
};

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('modalMetadataManager')) {
        MetadataManager.init();

        // Escuchar clics en botones de gestión (usando delegación para dinamismo)
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-manage-metadata');
            if (btn) {
                const category = btn.dataset.categoria;
                const title = btn.title || 'Opciones';
                
                // Determinar el select objetivo (asumimos el siguiente select o buscamos por nombre)
                // En nuestras plantillas, el botón está dentro del label, y el select es hermano o hijo del contenedor
                const parentCol = btn.closest('[class*="col-"]');
                const select = parentCol.querySelector('select');
                const selectId = select ? select.id : null;

                MetadataManager.open(category, selectId, title);
            }
        });
    }
});
