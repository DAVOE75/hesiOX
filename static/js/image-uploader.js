// =========================================================
// 📸 SISTEMA DE GESTIÓN DE IMÁGENES MEJORADO
// =========================================================

class ImageUploader {
    constructor() {
        this.fileInput = document.querySelector('input[name="imagen_scan"]');
        this.dropZone = document.getElementById('dropZone');
        this.previewContainer = document.getElementById('imagePreviewContainer');
        this.uploadedFiles = [];
        this.maxFileSize = 10 * 1024 * 1024; // 10 MB
        this.maxFiles = 10;
        
        console.log('[Image Uploader] Inicializando...', {
            fileInput: !!this.fileInput,
            dropZone: !!this.dropZone,
            previewContainer: !!this.previewContainer
        });
        
        if (this.fileInput && this.dropZone) {
            this.init();
        } else {
            console.error('[Image Uploader] No se encontraron elementos necesarios');
        }
    }
    
    init() {
        // Crear DataTransfer para manipular archivos
        this.dataTransfer = new DataTransfer();
        
        // Eventos del input tradicional
        this.fileInput.addEventListener('change', (e) => {
            console.log('[Image Uploader] Archivos seleccionados:', e.target.files.length);
            this.handleFiles(e.target.files);
        });
        
        // Configurar eventos del dropZone
        this.setupDropZoneEvents();
        
        console.log('[Image Uploader] ✅ Sistema inicializado correctamente');
    }
    
