/**
 * autores-dinamicos.js
 * Manejo de filas dinámicas para múltiples autores en formularios de HesiOX
 */

// Función para añadir una fila de autor - Definida globalmente para evitar race conditions
window.addAutorRow = function(nombre = '', apellido = '', tipo = 'firmado', esAnonimo = false, pseudonimo = '') {
    const container = document.getElementById('autores-container');
    if (!container) {
        console.error('[Autores Dinámicos] Contenedor no encontrado');
        return;
    }
    
    // Corrección: Si el nombre viene con coma y el apellido está vacío, dividirlos automáticamente
    if (nombre && nombre.includes(',') && !apellido) {
        const partes = nombre.split(',');
        apellido = partes[0].trim();
        nombre = partes[1].trim();
    }
    const rowId = Date.now() + Math.floor(Math.random() * 1000);
    
    const row = document.createElement('div');
    row.className = 'autor-row mb-3 p-3 border border-secondary rounded position-relative';
    row.id = `autor-row-${rowId}`;
    row.dataset.id = rowId;
    row.style.background = 'rgba(255,255,255,0.02)';
    
    row.innerHTML = `
        <div class="row g-2 align-items-end">
            <div class="col-md-3">
                <label class="form-label-sirio small">Nombre</label>
                <input type="text" name="nombre_autor[]" class="form-control form-control-sirio form-control-sm" 
                    value="${nombre}" ${esAnonimo ? 'readonly' : ''}>
            </div>
            <div class="col-md-4">
                <label class="form-label-sirio small">Apellido(s)</label>
                <input type="text" name="apellido_autor[]" class="form-control form-control-sirio form-control-sm" 
                    value="${apellido}" ${esAnonimo ? 'readonly' : ''}>
            </div>
            <div class="col-md-3">
                <label class="form-label-sirio small">Tipo</label>
                <select name="tipo_autor[]" class="form-select form-select-sirio form-select-sm">
                    <option value="firmado" ${tipo === 'firmado' ? 'selected' : ''}>Firmado</option>
                    <option value="anónimo" ${tipo === 'anónimo' || tipo === 'anónimo' ? 'selected' : ''}>Anónimo</option>
                    <option value="corresponsal" ${tipo === 'corresponsal' ? 'selected' : ''}>Corresponsal</option>
                    <option value="editor" ${tipo === 'editor' ? 'selected' : ''}>Editor/Coordinador</option>
                    <option value="traductor" ${tipo === 'traductor' ? 'selected' : ''}>Traductor</option>
                    <option value="ilustrador" ${tipo === 'ilustrador' ? 'selected' : ''}>Ilustrador/Grabador</option>
                </select>
            </div>
            <div class="col-md-2 d-flex gap-1 justify-content-end align-items-center">
                <button type="button" class="btn btn-outline-info btn-sm border-0 btn-bio-autor" title="Ficha Biográfica">
                    <i class="fa-solid fa-book-open"></i>
                </button>
                <button type="button" class="btn btn-outline-danger btn-sm border-0 btn-remove-autor" title="Eliminar">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
            <div class="col-12 mt-2 d-flex align-items-center">
                <div class="form-check form-switch">
                    <input class="form-check-input check-anonimo-autor" type="checkbox" id="check_${rowId}" ${esAnonimo ? 'checked' : ''}>
                    <label class="form-check-label small text-muted ms-2" for="check_${rowId}">Es anónimo / Sin firmar</label>
                    <input type="hidden" name="es_anonimo_raw[]" value="${esAnonimo ? 'si' : 'no'}">
                </div>
            </div>
        </div>
    `;
    
    container.appendChild(row);
    
    // Si el autor tiene un pseudónimo, intentar heredarlo al campo global si está vacío
    if (pseudonimo) {
        const psInput = document.querySelector('input[name="pseudonimo"]');
        if (psInput) {
            let currentVal = psInput.value.trim();
            if (currentVal) {
                // Si ya hay algo, añadirlo solo si no está ya presente
                const pseudos = currentVal.split(',').map(p => p.trim());
                if (!pseudos.includes(pseudonimo)) {
                    psInput.value = currentVal + ", " + pseudonimo;
                }
            } else {
                // Si está vacío, simplemente poner el pseudónimo
                psInput.value = pseudonimo;
            }
        }
    }
    
    // Lógica para el switch de anónimo
    const checkbox = row.querySelector('.check-anonimo-autor');
    const hiddenInput = row.querySelector('input[name="es_anonimo_raw[]"]');
    const nameInput = row.querySelector('input[name="nombre_autor[]"]');
    const surnameInput = row.querySelector('input[name="apellido_autor[]"]');
    const typeSelect = row.querySelector('select[name="tipo_autor[]"]');
    
    const updateState = (isAnon) => {
        hiddenInput.value = isAnon ? 'si' : 'no';
        nameInput.readOnly = isAnon;
        surnameInput.readOnly = isAnon;
        
        if (isAnon) {
            nameInput.classList.add('opacity-50');
            surnameInput.classList.add('opacity-50');
        } else {
            nameInput.classList.remove('opacity-50');
            surnameInput.classList.remove('opacity-50');
        }
    };

    checkbox.addEventListener('change', function() {
        const isAnon = this.checked;
        updateState(isAnon);
        if (isAnon) {
            nameInput.value = '';
            surnameInput.value = '';
            typeSelect.value = 'anónimo';
        } else {
            typeSelect.value = 'firmado';
        }
    });

    // Initial state
    updateState(esAnonimo);

    // Manejar eliminación
    row.querySelector('.btn-remove-autor').addEventListener('click', function() {
        if (container.querySelectorAll('.autor-row').length > 1) {
            row.remove();
        } else {
            nameInput.value = '';
            surnameInput.value = '';
            checkbox.checked = false;
            updateState(false);
        }
    });

    // Manejar Biografía
    row.querySelector('.btn-bio-autor').addEventListener('click', function() {
        if (typeof window.openBioModal === 'function') {
            window.openBioModal(row.dataset.id, nameInput.value, surnameInput.value);
        }
    });

    // --- AUTOCOMPLETE PARA AUTORES (BASE DE DATOS CENTRAL) ---
    const setupAutocomplete = (input) => {
        let dropdown = document.createElement('div');
        dropdown.className = 'smart-autocomplete-dropdown autor-autocomplete';
        input.parentElement.style.position = 'relative';
        input.parentElement.appendChild(dropdown);

        let timeout = null;

        input.addEventListener('input', function() {
            clearTimeout(timeout);
            const query = this.value.trim();
            if (query.length < 2) {
                dropdown.classList.remove('show');
                return;
            }

            timeout = setTimeout(() => {
                fetch(`/api/autocomplete/autores_bio?q=${encodeURIComponent(query)}&limit=5`)
                .then(res => res.json())
                .then(data => {
                    if (data.length === 0) {
                        dropdown.classList.remove('show');
                        return;
                    }

                    dropdown.innerHTML = '';
                    data.forEach(aut => {
                        const item = document.createElement('div');
                        item.className = 'autocomplete-item p-2 border-bottom d-flex justify-content-between align-items-center';
                        
                        const label = document.createElement('div');
                        label.innerHTML = `<div class="fw-bold small text-light">${aut.apellido || ''}, ${aut.nombre || ''}</div>
                        ${aut.pseudonimo ? `<div class="text-warning" style="font-size: 0.75rem;">${aut.pseudonimo}</div>` : ''}`;
                        
                        item.appendChild(label);
                        
                        if (aut.es_externo) {
                            const badge = document.createElement('span');
                            badge.className = 'badge bg-primary ms-2';
                            badge.style.fontSize = '0.6rem';
                            badge.innerText = 'UNIVERSAL';
                            item.appendChild(badge);
                        }

                        item.addEventListener('click', () => {
                            nameInput.value = aut.nombre || '';
                            surnameInput.value = aut.apellido || '';
                            dropdown.classList.remove('show');
                            nameInput.dispatchEvent(new Event('change'));
                            surnameInput.dispatchEvent(new Event('change'));
                        });
                        dropdown.appendChild(item);
                    });

                    dropdown.classList.add('show');
                });
            }, 300);
        });

        // Cerrar al hacer click fuera
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    };

    setupAutocomplete(nameInput);
    setupAutocomplete(surnameInput);
};

