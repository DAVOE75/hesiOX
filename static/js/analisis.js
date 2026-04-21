// ==========================================================
// 🧠 Proyecto Sirio — Módulo de Análisis de Contenido MEJORADO + NLP
// ==========================================================

let currentChart = null; // Referencia al gráfico activo
let corpusData = null;   // Datos del corpus NLP

// Función para obtener stopwords personalizadas
function getCustomStopwords() {
  const textarea = document.getElementById('custom-stopwords');
  return textarea ? textarea.value : '';
}

// Función para obtener el límite de documentos
function getDocumentLimit() {
  const select = document.getElementById('select-limite-docs');
  return select ? select.value : '300';
}

document.addEventListener("DOMContentLoaded", () => {
  // Limpieza forzada de residuos de Choices.js
  const ch = document.querySelector('.choices');
  if (ch && ch.parentNode && ch.parentNode.contains(ch)) {
    // Reemplazar el wrapper Choices por el select original si existe
    const select = document.getElementById('input-palabras-clave');
    if (select) {
      ch.parentNode.replaceChild(select, ch);
    } else {
      ch.remove();
    }
  }
  // =============================
  // 📈 DISTRIBUCIÓN TEMPORAL AVANZADA
  // =============================
  const formFiltroTemporal = document.getElementById("form-filtro-temporal");
  const tipoDistribucion = document.getElementById("tipo-distribucion");
  const fechaInicio = document.getElementById("fecha-inicio");
  const fechaFin = document.getElementById("fecha-fin");
  const bloquePalabrasClave = document.getElementById("bloque-palabras-clave");
  const inputPalabrasClave = document.getElementById("input-palabras-clave");
  const graficoDistribucionTemporal = document.getElementById("grafico-distribucion-temporal");

  // --- Inicializar multi-select de palabras clave (top 100 + libre) ---
  let topKeywords = [];


  // --- Choices.js: reinicialización segura ---
  let choicesInstance = null;

  async function cargarTopKeywords() {
    try {
      // Obtener fechas en formato yyyy-mm-dd
      let inicio = fechaInicio?.value;
      let fin = fechaFin?.value;
      // Normalizar formato si es necesario (asegura yyyy-mm-dd)
      if (inicio && inicio.includes('/')) {
        const [d, m, y] = inicio.split('/');
        inicio = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
      }
      if (fin && fin.includes('/')) {
        const [d, m, y] = fin.split('/');
        fin = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
      }
      let url = '/api/keywords/top100';
      const params = [];
      // Añadir campos seleccionados (título/contenido)
      const fields = [];
      if (document.getElementById('check-titulo')?.checked) fields.push('titulo');
      if (document.getElementById('check-contenido')?.checked) fields.push('contenido');
      if (fields.length > 0) params.push('fields=' + encodeURIComponent(fields.join(',')));
      if (inicio) params.push('inicio=' + encodeURIComponent(inicio));
      if (fin) params.push('fin=' + encodeURIComponent(fin));
      if (params.length > 0) url += '?' + params.join('&');
      const resp = await fetch(url);
      const data = await resp.json();
      if (data.success && Array.isArray(data.keywords)) {
        topKeywords = data.keywords;
        if (inputPalabrasClave.tagName === 'SELECT' && window.choicesInstance) {
          // Limpiar y añadir palabras frecuentes como opciones, sin seleccionar ninguna
          window.choicesInstance.clearChoices();
          const choices = topKeywords.map(kw => ({ value: kw, label: kw }));
          window.choicesInstance.setChoices(choices, 'value', 'label', true);
          // No seleccionar ninguna por defecto
          window.choicesInstance.removeActiveItems();
        } else {
          // Fallback para select clásico
          inputPalabrasClave.innerHTML = '';
          inputPalabrasClave.removeAttribute('hidden');
          inputPalabrasClave.removeAttribute('disabled');
          inputPalabrasClave.style.display = '';
          topKeywords.forEach((kw) => {
            const opt = document.createElement('option');
            opt.value = kw;
            opt.textContent = kw;
            inputPalabrasClave.appendChild(opt);
          });
          // No seleccionar ninguna por defecto
          inputPalabrasClave.selectedIndex = -1;
        }
      }
    } catch (e) {
      console.error('Error cargando top keywords', e);
    }
  }

  // Permitir añadir palabras libres al multi-select
  inputPalabrasClave?.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && this.value) {
      const val = this.value.trim();
      if (val && ![...this.options].some(opt => opt.value === val)) {
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = val;
        opt.selected = true;
        this.appendChild(opt);
      }
      this.value = '';
      e.preventDefault();
    }
  });

  // Mostrar/ocultar bloque de palabras clave según tipo

  tipoDistribucion?.addEventListener('change', function () {
    if (this.value === 'palabras') {
      bloquePalabrasClave.style.display = '';
      cargarTopKeywords().then(() => {
        // No seleccionar ninguna palabra clave automáticamente
        actualizarGraficoDistribucionTemporal();
      });
      return;
    } else {
      bloquePalabrasClave.style.display = 'none';
    }
    actualizarGraficoDistribucionTemporal();
  });


  // Actualizar gráfico y palabras clave al cambiar fechas
  [fechaInicio, fechaFin].forEach(ctrl => {
    ctrl?.addEventListener('change', () => {
      cargarTopKeywords().then(() => {
        actualizarGraficoDistribucionTemporal();
      });
    });
  });
  // Actualizar gráfico al cambiar palabras clave
  inputPalabrasClave?.addEventListener('change', actualizarGraficoDistribucionTemporal);

  // Botón manual de recálculo
  const btnRecalcularTemporal = document.getElementById("btn-recalcular-temporal");
  btnRecalcularTemporal?.addEventListener('click', actualizarGraficoDistribucionTemporal);

  // Botón aplicar límite con feedback visual
  const btnAplicarLimite = document.getElementById("btn-aplicar-limite");
  btnAplicarLimite?.addEventListener('click', function () {
    // Feedback visual
    const originalText = this.innerHTML;
    this.innerHTML = '<i class="fa-solid fa-check"></i>';
    this.classList.replace('btn-sirio-primary', 'btn-success');

    // Ejecutar actualización
    actualizarGraficoDistribucionTemporal();

    // Restaurar estado
    setTimeout(() => {
      this.innerHTML = originalText;
      this.classList.replace('btn-success', 'btn-sirio-primary');
    }, 1500);
  });

  // Helper para obtener palabras seleccionadas desde Choices.js
  function getSelectedPalabrasChoices() {
    if (choicesInstance && choicesInstance.getValue) {
      // Choices.js en modo input devuelve array de objetos {value, label}
      const vals = choicesInstance.getValue();
      if (Array.isArray(vals)) {
        return vals.map(v => typeof v === 'string' ? v : v.value);
      }
      return [];
    }
    // Fallback solo si es un select
    if (inputPalabrasClave && inputPalabrasClave.tagName === 'SELECT') {
      return Array.from(inputPalabrasClave.selectedOptions).map(opt => opt.value);
    }
    return [];
  }

  // Función principal para actualizar el gráfico
  async function actualizarGraficoDistribucionTemporal() {
    if (!graficoDistribucionTemporal) return;
    graficoDistribucionTemporal.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-warning" role="status"></div><p class="text-muted mt-2">Cargando gráfico...</p></div>';

    const tipo = tipoDistribucion?.value || 'referencias';
    const inicio = fechaInicio?.value;
    const fin = fechaFin?.value;
    let palabras = [];
    if (tipo === 'palabras' && inputPalabrasClave) {
      palabras = getSelectedPalabrasChoices();
      if (!palabras || palabras.length === 0) {
        // No mostrar nada hasta que el usuario seleccione alguna palabra clave
        graficoDistribucionTemporal.innerHTML = '<div class="alert alert-info">Selecciona al menos una palabra clave para mostrar la gráfica.</div>';
        return;
      }
    }

    let url = '/api/analisis/distribucion-temporal?tipo=' + encodeURIComponent(tipo);
    if (inicio) url += '&inicio=' + encodeURIComponent(inicio);
    if (fin) url += '&fin=' + encodeURIComponent(fin);

    if (tipo === 'palabras') {
      url += '&palabras=' + encodeURIComponent(palabras.join(','));
    }
    const limit = getDocumentLimit();
    if (limit) url += '&limit=' + encodeURIComponent(limit);

    try {
      const resp = await fetch(url);
      const data = await resp.json();
      if (data && data.success && Array.isArray(data.series) && Array.isArray(data.labels)) {
        renderGraficoDistribucionTemporal(data.labels, data.series, tipo, data.agrupacion || 'anio');
      } else {
        graficoDistribucionTemporal.innerHTML = '<div class="alert alert-warning">No hay datos para mostrar el gráfico.</div>';
      }
    } catch (e) {
      graficoDistribucionTemporal.innerHTML = '<div class="alert alert-danger">Error al cargar el gráfico.</div>';
      console.error(e);
    }
  }

  // Renderizar el gráfico temporal (líneas o barras)
  function renderGraficoDistribucionTemporal(labels, series, tipo, agrupacion) {
    if (!Array.isArray(labels) || !Array.isArray(series) || labels.length === 0 || series.length === 0) {
      graficoDistribucionTemporal.innerHTML = '<div class="alert alert-warning">No hay datos para mostrar el gráfico.</div>';
      return;
    }
    graficoDistribucionTemporal.innerHTML = '<canvas id="canvas-distribucion-temporal" style="height: 400px; width: 100%;"></canvas>';
    const ctx = document.getElementById('canvas-distribucion-temporal').getContext('2d');
    if (currentChart) currentChart.destroy();

    let datasets = [];
    if (tipo === 'palabras' && Array.isArray(series)) {
      // Paleta de colores para distinguir líneas
      const palette = [
        '#ff9800', '#03a9f4', '#4caf50', '#e91e63', '#9c27b0', '#ffc107', '#009688', '#f44336', '#607d8b', '#8bc34a',
        '#795548', '#00bcd4', '#cddc39', '#673ab7', '#2196f3', '#ff5722', '#3f51b5', '#bdbdbd', '#8d6e63', '#00e676'
      ];
      datasets = series.map((s, idx) => ({
        label: s.label,
        data: s.data,
        borderColor: palette[idx % palette.length],
        backgroundColor: palette[idx % palette.length] + '33', // color transparente
        fill: false,
        tension: 0.2
      }));
    } else {
      // referencias: una sola serie
      datasets = [{
        label: 'Referencias',
        data: series,
        borderColor: '#ff9800',
        backgroundColor: 'rgba(255,152,0,0.2)',
        fill: true,
        tension: 0.2
      }];
    }

    currentChart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#ff9800' } },
          tooltip: {
            backgroundColor: 'rgba(30,30,30,0.95)',
            titleColor: '#ff9800',
            bodyColor: '#fff',
            borderColor: '#ff9800',
            borderWidth: 1
          }
        },
        scales: {
          x: { ticks: { color: '#e0e0e0' }, grid: { color: '#333' } },
          y: {
            ticks: { color: '#e0e0e0' },
            grid: { color: '#333' },
            beginAtZero: true,
            maxTicksLimit: 5,
            suggestedMax: 100
          }
        },
        onClick: function (evt, elements) {
          if (!elements || !elements.length) return;
          const chart = this;
          const element = elements[0];
          // Obtener índice de la fecha (label)
          const fechaIdx = element.index;
          let fechaRaw = labels[fechaIdx];
          // Eliminar sufijo tipo ':1' si existe
          let fecha = fechaRaw.split(':')[0];

          // Obtener la palabra clave si estamos en modo palabras
          let palabraClave = null;
          if (tipo === 'palabras' && Array.isArray(series) && series[element.datasetIndex]) {
            palabraClave = series[element.datasetIndex].label;
          }

          let url = '/listar?';

          if (agrupacion === 'dia') {
            // La fecha ya está en formato YYYY-MM-DD
            url += 'fecha_original=' + encodeURIComponent(fecha);
          } else {
            // Es un año, buscar por año
            url += 'anio=' + encodeURIComponent(fecha);
          }

          // Añadir búsqueda por palabra clave si existe
          if (palabraClave) {
            url += '&q=' + encodeURIComponent(palabraClave);
          }

          if (url !== '/listar?') {
            window.open(url, '_blank');
          }
        }
      }
    });
  }

  // Inicialización: mostrar/ocultar bloque y cargar gráfico inicial
  if (tipoDistribucion) {
    if (tipoDistribucion.value === 'palabras') {
      bloquePalabrasClave.style.display = '';
      cargarTopKeywords();
    } else {
      bloquePalabrasClave.style.display = 'none';
    }
    actualizarGraficoDistribucionTemporal();
  }
  // Botones NLP
  const btnNLPWordcloud = document.getElementById("btn-nlp-wordcloud");
  const btnNLPEntities = document.getElementById("btn-nlp-entities");
  const btnNLPKeywords = document.getElementById("btn-nlp-keywords");

  // Botones análisis tradicional y nuevos
  const btnFreq = document.getElementById("btn-frecuencia"); // legacy
  const btnFreqAbs = document.getElementById("btn-frecuencia-absoluta");
  const btnFreqNorm = document.getElementById("btn-frecuencia-normalizada");
  const btnTfidf = document.getElementById("btn-tfidf");

  // Botones visualización (excepto temporal avanzado)
  const btnPorPub = document.getElementById("btn-por-publicacion");
  const btnPorCiudad = document.getElementById("btn-por-ciudad");

  // Controles
  const btnExportar = document.getElementById("btn-exportar");
  const btnLimpiar = document.getElementById("btn-limpiar");
  const resultado = document.getElementById("resultado");

  // Botones de stopwords
  const btnGuardarStopwords = document.getElementById("btn-guardar-stopwords");
  const btnResetStopwords = document.getElementById("btn-reset-stopwords");

  // Función para obtener los campos seleccionados
  function getSelectedFields() {
    const fields = [];
    if (document.getElementById('check-titulo')?.checked) fields.push('titulo');
    if (document.getElementById('check-contenido')?.checked) fields.push('contenido');
    return fields.join(',');
  }

  // Solo ejecutar funciones dependientes de #resultado si existe
  if (resultado) {
    // Cargar estadísticas generales al inicio
    loadGeneralStats();
    // ...el resto de funciones que dependan de resultado...
  }

  // ==========================================================
  // 🤖 FUNCIONES NLP CON IA
  // ==========================================================

  // --- Nube de palabras NLP (TF-IDF) ---
  if (btnNLPWordcloud) {
    btnNLPWordcloud.addEventListener("click", async () => {
      resultado.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-warning" role="status"></div><p class="text-muted mt-3">Analizando corpus con NLP...</p></div>';

      try {
        const stopwords = getCustomStopwords();
        const fields = getSelectedFields();
        const limit = getDocumentLimit();
        let url = '/api/corpus-analysis?';
        if (fields) url += `fields=${fields}&`;
        if (stopwords) url += `stopwords=${encodeURIComponent(stopwords)}&`;
        if (limit) url += `limit=${limit}&`;
        url = url.replace(/[&?]$/, '');

        const response = await fetch(url);
        const data = await response.json();

        if (data.success && data.word_cloud) {
          renderNLPWordCloud(data.word_cloud);
        } else {
          resultado.innerHTML = '<div class="alert alert-danger">No hay datos suficientes para generar la nube NLP</div>';
        }
      } catch (error) {
        console.error(error);
        resultado.innerHTML = '<div class="alert alert-danger">❌ Error al cargar análisis NLP</div>';
      }
    });
  }

  // --- Red de entidades ---
  if (btnNLPEntities) {
    btnNLPEntities.addEventListener("click", async () => {
      resultado.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-warning" role="status"></div><p class="text-muted mt-3">Extrayendo entidades con spaCy...</p></div>';

      try {
        const fields = getSelectedFields();
        const limit = getDocumentLimit();
        let url = '/api/corpus-analysis?';
        if (fields) url += `fields=${fields}&`;
        if (limit) url += `limit=${limit}&`;
        url = url.replace(/[&?]$/, '');

        const response = await fetch(url);
        const data = await response.json();

        if (data.success && data.entity_network) {
          renderEntityNetwork(data.entity_network);
        } else {
          resultado.innerHTML = '<div class="alert alert-danger">No hay entidades suficientes para generar la red</div>';
        }
      } catch (error) {
        console.error(error);
        resultado.innerHTML = '<div class="alert alert-danger">❌ Error al cargar red de entidades</div>';
      }
    });
  }

  // --- Top keywords NLP (MODIFICADO: Incluye títulos) ---
  if (btnNLPKeywords) {
    btnNLPKeywords.addEventListener("click", async () => {
      resultado.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-warning" role="status"></div><p class="text-muted mt-3">Calculando keywords con TF-IDF...</p></div>';

      try {
        const fields = getSelectedFields();
        const limit = getDocumentLimit();
        let url = '/api/corpus-analysis?';
        if (fields) url += `fields=${fields}&`;
        if (limit) url += `limit=${limit}&`;
        url = url.replace(/[&?]$/, '');

        const response = await fetch(url);
        const data = await response.json();

        if (data.success && data.word_cloud) {
          renderNLPKeywordsChart(data.word_cloud);
        } else {
          resultado.innerHTML = '<div class="alert alert-danger">No hay datos para generar keywords</div>';
        }
      } catch (error) {
        console.error(error);
        resultado.innerHTML = '<div class="alert alert-danger">❌ Error al cargar keywords</div>';
      }
    });
  }

  // ==========================================================
  // 📊 FUNCIONES DE ANÁLISIS TEXTUAL TRADICIONAL
  // ==========================================================

  // --- Frecuencia absoluta de palabras ---
  function renderFrecuenciaAbsoluta() {
    resultado.innerHTML = "<p class='text-warning'>⏳ Calculando frecuencias...</p>";
    const fields = getSelectedFields();
    const limit = getDocumentLimit();
    let url = '/analisis/frecuencia?';
    if (fields) url += `fields=${fields}&`;
    if (limit) url += `limit=${limit}&`;
    url = url.replace(/[&?]$/, '');
    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        const top120 = data.slice(0, 120);
        const isLight = document.body.getAttribute('data-theme') === 'light';
        const accentColor = isLight ? '#294a60' : '#ff9800';
        const textColor = isLight ? '#212121' : '#ffffff';

        const lista = top120.map(([palabra, freq]) =>
          `<li class='mb-1' style='color: ${textColor};'><strong>${palabra}</strong>: <span class='text-accent'>${freq}</span></li>`
        ).join("");
        resultado.innerHTML = `
          <div class='card bg-sirio-panel p-4'>
            <h4 class='text-accent mb-3'><svg width='18' height='18' fill='currentColor' viewBox='0 0 16 16' style='margin-right: 5px;'><rect x='2' y='8' width='3' height='6' fill='currentColor'/><rect x='6' y='4' width='3' height='10' fill='currentColor'/><rect x='10' y='6' width='3' height='8' fill='currentColor'/></svg> Palabras más frecuentes (Top 120)</h4>
            <ul class='list-unstyled' style='column-count: 4;'>${lista}</ul>
          </div>
        `;
      })
      .catch(() => {
        resultado.innerHTML = "<p class='text-danger'>❌ Error al calcular frecuencias.</p>";
      });
  }

  if (btnFreqAbs) {
    btnFreqAbs.addEventListener("click", renderFrecuenciaAbsoluta);
  }
  // Soporte legacy por si queda el botón antiguo
  if (btnFreq) {
    btnFreq.addEventListener("click", renderFrecuenciaAbsoluta);
  }

  // --- Frecuencia normalizada de palabras ---
  if (btnFreqNorm) {
    btnFreqNorm.addEventListener("click", () => {
      resultado.innerHTML = "<p class='text-warning'>⏳ Calculando frecuencia normalizada...</p>";
      const fields = getSelectedFields();
      const limit = getDocumentLimit();
      let url = '/analisis/frecuencia_normalizada?';
      if (fields) url += `fields=${fields}&`;
      if (limit) url += `limit=${limit}&`;
      url = url.replace(/[&?]$/, '');
      fetch(url)
        .then((r) => r.json())
        .then((data) => {
          const top120 = data.slice(0, 120);
          const isLight = document.body.getAttribute('data-theme') === 'light';
          const accentColor = isLight ? '#294a60' : '#ff9800';
          const textColor = isLight ? '#212121' : '#ffffff';

          const lista = top120.map(([palabra, freq]) =>
            `<li class='mb-1' style='color: ${textColor};'><strong>${palabra}</strong>: <span class='text-accent'>${freq.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span></li>`
          ).join("");
          resultado.innerHTML = `
            <div class='card bg-sirio-panel p-4'>
              <h4 class='text-accent mb-3'><svg width='18' height='18' fill='currentColor' viewBox='0 0 16 16' style='margin-right: 5px;'><rect x='2' y='8' width='3' height='6' fill='currentColor'/><rect x='6' y='4' width='3' height='10' fill='currentColor'/><rect x='10' y='6' width='3' height='8' fill='currentColor'/></svg> Palabras más frecuentes (Normalizadas, Top 120)</h4>
              <ul class='list-unstyled' style='column-count: 4;'>${lista}</ul>
            </div>
          `;
        })
        .catch(() => {
          resultado.innerHTML = "<p class='text-danger'>❌ Error al calcular frecuencia normalizada.</p>";
        });
    });
  }

  // --- TF-IDF (simulado con top frecuencias) ---
  if (btnTfidf) {
    btnTfidf.addEventListener("click", () => {
      resultado.innerHTML = "<p class='text-warning'><svg width='14' height='14' fill='currentColor' viewBox='0 0 24 24' style='margin-right: 5px;'><circle cx='10' cy='10' r='7' stroke='currentColor' stroke-width='2' fill='none'/><line x1='15' y1='15' x2='20' y2='20' stroke='currentColor' stroke-width='2'/></svg> Calculando términos relevantes...</p>";

      const fields = getSelectedFields();
      const limit = getDocumentLimit();
      let url = '/analisis/frecuencia?';
      if (fields) url += `fields=${fields}&`;
      if (limit) url += `limit=${limit}&`;
      url = url.replace(/[&?]$/, '');

      fetch(url)
        .then((r) => r.json())
        .then((data) => {
          const top15 = data.slice(0, 15);
          const labels = top15.map(([palabra]) => palabra);
          const values = top15.map(([, freq]) => freq);

          const isLight = document.body.getAttribute('data-theme') === 'light';
          const barColor = isLight ? 'rgba(41, 74, 96, 0.7)' : 'rgba(3, 169, 244, 0.7)';
          renderChart('bar', labels, values, 'Términos más relevantes (TF-IDF simulado)', barColor);
        })
        .catch(() => {
          resultado.innerHTML = "<p class='text-danger'>❌ Error al calcular TF-IDF.</p>";
        });
    });
  }

  // --- Distribución temporal ---


  // --- Por publicación ---
  if (btnPorPub) {
    btnPorPub.addEventListener("click", () => {
      resultado.innerHTML = "<p class='text-warning'><svg width='14' height='14' fill='currentColor' viewBox='0 0 24 24' style='margin-right: 5px;'><rect x='4' y='2' width='16' height='20' rx='1' stroke='currentColor' stroke-width='2' fill='none'/><line x1='8' y1='7' x2='16' y2='7' stroke='currentColor' stroke-width='1.5'/><line x1='8' y1='11' x2='16' y2='11' stroke='currentColor' stroke-width='1.5'/><line x1='8' y1='15' x2='13' y2='15' stroke='currentColor' stroke-width='1.5'/></svg> Analizando por publicación...</p>";

      fetch("/api/stats/por-publicacion?_t=" + new Date().getTime())
        .then((r) => r.json())
        .then((data) => {
          const labels = data.map(d => d.publicacion);
          const values = data.map(d => d.count);

          renderChart('pie', labels, values, 'Distribución por publicación', generateColors(data.length));
        })
        .catch(() => {
          resultado.innerHTML = "<p class='text-danger'>❌ Error al generar gráfico por publicación.</p>";
        });
    });
  }

  // --- Por ciudad ---
  if (btnPorCiudad) {
    btnPorCiudad.addEventListener("click", () => {
      resultado.innerHTML = "<p class='text-warning'><svg width='14' height='14' fill='currentColor' viewBox='0 0 24 24' style='margin-right: 5px;'><path d='M12,2 L12,11 M12,11 L6,14 M12,11 L18,14' stroke='currentColor' stroke-width='2' fill='none'/><circle cx='12' cy='12' r='10' stroke='currentColor' stroke-width='2' fill='none'/></svg> Analizando por ciudad...</p>";

      fetch("/api/stats/por-ciudad?_t=" + new Date().getTime())
        .then((r) => r.json())
        .then((data) => {
          const top10 = data.slice(0, 10);
          const labels = top10.map(d => d.ciudad);
          const values = top10.map(d => d.count);

          renderChart('bar', labels, values, 'Top 10 ciudades con mayor cobertura', 'rgba(244, 67, 54, 0.7)');
        })
        .catch((err) => {
          console.error(err);
          resultado.innerHTML = "<p class='text-danger'>❌ Error al generar gráfico por ciudad.</p>";
        });
    });
  }

  // --- Exportar resultados (simulado) ---
  if (btnExportar) {
    btnExportar.addEventListener("click", () => {
      alert("Función de exportación pendiente de implementar");
    });
  }

  // --- Limpiar resultados ---
  if (btnLimpiar) {
    btnLimpiar.addEventListener("click", () => {
      if (currentChart) {
        currentChart.destroy();
        currentChart = null;
      }
      resultado.innerHTML = "";
    });
  }

  // --- Guardar stopwords personalizadas ---
  if (btnGuardarStopwords) {
    btnGuardarStopwords.addEventListener("click", async () => {
      const stopwords = getCustomStopwords();
      localStorage.setItem('custom_stopwords', stopwords);
      // Actualizar la nube de palabras automáticamente
      if (btnNLPWordcloud && resultado) {
        resultado.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-warning" role="status"></div><p class="text-muted mt-3">Analizando corpus con NLP...</p></div>';
        try {
          const fields = getSelectedFields();
          const limit = getDocumentLimit();
          let url = '/api/corpus-analysis?';
          if (fields) url += `fields=${fields}&`;
          if (stopwords) url += `stopwords=${encodeURIComponent(stopwords)}&`;
          if (limit) url += `limit=${limit}&`;
          url = url.replace(/[&?]$/, '');
          const response = await fetch(url);
          const data = await response.json();
          if (data.success && data.word_cloud) {
            renderNLPWordCloud(data.word_cloud);
          } else {
            resultado.innerHTML = '<div class="alert alert-danger">No hay datos suficientes para generar la nube NLP</div>';
          }
        } catch (error) {
          console.error(error);
          resultado.innerHTML = '<div class="alert alert-danger">❌ Error al cargar análisis NLP</div>';
        }
      }
    });
  }

  // --- Restaurar stopwords predeterminadas ---
  if (btnResetStopwords) {
    btnResetStopwords.addEventListener("click", () => {
      const defaultStopwords = "de, la, que, el, en, y, a, los, del, se, las, por, un, para, con, no, una, su, al, lo, como, más, mas, pero, sus, le, ya, o, fue, este, ha, sí, si, porque, esta, son, entre, cuando, muy, sin, sobre, también, me, hasta, hay, donde, han, quien, desde, todo, nos, durante, todos, uno, les, ni, contra, otros, ese, eso, ante, ellos, esto, mí, antes, algunos, qué, unos, yo, otro, otras, otra, él, tanto, esa, estos, mucho, quienes, nada, muchos, cual, poco, ella, estar, estas, algunas, algo, nosotros, mi, mis, tú, te, ti, tu, tus, ellas, nosotras, vosotros, vosotras, os, estoy, estás, está, estamos, están, he, has, hace, hacía, hacer, cada, ser, haber, era, soy, es, sea, según, sino, sido, siendo, habían, eran, había, nuestra, suya, tuya, cómo, fueron, dr, dra, usted, ustedes, tal, tan, solo, solamente, inclusive, además, después, después, antes, ahora, aun, aún, todavía, siempre, nunca, jamás, hube, hubiese, hubiera, habría, habremos, habrán, aquello, aquella, aquellos, aquellas, cuales, cuanta, cuanto, cuantos, cuantas, aquel, aquello, allí, allá, aquí, acá, ahí, cerca, lejos, arriba, abajo, dentro, fuera, pronto, tarde, temprano, mientras, apenas, hoy, mañana, ayer, anoche, luego, entonces, así, bien, mal, incluso, acaso, quizá, quizás, tal, vez, harto, demasiado, bastante, cuan, casi, igual, diferente, diversos, ambos, sendos, cualquier, cualquiera, cualesquiera, propio, misma, mismo, mismos, mismas, mío, mía, míos, mías, tuyo, tuya, tuyos, tuyas, suyo, suya, suyos, suyas, nuestro, nuestra, nuestros, nuestras, vuestro, vuestra, vuestros, vuestras, cuyo, cuya, cuyos, cuyas, dijo, dice, dijeron, responde, respondió, parece, decir, dicho, hecho, hizo, hicieron, va, vas, vamos, van, vaya, ir, venir, viene, vienen, vino, dio, dar, daban, tenía, tenían, tener, habéis, hayamos, hubierais, hubiesen, pudieras, pudiese, pudimos, podrán, podrá, podrías, cual, cuales, quien, quienes, uno, una, unos, unas, alguna, algunas, alguno, algunos, ningún, ninguna, ningunos, ningunas, otro, otra, otros, otras, ya, pues, puesto, mientras";
      document.getElementById('custom-stopwords').value = defaultStopwords;
      localStorage.setItem('custom_stopwords', defaultStopwords);
      alert('✅ Filtros restaurados a valores predeterminados.');
    });
  }

  // Cargar stopwords guardadas al inicio
  const savedStopwords = localStorage.getItem('custom_stopwords');
  if (savedStopwords) {
    const textarea = document.getElementById('custom-stopwords');
    if (textarea) textarea.value = savedStopwords;
  }

  // ==========================================================
  // 📊 FUNCIONES DE RENDERIZADO
  // ==========================================================
  function renderChart(type, labels, data, title, backgroundColor, isTemporal = false) {
    if (currentChart) {
      currentChart.destroy();
    }

    const isLight = document.body.getAttribute('data-theme') === 'light';
    const textColor = isLight ? '#212121' : '#e0e0e0';
    const accentColor = isLight ? '#294a60' : '#ff9800';
    const gridColor = isLight ? 'rgba(0,0,0,0.05)' : '#333';

    resultado.innerHTML = `
      <div class="card bg-sirio-panel p-4">
        <h4 class="text-accent mb-3">${title}</h4>
        <canvas id="chart-canvas"></canvas>
      </div>
    `;

    const ctx = document.getElementById('chart-canvas').getContext('2d');

    const config = {
      type: type,
      data: {
        labels: labels,
        datasets: [{
          label: title,
          data: data,
          backgroundColor: backgroundColor,
          borderColor: type === 'line' ? accentColor : undefined,
          borderWidth: type === 'line' ? 2 : 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: type === 'pie',
            labels: { color: textColor, font: { family: 'JetBrains Mono' } }
          },
          tooltip: {
            backgroundColor: isLight ? 'rgba(255, 255, 255, 0.95)' : 'rgba(30, 30, 30, 0.9)',
            titleColor: accentColor,
            bodyColor: textColor,
            borderColor: accentColor,
            borderWidth: 1
          }
        },
        scales: type !== 'pie' ? {
          x: {
            ticks: { color: isLight ? '#666' : '#aaa', font: { family: 'JetBrains Mono' } },
            grid: { color: gridColor }
          },
          y: {
            ticks: { color: isLight ? '#666' : '#aaa', font: { family: 'JetBrains Mono' } },
            grid: { color: gridColor }
          }
        } : undefined
      }
    };

    currentChart = new Chart(ctx, config);
  }

  // Generar paleta de colores automática
  function generateColors(count) {
    const isLight = document.body.getAttribute('data-theme') === 'light';

    const darkColors = [
      '#ff9800', '#444950', '#ff6600', '#1a1a1a', '#b26a00', '#ffb300', '#757575', '#ff3d00', '#212121'
    ];

    const lightColors = [
      '#294a60', '#1565c0', '#42a5f5', '#90caf9', '#bdbdbd', '#78909c', '#546e7a', '#0288d1', '#b0bec5'
    ];

    const baseColors = isLight ? lightColors : darkColors;

    const colors = [];
    for (let i = 0; i < count; i++) {
      colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
  }

  // ==========================================================
  // 🤖 FUNCIONES DE RENDERIZADO NLP
  // ==========================================================

  // --- Cargar estadísticas generales ---
  async function loadGeneralStats() {
    try {
      const limit = getDocumentLimit();
      const response = await fetch('/api/corpus-analysis?limit=' + limit);
      const data = await response.json();

      if (data.success && data.stats) {
        document.getElementById('stat-total').textContent = data.stats.total_refs || '0';
        document.getElementById('stat-content').textContent = data.stats.with_content || '0';
        document.getElementById('stat-percentage').textContent = (data.stats.content_percentage || 0) + '%';
      }
    } catch (error) {
      console.error('Error cargando estadísticas:', error);
    }
  }

  // --- Nube de palabras NLP con WordCloud2 ---
  function renderNLPWordCloud(wordFreq) {
    if (!wordFreq || Object.keys(wordFreq).length === 0) {
      resultado.innerHTML = '<div class="alert alert-warning">No hay datos suficientes para generar la nube de palabras</div>';
      return;
    }

    const isLight = document.body.getAttribute('data-theme') === 'light';

    resultado.innerHTML = `
      <div class="card bg-sirio-panel">
        <div class="card-header bg-transparent">
          <h5 class="text-accent mb-0">
            <svg width="20" height="20" fill="currentColor" class="me-2">
              <circle cx="10" cy="10" r="2" fill="var(--ds-accent-primary)"/>
              <circle cx="16" cy="8" r="1.5" fill="var(--ds-accent-primary)"/>
              <circle cx="6" cy="14" r="1.5" fill="var(--ds-accent-primary)"/>
            </svg>
            Nube de Palabras Clave (TF-IDF NLP)
          </h5>
          <small class="text-muted">Términos más relevantes extraídos con procesamiento de lenguaje natural</small>
        </div>
        <div class="card-body">
          <div id="wordcloud-nlp" style="width: 100%; aspect-ratio: 1 / 0.5; min-height: 500px; background: ${isLight ? '#ffffff' : '#000000'}; border: 1px solid var(--ds-border-color); border-radius: 8px; display: flex; align-items: center; justify-content: center;"></div>
        </div>
      </div>
    `;

    setTimeout(() => {
      const container = document.getElementById('wordcloud-nlp');
      if (!container) {
        console.error('Container no encontrado');
        return;
      }

      // Verificar si WordCloud está disponible
      if (typeof WordCloud === 'undefined') {
        container.innerHTML = '<div class="alert alert-danger">Error: Librería WordCloud no cargada</div>';
        console.error('WordCloud2 no está disponible');
        return;
      }

      // Preparar datos - normalizar frecuencias y ordenar por frecuencia
      const entries = Object.entries(wordFreq);
      const maxFreq = Math.max(...entries.map(([, freq]) => freq));

      // DEBUG: Verificar si "sirio" está en los datos
      const sirioData = entries.find(([word]) => word.toLowerCase() === 'sirio');
      console.log('¿Sirio en datos?', sirioData);
      console.log('Total palabras recibidas:', entries.length);
      console.log('Top 10 palabras:', entries.sort((a, b) => b[1] - a[1]).slice(0, 10));

      // Ordenar de mayor a menor frecuencia (las más frecuentes primero, irán al centro)
      entries.sort((a, b) => b[1] - a[1]);

      // Normalizar con escala más amplia para palabras más grandes
      const wordList = entries.map(([word, freq]) => {
        const normalizedWeight = (freq / maxFreq) * 250;
        return [word, normalizedWeight];
      });

      // Guardar la palabra más frecuente para resaltarla
      const topWord = wordList.length > 0 ? wordList[0][0] : '';

      console.log('WordCloud data:', wordList.length, 'palabras');
      console.log('Palabra más frecuente:', wordList[0]);

      const canvas = document.createElement('canvas');
      const width = container.offsetWidth || 1000;
      const height = container.offsetHeight || 600;
      // Usar TODO el ancho sin margen
      canvas.width = width;
      canvas.height = height;
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      container.innerHTML = '';
      container.appendChild(canvas);

      const isLight = document.body.getAttribute('data-theme') === 'light';

      // Paleta moderna
      const darkPalette = [
        '#ff9800', '#444950', '#ff6600', '#1a1a1a', '#b26a00', '#ffb300', '#757575', '#ff3d00'
      ];

      // Escala Azul a Gris para modo claro
      const lightPalette = [
        '#3b5a70', '#4d6a80', '#5f7a90', '#718a9f', '#839aaf', '#95aac0', '#a7bacc', '#b9cadc', '#d0d0d0', '#757575'
      ];

      const modernPalette = isLight ? lightPalette : darkPalette;
      let colorIndex = 0;

      WordCloud(canvas, {
        list: wordList,
        gridSize: 8,
        weightFactor: function (size) {
          return size * (canvas.width / 400);
        },
        fontFamily: 'Roboto Condensed, Arial, sans-serif',
        fontWeight: function (word) {
          return word === topWord ? 'bold' : 'normal';
        },
        color: function (word, weight, fontSize, distance, theta) {
          if (word === topWord) return isLight ? '#294a60' : '#ffffff';
          colorIndex = (colorIndex + 1) % modernPalette.length;
          return modernPalette[colorIndex];
        },
        rotateRatio: 0.5,
        rotationSteps: 2,
        backgroundColor: 'transparent',
        minSize: 8,
        drawOutOfBound: false,
        shrinkToFit: true,
        clearCanvas: true,
        maxRotation: Math.PI / 4,
        minRotation: -Math.PI / 4,
        shuffle: false,
        shape: 'square',
        ellipticity: 0.85,
        wait: 0,
        origin: [canvas.width / 2, canvas.height / 2],
        drawMask: false,
        abortThreshold: 0,
        abort: function () {
          return false;
        }
      });
    }, 100);
  }

  // --- Red de entidades con D3.js ---
  function renderEntityNetwork(entityNetwork) {
    if (!entityNetwork || !entityNetwork.nodes || entityNetwork.nodes.length === 0) {
      resultado.innerHTML = '<div class="alert alert-warning">No hay entidades suficientes para generar la red</div>';
      return;
    }

    const isLight = document.body.getAttribute('data-theme') === 'light';

    resultado.innerHTML = `
      <div class="card bg-sirio-panel">
        <div class="card-header bg-transparent">
          <h5 class="text-accent mb-0">
            <svg width="20" height="20" fill="currentColor" class="me-2">
              <circle cx="5" cy="5" r="3" fill="var(--ds-accent-primary)"/>
              <circle cx="15" cy="5" r="3" fill="var(--ds-accent-primary)"/>
              <circle cx="10" cy="15" r="3" fill="var(--ds-accent-primary)"/>
            </svg>
            Red de Entidades (NER con spaCy)
          </h5>
          <small class="text-muted">Personas (naranja), Lugares (verde), Organizaciones (azul) - Arrastra los nodos</small>
        </div>
        <div class="card-body">
          <div id="network-nlp" style="width: 100%; aspect-ratio: 1 / 0.5; min-height: 500px; background: ${isLight ? '#f8f9fa' : '#1a1a1a'}; border: 1px solid var(--ds-border-color); border-radius: 8px; display: flex; align-items: center; justify-content: center;"></div>
        </div>
      </div>
    `;

    const container = document.getElementById('network-nlp');
    const width = container.offsetWidth;
    const height = container.offsetHeight;

    const svg = d3.select('#network-nlp')
      .append('svg')
      .attr('width', width)
      .attr('height', height);

    const simulation = d3.forceSimulation(entityNetwork.nodes)
      .force('link', d3.forceLink(entityNetwork.links).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    const link = svg.append('g')
      .selectAll('line')
      .data(entityNetwork.links)
      .enter().append('line')
      .attr('stroke', '#555')
      .attr('stroke-opacity', 0.3)
      .attr('stroke-width', 1);

    const node = svg.append('g')
      .selectAll('g')
      .data(entityNetwork.nodes)
      .enter().append('g')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

    node.append('circle')
      .attr('r', d => Math.min(Math.sqrt(d.count) * 5 + 5, 20))
      .attr('fill', d => {
        if (d.type === 'PER') return '#ff9800';
        if (d.type === 'LOC') return '#4a7c2f';
        if (d.type === 'ORG') return '#2196f3';
        return '#999';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    const labelColor = isLight ? '#212121' : '#e0e0e0';

    node.append('text')
      .text(d => d.name)
      .attr('x', 0)
      .attr('y', 25)
      .attr('text-anchor', 'middle')
      .attr('fill', labelColor)
      .attr('font-size', '10px')
      .attr('font-family', 'Roboto Condensed, sans-serif');

    node.append('title')
      .text(d => `${d.name}\nTipo: ${d.type}\nApariciones: ${d.count}`);

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
  }

  // --- Gráfico de keywords NLP ---
  function renderNLPKeywordsChart(wordFreq) {
    if (!wordFreq || Object.keys(wordFreq).length === 0) {
      resultado.innerHTML = '<div class="alert alert-warning">No hay datos para generar el gráfico de keywords</div>';
      return;
    }

    const sorted = Object.entries(wordFreq)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20);

    const labels = sorted.map(([word]) => word);
    const data = sorted.map(([, freq]) => freq);

    const isLight = document.body.getAttribute('data-theme') === 'light';
    const textColor = isLight ? '#212121' : '#e0e0e0';
    const accentColor = isLight ? '#294a60' : '#ff9800';

    resultado.innerHTML = `
      <div class="card bg-sirio-panel">
        <div class="card-header bg-transparent">
          <h5 class="text-accent mb-0">
            <svg width="20" height="20" fill="currentColor" class="me-2">
              <rect x="2" y="14" width="4" height="4" fill="var(--ds-accent-primary)"/>
              <rect x="8" y="10" width="4" height="8" fill="var(--ds-accent-primary)"/>
              <rect x="14" y="6" width="4" height="12" fill="var(--ds-accent-primary)"/>
            </svg>
            Top 20 Keywords (Frecuencia TF-IDF)
          </h5>
          <small class="text-muted">Términos más significativos del corpus</small>
        </div>
        <div class="card-body">
          <canvas id="keywords-nlp-chart" style="max-height: 600px;"></canvas>
        </div>
      </div>
    `;

    const ctx = document.getElementById('keywords-nlp-chart').getContext('2d');
    currentChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Frecuencia',
          data: data,
          backgroundColor: isLight ? 'rgba(41, 74, 96, 0.8)' : 'rgba(255, 152, 0, 0.8)',
          borderColor: accentColor,
          borderWidth: 1
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isLight ? 'rgba(255, 255, 255, 0.95)' : 'rgba(0, 0, 0, 0.9)',
            titleColor: accentColor,
            bodyColor: textColor,
            borderColor: accentColor,
            borderWidth: 1
          }
        },
        scales: {
          x: {
            grid: { color: isLight ? 'rgba(0,0,0,0.05)' : '#333' },
            ticks: { color: isLight ? '#666' : '#e0e0e0' }
          },
          y: {
            grid: { display: false },
            ticks: {
              color: isLight ? '#666' : '#e0e0e0',
              font: { family: 'JetBrains Mono, monospace', size: 11 }
            }
          }
        }
      }
    });
  }
});