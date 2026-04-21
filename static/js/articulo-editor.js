// ============================================================
// 📝 EDITOR DE ARTÍCULOS CIENTÍFICOS (Quill)
// Sistema completo de edición de artículos académicos
// ============================================================

/* eslint-disable */
// @ts-nocheck

class ArticuloEditor {
    constructor(articuloId, proyectoId) {
        this.articuloId = articuloId;
        this.proyectoId = proyectoId;
        this.seccionActual = 'portada';
        this.ultimoEditorEnfocado = null;

        this.datosArticulo = {
            id: articuloId,
            proyectoId: proyectoId,
            titulo: '',
            subtitulo: '',
            autores: [],
            resumen_es: '',
            abstract_en: '',
            palabras_clave: [],
            keywords: [],
            secciones: {},
            referencias: [],
            figuras: []
        };

        this.init();
    }

    init() {
        console.log('🔬 Inicializando Editor de Artículos Científicos');

        // Ya no dependemos de TinyMCE, usamos Quill que se inicializa en el HTML
        // Verificar que Quill esté disponible
        if (typeof Quill === 'undefined') {
            console.warn('⚠️ Quill no está cargado aún, esperando...');
        }

        // Configurar cuando el DOM esté listo
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        console.log('✓ Configurando editor de artículos...');

        // 1. Inicializar Quill en los contenedores designados
        this.inicializarQuill();

        // 2. Configurar autoguardado
        this.configurarAutoguardado();

        // 3. Inicializar navegación de secciones
        this.inicializarNavegacionSecciones();

        // 4. Actualizar estadísticas automáticamente
        this.actualizarEstadisticas();

        // 5. Configurar modal de citas
        this.configurarModalCitas();

        console.log('✅ Editor de artículos científicos listo');
    }

    // ========================================
    // INICIALIZACIÓN DE QUILL
    // ========================================