// --- Lógica del Modal de Biografía (Global) ---
let bioModal = null;

window.openBioModal = function(rowId, nombre, apellido) {
    const bioModalEl = document.getElementById('modalAutorBio');
    if (!bioModalEl) {
        console.error('[Autores Dinámicos] Modal de biografía no encontrado en el DOM');
        return;
    }

    if (!bioModal) {
        bioModal = new bootstrap.Modal(bioModalEl);
        bioModalEl.addEventListener('shown.bs.modal', function () {
            if (typeof window.reinitDatePickers === 'function') {
                window.reinitDatePickers();
            }
        });
    }
    
    const rowIdInput = document.getElementById('bio_row_id');
    if (rowIdInput) rowIdInput.value = rowId;
    
    // Limpiar formulario antes de cargar
    const formBio = document.getElementById('formAutorBio');
    if (formBio) formBio.reset();

    const avatarContainer = document.getElementById('bio_avatar_container');
    if (avatarContainer) avatarContainer.innerHTML = `<i class="fa-solid fa-user" style="font-size: 2.5rem; color: #ffffff;"></i>`;
    
    const bioNombre = document.getElementById('bio_nombre');
    const bioApellido = document.getElementById('bio_apellido');
    if (bioNombre) bioNombre.value = nombre || '';
    if (bioApellido) bioApellido.value = apellido || '';

    // Buscar si ya existe biografía
    if (nombre || apellido) {
        fetch(`/autor/bio/get?nombre=${encodeURIComponent(nombre)}&apellido=${encodeURIComponent(apellido)}`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success' && data.bio) {
                const bio = data.bio;
                Object.keys(bio).forEach(key => {
                    const input = document.getElementById('bio_' + key);
                    if (input) input.value = bio[key] || '';
                });
                
                if (bio.foto && avatarContainer) {
                    avatarContainer.innerHTML = `<img src="/static/uploads/autores/${bio.foto}" alt="Avatar" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
                }
            }
        })
        .catch(err => console.error("Error al cargar biografía:", err));
    }

    bioModal.show();
};

// --- Lógica del Modal Visor (Lectura) ---
let visorModal = null;
window.openVisorModal = async function(nombre, apellido) {
    const visorEl = document.getElementById('modalAutorVisor');
    if (!visorEl) return;

    if (!visorModal) {
        visorModal = new bootstrap.Modal(visorEl);
    }

    // Limpiar campos
    visorEl.querySelectorAll('[id^="visor_"]').forEach(el => el.innerHTML = '');
    
    try {
        const response = await fetch(`/autor/bio/get?nombre=${encodeURIComponent(nombre)}&apellido=${encodeURIComponent(apellido)}`);
        const data = await response.json();

        if (data.status === 'success' && data.bio) {
            const bio = data.bio;
            const setSafeHTML = (id, html) => {
                const el = document.getElementById(id);
                if (el) el.innerHTML = html || '-';
            };

            setSafeHTML('visor_nombre_completo', `${bio.nombre || ''} ${bio.apellido || ''}`);
            setSafeHTML('visor_seudonimo', bio.seudonimo ? `"${bio.seudonimo}"` : '');
            setSafeHTML('visor_nacionalidad', bio.nacionalidad);
            
            // Completitud
            const progBar = document.getElementById('visor_progreso_bar');
            const progTxt = document.getElementById('visor_progreso_texto');
            if (progBar) progBar.style.width = `${bio.completitud || 0}%`;
            if (progTxt) progTxt.innerHTML = `${bio.completitud || 0}%`;

            // Foto / Avatar
            const avatarInner = document.querySelector('.visor-avatar-dossier-inner');
            if (avatarInner) {
                if (bio.foto) {
                    avatarInner.innerHTML = `<img src="/static/uploads/autores/${bio.foto}" alt="Avatar">`;
                } else {
                    avatarInner.innerHTML = `<i class="fa-solid fa-user-tie" style="font-size: 3.5rem; color: #333;"></i>`;
                }
            }
            
            const pBadge = document.getElementById('visor_proyecto_badge');
            if (pBadge && bio.proyecto_nombre) {
                pBadge.style.display = 'inline-flex';
                setSafeHTML('visor_proyecto_nombre', bio.proyecto_nombre);
            } else if (pBadge) {
                pBadge.style.display = 'none';
            }
            
            // 1. Cronología
            const birthStr = `${bio.lugar_nacimiento || ''} ${bio.fecha_nacimiento ? `(${bio.fecha_nacimiento})` : ''}`.trim();
            const deathStr = `${bio.lugar_defuncion || ''} ${bio.fecha_defuncion ? `(${bio.fecha_defuncion})` : ''}`.trim();
            setSafeHTML('visor_nacimiento', birthStr || '-');
            setSafeHTML('visor_defuncion', deathStr || '-');

            // 2. Trayectoria
            setSafeHTML('visor_trayectoria', bio.formacion_academica);
            setSafeHTML('visor_movimiento', bio.movimiento_literario);
            setSafeHTML('visor_influencias', bio.influencias);
            setSafeHTML('visor_ocupaciones', bio.ocupaciones_secundarias);
            
            // 3. Obra
            setSafeHTML('visor_generos', bio.generos_literarios);
            setSafeHTML('visor_tematicas', bio.tematicas_recurrentes);
            setSafeHTML('visor_estilo', bio.estilo);
            
            // Obras Principales (Formato lista si es posible)
            let obrasHtml = bio.obras_principales || '-';
            if (obrasHtml !== '-') {
                obrasHtml = obrasHtml.split('\n').map(line => `• ${line.trim()}`).join('<br>');
            }
            setSafeHTML('visor_obras', obrasHtml);

            // 4. Legado
            setSafeHTML('visor_premios', bio.premios);
            setSafeHTML('visor_impacto', bio.impacto);

            // 5. Adicional
            setSafeHTML('visor_citas', bio.citas ? `"${bio.citas}"` : '-');
            setSafeHTML('visor_fuentes', bio.bibliografia);
            
            // Enlaces de interés: Convertir texto a links clickeables
            let enlacesHtml = bio.enlaces || '-';
            if (enlacesHtml !== '-') {
                // Regex para detectar URLs (Http/Https/www)
                const urlRegex = /(https?:\/\/[^\s,]+|www\.[^\s,]+)/g;
                enlacesHtml = enlacesHtml.replace(urlRegex, function(url) {
                    const href = url.startsWith('http') ? url : 'http://' + url;
                    return `<a href="${href}" target="_blank" rel="noopener noreferrer">${url}</a>`;
                });
            }
            setSafeHTML('visor_enlaces', enlacesHtml);
            setSafeHTML('visor_notas', bio.notas);

            // Botón editar desde visor: Volver al modal original
            const btnEdit = document.getElementById('btnEditarDesdeVisor');
            if (btnEdit) {
                btnEdit.onclick = function() {
                    const modalEl = document.getElementById('modalAutorVisor');
                    const modalInstance = bootstrap.Modal.getInstance(modalEl);
                    if (modalInstance) modalInstance.hide();
                    openBioModal(bio.id || null, bio.nombre, bio.apellido);
                };
            }
            visorModal.show();
        } else {
            Swal.fire('Atención', data.message || 'No se encontró la biografía.', 'info');
        }
    } catch (error) {
        console.error("Error al cargar visor:", error);
        Swal.fire('Error', 'No se pudo cargar la información del autor.', 'error');
    }
};

/**
 * Listener para el botón de editar biografía desde la lista (Directo)
 */
document.addEventListener('click', function(e) {
    const btnEdit = e.target.closest('.btn-bio-autor-direct');
    if (btnEdit) {
        const nombre = btnEdit.getAttribute('data-nombre');
        const apellido = btnEdit.getAttribute('data-apellido');
        openBioModal(null, null, nombre, apellido);
    }
});


document.addEventListener('DOMContentLoaded', function() {
    const btnGuardarBio = document.getElementById('btnGuardarBio');
    if (btnGuardarBio) {
        btnGuardarBio.addEventListener('click', function() {
            const formBio = document.getElementById('formAutorBio');
            if (!formBio) return;

            const formData = new FormData(formBio);
            const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || document.querySelector('meta[name="csrf-token"]')?.content;

            fetch('/autor/bio/save', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            })
            .then(res => res.json())
            .then(res => {
                if (res.status === 'success') {
                    // Si estamos en un formulario dinámico (artículo), actualizar la fila
                    const rowIdInput = document.getElementById('bio_row_id');
                    if (rowIdInput && rowIdInput.value) {
                        const rowId = rowIdInput.value;
                        const row = document.getElementById(`autor-row-${rowId}`);
                        if (row) {
                            row.querySelector('input[name="nombre_autor[]"]').value = document.getElementById('bio_nombre').value;
                            row.querySelector('input[name="apellido_autor[]"]').value = document.getElementById('bio_apellido').value;
                        }
                    }

                    // Disparar evento para que otros componentes se enteren
                    document.dispatchEvent(new CustomEvent('bioSaved', { detail: res }));

                    Swal.fire({
                        icon: 'success',
                        title: '¡Guardado!',
                        text: 'La ficha biográfica se ha guardado correctamente.',
                        timer: 1500,
                        showConfirmButton: false,
                        background: '#294a60',
                        color: '#fff'
                    }).then(() => {
                        const bioModalEl = document.getElementById('modalAutorBio');
                        if (bioModalEl) {
                            const modal = bootstrap.Modal.getInstance(bioModalEl);
                            if (modal) modal.hide();
                        }
                    });
                } else {
                    Swal.fire('Error', res.message || 'No se pudo guardar la biografía', 'error');
                }
            })
            .catch(err => {
                console.error(err);
                Swal.fire('Error', 'Error de comunicación con el servidor', 'error');
            });
        });
    }

    const container = document.getElementById('autores-container');
    const btnAdd = document.getElementById('btn-add-autor');
    
    if (!container || !btnAdd) return;

    // Inicializar filas si hay datos o si está vacío
    if (container.querySelectorAll('.autor-row').length === 0) {
        const autoresJson = container.dataset.initial;
        if (autoresJson) {
            try {
                const autores = JSON.parse(autoresJson);
                console.log("[Autores Dinámicos] Datos iniciales:", autores);
                if (autores && autores.length > 0) {
                    autores.forEach(a => {
                        console.log(`[Autores Dinámicos] Añadiendo fila para: ${a.nombre} ${a.apellido} con pseudónimo: ${a.pseudonimo}`);
                        window.addAutorRow(a.nombre, a.apellido, a.tipo, a.es_anonimo, a.pseudonimo);
                    });
                }
            } catch (e) {
                console.error("Error al parsear autores iniciales:", e);
            }
        }
    }

    // Modal de búsqueda con SweetAlert2 al pulsar AÑADIR
    btnAdd.addEventListener('click', function() {
        Swal.fire({
            title: 'Añadir Autoría',
            html: `
                <div class="mb-3 text-start">
                    <label class="form-label text-muted small">Buscar Autor/a en Base de Datos</label>
                    <input id="swal-autor-search" class="form-control form-control-sirio" placeholder="Escribe nombre o apellido..." autocomplete="off">
                </div>
                <div id="swal-autor-results" class="list-group text-start custom-scrollbar border border-secondary rounded" style="max-height: 200px; overflow-y: auto; background: var(--v-bg, #111); display: none;"></div>
                
                <div class="mt-4 pt-3 border-top border-secondary border-opacity-25 text-start">
                    <span class="d-block text-muted small mb-2">¿No está en la lista o quieres añadir un seudónimo manual?</span>
                    <button id="swal-btn-nuevo" class="btn btn-sm btn-outline-warning w-100 fw-bold"><i class="fa-solid fa-plus me-1"></i>Añadir entrada manual vacía</button>
                </div>
            `,
            showConfirmButton: false,
            showCancelButton: true,
            cancelButtonText: 'Cerrar',
            background: document.documentElement.getAttribute('data-theme') === 'light' ? '#ffffff' : '#1a1a1a',
            color: document.documentElement.getAttribute('data-theme') === 'light' ? '#333333' : '#ffffff',
            didOpen: () => {
                const isLight = document.documentElement.getAttribute('data-theme') === 'light';
                const searchInput = document.getElementById('swal-autor-search');
                const resultsContainer = document.getElementById('swal-autor-results');
                const btnNuevo = document.getElementById('swal-btn-nuevo');

                // Estilos específicos para modo claro si es necesario
                if (isLight) {
                    searchInput.style.backgroundColor = '#f8f9fa';
                    searchInput.style.color = '#333';
                    searchInput.style.borderColor = '#ddd';
                    resultsContainer.classList.remove('bg-dark');
                    resultsContainer.classList.add('bg-white');
                    if (btnNuevo) {
                        btnNuevo.classList.remove('btn-outline-warning');
                        btnNuevo.classList.add('btn-outline-primary');
                    }
                }
                
                let timeout = null;
                
                const performSearch = (query) => {
                    fetch('/api/autocomplete/autores_bio?q=' + encodeURIComponent(query) + '&limit=15&t=' + Date.now())
                    .then(res => res.json())
                    .then(data => {
                        resultsContainer.innerHTML = '';
                        resultsContainer.style.display = 'block';
                        
                        if (data.length > 0) {
                            data.forEach(aut => {
                                const btn = document.createElement('button');
                                const textColor = isLight ? 'text-dark' : 'text-light';
                                btn.className = `list-group-item list-group-item-action bg-transparent ${textColor} border-bottom border-secondary border-opacity-25`;
                                btn.style.cursor = 'pointer';
                                btn.innerHTML = `
                                    <div class="d-flex justify-content-between align-items-center w-100 p-1">
                                        <div style="color: #294a60 !important; font-weight: 700 !important; font-family: monospace;">
                                            ${(aut.apellido || '').toUpperCase()}, ${aut.nombre || ''}
                                            ${aut.pseudonimo ? '<br><span class="text-muted small">(' + aut.pseudonimo + ')</span>' : ''}
                                        </div>
                                        <span class="badge ${aut.origen === 'Este proyecto' ? 'bg-primary' : 'bg-secondary'} ms-2" style="font-size: 0.6rem; opacity: 1; min-width: 80px;">
                                            ${aut.origen || 'Global'}
                                        </span>
                                    </div>
                                `;
                                btn.onclick = () => {
                                    window.addAutorRow(aut.nombre, aut.apellido, 'firmado', false);
                                    
                                    // Autofill global pseudónimo field for the publication if applicable
                                    if (aut.pseudonimo) {
                                        const psInput = document.querySelector('input[name="pseudonimo"]');
                                        if (psInput) {
                                            let currentVal = psInput.value.trim();
                                            if (currentVal && !currentVal.includes(aut.pseudonimo)) {
                                                psInput.value = currentVal + ", " + aut.pseudonimo;
                                            } else if (!currentVal) {
                                                psInput.value = aut.pseudonimo;
                                            }
                                        }
                                    }
                                    
                                    Swal.close();
                                };
                                resultsContainer.appendChild(btn);
                            });
                        } else {
                            resultsContainer.innerHTML = '<div class="p-3 text-muted small text-center">No se encontraron autores con ese nombre.</div>';
                        }
                    })
                    .catch(err => {
                        console.error(err);
                        resultsContainer.innerHTML = '<div class="p-3 text-danger small text-center">Error de conexión.</div>';
                    });
                };

                // Mostrar lista inicial vacía (últimos/populares)
                performSearch('');

                searchInput.addEventListener('input', function() {
                    clearTimeout(timeout);
                    const query = this.value.trim();
                    timeout = setTimeout(() => {
                        performSearch(query);
                    }, 300);
                });
                
                btnNuevo.onclick = () => {
                    window.addAutorRow('', '', 'firmado', false);
                    Swal.close();
                };

                setTimeout(() => searchInput.focus(), 100);
            }
        });
    });
});
