// =========================================================
// 📥 UTILIDADES DE EXPORTACIÓN - Proyecto Sirio
// =========================================================

class ExportUtils {
    constructor() {
        this.formats = ['csv', 'json', 'bibtex', 'txt'];
    }

    /**
     * Exporta datos de referencias bibliográficas a diferentes formatos
     * @param {Array} referencias - Array de objetos con datos de referencias
     * @param {String} formato - Formato de exportación (csv, json, bibtex, txt)
     * @param {String} filename - Nombre del archivo (sin extensión)
     */
    exportar(referencias, formato, filename = 'bibliografia_sirio') {
        if (!referencias || referencias.length === 0) {
            alert('⚠️ No hay datos para exportar');
            return;
        }

        let contenido = '';
        let extension = '';
        let mimeType = '';

        switch (formato.toLowerCase()) {
            case 'csv':
                contenido = this.toCSV(referencias);
                extension = 'csv';
                mimeType = 'text/csv;charset=utf-8;';
                break;

            case 'json':
                contenido = this.toJSON(referencias);
                extension = 'json';
                mimeType = 'application/json;charset=utf-8;';
                break;

            case 'bibtex':
            case 'bib':
                contenido = this.toBibTeX(referencias);
                extension = 'bib';
                mimeType = 'text/plain;charset=utf-8;';
                break;

            case 'txt':
            case 'texto':
                contenido = this.toTextoPlano(referencias);
                extension = 'txt';
                mimeType = 'text/plain;charset=utf-8;';
                break;

            default:
                alert('⚠️ Formato no soportado: ' + formato);
                return;
        }

        this.descargarArchivo(contenido, `${filename}.${extension}`, mimeType);
    }

