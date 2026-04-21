/**
 * Validador de formularios - Proyecto S.S. Sirio
 * Validación de fechas en formato DD/MM/YYYY
 */

document.addEventListener('DOMContentLoaded', function () {
    // Seleccionar todos los inputs de fecha con clase 'validate-date'
    const fechaInputs = document.querySelectorAll('input.validate-date');

    fechaInputs.forEach(input => {
        input.addEventListener('blur', function () {
            validarFecha(this);
        });

        // Validación en tiempo real (opcional)
        input.addEventListener('input', function () {
            // Remover mensaje de error mientras escribe
            const feedback = this.nextElementSibling;
            if (feedback && feedback.classList.contains('invalid-feedback')) {
                feedback.remove();
            }
            this.classList.remove('is-invalid');
        });
    });

    // Validar al enviar formulario
    const formularios = document.querySelectorAll('form');
    formularios.forEach(form => {
        form.addEventListener('submit', function (e) {
            let hayErrores = false;

            const fechas = this.querySelectorAll('input.validate-date');
            fechas.forEach(input => {
                if (input.value.trim() !== '' && !validarFecha(input)) {
                    hayErrores = true;
                }
            });

            if (hayErrores) {
                e.preventDefault();
                alert('⚠️ Por favor, corrige los errores en el formulario antes de guardar.');
                // Scroll al primer error
                const primerError = this.querySelector('.is-invalid');
                if (primerError) {
                    primerError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    primerError.focus();
                }
            }
        });
    });
});

/**
 * Valida que una fecha tenga formato DD/MM/YYYY correcto
 * @param {HTMLInputElement} input - Campo de entrada
 * @returns {boolean} - true si es válido o está vacío
 */
function validarFecha(input) {
    const valor = input.value.trim();

    // Si está vacío, es válido (campo opcional)
    if (valor === '') {
        input.classList.remove('is-invalid');
        return true;
    }

    // Patrón para DD/MM/YYYY
    const patron = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
    const match = valor.match(patron);

    if (!match) {
        mostrarError(input, 'Formato inválido. Use DD/MM/YYYY (ej: 04/08/1906)');
        return false;
    }

    const dia = parseInt(match[1], 10);
    const mes = parseInt(match[2], 10);
    const anio = parseInt(match[3], 10);

    // Validar rangos básicos
    if (mes < 1 || mes > 12) {
        mostrarError(input, 'Mes inválido (debe ser 01-12)');
        return false;
    }

    if (dia < 1 || dia > 31) {
        mostrarError(input, 'Día inválido (debe ser 01-31)');
        return false;
    }

    // Validar año razonable para prensa histórica
    if (anio < 1000 || anio > 2100) {
        mostrarError(input, 'Año fuera de rango (1000-2100)');
        return false;
    }

    // Validar días según mes
    const diasPorMes = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

    // Año bisiesto
    if ((anio % 4 === 0 && anio % 100 !== 0) || anio % 400 === 0) {
        diasPorMes[1] = 29;
    }

    if (dia > diasPorMes[mes - 1]) {
        mostrarError(input, `El mes ${mes} no tiene ${dia} días`);
        return false;
    }

    // Todo correcto
    input.classList.remove('is-invalid');
    input.classList.add('is-valid');

    // Remover mensaje de error previo
    const feedback = input.nextElementSibling;
    if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.remove();
    }

    return true;
}

/**
 * Muestra mensaje de error bajo el campo
 */
function mostrarError(input, mensaje) {
    input.classList.add('is-invalid');
    input.classList.remove('is-valid');

    // Remover mensaje previo
    let feedback = input.nextElementSibling;
    if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.textContent = mensaje;
    } else {
        // Crear nuevo mensaje
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = mensaje;
        input.parentNode.insertBefore(feedback, input.nextSibling);
    }
}

/**
 * Helper para formatear fecha automáticamente mientras escribe
 * Uso: <input type="text" onkeyup="autoformatearFecha(event)">
 */
function autoformatearFecha(event) {
    let input = event.target;
    let valor = input.value.replace(/\D/g, ''); // Solo números

    if (valor.length >= 2) {
        valor = valor.slice(0, 2) + '/' + valor.slice(2);
    }
    if (valor.length >= 5) {
        valor = valor.slice(0, 5) + '/' + valor.slice(5, 9);
    }

    input.value = valor;
}
