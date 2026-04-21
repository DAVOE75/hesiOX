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
                
                // Descripción de la Publicación
                const campoDescripcionPub = document.querySelector('textarea[name="descripcion_publicacion"]');
                if (campoDescripcionPub && datos.descripcion_publicacion) {
                    campoDescripcionPub.value = datos.descripcion_publicacion;
                    console.log('[Publicación Autocomplete] ✓ Descripción Publicación:', datos.descripcion_publicacion);
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