    inicializarQuill() {
        const editorIds = ['resumen-es', 'abstract-en', 'introduccion', 'metodologia', 'resultados', 'discusion', 'conclusiones', 'referencias'];
        const toolbarOptions = [
            [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
            [{ 'font': [] }],
            [{ 'size': ['small', false, 'large', 'huge'] }],
            ['bold', 'italic', 'underline', 'strike'],
            [{ 'script': 'sub' }, { 'script': 'super' }],
            [{ 'color': [] }, { 'background': [] }],
            [{ 'list': 'ordered' }, { 'list': 'bullet' }, { 'list': 'check' }],
            [{ 'indent': '-1' }, { 'indent': '+1' }],
            [{ 'align': [] }],
            ['blockquote', 'code-block'],
            ['link', 'image', 'video'],
            ['clean']
        ];

        window.quillEditors = window.quillEditors || {};

        editorIds.forEach(id => {
            const selector = '#' + id;
            const element = document.querySelector(selector);
            if (!element) return;

            const placeholder = element.dataset.placeholder || 'Escriba aquí...';
            let initialContent = element.innerHTML.trim();

            // Decodificar entidades HTML de forma recursiva (para casos de doble escape)
            const decodeHTMLEntities = (text) => {
                const textarea = document.createElement('textarea');
                textarea.innerHTML = text;
                return textarea.value;
            };

            let prevContent = '';
            while (initialContent !== prevContent && initialContent.includes('&')) {
                prevContent = initialContent;
                initialContent = decodeHTMLEntities(initialContent);
            }

            element.innerHTML = ''; // Limpiar para Quill

            const quill = new Quill(selector, {
                theme: 'snow',
                modules: { toolbar: toolbarOptions },
                placeholder: placeholder,
            });

            // Guardar globalmente
            window.quillEditors[id] = quill;

            // Cargar contenido decodificado
            quill.clipboard.dangerouslyPasteHTML(0, initialContent);

            // Sincronizar con campos ocultos
            quill.on('text-change', () => {
                const hiddenField = document.getElementById(id + '-hidden');
                if (hiddenField) hiddenField.value = quill.root.innerHTML;
                this.marcarComoModificado();
            });

            // Registrar enfoque para inserción de citas
            quill.on('selection-change', (range) => {
                if (range) this.ultimoEditorEnfocado = quill;
            });
        });
    }

    // ========================================
    // NAVEGACIÓN Y SECCIONES
    // ========================================

    inicializarNavegacionSecciones() {
        const botonesEstructura = document.querySelectorAll('.estructura-item');
        const container = document.querySelector('.desktop-content');
        // Ajustamos el offset para que el título no quede tapado por la navbar del editor
        const offsetAdjust = 100; 

        botonesEstructura.forEach(boton => {
            boton.addEventListener('click', (e) => {
                e.preventDefault();
                const seccionId = boton.dataset.seccion;
                let targetId = `seccion-${seccionId}`;
                
                const element = document.getElementById(targetId);
                if (element && container) {
                    // Calculamos la posición relativa al contenedor principal de scroll
                    const topPos = element.offsetTop - offsetAdjust;
                    
                    container.scrollTo({ 
                        top: topPos, 
                        behavior: 'smooth' 
                    });
                    
                    // Marcar como activo en el menú
                    botonesEstructura.forEach(b => b.classList.remove('activo', 'active'));
                    boton.classList.add('activo', 'active');
                    this.seccionActual = seccionId;
                }
            });
        });
    }

    agregarAutor() {
        const container = document.getElementById('autores-lista');
        if (!container) return;

        const nuevoAutor = document.createElement('div');
        nuevoAutor.className = 'autor-item d-flex align-items-center gap-3 mt-2';
        nuevoAutor.innerHTML = `
            <div class="icon-autor text-secondary bg-secondary bg-opacity-10 p-2 rounded">
                <i class="fa-solid fa-user"></i>
            </div>
            <div>
                <div class="autor-nombre" contenteditable="true" data-placeholder="Nombre Co-autor">Nombre Co-autor</div>
                <div class="autor-afiliacion small text-muted" contenteditable="true" data-placeholder="Afiliación">Afiliación</div>
            </div>
            <button class="btn btn-sm text-danger" onclick="this.parentElement.remove()"><i class="fa-solid fa-times"></i></button>
        `;
        container.appendChild(nuevoAutor);
        this.marcarComoModificado();
    }

    agregarSeccion() {
        const nombreSeccion = prompt("Introduzca el nombre de la nueva sección:", "Nueva Sección");
        if (!nombreSeccion) return;

        const mainContainer = document.querySelector('.editor-content-container');
        if (!mainContainer) return;

        const seccionId = 'seccion-custom-' + Date.now();
        const editorId = 'custom-' + Date.now();

        const nuevaSeccionHTML = `
            <section class="seccion-cuerpo" id="${seccionId}" style="margin-top: 60px;">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h4 class="seccion-titulo m-0">${nombreSeccion}</h4>
                    <button class="btn btn-sm btn-outline-danger" onclick="this.closest('section').remove(); window.articuloEditor.actualizarMenuEstructura();">
                        <i class="fa-solid fa-trash me-1"></i> Eliminar Sección
                    </button>
                </div>
                <div class="quill-editor" id="${editorId}" data-placeholder="Redacte el contenido de ${nombreSeccion}..."
                    style="min-height: 300px;"></div>
                <input type="hidden" name="${editorId}" id="${editorId}-hidden">
            </section>
        `;

        // Insertar antes de las referencias
        const referenciasSeccion = document.getElementById('seccion-referencias');
        if (referenciasSeccion) {
            referenciasSeccion.insertAdjacentHTML('beforebegin', nuevaSeccionHTML);
        } else {
            mainContainer.insertAdjacentHTML('beforeend', nuevaSeccionHTML);
        }

        // Inicializar Quill para la nueva sección
        this.inicializarQuillIndividual(editorId);
        
        // Añadir al menú de estructura
        this.actualizarMenuEstructura();
        
        // Scroll a la nueva sección
        setTimeout(() => {
            const el = document.getElementById(seccionId);
            if (el) el.scrollIntoView({ behavior: 'smooth' });
        }, 100);
    }

    inicializarQuillIndividual(id) {
        const toolbarOptions = [
            [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
            ['bold', 'italic', 'underline', 'strike'],
            [{ 'list': 'ordered' }, { 'list': 'bullet' }],
            ['link', 'image', 'video'],
            ['clean']
        ];

        const selector = '#' + id;
        const element = document.querySelector(selector);
        if (!element) return;

        const quill = new Quill(selector, {
            theme: 'snow',
            modules: { toolbar: toolbarOptions },
            placeholder: element.dataset.placeholder || 'Escriba aquí...',
        });

        window.quillEditors[id] = quill;

        quill.on('text-change', () => {
            const hiddenField = document.getElementById(id + '-hidden');
            if (hiddenField) hiddenField.value = quill.root.innerHTML;
            this.marcarComoModificado();
        });
    }

    actualizarMenuEstructura() {
        const menu = document.querySelector('.editor-navbar-combined .overflow-auto');
        if (!menu) return;

        // Limpiar botones de secciones custom anteriores
        const customButtons = menu.querySelectorAll('.estructura-custom');
        customButtons.forEach(b => b.remove());

        // Buscar todas las secciones custom
        const seccionesCustom = document.querySelectorAll('section[id^="seccion-custom-"]');
        seccionesCustom.forEach(sec => {
            const titulo = sec.querySelector('.seccion-titulo').textContent;
            const id = sec.id.replace('seccion-', '');
            
            const btn = document.createElement('button');
            btn.className = 'estructura-item estructura-custom btn btn-sm';
            btn.dataset.seccion = id;
            btn.style.cssText = 'background: var(--editor-toolbar-bg); color: var(--editor-text); border: 1px solid var(--editor-border);';
            btn.innerHTML = `<i class="fa-solid fa-bookmark me-1"></i> ${titulo}`;
            
            // Añadir listener
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = `seccion-${id}`;
                const element = document.getElementById(targetId);
                const offsetAdjust = 140;
                if (element) {
                    const topPos = element.getBoundingClientRect().top + window.pageYOffset - offsetAdjust;
                    window.scrollTo({ top: topPos, behavior: 'smooth' });
                }
            });

            // Insertar antes del botón "Agregar Sección"
            const btnAgregar = menu.querySelector('button[onclick="agregarSeccion()"]');
            if (btnAgregar) {
                menu.insertBefore(btn, btnAgregar);
            }
        });
    }

