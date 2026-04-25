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
    
    // 🔍 Trigger inicial solo si hay valor y el contenedor de autores está vacío/inicial
    // Esto asegura que en "Nueva Referencia" con publicación precargada se hereden los autores
    const container = document.getElementById('autores-container');
    const esVacio = container && (container.querySelectorAll('.autor-row').length === 0 || 
                    (container.querySelectorAll('.autor-row').length === 1 && 
                     container.querySelector('input[name="nombre_autor[]"]').value === '' && 
                     container.querySelector('input[name="apellido_autor[]"]').value === ''));

    if (inputPublicacion.value.trim().length > 1 && esVacio) {
        cargarDatosPublicacion(inputPublicacion.value.trim());
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
                    console.log('[Publicación Autocomplete] Publicación seleccionada:', nuevoValor);
                    cargarDatosPublicacion(nuevoValor);
                }
            }
        }
    });
    
    function cargarDatosPublicacion(nombre) {
        console.log('[Publicación Autocomplete] Cargando datos para:', nombre);
        
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
                
                // Edición (frecuencia)
                const campoEdicion = document.querySelector('select[name="edicion"]');
                if (campoEdicion && datos.edicion) {
                    const edicion = datos.edicion.toLowerCase();
                    const opciones = Array.from(campoEdicion.options);
                    const opcion = opciones.find(opt => opt.value.toLowerCase() === edicion);
                    
                    if (opcion) {
                        campoEdicion.value = opcion.value;
                        console.log('[Publicación Autocomplete] ✓ Edición:', opcion.value);
                    }
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

                // Autores y Pseudónimo (HERENCIA SOLICITADA)
                if (datos.autores && datos.autores.length > 0) {
                    console.log('[Publicación Autocomplete] ✓ Autores encontrados:', datos.autores.length);
                    const container = document.getElementById('autores-container');
                    
                    const heredarAutores = () => {
                        if (container && typeof window.addAutorRow === 'function') {
                            const rows = container.querySelectorAll('.autor-row');
                            let vacias = true;
                            rows.forEach(r => {
                                if (r.querySelector('input[name="nombre_autor[]"]').value || 
                                    r.querySelector('input[name="apellido_autor[]"]').value) {
                                    vacias = false;
                                }
                            });

                            if (vacias) {
                                container.innerHTML = '';
                                datos.autores.forEach(aut => {
                                    window.addAutorRow(aut.nombre || '', aut.apellido || '', aut.tipo || 'firmado', aut.es_anonimo);
                                });
                            } else {
                                Swal.fire({
                                    title: '¿Heredar autores?',
                                    text: `La publicación "${nombre}" tiene autores definidos. ¿Deseas añadirlos a la lista actual?`,
                                    icon: 'question',
                                    showCancelButton: true,
                                    confirmButtonText: 'Sí, añadir',
                                    cancelButtonText: 'No',
                                    background: '#294a60',
                                    color: '#fff'
                                }).then((result) => {
                                    if (result.isConfirmed) {
                                        datos.autores.forEach(aut => {
                                            window.addAutorRow(aut.nombre || '', aut.apellido || '', aut.tipo || 'firmado', aut.es_anonimo);
                                        });
                                    }
                                });
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
