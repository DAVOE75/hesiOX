/**
 * Validaciones de formularios del lado del cliente
 * Mejora la experiencia de usuario y reduce carga en el servidor
 */

// =========================================================
// VALIDACIÓN DE FECHAS DD/MM/YYYY
// =========================================================
function validarFecha(fechaStr) {
    if (!fechaStr || fechaStr.trim() === '') {
        return { valido: true, mensaje: '' }; // Campo vacío es válido
    }

    const fecha = fechaStr.trim();
    const regex = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
    const match = fecha.match(regex);

    if (!match) {
        return {
            valido: false,
            mensaje: `Formato incorrecto: '${fecha}'. Use DD/MM/YYYY`
        };
    }

    const dia = parseInt(match[1], 10);
    const mes = parseInt(match[2], 10);
    const anio = parseInt(match[3], 10);

    // Validar mes
    if (mes < 1 || mes > 12) {
        return {
            valido: false,
            mensaje: `Mes inválido (${mes}). Debe estar entre 1 y 12`
        };
    }

    // Validar año
    if (anio < 1800 || anio > 2100) {
        return {
            valido: false,
            mensaje: `Año fuera de rango (${anio}). Debe estar entre 1800 y 2100`
        };
    }

    // Validar días por mes (incluyendo años bisiestos)
    const diasMes = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if ((anio % 4 === 0 && anio % 100 !== 0) || (anio % 400 === 0)) {
        diasMes[1] = 29; // Febrero en año bisiesto
    }

    if (dia < 1 || dia > diasMes[mes - 1]) {
        return {
            valido: false,
            mensaje: `Día inválido (${dia}) para el mes ${mes}. Máximo: ${diasMes[mes - 1]}`
        };
    }

    return { valido: true, mensaje: '' };
}

// =========================================================
// APLICAR VALIDACIÓN A CAMPOS DE FECHA EN FORMULARIOS
// =========================================================
function inicializarValidacionFechas() {
    const camposFecha = document.querySelectorAll('input[name="fecha_original"], input[name="fecha_consulta"]');
    
    camposFecha.forEach(campo => {
        campo.addEventListener('blur', function() {
            const resultado = validarFecha(this.value);
            
            // Eliminar mensajes de error anteriores
            const errorAnterior = this.parentElement.querySelector('.error-validacion');
            if (errorAnterior) {
                errorAnterior.remove();
            }
            
            // Restablecer estilo
            this.classList.remove('error', 'valido');
            
            if (!resultado.valido) {
                this.classList.add('error');
                const mensajeError = document.createElement('div');
                mensajeError.className = 'error-validacion';
                mensajeError.textContent = '⚠️ ' + resultado.mensaje;
                mensajeError.style.color = '#ff4444';
                mensajeError.style.fontSize = '0.85rem';
                mensajeError.style.marginTop = '4px';
                this.parentElement.appendChild(mensajeError);
            } else if (this.value.trim() !== '') {
                this.classList.add('valido');
            }
        });
    });
}

// =========================================================
// VALIDACIÓN DE CAMPOS REQUERIDOS
// =========================================================
function validarCamposRequeridos(formulario) {
    const camposRequeridos = formulario.querySelectorAll('[required]');
    let todosValidos = true;

    camposRequeridos.forEach(campo => {
        if (!campo.value || campo.value.trim() === '') {
            campo.classList.add('error');
            todosValidos = false;
            
            // Mostrar mensaje si no existe
            if (!campo.parentElement.querySelector('.error-validacion')) {
                const mensajeError = document.createElement('div');
                mensajeError.className = 'error-validacion';
                mensajeError.textContent = '⚠️ Este campo es obligatorio';
                mensajeError.style.color = '#ff4444';
                mensajeError.style.fontSize = '0.85rem';
                mensajeError.style.marginTop = '4px';
                campo.parentElement.appendChild(mensajeError);
            }
        } else {
            campo.classList.remove('error');
            const errorAnterior = campo.parentElement.querySelector('.error-validacion');
            if (errorAnterior && errorAnterior.textContent.includes('obligatorio')) {
                errorAnterior.remove();
            }
        }
    });

    return todosValidos;
}

// =========================================================
// VALIDACIÓN COMPLETA DEL FORMULARIO
// =========================================================
function validarFormulario(event) {
    const formulario = event.target;
    
    // Validar campos requeridos
    if (!validarCamposRequeridos(formulario)) {
        event.preventDefault();
        mostrarNotificacion('Por favor, complete todos los campos obligatorios', 'error');
        return false;
    }

    // Validar fechas específicamente
    const camposFecha = formulario.querySelectorAll('input[name="fecha_original"], input[name="fecha_consulta"]');
    let hayErroresFecha = false;

    camposFecha.forEach(campo => {
        const resultado = validarFecha(campo.value);
        if (!resultado.valido) {
            hayErroresFecha = true;
            campo.classList.add('error');
        }
    });

    if (hayErroresFecha) {
        event.preventDefault();
        mostrarNotificacion('Por favor, corrija las fechas inválidas', 'error');
        return false;
    }

    return true;
}

