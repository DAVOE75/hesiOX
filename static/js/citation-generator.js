// =========================================================
// 📚 GENERADOR DE CITAS BIBLIOGRÁFICAS
// =========================================================

class CitationGenerator {
    constructor() {
        this.formats = {
            'iso690': 'ISO 690 (Internacional)',
            'apa7': 'APA 7ª Ed. (Psicología)',
            'harvard': 'Harvard (Autor-Fecha)',
            'mla9': 'MLA 9ª Ed. (Humanidades)',
            'chicago': 'Chicago 17ª Ed. (Notas)',
            'vancouver': 'Vancouver (Medicina)',
            'hemerografico': 'Hemerográfico (Prensa)'
        };
        
        this.currentFormat = 'iso690';
        this.data = {};
        
        console.log('[Citation Generator] Inicializado con', Object.keys(this.formats).length, 'formatos');
    }
    
    /**
     * Extrae datos del formulario actual
     */
    extractFormData() {
        const data = {
            // Identificación básica
            tipo_recurso: this.getValue('[name="tipo_recurso"]'),
            
            // Autoría
            autor: this.getValue('[name="autor"]'),
            
            // Publicación
            titulo: this.getValue('[name="titulo"]'),
            publicacion: this.getValue('[name="publicacion"]'),
            ciudad: this.getValue('[name="ciudad"]'),
            
            // Fechas
            fecha_original: this.getValue('[name="fecha_original"]'),
            anio: this.getValue('[name="anio"]'),
            fecha_consulta: this.getValue('[name="fecha_consulta"]'),
            
            // Detalles bibliográficos
            numero: this.getValue('[name="numero"]'),
            paginas: this.getValue('[name="paginas"]'),
            volumen: this.getValue('[name="volumen"]'),
            edicion: this.getValue('[name="edicion"]'),
            
            // Campos condicionales
            editorial: this.getValue('[name="editorial"]'),
            isbn: this.getValue('[name="isbn"]'),
            doi: this.getValue('[name="doi"]'),
            issn: this.getValue('[name="issn"]'),
            lugar_publicacion: this.getValue('[name="lugar_publicacion"]'),
            
            // Digital
            url: this.getValue('[name="url"]')
        };
        
        this.data = data;
        console.log('[Citation Generator] Datos extraídos:', data);
        return data;
    }
    
    /**
     * Obtiene valor de un campo del formulario
     */
    getValue(selector) {
        const element = document.querySelector(selector);
        if (!element) return '';
        
        // Para TinyMCE, obtener contenido del editor
        if (element.classList.contains('has-rich-editor') && window.tinymce) {
            const editor = window.tinymce.get(element.id);
            if (editor) return this.stripHtml(editor.getContent());
        }
        
        return element.value || '';
    }
    
    /**
     * Elimina HTML de un texto
     */
    stripHtml(html) {
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || '';
    }
    
    /**
     * Genera la cita en el formato especificado
     */
    generate(format = this.currentFormat) {
        this.currentFormat = format;
        this.extractFormData();
        
        const tipo = this.data.tipo_recurso || 'prensa';
        
        // Seleccionar método según formato
        switch(format) {
            case 'iso690':
                return this.generateISO690(tipo);
            case 'apa7':
                return this.generateAPA7(tipo);
            case 'harvard':
                return this.generateHarvard(tipo);
            case 'mla9':
                return this.generateMLA9(tipo);
            case 'chicago':
                return this.generateChicago(tipo);
            case 'vancouver':
                return this.generateVancouver(tipo);
            default:
                return this.generateISO690(tipo);
        }
    }
    
    // =========================================================
    // ISO 690 (Norma Internacional)
    // =========================================================
    
