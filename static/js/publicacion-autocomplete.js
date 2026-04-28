/**
 * Autocompletar datos de publicación
 * Cuando se selecciona una publicación, autocompleta: edición, ciudad, país y fuente/institución
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('[Publicación Autocomplete] Script iniciado');
    
    const inputPublicacion = document.getElementById('input-publicacion');
    
    if (!inputPublicacion) {
        console.error('[Publicación Autocomplete] Input no encontrado');
        return;
    }
    
    console.log('[Publicación Autocomplete] Input encontrado correctamente');
    
    // SOLUCIÓN AL PROBLEMA DEL DOBLE CLIC: Forzar apertura del datalist al hacer clic
    inputPublicacion.addEventListener('click', function() {
        // Simular que el usuario está escribiendo para forzar la apertura
        if (this.value === '') {
            this.value = ' ';
            setTimeout(() => {
                this.value = '';
                this.focus();
            }, 10);
        }
    });
    
    // Detectar cuando se selecciona una opción del datalist
    let ultimoValor = inputPublicacion.value;
    
    // 🔍 Solo disparar automáticamente si estamos en un formulario NUEVO (sin ID de referencia)
    // o si el contenedor está realmente vacío.
    const isEditPage = window.location.pathname.includes('/editar/');
    
    const container = document.getElementById('autores-container');
    const esVacio = container && (container.querySelectorAll('.autor-row').length === 0 || 
                    (container.querySelectorAll('.autor-row').length === 1 && 
                     container.querySelector('input[name="nombre_autor[]"]').value === '' && 
                     container.querySelector('input[name="apellido_autor[]"]').value === ''));

    // En edición, NO disparamos automáticamente al cargar para evitar el molesto modal
    if (inputPublicacion.value.trim().length > 1 && esVacio && !isEditPage) {
        cargarDatosPublicacion(inputPublicacion.value.trim(), false);
    }

    inputPublicacion.addEventListener('input', function() {
        const nuevoValor = this.value.trim();
        
        // Solo actuar si el valor cambió realmente
        if (nuevoValor && nuevoValor !== ultimoValor) {
            ultimoValor = nuevoValor;
            
            // Verificar si es una opción válida del datalist
            const datalist = document.getElementById('lista_publicaciones');
            if (datalist) {
                const opciones = Array.from(datalist.options).map(opt => opt.value);
                
                if (opciones.includes(nuevoValor)) {
                    console.log('[Publicación Autocomplete] Publicación seleccionada manualmente:', nuevoValor);
                    cargarDatosPublicacion(nuevoValor, true); // true = cambio manual
                }
            }
        }
    });

    // Soporte para cuando el usuario escribe manualmente y pulsa Tab/Enter
    inputPublicacion.addEventListener('change', function() {
        const nuevoValor = this.value.trim();
        if (nuevoValor) {
            console.log('[Publicación Autocomplete] Cambio detectado en publicación:', nuevoValor);
            cargarDatosPublicacion(nuevoValor, true);
        }
    });
    
    function cargarDatosPublicacion(nombre, isManual = false) {
        console.log('[Publicación Autocomplete] Cargando datos para:', nombre, 'Manual:', isManual);
        
        fetch(`/api/publicacion_info/${encodeURIComponent(nombre)}`)
            .then(response => {
                if (!response.ok) {
                    if (response.status === 404) {
                        console.log('[Publicación Autocomplete] Publicación no encontrada en BD');
                        return null;
                    }
                    throw new Error('Error HTTP: ' + response.status);
                }
                return response.json();
            })
            .then(datos => {
                if (!datos) return;
                
                console.log('[Publicación Autocomplete] Datos recibidos:', datos);
                
                function setSelectValue(select, value) {
                    if (!select || !value) return;
                    
                    let choicesInstance = null;
                    if (window.choicesInstances && select.id && window.choicesInstances[select.id]) {
                        choicesInstance = window.choicesInstances[select.id];
                    } else if (select._choices) {
                        choicesInstance = select._choices;
                    }

                    if (choicesInstance && typeof choicesInstance.setChoiceByValue === 'function') {
                        choicesInstance.setChoiceByValue(String(value));
                    } else {
                        select.value = value;
                    }
                    
                    select.setAttribute('data-value', value);
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                }

                // Edición (frecuencia)
                const campoEdicion = document.querySelector('select[name="edicion"]');
                if (campoEdicion && datos.edicion) {
                    setSelectValue(campoEdicion, datos.edicion);
                    console.log('[Publicación Autocomplete] ✓ Edición:', datos.edicion);
                }
                
                // Ciudad
                const campoCiudad = document.querySelector('input[name="ciudad"]');
                if (campoCiudad && datos.ciudad) {
                    campoCiudad.value = datos.ciudad;
                    console.log('[Publicación Autocomplete] ✓ Ciudad:', datos.ciudad);
                }
                
                // País
                const campoPais = document.querySelector('input[name="pais_publicacion"]');
                if (campoPais && datos.pais_publicacion) {
                    campoPais.value = datos.pais_publicacion;
                    console.log('[Publicación Autocomplete] ✓ País:', datos.pais_publicacion);
                }
                
                // Idioma
                const campoIdioma = document.querySelector('select[name="idioma"]');
                if (campoIdioma && datos.idioma) {
                    let idiomaValue = datos.idioma.toLowerCase().trim();
                    const idiomaMapping = {
                        'español': 'es',
                        'espanol': 'es',
                        'spanish': 'es',
                        'es': 'es',
                        'italiano': 'it',
                        'italian': 'it',
                        'it': 'it',
                        'francés': 'fr',
                        'frances': 'fr',
                        'french': 'fr',
                        'fr': 'fr',
                        'inglés': 'en',
                        'ingles': 'en',
                        'english': 'en',
                        'en': 'en',
                        'portugués': 'pt',
                        'portugues': 'pt',
                        'portuguese': 'pt',
                        'pt': 'pt',
                        'catalán': 'ct',
                        'catalan': 'ct',
                        'ct': 'ct'
                    };
                    if (idiomaMapping[idiomaValue]) {
                        idiomaValue = idiomaMapping[idiomaValue];
                    }
                    setSelectValue(campoIdioma, idiomaValue);
                    console.log('[Publicación Autocomplete] ✓ Idioma:', idiomaValue);
                }
                
                // Institución
                const campoInstitucion = document.querySelector('.fuente-institucion-input');
                if (campoInstitucion && datos.institucion) {
                    campoInstitucion.value = datos.institucion;
                    console.log('[Publicación Autocomplete] ✓ Institución:', datos.institucion);
                }
                
                const campoDescripcionPub = document.querySelector('textarea[name="descripcion_publicacion"]');
                if (campoDescripcionPub && datos.descripcion_publicacion) {
                    campoDescripcionPub.value = datos.descripcion_publicacion;
                    console.log('[Publicación Autocomplete] ✓ Descripción Publicación:', datos.descripcion_publicacion);
                }

                // Colección
                const campoColeccion = document.querySelector('input[name="coleccion"]');
                if (campoColeccion && datos.coleccion) {
                    campoColeccion.value = datos.coleccion;
                    console.log('[Publicación Autocomplete] ✓ Colección:', datos.coleccion);
                }

                // Datos Teatrales Globales
                const campoActosTotales = document.querySelector('input[name="actos_totales"]');
                if (campoActosTotales && datos.actos_totales) {
                    campoActosTotales.value = datos.actos_totales;
                    console.log('[Publicación Autocomplete] ✓ Actos Totales:', datos.actos_totales);
                }

                const campoEscenasTotales = document.querySelector('input[name="escenas_totales"]');
                if (campoEscenasTotales && datos.escenas_totales) {
                    campoEscenasTotales.value = datos.escenas_totales;
                    console.log('[Publicación Autocomplete] ✓ Escenas Totales:', datos.escenas_totales);
                }

                const campoRepartoTotal = document.querySelector('textarea[name="reparto_total"]');
                if (campoRepartoTotal && datos.reparto_total) {
                    campoRepartoTotal.value = datos.reparto_total;
                    console.log('[Publicación Autocomplete] ✓ Reparto Total:', datos.reparto_total);
                }

                // Autores y Pseudónimo (HERENCIA INTELIGENTE)
                if (datos.autores && datos.autores.length > 0) {
                    console.log('[Publicación Autocomplete] ✓ Autores encontrados:', datos.autores.length);
                    const container = document.getElementById('autores-container');
                    
                    const heredarAutores = () => {
                        if (container && typeof window.addAutorRow === 'function') {
                            const rows = container.querySelectorAll('.autor-row');
                            let vacias = true;
                            let autoresActuales = [];
                            
                            rows.forEach(r => {
                                const n = r.querySelector('input[name="nombre_autor[]"]').value.trim();
                                const a = r.querySelector('input[name="apellido_autor[]"]').value.trim();
                                if (n || a) {
                                    vacias = false;
                                    autoresActuales.push(`${n}|${a}`.toLowerCase());
                                }
                            });

                            // Si está vacío, heredar sin preguntar
                            if (vacias) {
                                container.innerHTML = '';
                                datos.autores.forEach(aut => {
                                    window.addAutorRow(aut.nombre || '', aut.apellido || '', aut.tipo || 'firmado', aut.es_anonimo, aut.pseudonimo || '');
                                });
                            } else if (isManual) {
                                // Solo preguntar si es un cambio MANUAL y hay autores que NO están ya en la lista
                                const nuevos = datos.autores.filter(aut => 
                                    !autoresActuales.includes(`${aut.nombre || ''}|${aut.apellido || ''}`.toLowerCase())
                                );

                                if (nuevos.length > 0) {
                                    Swal.fire({
                                        title: '¿Heredar autores?',
                                        text: `La publicación "${nombre}" tiene autores definidos que no están en la lista. ¿Deseas añadirlos?`,
                                        icon: 'question',
                                        showCancelButton: true,
                                        confirmButtonText: 'Sí, añadir',
                                        cancelButtonText: 'No',
                                        background: '#294a60',
                                        color: '#fff'
                                    }).then((result) => {
                                        if (result.isConfirmed) {
                                            nuevos.forEach(aut => {
                                                window.addAutorRow(aut.nombre || '', aut.apellido || '', aut.tipo || 'firmado', aut.es_anonimo, aut.pseudonimo || '');
                                            });
                                        }
                                    });
                                }
                            }
                        } else {
                            console.warn('[Publicación Autocomplete] addAutorRow no disponible, reintentando en 100ms...');
                            setTimeout(heredarAutores, 100);
                        }
                    };
                    
                    heredarAutores();
                }

                const campoPseudo = document.querySelector('input[name="pseudonimo"]');
                if (campoPseudo && datos.pseudonimo) {
                    if (!campoPseudo.value) {
                        campoPseudo.value = datos.pseudonimo;
                    }
                }

                // Licencia (HERENCIA)
                const campoLicencia = document.querySelector('select[name="licencia"]');
                if (campoLicencia && datos.licencia) {
                    setSelectValue(campoLicencia, datos.licencia);
                    console.log('[Publicación Autocomplete] ✓ Licencia:', datos.licencia);
                }

                // Metadatos Dinámicos (Género, Subgénero, Periodicidad)
                // 1. Género (tipo_recurso)
                const campoRecurso = document.getElementById('selectRecurso') || document.querySelector('select[name="tipo_recurso"]');
                if (campoRecurso && (datos.tipo_recurso || datos.tipo_publicacion_base)) {
                    const tr = datos.tipo_recurso || datos.tipo_publicacion_base;
                    setSelectValue(campoRecurso, tr);
                    console.log('[Publicación Autocomplete] ✓ Recurso:', tr);
                }

                // 2. Subgénero (tipo_publicacion)
                const campoSubgenero = document.getElementById('selectTipoPublicacion') || document.querySelector('select[name="tipo_publicacion"]');
                if (campoSubgenero && (datos.tipo_publicacion || datos.subtipo_base)) {
                    const sp = datos.tipo_publicacion || datos.subtipo_base;
                    setSelectValue(campoSubgenero, sp);
                    console.log('[Publicación Autocomplete] ✓ Subgénero:', sp);
                }

                // 3. Periodicidad
                const campoPeriodicidad = document.getElementById('selectPeriodicidad') || document.querySelector('select[name="periodicidad"]');
                if (campoPeriodicidad && datos.periodicidad) {
                    setSelectValue(campoPeriodicidad, datos.periodicidad);
                    console.log('[Publicación Autocomplete] ✓ Periodicidad:', datos.periodicidad);
                }
                
                // Feedback visual
                inputPublicacion.style.borderColor = '#28a745';
                setTimeout(() => {
                    inputPublicacion.style.borderColor = '';
                }, 1000);
                
            })
            .catch(error => {
                console.error('[Publicación Autocomplete] Error:', error);
            });
    }
});