    setupDropZoneEvents() {
        // Prevenir duplicación de eventos
        if (this.dropZone.dataset.eventsConfigured === 'true') {
            return;
        }
        
        this.dropZone.dataset.eventsConfigured = 'true';
        
        // Eventos drag & drop
        this.dropZone.addEventListener('dragenter', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.highlight();
        });
        
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.highlight();
        });
        
        this.dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.unhighlight();
        });
        
        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.unhighlight();
            this.handleDrop(e);
        });
        
        // Click en drop zone abre selector
        this.dropZone.addEventListener('click', () => {
            console.log('[Image Uploader] Click en dropZone');
            this.fileInput.click();
        });
        
        // Añadir estilos hover
        this.dropZone.addEventListener('mouseenter', () => {
            if (!this.dropZone.classList.contains('highlight')) {
                this.dropZone.style.borderColor = '#0dcaf0';
                this.dropZone.style.background = 'rgba(13, 202, 240, 0.05)';
            }
        });
        
        this.dropZone.addEventListener('mouseleave', () => {
            if (!this.dropZone.classList.contains('highlight')) {
                this.dropZone.style.borderColor = '#6c757d';
                this.dropZone.style.background = 'rgba(33, 37, 41, 0.5)';
            }
        });
        
        console.log('[Image Uploader] Eventos configurados en dropZone');
    }
    
    highlight() {
        this.dropZone.style.borderColor = '#0dcaf0';
        this.dropZone.style.background = 'rgba(13, 202, 240, 0.15)';
        this.dropZone.style.transform = 'scale(1.02)';
        this.dropZone.classList.add('highlight');
    }
    
    unhighlight() {
        this.dropZone.style.borderColor = '#6c757d';
        this.dropZone.style.background = 'rgba(33, 37, 41, 0.5)';
        this.dropZone.style.transform = 'scale(1)';
        this.dropZone.classList.remove('highlight');
    }
    
    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        console.log('[Image Uploader] Archivos arrastrados:', files.length);
        this.handleFiles(files);
    }
    
    handleFiles(files) {
        const validFiles = [...files].filter(file => this.validateFile(file));
        
        if (this.uploadedFiles.length + validFiles.length > this.maxFiles) {
            alert(`⚠️ Máximo ${this.maxFiles} imágenes permitidas`);
            return;
        }
        
        validFiles.forEach(file => {
            this.uploadedFiles.push(file);
            this.dataTransfer.items.add(file);
            this.compressAndPreview(file);
        });
        
        // Actualizar el input file con los archivos
        this.fileInput.files = this.dataTransfer.files;
        
        this.updateUI();
    }
    
    validateFile(file) {
        // Verificar tipo
        if (!file.type.startsWith('image/')) {
            alert(`❌ "${file.name}" no es una imagen válida`);
            return false;
        }
        
        // Verificar tamaño
        if (file.size > this.maxFileSize) {
            alert(`❌ "${file.name}" supera el tamaño máximo (10 MB)`);
            return false;
        }
        
        return true;
    }
    
    async compressAndPreview(file) {
        const reader = new FileReader();
        
        reader.onload = async (e) => {
            const img = new Image();
            img.src = e.target.result;
            
            img.onload = () => {
                // Crear thumbnail
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                // Tamaño máximo para preview
                const maxWidth = 200;
                const maxHeight = 200;
                let width = img.width;
                let height = img.height;
                
                if (width > height) {
                    if (width > maxWidth) {
                        height *= maxWidth / width;
                        width = maxWidth;
                    }
                } else {
                    if (height > maxHeight) {
                        width *= maxHeight / height;
                        height = maxHeight;
                    }
                }
                
                canvas.width = width;
                canvas.height = height;
                ctx.drawImage(img, 0, 0, width, height);
                
                // Crear preview card
                this.createPreviewCard(file, canvas.toDataURL('image/jpeg', 0.7));
            };
        };
        
        reader.readAsDataURL(file);
    }
    
    createPreviewCard(file, thumbnailUrl) {
        const card = document.createElement('div');
        card.style.cssText = `
            position: relative;
            background: #1a1a1a;
            border: 2px solid #333;
            border-radius: 8px;
            overflow: hidden;
            transition: all 0.2s ease;
            display: inline-block;
            margin: 5px;
            width: 180px;
        `;
        card.dataset.filename = file.name;
        
        const sizeKB = (file.size / 1024).toFixed(1);
        
        card.innerHTML = `
            <div style="width: 100%; height: 140px; background-image: url('${thumbnailUrl}'); background-size: cover; background-position: center; cursor: pointer; position: relative;">
                <button type="button" style="position: absolute; top: 8px; right: 8px; background: rgba(220, 53, 69, 0.95); border: none; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: white; font-weight: bold; font-size: 18px; line-height: 1; padding: 0;" title="Eliminar">×</button>
            </div>
            <div style="padding: 10px; background: rgba(0, 0, 0, 0.9);">
                <div style="color: #fff; font-size: 0.75rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${file.name}">${this.truncateFilename(file.name, 20)}</div>
                <div style="color: #0dcaf0; font-size: 0.7rem; margin-top: 3px;">${sizeKB} KB</div>
            </div>
        `;
        
        // Hover effect
        card.addEventListener('mouseenter', () => {
            card.style.borderColor = '#0dcaf0';
            card.style.transform = 'translateY(-3px)';
            card.style.boxShadow = '0 6px 16px rgba(13, 202, 240, 0.3)';
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.borderColor = '#333';
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = 'none';
        });
        
        // Evento para eliminar
        const btnRemove = card.querySelector('button');
        btnRemove.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeFile(file.name);
        });
        
        btnRemove.addEventListener('mouseenter', () => {
            btnRemove.style.background = 'rgba(220, 53, 69, 1)';
            btnRemove.style.transform = 'scale(1.1)';
        });
        
        btnRemove.addEventListener('mouseleave', () => {
            btnRemove.style.background = 'rgba(220, 53, 69, 0.95)';
            btnRemove.style.transform = 'scale(1)';
        });
        
        // Click en la imagen abre lightbox
        const imgDiv = card.querySelector('div');
        imgDiv.addEventListener('click', () => {
            this.openLightbox(thumbnailUrl, file.name);
        });
        
        this.previewContainer.appendChild(card);
        console.log('[Image Uploader] Preview creado para:', file.name);
    }
    
    removeFile(filename) {
        // Eliminar de array
        const index = this.uploadedFiles.findIndex(f => f.name === filename);
        if (index > -1) {
            this.uploadedFiles.splice(index, 1);
        }
        
        // Actualizar DataTransfer
        this.dataTransfer = new DataTransfer();
        this.uploadedFiles.forEach(file => {
            this.dataTransfer.items.add(file);
        });
        this.fileInput.files = this.dataTransfer.files;
        
        // Eliminar preview
        const card = this.previewContainer.querySelector(`[data-filename="${filename}"]`);
        if (card) {
            card.remove();
        }
        
        this.updateUI();
        console.log(`[Image Uploader] Eliminado: ${filename}`);
    }
    
    updateUI() {
        const count = this.uploadedFiles.length;
        
        // Guardar el estado de eventos antes de cambiar HTML
        const wasConfigured = this.dropZone.dataset.eventsConfigured === 'true';
        
        if (count === 0) {
            this.dropZone.innerHTML = `
                <svg width="64" height="64" fill="currentColor" opacity="0.4" class="mb-3">
                    <rect x="8" y="16" width="48" height="40" rx="3" stroke="currentColor" stroke-width="3" fill="none"/>
                    <circle cx="24" cy="32" r="5"/>
                    <polyline points="8,48 22,34 36,48 48,36 56,48" stroke="currentColor" stroke-width="3" fill="none"/>
                </svg>
                <div class="text-light mb-2" style="font-size: 1.1rem;">
                    <strong>📁 Arrastra imágenes aquí</strong>
                </div>
                <div class="text-info mb-2">o haz click para seleccionar archivos</div>
                <div class="small text-secondary">
                    <span class="badge bg-secondary me-2">Máximo: ${this.maxFiles} imágenes</span>
                    <span class="badge bg-secondary">Tamaño: 10 MB c/u</span>
                </div>
                <div class="small text-warning mt-2">Formatos: JPG, PNG, WEBP, GIF</div>
            `;
        } else {
            this.dropZone.innerHTML = `
                <div class="text-success mb-2" style="font-size: 1.1rem;">
                    <svg width="24" height="24" fill="currentColor" class="me-2" style="vertical-align: text-bottom;">
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                    </svg>
                    <strong>✅ ${count} imagen${count > 1 ? 'es' : ''} seleccionada${count > 1 ? 's' : ''}</strong>
                </div>
                <div class="text-light mb-2">Click aquí para añadir más imágenes</div>
                <div class="small text-secondary">
                    <span class="badge bg-info">${count}/${this.maxFiles} archivos</span>
                </div>
            `;
        }
        
        // Si los eventos ya estaban configurados, restaurar el flag y NO volver a configurar
        if (wasConfigured) {
            this.dropZone.dataset.eventsConfigured = 'true';
        }
        
        console.log('[Image Uploader] UI actualizada. Total archivos:', count);
    }
    
    truncateFilename(filename, maxLength) {
        if (filename.length <= maxLength) return filename;
        const ext = filename.split('.').pop();
        const name = filename.substring(0, filename.lastIndexOf('.'));
        const truncated = name.substring(0, maxLength - ext.length - 4) + '...';
        return truncated + '.' + ext;
    }
    
    openLightbox(imageUrl, filename) {
        console.log('[Image Uploader] Abriendo lightbox para:', filename);
        
        // Crear lightbox modal
        const lightbox = document.createElement('div');
        lightbox.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(0, 0, 0, 0.95);
            animation: fadeIn 0.2s ease;
        `;
        
        lightbox.innerHTML = `
            <button style="position: absolute; top: 20px; right: 20px; background: rgba(220, 53, 69, 0.9); border: none; border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: white; font-weight: bold; font-size: 24px; z-index: 10000; transition: all 0.2s;" title="Cerrar (ESC)">×</button>
            <div style="max-width: 90%; max-height: 90%; text-align: center;">
                <img src="${imageUrl}" style="max-width: 100%; max-height: 85vh; border-radius: 8px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8);">
                <div style="color: #fff; margin-top: 15px; font-size: 1rem; background: rgba(0,0,0,0.7); padding: 10px 20px; border-radius: 20px; display: inline-block;">${filename}</div>
            </div>
        `;
        
        document.body.appendChild(lightbox);
        
        const btnClose = lightbox.querySelector('button');
        
        // Eventos de cierre
        const close = () => {
            lightbox.style.opacity = '0';
            setTimeout(() => lightbox.remove(), 200);
        };
        
        btnClose.addEventListener('click', close);
        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) close();
        });
        
        btnClose.addEventListener('mouseenter', () => {
            btnClose.style.background = 'rgba(220, 53, 69, 1)';
            btnClose.style.transform = 'scale(1.1)';
        });
        
        btnClose.addEventListener('mouseleave', () => {
            btnClose.style.background = 'rgba(220, 53, 69, 0.9)';
            btnClose.style.transform = 'scale(1)';
        });
        
        // Cerrar con ESC
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                close();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
        
        // Animación de entrada
        setTimeout(() => lightbox.style.opacity = '1', 10);
    }
}

// Test de elementos antes de inicializar
function testImageUploaderElements() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.querySelector('input[name="imagen_scan"]');
    const previewContainer = document.getElementById('imagePreviewContainer');
    
    console.log('[Image Uploader] Test de elementos:', {
        dropZone: dropZone ? '✅ Encontrado' : '❌ NO encontrado',
        fileInput: fileInput ? '✅ Encontrado' : '❌ NO encontrado', 
        previewContainer: previewContainer ? '✅ Encontrado' : '❌ NO encontrado'
    });
    
    if (!dropZone) {
        console.error('[Image Uploader] ERROR: No se encuentra #dropZone en el HTML');
    }
    if (!fileInput) {
        console.error('[Image Uploader] ERROR: No se encuentra input[name="imagen_scan"]');
    }
    if (!previewContainer) {
        console.error('[Image Uploader] ERROR: No se encuentra #imagePreviewContainer');
    }
}

// Inicializar
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        testImageUploaderElements();
        window.imageUploader = new ImageUploader();
        console.log('[Image Uploader] Instancia global creada');
    });
} else {
    testImageUploaderElements();
    window.imageUploader = new ImageUploader();
    console.log('[Image Uploader] Instancia global creada (DOM ya listo)');
}