// =========================================================
// SISTEMA DE NOTIFICACIONES
// =========================================================
function mostrarNotificacion(mensaje, tipo = 'info') {
    // Crear elemento de notificación si no existe
    let contenedorNotif = document.getElementById('notificaciones-container');
    if (!contenedorNotif) {
        contenedorNotif = document.createElement('div');
        contenedorNotif.id = 'notificaciones-container';
        contenedorNotif.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `;
        document.body.appendChild(contenedorNotif);
    }

    const notificacion = document.createElement('div');
    notificacion.className = `notificacion notificacion-${tipo}`;
    notificacion.style.cssText = `
        background: ${tipo === 'error' ? '#ff4444' : tipo === 'success' ? '#4caf50' : '#2196f3'};
        color: white;
        padding: 15px 20px;
        margin-bottom: 10px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease-out;
        font-size: 0.95rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    `;
    
    const icono = tipo === 'error' ? '⚠️' : tipo === 'success' ? '✅' : 'ℹ️';
    notificacion.innerHTML = `
        <span><strong>${icono}</strong> ${mensaje}</span>
        <button onclick="this.parentElement.remove()" style="background:none; border:none; color:white; font-size:1.2rem; cursor:pointer; margin-left:15px;">&times;</button>
    `;

    contenedorNotif.appendChild(notificacion);

    // Auto-eliminar después de 5 segundos
    setTimeout(() => {
        notificacion.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notificacion.remove(), 300);
    }, 5000);
}

// =========================================================
// CONTADOR DE CARACTERES / PALABRAS
// =========================================================
function inicializarContadores() {
    const textareas = document.querySelectorAll('textarea[data-contador]');
    
    textareas.forEach(textarea => {
        const contadorTipo = textarea.dataset.contador; // 'caracteres' o 'palabras'
        const maxLength = textarea.dataset.maxLength;
        
        // Crear elemento contador
        const contador = document.createElement('div');
        contador.className = 'contador-texto';
        contador.style.cssText = `
            text-align: right;
            font-size: 0.85rem;
            color: #999;
            margin-top: 4px;
        `;
        textarea.parentElement.appendChild(contador);
        
        // Función de actualización
        const actualizarContador = () => {
            let valor;
            if (contadorTipo === 'palabras') {
                valor = textarea.value.trim().split(/\s+/).filter(w => w).length;
            } else {
                valor = textarea.value.length;
            }
            
            contador.textContent = `${valor}${maxLength ? '/' + maxLength : ''} ${contadorTipo}`;
            
            // Cambiar color si se acerca al límite
            if (maxLength) {
                const porcentaje = (valor / maxLength) * 100;
                if (porcentaje >= 90) {
                    contador.style.color = '#ff4444';
                } else if (porcentaje >= 75) {
                    contador.style.color = '#ff9800';
                } else {
                    contador.style.color = '#999';
                }
            }
        };
        
        textarea.addEventListener('input', actualizarContador);
        actualizarContador(); // Inicializar
    });
}

// =========================================================
// AUTOCOMPLETADO INTELIGENTE
// =========================================================
function inicializarAutocompletado(inputId, opciones) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const contenedor = document.createElement('div');
    contenedor.className = 'autocomplete-contenedor';
    contenedor.style.cssText = `
        position: relative;
        display: inline-block;
        width: 100%;
    `;
    
    input.parentNode.insertBefore(contenedor, input);
    contenedor.appendChild(input);
    
    const lista = document.createElement('div');
    lista.className = 'autocomplete-lista';
    lista.style.cssText = `
        position: absolute;
        border: 1px solid #ddd;
        border-top: none;
        z-index: 99;
        top: 100%;
        left: 0;
        right: 0;
        max-height: 200px;
        overflow-y: auto;
        background: white;
        display: none;
    `;
    contenedor.appendChild(lista);
    
    input.addEventListener('input', function() {
        const valor = this.value.toLowerCase();
        lista.innerHTML = '';
        
        if (!valor) {
            lista.style.display = 'none';
            return;
        }
        
        const coincidencias = opciones.filter(op => 
            op.toLowerCase().includes(valor)
        ).slice(0, 10);
        
        if (coincidencias.length === 0) {
            lista.style.display = 'none';
            return;
        }
        
        coincidencias.forEach(coincidencia => {
            const div = document.createElement('div');
            div.textContent = coincidencia;
            div.style.cssText = `
                padding: 10px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
            `;
            div.addEventListener('mouseenter', () => {
                div.style.background = '#f0f0f0';
            });
            div.addEventListener('mouseleave', () => {
                div.style.background = 'white';
            });
            div.addEventListener('click', () => {
                input.value = coincidencia;
                lista.style.display = 'none';
            });
            lista.appendChild(div);
        });
        
        lista.style.display = 'block';
    });
    
    // Cerrar al hacer clic fuera
    document.addEventListener('click', (e) => {
        if (!contenedor.contains(e.target)) {
            lista.style.display = 'none';
        }
    });
}

// =========================================================
// INICIALIZACIÓN AL CARGAR LA PÁGINA
// =========================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Módulo de validación de formularios cargado');
    
    // Inicializar validación de fechas
    inicializarValidacionFechas();
    
    // Inicializar contadores de texto
    inicializarContadores();
    
    // Agregar validación a todos los formularios principales
    const formularios = document.querySelectorAll('form[data-validar="true"]');
    formularios.forEach(form => {
        form.addEventListener('submit', validarFormulario);
    });
    
    console.log(`📋 ${formularios.length} formulario(s) con validación activada`);
});

// Exportar funciones para uso global
window.validarFecha = validarFecha;
window.mostrarNotificacion = mostrarNotificacion;
window.inicializarAutocompletado = inicializarAutocompletado;
