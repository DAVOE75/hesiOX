/**
 * Módulo de Comparación de Reuso Textual
 * Proyecto Sirio
 */

(function () {
    // Función para resaltar n-gramas en el texto
    function highlightText(text, fragments) {
        if (!text || !fragments || fragments.length === 0) return text || "";

        let highlighted = text;
        // Ordenar fragmentos por longitud descendente para evitar problemas de anidamiento parcial
        const sortedFragments = [...fragments].sort((a, b) => b.length - a.length);

        sortedFragments.forEach(frag => {
            if (frag.length < 10) return; // Evitar resaltar cosas demasiado cortas que pueden dar falsos positivos

            // Escapar caracteres especiales para el regex
            const escaped = frag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`(${escaped})`, 'gi');
            highlighted = highlighted.replace(regex, '<span class="reuso-highlight" title="Fragmento compartido">$1</span>');
        });

        return highlighted;
    }

    // Inicializar el comparador
    function initReusoComparator() {
        // Usar delegación de eventos para los badges que se inyectan dinámicamente
        document.addEventListener('click', async function (e) {
            const btn = e.target.closest('.btn-comparar-reuso');
            if (!btn) return;

            const id1 = btn.getAttribute('data-id1');
            const id2 = btn.getAttribute('data-id2');
            const fragments = JSON.parse(btn.getAttribute('data-fragments') || '[]');

            if (!id1 || !id2) return;

            // Mostrar modal (Bootstrap 5)
            const modalEl = document.getElementById('modalReuso');
            const modal = new bootstrap.Modal(modalEl);
            modal.show();

            // Reset contenidos
            document.getElementById('reuso-doc1-content').innerHTML = '<div class="p-5 text-center"><i class="fa-solid fa-spinner fa-spin fa-2x text-warning"></i><br>Cargando...</div>';
            document.getElementById('reuso-doc2-content').innerHTML = '<div class="p-5 text-center"><i class="fa-solid fa-spinner fa-spin fa-2x text-warning"></i><br>Cargando...</div>';

            try {
                const response = await fetch('/api/analisis/reuso-detalle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id1, id2 })
                });

                if (!response.ok) {
                    const text = await response.text();
                    console.error('Error response from server:', text);
                    throw new Error(`Servidor respondió con estado ${response.status}`);
                }

                const data = await response.json();
                if (!data.exito) throw new Error(data.error);

                // Actualizar Meta
                document.getElementById('doc1-pub').textContent = (data.doc1.publicacion || 'Desconocido') + ' (' + (data.doc1.fecha || 'S/F') + ')';
                document.getElementById('doc1-title').textContent = data.doc1.titulo || 'Sin título';
                document.getElementById('doc2-pub').textContent = (data.doc2.publicacion || 'Desconocido') + ' (' + (data.doc2.fecha || 'S/F') + ')';
                document.getElementById('doc2-title').textContent = data.doc2.titulo || 'Sin título';

                // Resaltar y mostrar
                document.getElementById('reuso-doc1-content').innerHTML = highlightText(data.doc1.contenido, fragments);
                document.getElementById('reuso-doc2-content').innerHTML = highlightText(data.doc2.contenido, fragments);

            } catch (err) {
                console.error('Error al cargar detalle de reuso:', err);
                const errorMsg = `<div class="alert alert-danger m-4">
                    <i class="fa-solid fa-triangle-exclamation me-2"></i>
                    <strong>Error:</strong> ${err.message}<br>
                    <small class="text-muted">Ver detalles en la consola del navegador.</small>
                </div>`;
                document.getElementById('reuso-doc1-content').innerHTML = errorMsg;
                document.getElementById('reuso-doc2-content').innerHTML = errorMsg;
            }
        });
    }

    // Cargar al inicio
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initReusoComparator);
    } else {
        initReusoComparator();
    }
})();