    /**
     * Convierte referencias a formato CSV
     */
    toCSV(referencias) {
        const headers = [
            'id', 'numero_referencia', 'titulo', 'autor', 'publicacion',
            'fecha_original', 'anio', 'numero', 'edicion',
            'ciudad', 'pais_publicacion', 'idioma',
            'pagina_inicio', 'pagina_fin', 'tipo_recurso',
            'url', 'fecha_consulta', 'licencia',
            'fuente', 'formato_fuente',
            'contenido', 'texto_original', 'notas', 'temas',
            'incluido'
        ];

        const filas = referencias.map(ref => {
            return headers.map(campo => {
                let valor = ref[campo] !== undefined && ref[campo] !== null ? String(ref[campo]) : '';
                // Escapar comillas dobles y envolver en comillas si contiene comas o saltos de línea
                valor = valor.replace(/"/g, '""');
                if (valor.includes(',') || valor.includes('\n') || valor.includes('"')) {
                    valor = `"${valor}"`;
                }
                return valor;
            }).join(',');
        });

        return [headers.join(','), ...filas].join('\n');
    }

    /**
     * Convierte referencias a formato JSON
     */
    toJSON(referencias) {
        return JSON.stringify(referencias, null, 2);
    }

    /**
     * Convierte referencias a formato BibTeX
     */
    toBibTeX(referencias) {
        return referencias.map(ref => {
            const citekey = this.generarCitekey(ref);
            const tipo = this.mapearTipoBibTeX(ref.tipo_recurso);

            let entrada = `@${tipo}{${citekey},\n`;

            if (ref.autor) {
                entrada += `  author = {${ref.autor}},\n`;
            }

            if (ref.titulo) {
                entrada += `  title = {${ref.titulo}},\n`;
            }

            if (ref.publicacion) {
                if (tipo === 'article') {
                    entrada += `  journal = {${ref.publicacion}},\n`;
                } else {
                    entrada += `  publisher = {${ref.publicacion}},\n`;
                }
            }

            if (ref.anio) {
                entrada += `  year = {${ref.anio}},\n`;
            }

            if (ref.numero) {
                entrada += `  number = {${ref.numero}},\n`;
            }

            if (ref.pagina_inicio) {
                if (ref.pagina_fin) {
                    entrada += `  pages = {${ref.pagina_inicio}--${ref.pagina_fin}},\n`;
                } else {
                    entrada += `  pages = {${ref.pagina_inicio}},\n`;
                }
            }

            if (ref.ciudad) {
                entrada += `  address = {${ref.ciudad}},\n`;
            }

            if (ref.url) {
                entrada += `  url = {${ref.url}},\n`;
            }

            if (ref.fecha_consulta) {
                entrada += `  urldate = {${ref.fecha_consulta}},\n`;
            }

            if (ref.idioma) {
                entrada += `  language = {${ref.idioma}},\n`;
            }

            if (ref.notas) {
                entrada += `  note = {${ref.notas}},\n`;
            }

            entrada += `}\n`;

            return entrada;
        }).join('\n');
    }

    /**
     * Convierte referencias a texto plano (formato Chicago)
     */
    toTextoPlano(referencias, estilo = 'chicago') {
        return referencias.map((ref, index) => {
            let cita = '';

            if (ref.numero_referencia) {
                cita += `[${ref.numero_referencia}] `;
            } else {
                cita += `${index + 1}. `;
            }

            // Autor
            if (ref.autor) {
                cita += `${ref.autor}. `;
            } else {
                cita += 'Anónimo. ';
            }

            // Título
            if (ref.titulo) {
                cita += `"${ref.titulo}." `;
            }

            // Publicación
            if (ref.publicacion) {
                cita += `*${ref.publicacion}*`;
            }

            // Fecha
            if (ref.fecha_original) {
                cita += ` (${ref.fecha_original})`;
            } else if (ref.anio) {
                cita += ` (${ref.anio})`;
            }

            // Páginas
            if (ref.pagina_inicio) {
                if (ref.pagina_fin) {
                    cita += `: ${ref.pagina_inicio}-${ref.pagina_fin}`;
                } else {
                    cita += `: ${ref.pagina_inicio}`;
                }
            }

            // URL
            if (ref.url) {
                cita += `. ${ref.url}`;
            }

            cita += '.';

            return cita;
        }).join('\n\n');
    }

    /**
     * Genera una clave de cita BibTeX única
     */
    generarCitekey(ref) {
        let citekey = '';

        // Obtener apellido del autor o usar "anonimo"
        if (ref.autor) {
            const apellido = ref.autor.split(',')[0].trim().toLowerCase();
            citekey += apellido.replace(/\s+/g, '');
        } else {
            citekey += 'anonimo';
        }

        // Añadir año
        if (ref.anio) {
            citekey += ref.anio;
        }

        // Añadir primeras palabras del título
        if (ref.titulo) {
            const palabras = ref.titulo.toLowerCase()
                .replace(/[^\w\s]/g, '')
                .split(/\s+/)
                .filter(p => p.length > 3)
                .slice(0, 2);
            if (palabras.length > 0) {
                citekey += '_' + palabras.join('_');
            }
        }

        // Si hay numero_referencia, añadirlo para garantizar unicidad
        if (ref.numero_referencia) {
            citekey += '_ref' + ref.numero_referencia;
        } else if (ref.id) {
            citekey += '_id' + ref.id;
        }

        return citekey;
    }

    /**
     * Mapea tipo de recurso a tipo BibTeX
     */
    mapearTipoBibTeX(tipoRecurso) {
        const mapeo = {
            'prensa': 'article',
            'libro': 'book',
            'articulo': 'article',
            'tesis': 'phdthesis',
            'mapa': 'misc',
            'fotografia': 'misc',
            'otros': 'misc'
        };
        return mapeo[tipoRecurso] || 'misc';
    }

    /**
     * Descarga el contenido como archivo
     */
    descargarArchivo(contenido, nombreArchivo, mimeType) {
        const blob = new Blob([contenido], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = nombreArchivo;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }

    /**
     * Extrae datos de una tabla HTML para exportar
     */
    extraerDatosTabla(selector = '#tablaRegistros tbody tr') {
        const filas = document.querySelectorAll(selector);
        const datos = [];

        filas.forEach(fila => {
            if (!fila.dataset.id) return; // Saltar filas sin datos

            const dato = {
                id: fila.dataset.id,
                titulo: fila.dataset.titulo,
                publicacion: fila.dataset.publicacion,
                fecha: fila.dataset.fecha,
                autor: fila.dataset.autor,
                licencia: fila.dataset.licencia,
                contenido: fila.dataset.contenido
            };

            datos.push(dato);
        });

        return datos;
    }

    /**
     * Exporta selección actual de la tabla
     */
    exportarSeleccion(formato) {
        const checkboxes = document.querySelectorAll('.registro-checkbox:checked');
        if (checkboxes.length === 0) {
            alert('⚠️ No hay elementos seleccionados para exportar');
            return;
        }

        const datos = [];
        checkboxes.forEach(checkbox => {
            const fila = checkbox.closest('tr');
            if (fila && fila.dataset.id) {
                datos.push({
                    id: fila.dataset.id,
                    titulo: fila.dataset.titulo,
                    publicacion: fila.dataset.publicacion,
                    fecha: fila.dataset.fecha || fila.dataset.fechaOriginal,
                    autor: fila.dataset.autor,
                    licencia: fila.dataset.licencia,
                    contenido: fila.dataset.contenido
                });
            }
        });

        const timestamp = new Date().toISOString().slice(0, 10);
        this.exportar(datos, formato, `sirio_seleccion_${timestamp}`);
    }
}

// Crear instancia global
window.exportUtils = new ExportUtils();

// =========================================================
// INTEGRACIÓN CON INTERFAZ
// =========================================================

document.addEventListener('DOMContentLoaded', function () {
    // [ELIMINADO] Añadir botones de exportación rápida (Legacy)
    // agregarBotonesExportacion();
});

function agregarBotonesExportacion() {
    // Buscar el menú de acciones por lote
    const menuLote = document.querySelector('#btn-acciones-lote')?.closest('.dropdown');

    if (menuLote) {
        const dropdownMenu = menuLote.querySelector('.dropdown-menu');
        if (dropdownMenu && !document.getElementById('export-menu-added')) {
            // Marcar como añadido para evitar duplicados
            dropdownMenu.id = 'export-menu-added';

            // Añadir separador
            const separator = document.createElement('li');
            separator.innerHTML = '<hr class="dropdown-divider">';
            dropdownMenu.appendChild(separator);

            // Añadir título
            const header = document.createElement('li');
            header.innerHTML = '<h6 class="dropdown-header text-info">Exportar Selección</h6>';
            dropdownMenu.appendChild(header);

            // Añadir opciones de exportación
            const formatos = [
                { id: 'csv', label: 'CSV', icon: '📊' },
                { id: 'json', label: 'JSON', icon: '{ }' },
                { id: 'bibtex', label: 'BibTeX', icon: '📚' },
                { id: 'txt', label: 'Texto', icon: '📄' }
            ];

            formatos.forEach(formato => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <a class="dropdown-item text-light export-option" href="#" data-formato="${formato.id}">
                        ${formato.icon} Exportar ${formato.label}
                    </a>
                `;
                dropdownMenu.appendChild(li);
            });
        }
    }

    // Event listeners para las opciones de exportación
    document.querySelectorAll('.export-option').forEach(option => {
        option.addEventListener('click', function (e) {
            e.preventDefault();
            const formato = this.dataset.formato;
            window.exportUtils.exportarSeleccion(formato);
        });
    });
}
