/**
 * ========================================
 * OCR PROCESSOR CON TESSERACT.JS
 * ========================================
 * Sistema de extracción de texto con reconocimiento
 * inteligente de metadatos bibliográficos
 */

// === PREPROCESADO DE IMAGEN PARA OCR ===
// Convierte la imagen a blanco y negro, aumenta contraste y deskew (si es posible)
function preprocessImageForOCR(file, callback) {
    const img = new Image();
    const reader = new FileReader();
    reader.onload = function(e) {
        img.onload = function() {
            // Crear canvas
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);

            // Obtener datos de imagen
            let imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            let data = imageData.data;

            // 1. Convertir a escala de grises
            for (let i = 0; i < data.length; i += 4) {
                const avg = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
                data[i] = data[i+1] = data[i+2] = avg;
            }

            // 2. Aumentar contraste y binarizar
            const threshold = 180; // Puedes ajustar este valor
            for (let i = 0; i < data.length; i += 4) {
                const v = data[i] > threshold ? 255 : 0;
                data[i] = data[i+1] = data[i+2] = v;
            }

            // 3. (Opcional) Deskew: No nativo en JS puro, requiere librerías externas
            // Aquí solo preparamos para posible integración futura

            ctx.putImageData(imageData, 0, 0);
            canvas.toBlob(function(blob) {
                callback(blob);
            }, file.type || 'image/png');
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

class OCRProcessor {
    constructor() {
        this.worker = null;
        this.isInitialized = false;
        this.currentProgress = 0;
        
        // Patrones de detección de metadatos
        this.patterns = {
            // Fechas: DD/MM/YYYY, DD-MM-YYYY, D de Mes de YYYY
            dates: [
                /(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})/g,
                /(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})/gi,
                /(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{1,2}),?\s+(\d{4})/gi
            ],
            
            // Autores: APELLIDO, Nombre | Nombre APELLIDO
            authors: [
                /([A-ZÁÉÍÓÚÑ]{2,}),\s+([A-Za-záéíóúñ]+)/g,  // SURNAME, Name
                /Por:?\s+([A-Z][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ]+)/gi,  // Por: Name SURNAME
                /Autor:?\s+([A-Z][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ]+)/gi  // Autor: Name SURNAME
            ],
            
            // Publicaciones conocidas (de nuestro catálogo)
            publications: [
                /El\s+Eco\s+de\s+Asturias/gi,
                /Il\s+Lavoro/gi,
                /Diario\s+de\s+Asturias/gi,
                /La\s+Voz\s+de\s+Asturias/gi,
                /El\s+Correo\s+de\s+Asturias/gi,
                /El\s+Noroeste/gi,
                /La\s+Mañana/gi
            ],
            
            // Ciudades (principales del catálogo)
            cities: [
                /(Oviedo|Gijón|Avilés|Madrid|Barcelona|Valencia|Sevilla|Buenos\s+Aires|São\s+Paulo)/gi
            ],
            
            // Páginas: p. 3, pág. 5-7, pp. 10-12
            pages: [
                /p(?:ág)?\.?\s*(\d+)/gi,
                /pp\.?\s*(\d+)-(\d+)/gi,
                /página[s]?\s+(\d+)/gi
            ],
            
            // Títulos: Primera línea en mayúsculas o entre comillas
            titles: [
                /^([A-ZÁÉÍÓÚÑ\s]{10,})$/m,  // Línea completa en mayúsculas (mín 10 chars)
                /"([^"]{10,})"/g,  // Texto entre comillas
                /«([^»]{10,})»/g   // Texto entre comillas latinas
            ],
            
            // Años aislados: 1906, 1910, etc.
            years: /\b(19\d{2}|20\d{2})\b/g
        };
        
        // Mapeo de meses a números
        this.monthMap = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        };
        
        console.log('[OCR] Procesador inicializado');
    }
    
    /**
     * Inicializar Tesseract.js worker
     */
    async initialize() {
        if (this.isInitialized) return;
        
        try {
            console.log('[OCR] Inicializando Tesseract.js worker...');
            
            this.worker = await Tesseract.createWorker({
                logger: m => {
                    // Solo actualizar progreso UI, sin console.log (mejora velocidad)
                    if (m.status === 'recognizing text') {
                        this.currentProgress = Math.round(m.progress * 100);
                        this.updateProgressUI(this.currentProgress);
                    }
                }
            });
            
            // Configurar solo español (más rápido que spa+ita)
            await this.worker.loadLanguage('spa');
            await this.worker.initialize('spa');
            
            // CONFIGURACIÓN OPTIMIZADA PARA VELOCIDAD
            await this.worker.setParameters({
                tessedit_pageseg_mode: '3',  // PSM 3: Fully automatic (más rápido que PSM 1 con OSD)
                preserve_interword_spaces: '1'  // Solo parámetro crítico
            });
            
            this.isInitialized = true;
            console.log('[OCR] ✓ Worker inicializado correctamente');
            
        } catch (error) {
            console.error('[OCR] Error al inicializar Tesseract:', error);
            throw new Error('No se pudo inicializar el motor de OCR');
        }
    }
    
    /**
     * Procesar archivo de imagen con OCR
     */
    async processFile(file) {
        console.log('[OCR] Procesando archivo:', file.name, `(${(file.size / 1024).toFixed(2)} KB)`);
        
        // Validar tipo de archivo
        const validTypes = ['image/jpeg', 'image/png', 'image/tiff', 'image/webp', 'application/pdf'];
        if (!validTypes.includes(file.type)) {
            throw new Error(`Tipo de archivo no soportado: ${file.type}. Use JPG, PNG, TIFF, WEBP o PDF.`);
        }
        
        // Validar tamaño (máx 10MB)
        if (file.size > 10 * 1024 * 1024) {
            throw new Error('El archivo es demasiado grande. Máximo: 10 MB.');
        }
        
        // Asegurar que el worker está inicializado
        if (!this.isInitialized) {
            await this.initialize();
        }
        
        try {
            // Resetear progreso
            this.currentProgress = 0;
            this.updateProgressUI(0);
            
            // Preprocesar imagen (binarización, contraste, etc.)
            const preprocessedFile = await new Promise((resolve, reject) => {
                preprocessImageForOCR(file, (blob) => {
                    if (blob) {
                        resolve(blob);
                    } else {
                        reject(new Error('Error al preprocesar la imagen'));
                    }
                });
            });
            
            // Ejecutar OCR
            const startTime = Date.now();
            const { data: { text, confidence } } = await this.worker.recognize(preprocessedFile);
            const duration = ((Date.now() - startTime) / 1000).toFixed(2);
            
            console.log(`[OCR] ✓ ${duration}s | ${confidence.toFixed(0)}% confianza | ${text.length} caracteres`);
            
            // Extraer metadatos del texto
            const metadata = this.extractMetadata(text);
            
            return {
                text,
                confidence,
                metadata,
                duration: parseFloat(duration)
            };
            
        } catch (error) {
            console.error('[OCR] Error al procesar archivo:', error);
            throw new Error(`Error en el reconocimiento de texto: ${error.message}`);
        }
    }
    
    /**
     * Extraer metadatos del texto reconocido
     */
    extractMetadata(text) {
        console.log('[OCR] Extrayendo metadatos del texto...');
        
        const metadata = {
            fecha_original: null,
            anio: null,
            autor: null,
            nombre_autor: null,
            apellido_autor: null,
            publicacion: null,
            ciudad: null,
            titulo: null,
            pagina_inicio: null,
            pagina_fin: null
        };
        
        // 1. FECHA
        for (const datePattern of this.patterns.dates) {
            const match = text.match(datePattern);
            if (match) {
                metadata.fecha_original = this.normalizarFecha(match[0]);
                if (metadata.fecha_original) {
                    const partes = metadata.fecha_original.split('/');
                    if (partes.length === 3) {
                        metadata.anio = parseInt(partes[2]);
                    }
                }
                break;
            }
        }
        
        // 2. AÑO (si no se encontró fecha completa)
        if (!metadata.anio) {
            const yearMatch = text.match(this.patterns.years);
            if (yearMatch) {
                metadata.anio = parseInt(yearMatch[0]);
            }
        }
        
        // 3. AUTOR
        for (const authorPattern of this.patterns.authors) {
            const match = text.match(authorPattern);
            if (match) {
                const autor = match[0].replace(/^(Por|Autor):?\s*/i, '').trim();
                
                // Detectar formato APELLIDO, Nombre
                if (autor.includes(',')) {
                    const partes = autor.split(',').map(p => p.trim());
                    metadata.apellido_autor = partes[0];
                    metadata.nombre_autor = partes[1];
                    metadata.autor = `${partes[0]}, ${partes[1]}`;
                } 
                // Formato Nombre APELLIDO
                else {
                    const partes = autor.split(/\s+/);
                    if (partes.length >= 2) {
                        metadata.nombre_autor = partes.slice(0, -1).join(' ');
                        metadata.apellido_autor = partes[partes.length - 1];
                        metadata.autor = `${metadata.apellido_autor}, ${metadata.nombre_autor}`;
                    }
                }
                break;
            }
        }
        
        // 4. PUBLICACIÓN
        for (const pubPattern of this.patterns.publications) {
            const match = text.match(pubPattern);
            if (match) {
                metadata.publicacion = match[0];
                break;
            }
        }
        
        // 5. CIUDAD
        const cityMatch = text.match(this.patterns.cities);
        if (cityMatch) {
            metadata.ciudad = cityMatch[0];
        }
        
        // 6. PÁGINAS
        for (const pagePattern of this.patterns.pages) {
            const match = text.match(pagePattern);
            if (match) {
                if (match[2]) {
                    // Rango de páginas (pp. 10-12)
                    metadata.pagina_inicio = match[1];
                    metadata.pagina_fin = match[2];
                } else {
                    // Página única
                    metadata.pagina_inicio = match[1];
                }
                break;
            }
        }
        
        // 7. TÍTULO
        for (const titlePattern of this.patterns.titles) {
            const match = text.match(titlePattern);
            if (match) {
                // Tomar el primer match válido y limpiarlo
                let titulo = match[1] || match[0];
                titulo = titulo.trim();
                
                // Validar que no sea demasiado largo (máx 200 chars)
                if (titulo.length > 200) {
                    titulo = titulo.substring(0, 200) + '...';
                }
                
                metadata.titulo = titulo;
                break;
            }
        }
        
        console.log('[OCR] Metadatos extraídos:', metadata);
        return metadata;
    }
    
    /**
     * Normalizar fecha a formato DD/MM/YYYY
     */
    normalizarFecha(fechaStr) {
        // Formato DD/MM/YYYY o DD-MM-YYYY
        const match1 = fechaStr.match(/(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})/);
        if (match1) {
            const dia = match1[1].padStart(2, '0');
            const mes = match1[2].padStart(2, '0');
            const anio = match1[3];
            return `${dia}/${mes}/${anio}`;
        }
        
        // Formato "D de Mes de YYYY"
        const match2 = fechaStr.match(/(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})/i);
        if (match2) {
            const dia = match2[1].padStart(2, '0');
            const mes = this.monthMap[match2[2].toLowerCase()];
            const anio = match2[3];
            return `${dia}/${mes}/${anio}`;
        }
        
        // Formato "Mes D, YYYY"
        const match3 = fechaStr.match(/(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{1,2}),?\s+(\d{4})/i);
        if (match3) {
            const dia = match3[2].padStart(2, '0');
            const mes = this.monthMap[match3[1].toLowerCase()];
            const anio = match3[3];
            return `${dia}/${mes}/${anio}`;
        }
        
        return null;
    }
    
    /**
     * Actualizar UI de progreso
     */
    updateProgressUI(progress) {
        const progressBar = document.getElementById('ocr-progress-bar');
        const progressText = document.getElementById('ocr-progress-text');
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
            
            // Animación suave
            progressBar.style.transition = 'width 0.3s ease';
        }
        
        if (progressText) {
            const timeRemaining = progress > 0 ? Math.round((100 - progress) * 0.5) : '--';
            progressText.innerHTML = `
                <i class="fa-solid fa-spinner fa-spin me-2"></i>
                Procesando OCR... ${progress}%
                ${progress > 0 && progress < 100 ? `<span class="text-muted ms-2">(~${timeRemaining}s restantes)</span>` : ''}
            `;
        }
    }
    
    /**
     * Limpiar recursos
     */
    async terminate() {
        if (this.worker) {
            console.log('[OCR] Terminando worker...');
            await this.worker.terminate();
            this.worker = null;
            this.isInitialized = false;
        }
    }
}

// Exportar como singleton
window.OCRProcessor = OCRProcessor;
console.log('[OCR] Módulo cargado correctamente');