    generateISO690(tipo) {
        const d = this.data;
        let cita = '';
        
        switch(tipo) {
            case 'prensa':
                // APELLIDO, Nombre. Título del artículo. Publicación [tipo]. Fecha, vol./núm., páginas. ISSN.
                if (d.autor) cita += this.formatAutorISO(d.autor) + '. ';
                if (d.titulo) cita += d.titulo + '. ';
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em> [periódico]. ';
                if (d.fecha_original) cita += d.fecha_original;
                if (d.volumen || d.numero) {
                    cita += ', ';
                    if (d.volumen) cita += 'vol. ' + d.volumen;
                    if (d.numero) cita += (d.volumen ? ', ' : '') + 'n.º ' + d.numero;
                }
                if (d.paginas) cita += ', p. ' + d.paginas;
                cita += '.';
                if (d.issn) cita += ' ISSN ' + d.issn + '.';
                break;
                
            case 'libro':
                // APELLIDO, Nombre. Título. Edición. Lugar de publicación: Editorial, Año. páginas. ISBN.
                if (d.autor) cita += this.formatAutorISO(d.autor) + '. ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.edicion && d.edicion !== '1' && d.edicion !== 'Primera') {
                    cita += d.edicion + (d.edicion.match(/\d/) ? '.ª' : '') + ' ed. ';
                }
                if (d.lugar_publicacion || d.ciudad) cita += (d.lugar_publicacion || d.ciudad) + ': ';
                if (d.editorial) cita += d.editorial + ', ';
                if (d.anio) cita += d.anio + '. ';
                if (d.paginas) cita += d.paginas + ' p. ';
                if (d.isbn) cita += 'ISBN ' + d.isbn + '.';
                break;
                
            case 'articulo':
                // APELLIDO, Nombre. Título del artículo. Publicación [tipo]. Año, vol., n.º, pp. DOI/ISSN.
                if (d.autor) cita += this.formatAutorISO(d.autor) + '. ';
                if (d.titulo) cita += d.titulo + '. ';
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em> [en línea]. ';
                if (d.anio) cita += d.anio;
                if (d.volumen) cita += ', vol. ' + d.volumen;
                if (d.numero) cita += ', n.º ' + d.numero;
                if (d.paginas) cita += ', pp. ' + d.paginas;
                cita += '. ';
                if (d.doi) cita += 'DOI ' + d.doi + '. ';
                else if (d.issn) cita += 'ISSN ' + d.issn + '.';
                break;
                
            case 'tesis':
                // APELLIDO, Nombre. Título [tipo de tesis]. Lugar: Institución, Año. páginas.
                if (d.autor) cita += this.formatAutorISO(d.autor) + '. ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em> [tesis doctoral]. ';
                if (d.lugar_publicacion || d.ciudad) cita += (d.lugar_publicacion || d.ciudad) + ': ';
                if (d.publicacion) cita += d.publicacion + ', ';
                if (d.anio) cita += d.anio + '. ';
                if (d.paginas) cita += d.paginas + ' p.';
                break;
                
            case 'obra_teatral':
                // APELLIDO, Nombre. Título de la obra. Teatro: Compañía, Fecha.
                if (d.autor) cita += this.formatAutorISO(d.autor) + '. ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.lugar_publicacion || d.ciudad) cita += (d.lugar_publicacion || d.ciudad) + ': ';
                if (d.editorial) cita += d.editorial + ', ';
                if (d.fecha_original) cita += d.fecha_original;
                else if (d.anio) cita += d.anio;
                cita += '.';
                break;
                
            default:
                if (d.autor) cita += this.formatAutorISO(d.autor) + '. ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.publicacion) cita += d.publicacion + '. ';
                if (d.anio) cita += d.anio + '.';
        }
        
        // URL si existe
        if (d.url) {
            cita += ' [Consulta: ' + (d.fecha_consulta || 'fecha no especificada') + ']. Disponible en: ' + d.url;
        }
        
