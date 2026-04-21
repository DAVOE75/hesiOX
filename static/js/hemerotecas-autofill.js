(function () {
    // Verificar que los datos de hemerotecas (inyectados desde el HTML) existen
    if (!window.HEMEROTECAS_DATA) {
        console.warn("HEMEROTECAS_DATA no está definido. Asegúrate de incluir el objeto JSON antes de este script.");
        return;
    }

    const selectHemeroteca = document.getElementById("selectHemeroteca"); // En editar
    // En nueva_publicacion el select se llama 'hemeroteca_id', intentamos buscar ambos por si acaso
    const selectElem = selectHemeroteca || document.querySelector("select[name='hemeroteca_id']");

    const inputFuente = document.getElementById("inputFuente") || document.querySelector("input[name='fuente']");
    const inputCiudad = document.getElementById("inputCiudad") || document.querySelector("input[name='ciudad']");
    const inputPais   = document.getElementById("inputPais") || document.querySelector("input[name='pais']");

    if (!selectElem) {
        // Si no hay selector de hemeroteca, no hace falta ejecutar nada (ej: en otras páginas)
        return;
    }

    /**
     * Rellena los campos basados en la hemeroteca seleccionada.
     * @param {string} id - ID de la hemeroteca
     * @param {boolean} force - Si es true, sobrescribe aunque haya texto.
     */
    function aplicarDatosHemeroteca(id, force) {
        if (!id) return;

        const h = window.HEMEROTECAS_DATA[id];
        if (!h) return;

        // 1. Fuente / Institución
        // Se sobrescribe si force=true (cambio manual de select) o si el campo está vacío
        if (inputFuente && (force || !inputFuente.value.trim())) {
            // Preferimos la 'institucion', si no hay, usamos el 'nombre'
            inputFuente.value = h.institucion || h.nombre || "";
        }

        // 2. Ciudad
        if (inputCiudad && (force || !inputCiudad.value.trim())) {
            inputCiudad.value = h.ciudad || "";
        }

        // 3. País
        if (inputPais && (force || !inputPais.value.trim())) {
            inputPais.value = h.pais || "";
        }

        // NOTA: No tocamos el "Formato" (selectFormatoFuente).
        // Ese campo lo define el usuario manualmente para la Publicación (Digital/Físico/Microfilm).
    }

    // 💡 EVENTO: Al CAMBIAR la hemeroteca en el desplegable
    selectElem.addEventListener("change", function () {
        const id = this.value;
        // force = true para que actualice la fuente al cambiar de hemeroteca
        aplicarDatosHemeroteca(id, true);   
    });

    // 💡 EVENTO: Al CARGAR la página (para ediciones o recargas)
    if (selectElem.value) {
        // force = false para no borrar lo que ya venga de la base de datos si estamos editando
        aplicarDatosHemeroteca(selectElem.value, false);  
    }

    console.log("✅ Sistema de autofill de hemerotecas inicializado.");
})();