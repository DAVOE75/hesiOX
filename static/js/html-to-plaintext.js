/**
 * Convierte contenido HTML a texto plano
 * Limpia etiquetas HTML y decodifica entidades HTML
 */

function htmlToPlainText(html) {
    if (!html || typeof html !== 'string') {
        return '';
    }

    // Crear un elemento temporal para decodificar entidades HTML
    const tempDiv = document.createElement('div');
    
    // Reemplazar <p> y <br> por saltos de línea antes de eliminar etiquetas
    let text = html
        .replace(/<\/p>/gi, '\n')
        .replace(/<p[^>]*>/gi, '')
        .replace(/<br\s*\/?>/gi, '\n')
        .replace(/<\/div>/gi, '\n')
        .replace(/<div[^>]*>/gi, '');
    
    // Decodificar entidades HTML
    tempDiv.innerHTML = text;
    text = tempDiv.textContent || tempDiv.innerText || '';
    
    // Eliminar líneas que solo contienen espacios o guiones
    text = text
        .split('\n')
        .map(line => line.trim())
        .filter(line => line !== '' && line !== '------------' && line !== '---')
        .join('\n\n');
    
    // Limpiar espacios múltiples y saltos de línea excesivos
    text = text
        .replace(/[ \t]+/g, ' ')
        .replace(/\n{3,}/g, '\n\n')
        .trim();
    
    return text;
}

function cleanTextareaFromHTML(textareaId) {
    const textarea = document.getElementById(textareaId);
    if (!textarea) return;
    
    const content = textarea.value;
    
    // Detectar si contiene HTML (etiquetas o entidades HTML)
    const hasHTML = /<[^>]+>|&[a-z]+;|&#\d+;/i.test(content);
    
    if (hasHTML) {
        const cleaned = htmlToPlainText(content);
        textarea.value = cleaned;
        console.log(`[HTML Cleaner] Limpiado HTML de #${textareaId}`);
    }
}

// Auto-limpiar textareas al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    // Limpiar contenido traducido
    cleanTextareaFromHTML('contenido');
    
    // Limpiar texto original
    cleanTextareaFromHTML('texto_original');
    
    console.log('[HTML Cleaner] Verificación completada');
});