    // ========================================
    // FUNCIONES AUXILIARES QUILL
    // ========================================

    // Función de compatibilidad - ya no se usa con Quill
    // Los editores se inicializan directamente en el HTML

    // ========================================
    // ESTADÍSTICAS AUTOMÁTICAS
    // ========================================

    actualizarEstadisticas() {
        // Contar palabras en resumen y abstract desde Quill
        const resumenEditor = window.quillEditors?.['resumen-es'];
        const abstractEditor = window.quillEditors?.['abstract-en'];

        const resumen = resumenEditor ? resumenEditor.getText() : '';
        const abstract = abstractEditor ? abstractEditor.getText() : '';

        const contadorResumen = document.getElementById('contador-resumen');
        const contadorAbstract = document.getElementById('contador-abstract');

        if (contadorResumen) {
            contadorResumen.textContent = this.contarPalabras(resumen);
        }
        if (contadorAbstract) {
            contadorAbstract.textContent = this.contarPalabras(abstract);
        }

        // Contar palabras totales de todos los editores Quill
        let palabrasTotales = 0;

        if (window.quillEditors) {
            Object.values(window.quillEditors).forEach(editor => {
                try {
                    const contenido = editor.getText();
                    palabrasTotales += this.contarPalabras(contenido);
                } catch (e) {
                    console.warn('Error al obtener contenido de editor Quill:', e);
                }
            });
        }

        // Añadir palabras del resumen/abstract
        palabrasTotales += this.contarPalabras(resumen);
        palabrasTotales += this.contarPalabras(abstract);

        // Actualizar estadísticas en el DOM
        const totalPalabrasEl = document.getElementById('total-palabras');
        if (totalPalabrasEl) totalPalabrasEl.textContent = palabrasTotales;

        const totalPaginasEl = document.getElementById('total-paginas');
        if (totalPaginasEl) {
            totalPaginasEl.textContent = Math.ceil(palabrasTotales / 300);
        }

        // Actualizar total de referencias
        const totalRefEl = document.getElementById('total-referencias');
        if (totalRefEl && this.datosArticulo.referencias) {
            totalRefEl.textContent = this.datosArticulo.referencias.length;
        }

        // Actualizar citas insertadas
        this.actualizarContadorCitas();

        // Contar figuras
        this.actualizarContadorFiguras();

        // Repetir cada 3 segundos
        setTimeout(() => this.actualizarEstadisticas(), 3000);
    }

    contarPalabras(texto) {
        if (!texto) return 0;
        return texto.split(/\s+/).filter(w => w.length > 0).length;
    }

    actualizarContadorCitas() {
        let contador = 0;

        try {
            if (window.quillEditors) {
                Object.values(window.quillEditors).forEach(editor => {
                    try {
                        const container = editor.root;
                        if (container && container.querySelectorAll) {
                            contador += container.querySelectorAll('.cite-ref').length;
                        }
                    } catch (e) { }
                });
            }

            // Contar también en DOM principal
            contador += document.querySelectorAll('.cite-ref').length;
        } catch (e) {
            console.warn('Error al contar citas:', e);
        }

        const totalCitasEl = document.getElementById('total-citas');
        if (totalCitasEl) totalCitasEl.textContent = contador;
    }