        return cita.trim();
    }
    
    // =========================================================
    // APA 7ª Edición
    // =========================================================
    
    generateAPA7(tipo) {
        const d = this.data;
        let cita = '';
        
        switch(tipo) {
            case 'prensa':
                // Apellido, I. (Año, Día de Mes). Título del artículo. Nombre de la publicación. URL
                if (d.autor) cita += this.formatAutorAPA(d.autor) + ' ';
                if (d.fecha_original) {
                    // Convertir fecha DD/MM/AAAA a formato APA: Año, Día de Mes
                    const fecha = this.formatFechaAPA(d.fecha_original);
                    cita += '(' + fecha + '). ';
                } else if (d.anio) {
                    cita += '(' + d.anio + '). ';
                }
                if (d.titulo) cita += d.titulo + '. ';
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em>';
                if (d.paginas) cita += ', ' + d.paginas;
                cita += '. ';
                if (d.url) cita += d.url;
                break;
                
            case 'libro':
                // Apellido, I. (Año). Título del libro (n.º de ed.). Editorial. DOI o URL
                if (d.autor) cita += this.formatAutorAPA(d.autor) + ' ';
                if (d.anio) cita += '(' + d.anio + '). ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>';
                if (d.edicion && d.edicion !== '1' && d.edicion !== 'Primera') {
                    cita += ' (' + d.edicion + '.ª ed.)';
                }
                cita += '. ';
                if (d.editorial) cita += d.editorial + '. ';
                if (d.doi) cita += 'https://doi.org/' + d.doi;
                else if (d.url) cita += d.url;
                break;
                
            case 'articulo':
                // Apellido, I. (Año). Título del artículo. Nombre de la revista, volumen(número), pp-pp. DOI o URL
                if (d.autor) cita += this.formatAutorAPA(d.autor) + ' ';
                if (d.anio) cita += '(' + d.anio + '). ';
                if (d.titulo) cita += d.titulo + '. ';
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em>, ';
                if (d.volumen) cita += '<em>' + d.volumen + '</em>';
                if (d.numero) cita += '(' + d.numero + ')';
                if (d.paginas) cita += ', ' + d.paginas;
                cita += '. ';
                if (d.doi) cita += 'https://doi.org/' + d.doi;
                else if (d.url) cita += d.url;
                break;
                
            case 'tesis':
                // Apellido, I. (Año). Título de la tesis [Tesis de doctorado, Nombre de la institución]. URL
                if (d.autor) cita += this.formatAutorAPA(d.autor) + ' ';
                if (d.anio) cita += '(' + d.anio + '). ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em> ';
                cita += '[Tesis de doctorado';
                if (d.publicacion) cita += ', ' + d.publicacion;
                cita += ']. ';
                if (d.url) cita += d.url;
                break;
                
            case 'obra_teatral':
                // Apellido, I. (Año). Título de la obra. Teatro.
                if (d.autor) cita += this.formatAutorAPA(d.autor) + ' ';
                if (d.anio || d.fecha_original) {
                    cita += '(' + (d.anio || this.extractYear(d.fecha_original)) + '). ';
                }
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.lugar_publicacion || d.ciudad) cita += (d.lugar_publicacion || d.ciudad);
                if (d.editorial) cita += ' [' + d.editorial + ']';
                cita += '.';
                break;
                
            default:
                if (d.autor) cita += this.formatAutorAPA(d.autor) + ' ';
                if (d.anio) cita += '(' + d.anio + '). ';
                if (d.titulo) cita += d.titulo + '. ';
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em>.';
        }
        
        return cita.trim();
    }
    
    // =========================================================
    // Harvard (Autor-Fecha)
    // =========================================================
    
    generateHarvard(tipo) {
        const d = this.data;
        let cita = '';
        
        switch(tipo) {
            case 'prensa':
                // Apellido, I. (año) 'Título del artículo', Nombre de la publicación, Día Mes, p./pp. página(s).
                if (d.autor) cita += this.formatAutorHarvard(d.autor) + ' ';
                if (d.anio || d.fecha_original) {
                    cita += '(' + (d.anio || this.extractYear(d.fecha_original)) + ') ';
                }
                if (d.titulo) cita += "'" + d.titulo + "', ";
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em>, ';
                if (d.fecha_original) cita += this.formatFechaHarvard(d.fecha_original);
                if (d.paginas) {
                    const esSingular = !d.paginas.includes('-');
                    cita += ', ' + (esSingular ? 'p. ' : 'pp. ') + d.paginas;
                }
                cita += '.';
                break;
                
            case 'libro':
                // Apellido, I. (año) Título del libro. Edición. Lugar de publicación: Editorial.
                if (d.autor) cita += this.formatAutorHarvard(d.autor) + ' ';
                if (d.anio) cita += '(' + d.anio + ') ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.edicion && d.edicion !== '1' && d.edicion !== 'Primera') {
                    cita += d.edicion + (d.edicion.match(/\d/) ? 'ª' : '') + ' edn. ';
                }
                if (d.lugar_publicacion || d.ciudad) cita += (d.lugar_publicacion || d.ciudad) + ': ';
                if (d.editorial) cita += d.editorial + '.';
                break;
                
            case 'articulo':
                // Apellido, I. (año) 'Título del artículo', Nombre de la revista, vol(núm), pp. páginas.
                if (d.autor) cita += this.formatAutorHarvard(d.autor) + ' ';
                if (d.anio) cita += '(' + d.anio + ') ';
                if (d.titulo) cita += "'" + d.titulo + "', ";
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em>, ';
                if (d.volumen) cita += 'vol. ' + d.volumen;
                if (d.numero) cita += '(' + d.numero + ')';
                if (d.paginas) cita += ', pp. ' + d.paginas;
                cita += '.';
                break;
                
            default:
                if (d.autor) cita += this.formatAutorHarvard(d.autor) + ' ';
                if (d.anio) cita += '(' + d.anio + ') ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.publicacion) cita += d.publicacion + '.';
        }
        
        if (d.url) {
            cita += ' Available at: ' + d.url;
            if (d.fecha_consulta) {
                cita += ' (Accessed: ' + this.formatFechaHarvard(d.fecha_consulta) + ')';
            }
            cita += '.';
        }
        
        return cita.trim();
    }
    
    // =========================================================
    // MLA 9ª Edición
    // =========================================================
    
    generateMLA9(tipo) {
        const d = this.data;
        let cita = '';
        
        switch(tipo) {
            case 'prensa':
                // Apellido, Nombre. "Título del artículo." Nombre de la publicación, Día Mes Año, pp. páginas.
                if (d.autor) cita += this.formatAutorMLA(d.autor) + '. ';
                if (d.titulo) cita += '"' + d.titulo + '." ';
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em>, ';
                if (d.fecha_original) cita += this.formatFechaMLA(d.fecha_original) + ', ';
                if (d.paginas) cita += 'pp. ' + d.paginas + '.';
                else cita = cita.slice(0, -2) + '.'; // Remover última coma si no hay páginas
                break;
                
            case 'libro':
                // Apellido, Nombre. Título del libro. Editorial, Año.
                if (d.autor) cita += this.formatAutorMLA(d.autor) + '. ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.edicion && d.edicion !== '1' && d.edicion !== 'Primera') {
                    cita += d.edicion + (d.edicion.match(/\d/) ? ' ed., ' : ' ed., ');
                }
                if (d.editorial) cita += d.editorial + ', ';
                if (d.anio) cita += d.anio + '.';
                break;
                
            case 'articulo':
                // Apellido, Nombre. "Título del artículo." Nombre de la revista, vol. núm., no. núm., Año, pp. páginas.
                if (d.autor) cita += this.formatAutorMLA(d.autor) + '. ';
                if (d.titulo) cita += '"' + d.titulo + '." ';
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em>, ';
                if (d.volumen) cita += 'vol. ' + d.volumen + ', ';
                if (d.numero) cita += 'no. ' + d.numero + ', ';
                if (d.anio) cita += d.anio + ', ';
                if (d.paginas) cita += 'pp. ' + d.paginas + '.';
                break;
                
            case 'tesis':
                // Apellido, Nombre. Título de la tesis. Año. Institución, Tesis doctoral.
                if (d.autor) cita += this.formatAutorMLA(d.autor) + '. ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.anio) cita += d.anio + '. ';
                if (d.publicacion) cita += d.publicacion + ', ';
                cita += 'Tesis doctoral.';
                break;

            case 'obra_teatral':
                // Apellido, Nombre. Título de la obra. Teatro, Año.
                if (d.autor) cita += this.formatAutorMLA(d.autor) + '. ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.lugar_publicacion || d.ciudad) cita += (d.lugar_publicacion || d.ciudad) + ', ';
                if (d.editorial) cita += d.editorial + ', ';
                if (d.anio || d.fecha_original) cita += (d.anio || this.extractYear(d.fecha_original)) + '.';
                break;
                
            default:
                if (d.autor) cita += this.formatAutorMLA(d.autor) + '. ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.publicacion) cita += d.publicacion + ', ';
                if (d.anio) cita += d.anio + '.';
        }
        
        if (d.url) cita += ' ' + d.url + '.';
        
        return cita.trim();
    }
    
    // =========================================================
    // Chicago 17ª Edición (Notas y Bibliografía)
    // =========================================================
    
    generateChicago(tipo) {
        const d = this.data;
        let cita = '';
        
        switch(tipo) {
            case 'prensa':
                // Apellido, Nombre. "Título del artículo." Nombre de la publicación, Día Mes, Año.
                if (d.autor) cita += this.formatAutorChicago(d.autor) + '. ';
                if (d.titulo) cita += '"' + d.titulo + '." ';
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em>, ';
                if (d.fecha_original) cita += this.formatFechaChicago(d.fecha_original) + '.';
                break;
                
            case 'libro':
                // Apellido, Nombre. Título del libro. Lugar de publicación: Editorial, Año.
                if (d.autor) cita += this.formatAutorChicago(d.autor) + '. ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.edicion && d.edicion !== '1' && d.edicion !== 'Primera') {
                    cita += d.edicion + (d.edicion.match(/\d/) ? ' ed. ' : ' ed. ');
                }
                if (d.lugar_publicacion || d.ciudad) cita += (d.lugar_publicacion || d.ciudad) + ': ';
                if (d.editorial) cita += d.editorial + ', ';
                if (d.anio) cita += d.anio + '.';
                break;
                
            case 'articulo':
                // Apellido, Nombre. "Título del artículo." Nombre de la revista volumen, no. número (Año): páginas.
                if (d.autor) cita += this.formatAutorChicago(d.autor) + '. ';
                if (d.titulo) cita += '"' + d.titulo + '." ';
                if (d.publicacion) cita += '<em>' + d.publicacion + '</em> ';
                if (d.volumen) cita += d.volumen;
                if (d.numero) cita += ', no. ' + d.numero;
                if (d.anio) cita += ' (' + d.anio + ')';
                if (d.paginas) cita += ': ' + d.paginas;
                cita += '.';
                if (d.doi) cita += ' https://doi.org/' + d.doi + '.';
                break;
                
            case 'tesis':
                // Apellido, Nombre. "Título de la tesis." Tipo de tesis, Institución, Año.
                if (d.autor) cita += this.formatAutorChicago(d.autor) + '. ';
                if (d.titulo) cita += '"' + d.titulo + '." ';
                cita += 'Tesis doctoral, ';
                if (d.publicacion) cita += d.publicacion + ', ';
                if (d.anio) cita += d.anio + '.';
                break;
                
            default:
                if (d.autor) cita += this.formatAutorChicago(d.autor) + '. ';
                if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
                if (d.anio) cita += d.anio + '.';
        }
        
        return cita.trim();
    }
    
    // =========================================================
    // Vancouver (Medicina)
    // =========================================================
    
    generateVancouver(tipo) {
        const d = this.data;
        let cita = '';
        
        switch(tipo) {
            case 'prensa':
                // Apellido Iniciales. Título del artículo. Nombre del periódico. Fecha;Sección:páginas (col.).
                if (d.autor) cita += this.formatAutorVancouver(d.autor) + '. ';
                if (d.titulo) cita += d.titulo + '. ';
                if (d.publicacion) cita += d.publicacion + '. ';
                if (d.fecha_original) cita += this.formatFechaVancouver(d.fecha_original);
                if (d.paginas) cita += ':' + d.paginas;
                cita += '.';
                break;
                
            case 'libro':
                // Apellido Iniciales. Título. Edición. Lugar: Editorial; Año. páginas p.
                if (d.autor) cita += this.formatAutorVancouver(d.autor) + '. ';
                if (d.titulo) cita += d.titulo + '. ';
                if (d.edicion && d.edicion !== '1' && d.edicion !== 'Primera') {
                    cita += d.edicion + (d.edicion.match(/\d/) ? 'ª' : '') + ' ed. ';
                }
                if (d.lugar_publicacion || d.ciudad) cita += (d.lugar_publicacion || d.ciudad) + ': ';
                if (d.editorial) cita += d.editorial + '; ';
                if (d.anio) cita += d.anio + '. ';
                if (d.paginas) cita += d.paginas + ' p.';
                break;
                
            case 'articulo':
                // Apellido Iniciales. Título del artículo. Abreviatura de la revista. Año;volumen(número):páginas.
                if (d.autor) cita += this.formatAutorVancouver(d.autor) + '. ';
                if (d.titulo) cita += d.titulo + '. ';
                if (d.publicacion) cita += d.publicacion + '. ';
                if (d.anio) cita += d.anio;
                if (d.volumen) cita += ';' + d.volumen;
                if (d.numero) cita += '(' + d.numero + ')';
                if (d.paginas) cita += ':' + d.paginas;
                cita += '.';
                if (d.doi) cita += ' DOI: ' + d.doi + '.';
                break;
                
            case 'tesis':
                // Apellido Iniciales. Título [tipo]. Lugar: Institución; Año.
                if (d.autor) cita += this.formatAutorVancouver(d.autor) + '. ';
                if (d.titulo) cita += d.titulo + ' [tesis doctoral]. ';
                if (d.lugar_publicacion || d.ciudad) cita += (d.lugar_publicacion || d.ciudad) + ': ';
                if (d.publicacion) cita += d.publicacion + '; ';
                if (d.anio) cita += d.anio + '.';
                break;
                
            default:
                if (d.autor) cita += this.formatAutorVancouver(d.autor) + '. ';
                if (d.titulo) cita += d.titulo + '. ';
                if (d.publicacion) cita += d.publicacion + '. ';
                if (d.anio) cita += d.anio + '.';
        }
        
        if (d.url) cita += ' Disponible en: ' + d.url;
        
        return cita.trim();
    }
    
    /**
     * Genera cita en formato hemerográfico (específico para prensa)
     * APELLIDO, Nombre. "Título del artículo". Publicación, Ciudad, Fecha completa, Número, Página(s).
     */
    generateHemerografico(tipo) {
        const d = this.data;
        let cita = '';
        
        // Principalmente para prensa, pero adaptable
        if (tipo === 'prensa' || !tipo) {
            // Autor: APELLIDO, Nombre.
            if (d.autor) {
                const partes = d.autor.trim().split(/\s+/);
                if (partes.length > 1) {
                    const apellido = partes[partes.length - 1].toUpperCase();
                    const nombres = partes.slice(0, -1).join(' ');
                    cita += apellido + ', ' + nombres + '. ';
                } else {
                    cita += d.autor.toUpperCase() + '. ';
                }
            }
            
            // Título entre comillas
            if (d.titulo) cita += '"' + d.titulo + '". ';
            
            // Publicación en cursiva
            if (d.publicacion) cita += '<em>' + d.publicacion + '</em>, ';
            
            // Ciudad
            if (d.ciudad) cita += d.ciudad + ', ';
            
            // Fecha completa (día mes año)
            if (d.fecha_original) {
                cita += d.fecha_original;
            } else if (d.anio) {
                cita += d.anio;
            }
            
            // Número de publicación
            if (d.numero) cita += ', Núm. ' + d.numero;
            
            // Páginas
            if (d.paginas) cita += ', p. ' + d.paginas;
            
            cita += '.';
        }
        // Para otros tipos de recursos, usar estructura similar
        else if (tipo === 'libro') {
            if (d.autor) {
                const partes = d.autor.trim().split(/\s+/);
                if (partes.length > 1) {
                    const apellido = partes[partes.length - 1].toUpperCase();
                    const nombres = partes.slice(0, -1).join(' ');
                    cita += apellido + ', ' + nombres + '. ';
                } else {
                    cita += d.autor.toUpperCase() + '. ';
                }
            }
            if (d.titulo) cita += '<em>' + d.titulo + '</em>. ';
            if (d.ciudad) cita += d.ciudad + ': ';
            if (d.editorial) cita += d.editorial + ', ';
            if (d.anio) cita += d.anio + '. ';
            if (d.paginas) cita += d.paginas + ' p.';
        }
        else if (tipo === 'obra_teatral') {
            if (d.autor) cita += d.autor.toUpperCase() + '. ';
            if (d.titulo) cita += '"' + d.titulo + '". ';
            if (d.lugar_publicacion || d.ciudad) cita += (d.lugar_publicacion || d.ciudad) + ', ';
            if (d.editorial) cita += d.editorial + ', ';
            if (d.fecha_original) cita += d.fecha_original;
            else if (d.anio) cita += d.anio;
            cita += '.';
        }
        else if (tipo === 'articulo') {
            if (d.autor) {
                const partes = d.autor.trim().split(/\s+/);
                if (partes.length > 1) {
                    const apellido = partes[partes.length - 1].toUpperCase();
                    const nombres = partes.slice(0, -1).join(' ');
                    cita += apellido + ', ' + nombres + '. ';
                } else {
                    cita += d.autor.toUpperCase() + '. ';
                }
            }
            if (d.titulo) cita += '"' + d.titulo + '". ';
            if (d.publicacion) cita += '<em>' + d.publicacion + '</em>, ';
            if (d.volumen) cita += 'Vol. ' + d.volumen;
            if (d.numero) cita += ', Núm. ' + d.numero;
            if (d.anio) cita += ' (' + d.anio + ')';
            if (d.paginas) cita += ', pp. ' + d.paginas;
            cita += '.';
        }
        else {
            // Genérico para otros tipos
            if (d.autor) cita += d.autor.toUpperCase() + '. ';
            if (d.titulo) cita += '"' + d.titulo + '". ';
            if (d.publicacion) cita += '<em>' + d.publicacion + '</em>. ';
            if (d.fecha_original) cita += d.fecha_original + '.';
        }
        
        return cita || '<em class="text-muted">Completa los campos para generar la cita hemerográfica...</em>';
    }
    
    // =========================================================
    // Utilidades de Formato
    // =========================================================
    
    /**
     * Formatea autor para ISO 690 (APELLIDO, Nombre)
     */
    formatAutorISO(autor) {
        if (!autor) return '';
        if (autor.includes(',')) {
            // Ya está en formato correcto, solo capitalizar apellido
            const partes = autor.split(',');
            return partes[0].trim().toUpperCase() + ', ' + partes[1].trim();
        }
        // Separar nombres: último como apellido
        const partes = autor.trim().split(/\s+/);
        if (partes.length === 1) return autor.toUpperCase();
        const apellido = partes[partes.length - 1].toUpperCase();
        const nombres = partes.slice(0, -1).join(' ');
        return apellido + ', ' + nombres;
    }
    
    /**
     * Formatea autor para APA (Apellido, I.)
     */
    formatAutorAPA(autor) {
        if (!autor) return '';
        if (autor.includes(',')) {
            // Ya tiene coma, extraer iniciales
            const partes = autor.split(',');
            const apellido = partes[0].trim();
            const nombres = partes[1].trim().split(/\s+/);
            const iniciales = nombres.map(n => n.charAt(0).toUpperCase() + '.').join(' ');
            return apellido + ', ' + iniciales;
        }
        // Separar nombres
        const partes = autor.trim().split(/\s+/);
        if (partes.length === 1) return autor;
        const apellido = partes[partes.length - 1];
        const nombres = partes.slice(0, -1);
        const iniciales = nombres.map(n => n.charAt(0).toUpperCase() + '.').join(' ');
        return apellido + ', ' + iniciales;
    }
    
    /**
     * Formatea autor para Harvard (Apellido, I.)
     */
    formatAutorHarvard(autor) {
        return this.formatAutorAPA(autor); // Harvard usa el mismo formato que APA
    }
    
    /**
     * Formatea autor para MLA (Apellido, Nombre completo)
     */
    formatAutorMLA(autor) {
        if (!autor) return '';
        if (autor.includes(',')) return autor; // Ya está en formato correcto
        const partes = autor.trim().split(/\s+/);
        if (partes.length === 1) return autor;
        const apellido = partes[partes.length - 1];
        const nombres = partes.slice(0, -1).join(' ');
        return apellido + ', ' + nombres;
    }
    
    /**
     * Formatea autor para Chicago (Apellido, Nombre completo)
     */
    formatAutorChicago(autor) {
        return this.formatAutorMLA(autor); // Chicago usa el mismo formato que MLA
    }
    
    /**
     * Formatea autor para Vancouver (Apellido Iniciales sin puntos)
     */
    formatAutorVancouver(autor) {
        if (!autor) return '';
        if (autor.includes(',')) {
            const partes = autor.split(',');
            const apellido = partes[0].trim();
            const nombres = partes[1].trim().split(/\s+/);
            const iniciales = nombres.map(n => n.charAt(0).toUpperCase()).join('');
            return apellido + ' ' + iniciales;
        }
        const partes = autor.trim().split(/\s+/);
        if (partes.length === 1) return autor;
        const apellido = partes[partes.length - 1];
        const nombres = partes.slice(0, -1);
        const iniciales = nombres.map(n => n.charAt(0).toUpperCase()).join('');
        return apellido + ' ' + iniciales;
    }
    
    /**
     * Formatea fecha para APA (Año, Día de Mes)
     */
    formatFechaAPA(fecha) {
        if (!fecha) return '';
        const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                      'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
        const partes = fecha.split('/');
        if (partes.length === 3) {
            const dia = partes[0];
            const mes = meses[parseInt(partes[1]) - 1] || partes[1];
            const anio = partes[2];
            return anio + ', ' + dia + ' de ' + mes;
        }
        return fecha;
    }
    
    /**
     * Formatea fecha para Harvard (Día Mes)
     */
    formatFechaHarvard(fecha) {
        if (!fecha) return '';
        const meses = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December'];
        const partes = fecha.split('/');
        if (partes.length === 3) {
            const dia = partes[0];
            const mes = meses[parseInt(partes[1]) - 1] || partes[1];
            return dia + ' ' + mes;
        }
        return fecha;
    }
    
    /**
     * Formatea fecha para MLA (Día Mes Año)
     */
    formatFechaMLA(fecha) {
        if (!fecha) return '';
        const meses = ['Jan.', 'Feb.', 'Mar.', 'Apr.', 'May', 'June', 
                      'July', 'Aug.', 'Sept.', 'Oct.', 'Nov.', 'Dec.'];
        const partes = fecha.split('/');
        if (partes.length === 3) {
            const dia = partes[0];
            const mes = meses[parseInt(partes[1]) - 1] || partes[1];
            const anio = partes[2];
            return dia + ' ' + mes + ' ' + anio;
        }
        return fecha;
    }
    
    /**
     * Formatea fecha para Chicago (Día Mes, Año)
     */
    formatFechaChicago(fecha) {
        if (!fecha) return '';
        const meses = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December'];
        const partes = fecha.split('/');
        if (partes.length === 3) {
            const dia = partes[0];
            const mes = meses[parseInt(partes[1]) - 1] || partes[1];
            const anio = partes[2];
            return mes + ' ' + dia + ', ' + anio;
        }
        return fecha;
    }
    
    /**
     * Formatea fecha para Vancouver (Año Mes Día)
     */
    formatFechaVancouver(fecha) {
        if (!fecha) return '';
        const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                      'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        const partes = fecha.split('/');
        if (partes.length === 3) {
            const dia = partes[0];
            const mes = meses[parseInt(partes[1]) - 1] || partes[1];
            const anio = partes[2];
            return anio + ' ' + mes + ' ' + dia;
        }
        return fecha;
    }
    
    /**
     * Extrae año de una fecha DD/MM/AAAA
     */
    extractYear(fecha) {
        if (!fecha) return '';
        const partes = fecha.split('/');
        return partes.length === 3 ? partes[2] : '';
    }
    
    /**
     * Obtiene lista de formatos disponibles
     */
    getFormats() {
        return this.formats;
    }
}

// Exponer globalmente
window.CitationGenerator = CitationGenerator;

console.log('[Citation Generator] ✅ Módulo cargado correctamente');