    actualizarContadorFiguras() {
        let figuras = 0;

        if (window.quillEditors) {
            Object.values(window.quillEditors).forEach(editor => {
                try {
                    const container = editor.root;
                    if (container) {
                        figuras += (container.querySelectorAll('img').length || 0);
                    }
                } catch (e) { }
            });
        }

        const totalFigurasEl = document.getElementById('total-figuras');
        if (totalFigurasEl) totalFigurasEl.textContent = figuras;
    }

    // ========================================
    // AUTOGUARDADO
    // ========================================

    configurarAutoguardado() {
        // Guardar cada 2 minutos
        setInterval(() => {
            this.guardarBorrador(true);
        }, 120000);

        console.log('✓ Autoguardado configurado (cada 2 minutos)');
    }

    guardarBorrador(auto = false) {
        const indicador = document.getElementById('indicador-guardado');
        const texto = document.getElementById('texto-guardado');

        if (indicador) indicador.classList.add('guardando');
        if (texto) texto.textContent = 'Guardando...';

        this.recopilarDatosFormulario();

        fetch('/api/articulos/guardar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.datosArticulo)
        })
            .then(res => res.json())
            .then(data => {
                if (indicador) indicador.classList.remove('guardando');
                if (texto) {
                    texto.textContent = auto
                        ? 'Autoguardado ' + new Date().toLocaleTimeString()
                        : 'Guardado correctamente';
                }
                if (data.id && !this.datosArticulo.id) {
                    this.datosArticulo.id = data.id;
                }

                // Notificar al usuario si fue guardado manual
                if (!auto && typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: '¡Guardado!',
                        text: 'Los cambios del artículo se han guardado correctamente.',
                        icon: 'success',
                        timer: 2000,
                        showConfirmButton: false,
                        toast: true,
                        position: 'top-end'
                    });
                }
            })
            .catch(err => {
                if (texto) texto.textContent = 'Error al guardar';
                console.error('Error al guardar:', err);

                if (!auto && typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'Error',
                        text: 'No se pudieron guardar los cambios. ' + err,
                        icon: 'error'
                    });
                }
            });
    }

    recopilarDatosFormulario() {
        // Recopilar datos de portada
        this.datosArticulo.titulo = document.getElementById('titulo-articulo')?.value || '';
        this.datosArticulo.subtitulo = document.getElementById('subtitulo-articulo')?.value || '';

        // Recopilar resúmenes desde Quill
        const resumenEditor = window.quillEditors?.['resumen-es'];
        const abstractEditor = window.quillEditors?.['abstract-en'];
        this.datosArticulo.resumen_es = resumenEditor ? resumenEditor.root.innerHTML : '';
        this.datosArticulo.abstract_en = abstractEditor ? abstractEditor.root.innerHTML : '';
        
        // Recopilar palabras clave (asegurando nombres correctos para backend)
        this.datosArticulo.palabras_clave = this.datosArticulo.palabras_clave_es || [];
        this.datosArticulo.keywords = this.datosArticulo.keywords_en || [];

        // Recopilar contenido de secciones desde Quill
        this.datosArticulo.secciones = {};

        if (window.quillEditors) {
            Object.entries(window.quillEditors).forEach(([id, editor]) => {
                // Excluir resumen y abstract que ya se recopilaron de forma específica si se desea,
                // pero el backend espera 'secciones' como un objeto de todos los contenidos.
                // Según app.py line 8340: contenido_json = json.dumps(datos.get('secciones', []))
                // Espera una lista o un objeto? app.py line 8344: calcular_palabras_totales(datos.get('secciones', []))
                this.datosArticulo.secciones[id] = editor.root.innerHTML;
            });
        }
    }

    marcarComoModificado() {
        const texto = document.getElementById('texto-guardado');
        if (texto && !texto.textContent.includes('modificado')) {
            texto.textContent = 'Cambios sin guardar';
        }
    }

    // ========================================
    // MODAL DE CITAS
    // ========================================

    configurarModalCitas() {
        // Los botones del DOM ya llaman a estas funciones globales
        // Solo necesitamos asegurarnos de que existan
        window.abrirModalCitas = () => this.abrirModalCitas();
        window.cerrarModalCitas = () => this.cerrarModalCitas();
        window.insertarCita = (refId, formato) => this.insertarCita(refId, formato);
        window.insertarBibliografiaCompleta = () => this.insertarBibliografiaCompleta();
        window.agregarSeccion = () => this.agregarSeccion();
    }

    abrirModalCitas() {
        const modal = document.getElementById('modal-citas');
        if (modal) {
            modal.classList.add('activo');
            this.cargarReferencias();
        }
    }

    cerrarModalCitas() {
        const modal = document.getElementById('modal-citas');
        if (modal) {
            modal.classList.remove('activo');
        }
    }

    cargarReferencias() {
        const listaReferencias = document.getElementById('lista-referencias');
        if (!listaReferencias) return;

        listaReferencias.innerHTML = '<p style="text-align:center;color:#999;">Cargando referencias...</p>';

        fetch(`/api/proyectos/${this.proyectoId}/referencias`)
            .then(res => res.json())
            .then(referencias => {
                if (referencias.length === 0) {
                    listaReferencias.innerHTML = '<p style="text-align:center;color:#999;">No hay referencias en este proyecto</p>';
                    return;
                }

                this.datosArticulo.referencias = referencias;
                this.renderizarReferencias(referencias);
            })
            .catch(err => {
                console.error('Error al cargar referencias:', err);
                listaReferencias.innerHTML = '<p style="text-align:center;color:#ff5252;">Error al cargar referencias</p>';
            });
    }

    renderizarReferencias(referencias) {
        const lista = document.getElementById('lista-referencias');
        if (!lista) return;

        lista.innerHTML = referencias.map((ref, idx) => `
            <div class="referencia-item d-flex justify-content-between align-items-center"
                 style="padding:10px; border-bottom: 1px solid var(--editor-border); transition: background 0.2s;">
                <div style="cursor:pointer; flex: 1;" onclick="window.articuloEditor.insertarCita(${ref.id})">
                    <div class="referencia-titulo" style="font-weight:600; color:var(--editor-accent);">
                        ${ref.numero_referencia ? `[${ref.numero_referencia}] ` : ''}${ref.titulo || 'Sin título'}
                    </div>
                    <div class="referencia-meta" style="font-size:0.85rem; opacity:0.8;">
                        ${ref.autor || 'Autor desconocido'} • ${ref.fecha || 'S.f.'}
                        ${ref.medio ? ' • ' + ref.medio : ''}
                    </div>
                </div>
                <button class="btn btn-sm btn-sirio mt-0 mb-0 ms-2" onclick="window.articuloEditor.insertarUnaBibliografia(${ref.id})" title="Añadir al recuadro de Bibliografía">
                    <i class="fa-solid fa-plus me-1"></i> Bibliografía
                </button>
            </div>
        `).join('');
    }

    insertarCita(refId) {
        const referencia = this.datosArticulo.referencias.find(r => r.id === refId);
        if (!referencia) {
            console.error('Referencia no encontrada:', refId);
            return;
        }

        const estiloSelect = document.getElementById('estilo-citas');
        const formato = estiloSelect ? estiloSelect.value : 'apa';

        // Generar texto de cita según formato
        const textoCita = this.generarCita(referencia, formato);

        // Insertar en el editor enfocado (Quill)
        if (this.ultimoEditorEnfocado) {
            const range = this.ultimoEditorEnfocado.getSelection(true);
            const citaHTML = `<span class="cite-ref" data-ref-id="${refId}" style="color:var(--editor-accent); font-weight:600;">${textoCita}</span>`;
            this.ultimoEditorEnfocado.clipboard.dangerouslyPasteHTML(range.index, citaHTML);
            this.ultimoEditorEnfocado.setSelection(range.index + textoCita.length);
        } else {
            alert('Por favor, haga clic en el área de texto donde desea insertar la cita');
        }

        this.cerrarModalCitas();
    }

    generarCita(ref, formato) {
        // En cualquier formato, si tiene número de referencia asignado como cita principal, se usa (e.g Vancouver o corchetes nativos)
        if (ref.numero_referencia && (formato === 'vancouver' || formato === 'ieee')) {
            return `[${ref.numero_referencia}]`;
        }
        
        const autor = ref.autor ? ref.autor.split(',')[0] : 'S.a.';
        const anio = ref.fecha ? new Date(ref.fecha).getFullYear() || ref.fecha : 's.f.';
        
        switch (formato) {
            case 'apa':
                return `(${autor}, ${anio})`;
            case 'chicago':
                return `(${autor} ${anio})`;
            case 'mla':
                return `(${autor})`;
            default:
                if (ref.numero_referencia) return `[${ref.numero_referencia}]`;
                return `(${autor}, ${anio})`;
        }
    }

    generarReferenciaBibliograficaCompleta(ref, formato) {
        const numero = ref.numero_referencia ? `[${ref.numero_referencia}] ` : '';
        const autor = ref.autor || 'Anónimo';
        const titulo = ref.titulo || 'Sin título';
        const medio = ref.medio || '';
        const fecha = ref.fecha || 'S.f.';
        const url = ref.url ? `Disponible en: <a href="${ref.url}">${ref.url}</a>` : '';
        
        // Versión simplificada para todos los estilos (unificar en el futuro para mayor rigor académico)
        let cita = `${autor}. `;
        if (formato === 'apa') {
            cita += `(${fecha}). <i>${titulo}</i>. ${medio}. ${url}`;
        } else {
            cita += `<i>${titulo}</i>. ${medio}. ${fecha}. ${url}`;
        }
        
        return `${numero}${cita}`;
    }

    insertarUnaBibliografia(refId) {
        const referencia = this.datosArticulo.referencias.find(r => r.id === refId);
        if (!referencia) return;

        const estiloSelect = document.getElementById('estilo-citas');
        const formato = estiloSelect ? estiloSelect.value : 'apa';
        const citaStr = this.generarReferenciaBibliograficaCompleta(referencia, formato);
        
        // Obtener el editor de la sección Referencias
        const refEditor = window.quillEditors && window.quillEditors['referencias'];
        if (refEditor) {
            const length = refEditor.getLength();
            const liHTML = `<p>${citaStr}</p>`;
            refEditor.clipboard.dangerouslyPasteHTML(length, liHTML);
            alert('Referencia individual añadida al recuadro inferior de Bibliografía.');
        } else {
            alert('No se pudo encontrar el editor de Referencias.');
        }
        
        this.cerrarModalCitas();
    }

    insertarBibliografiaCompleta() {
        if (!this.datosArticulo.referencias || this.datosArticulo.referencias.length === 0) {
            alert('No hay referencias para insertar');
            return;
        }

        const estiloSelect = document.getElementById('estilo-citas');
        const formato = estiloSelect ? estiloSelect.value : 'apa';

        // Ordenar por número de referencia
        const sortedRef = [...this.datosArticulo.referencias].sort((a, b) => {
            return (a.numero_referencia || 0) - (b.numero_referencia || 0);
        });

        let bibliografiaHTML = '<div class="bibliografia-generada"><h3>Referencias Bibliográficas</h3><ul style="list-style: none; padding-left: 0;">';

        sortedRef.forEach(ref => {
            const cita = this.generarReferenciaBibliograficaCompleta(ref, formato);
            bibliografiaHTML += `<li style="margin-bottom: 8px;">${cita}</li>`;
        });

        bibliografiaHTML += '</ul></div><p><br></p>';

        if (this.ultimoEditorEnfocado) {
            const range = this.ultimoEditorEnfocado.getSelection(true);
            this.ultimoEditorEnfocado.clipboard.dangerouslyPasteHTML(range.index, bibliografiaHTML);
        } else {
            alert('Por favor, haga clic en el área de texto donde desea insertar la bibliografía');
        }

        this.cerrarModalCitas();
    }
}

// ========================================
// FUNCIONES GLOBALES DE ACCIONES
// ========================================

window.guardarBorrador = function () {
    if (window.articuloEditor) {
        window.articuloEditor.guardarBorrador(false);
    }
};

window.previsualizarPDF = function () {
    alert('Función de vista previa en desarrollo');
    // TODO: Implementar generación de PDF
};

window.guardarYPublicar = function () {
    if (confirm('¿Está seguro de que desea publicar este artículo?')) {
        if (window.articuloEditor) {
            window.articuloEditor.guardarBorrador(false);
            // TODO: Marcar como publicado
            alert('Artículo guardado. La publicación real se implementará próximamente.');
        }
    }
};

// ========================================
// EXPORTAR PARA USO GLOBAL
// ========================================

// --- MODAL DE EDICIÓN RÁPIDA (En desarrollo por la interfaz global) ---
window.abrirEdicionRapidaReferencia = function(refId) {
    if (window.articuloEditor) {
        window.articuloEditor.abrirEdicionRapidaReferencia(refId);
    }
}
window.ArticuloEditor = ArticuloEditor;

console.log('✓ articulo-editor.js cargado');
