/**
 * Módulo Teatral - Atribución Estilométrica Standalone
 */

let filtros = {
  proyecto_id: null
};

let datosActuales = {};
let chartsInstances = {};

const UI_COLORS = {
  isLight: () => document.documentElement.getAttribute('data-theme') === 'light',
  grid: (opacity = 0.1) => UI_COLORS.isLight() ? `rgba(0,0,0,${opacity})` : `rgba(255,255,255,${opacity})`,
  text: () => UI_COLORS.isLight() ? '#294a60' : '#ccc',
  legend: () => UI_COLORS.isLight() ? '#294a60' : '#fff',
  series: (index) => {
    const darkPalette = [
        { border: 'rgba(230, 162, 60, 0.9)', bg: 'rgba(230, 162, 60, 0.15)' }, // Gold/Soft Ochre
        { border: 'rgba(92, 148, 204, 0.9)', bg: 'rgba(92, 148, 204, 0.15)' }, // Soft Blue
        { border: 'rgba(163, 123, 184, 0.9)', bg: 'rgba(163, 123, 184, 0.15)' } // Soft Purple
    ];
    const lightPalette = [
        { border: '#e65100', bg: 'rgba(255, 152, 0, 0.1)' },
        { border: '#006064', bg: 'rgba(0, 242, 255, 0.1)' },
        { border: '#4a148c', bg: 'rgba(156, 39, 176, 0.1)' }
    ];
    const p = UI_COLORS.isLight() ? lightPalette : darkPalette;
    return p[index % p.length];
  }
};

let currentTheme = document.documentElement.getAttribute('data-theme');
const themeObserver = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    if (mutation.attributeName === 'data-theme') {
      const newTheme = document.documentElement.getAttribute('data-theme');
      if (newTheme !== currentTheme) {
        currentTheme = newTheme;
        if (datosActuales && Object.keys(datosActuales).length > 0) {
          renderAtribucion(datosActuales);
        }
      }
    }
  });
});

function showLoader() {
    const btn = document.getElementById('btn-atribucion-comparar');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>ANALIZANDO...`;
    }
}

function hideLoader() {
    const btn = document.getElementById('btn-atribucion-comparar');
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-bolt-lightning me-2"></i>Iniciar Análisis`;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar observador de tema
    themeObserver.observe(document.documentElement, { attributes: true });

    const activeProj = document.body.dataset.proyectoId || '';
    filtros.proyecto_id = activeProj;

    // Persistencia del Selector de IA
    const aiSelector = document.getElementById('ai-model-selector');
    if (aiSelector) {
        const savedModel = sessionStorage.getItem('hesi_teatral_ai_model');
        if (savedModel) aiSelector.value = savedModel;
        
        aiSelector.addEventListener('change', function() {
            sessionStorage.setItem('hesi_teatral_ai_model', this.value);
        });
    }
    
    cargarObrasParaAtribucion();
});

function renderAtribucion(data) {
  datosActuales = data; // Guardar para re-renderizar en cambio de tema
  const deltaBody = document.getElementById('atribucion-delta-body');
  const vocabList = document.getElementById('atribucion-vocab-list');
  const ctxRadar = document.getElementById('chart-atribucion-radar');

  if (!data || !data.exito) {
    if (deltaBody) deltaBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">${data.error || 'Error al cargar datos'}</td></tr>`;
    if (vocabList) vocabList.innerText = '---';
    if (chartsInstances['atribucion-radar']) {
        chartsInstances['atribucion-radar'].destroy();
        chartsInstances['atribucion-radar'] = null;
    }
    return;
  }

  // 1. Matriz Delta
  if (deltaBody) {
    if (!data.matriz_delta || data.matriz_delta.length === 0) {
      deltaBody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">Se requieren al menos 2 obras coincidentes con texto suficiente.</td></tr>`;
    } else {
      let html = '';
      data.matriz_delta.forEach(row => {
        let affinityClass = 'text-danger';
        if (row.similitud_prob > 75) affinityClass = 'text-success fw-bold';
        else if (row.similitud_prob > 40) affinityClass = 'text-warning';

        html += `
          <tr>
            <td>
              <div class="fw-bold text-truncate" style="max-width: 180px;" title="${row.titulo_a}">${row.titulo_a}</div>
              <div class="xsmall text-muted">${row.autor_a}</div>
            </td>
            <td>
              <div class="fw-bold text-truncate" style="max-width: 180px;" title="${row.titulo_b}">${row.titulo_b}</div>
              <div class="xsmall text-muted">${row.autor_b}</div>
            </td>
            <td class="text-center font-monospace" style="color: var(--ds-accent-primary);">${row.delta.toFixed(3)}</td>
            <td class="text-center ${affinityClass}">${row.similitud_prob.toFixed(1)}%</td>
          </tr>
        `;
      });
      deltaBody.innerHTML = html;
    }
  }

  // 2. Vocabulario Base
  if (vocabList && data.vocabulario_frecuente) {
    vocabList.innerText = data.vocabulario_frecuente.join(' · ');
  }

  // AI Interpretation Button
  const aiContainer = document.getElementById('atribucion-ai-container');
  if (aiContainer) {
    aiContainer.innerHTML = `
      <div class="mt-4 p-4 rounded-3 border border-sirio-accent-alpha" style="background: var(--ds-bg-app);">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h6 class="mb-0 small fw-bold text-uppercase" style="color: var(--ds-accent-primary);">
            <i class="fa-solid fa-wand-magic-sparkles me-2"></i>Interpretación Estratégica (IA PRO)
          </h6>
          <button id="btn-atribucion-ai" class="btn btn-sm btn-outline-sirio">
            <i class="fa-solid fa-brain me-1"></i>Generar Informe IA
          </button>
        </div>
        <div id="atribucion-ai-content" class="xsmall text-muted" style="line-height: 1.6;">
          Pulsa el botón para que la IA analice las distancias Delta y el vocabulario evaluado.
        </div>
      </div>
    `;
    
    document.getElementById('btn-atribucion-ai')?.addEventListener('click', interpretarAtribucionIA);
  }

  // 3. Gráfico Radar
  if (chartsInstances['atribucion-radar']) {
    chartsInstances['atribucion-radar'].destroy();
  }

  if (ctxRadar && data.metricas_comparativas && data.metricas_comparativas.length > 0) {
    const labels = [
      'Diversidad Léxica',
      'Palabras/Oración',
      'Longitud Palabra',
      'Puntuación (%)',
      'Pronombres (%)',
      'Preposiciones (%)',
      'Conjunciones (%)',
      'Adverbios (%)'
    ];

    const maxVals = { ttr: 0, ppo: 0, lp: 0, punt: 0, pron: 0, prep: 0, conj: 0, adv: 0 };
    data.metricas_comparativas.forEach(doc => {
      const m = doc.metricas;
      maxVals.ttr = Math.max(maxVals.ttr, m.diversidad_lexica || 0.001);
      maxVals.ppo = Math.max(maxVals.ppo, m.palabras_por_oracion || 0.001);
      maxVals.lp = Math.max(maxVals.lp, m.longitud_promedio_palabra || 0.001);
      maxVals.punt = Math.max(maxVals.punt, m.densidad_puntuacion || 0.001);
      maxVals.pron = Math.max(maxVals.pron, m.ratio_pronombres || 0.001);
      maxVals.prep = Math.max(maxVals.prep, m.ratio_preposiciones || 0.001);
      maxVals.conj = Math.max(maxVals.conj, m.ratio_conjunciones || 0.001);
      maxVals.adv = Math.max(maxVals.adv, m.ratio_adverbios || 0.001);
    });

    const datasets = data.metricas_comparativas.slice(0, 4).map((doc, idx) => {
      const m = doc.metricas;
      const color = UI_COLORS.series(idx);

      const dataValues = [
        ((m.diversidad_lexica || 0) / maxVals.ttr) * 100,
        ((m.palabras_por_oracion || 0) / maxVals.ppo) * 100,
        ((m.longitud_promedio_palabra || 0) / maxVals.lp) * 100,
        ((m.densidad_puntuacion || 0) / maxVals.punt) * 100,
        ((m.ratio_pronombres || 0) / maxVals.pron) * 100,
        ((m.ratio_preposiciones || 0) / maxVals.prep) * 100,
        ((m.ratio_conjunciones || 0) / maxVals.conj) * 100,
        ((m.ratio_adverbios || 0) / maxVals.adv) * 100
      ];

      return {
        label: doc.titulo.length > 15 ? doc.titulo.substring(0, 15) + '...' : doc.titulo,
        data: dataValues,
        borderColor: color.border,
        backgroundColor: color.bg,
        borderWidth: 2,
        pointBackgroundColor: color.border
      };
    });

    chartsInstances['atribucion-radar'] = new Chart(ctxRadar, {
      type: 'radar',
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            angleLines: { color: UI_COLORS.grid(0.1) },
            grid: { color: UI_COLORS.grid(0.1) },
            pointLabels: { color: UI_COLORS.text(), font: { size: 10 } },
            ticks: { display: false },
            suggestedMin: 0,
            suggestedMax: 100
          }
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: UI_COLORS.legend(), font: { size: 11 }, padding: 10, boxWidth: 12 }
          }
        }
      }
    });
  }
}

function cargarObrasParaAtribucion() {
  const select = document.getElementById('atribucion-obras-select');
  if (!select) return;

  showLoader();

  const btn = document.getElementById('btn-atribucion-comparar');
  if (btn && !btn.dataset.bound) {
    btn.addEventListener('click', ejecutarAtribucion);
    btn.dataset.bound = 'true';
  }

  fetch('/api/analisis/lista-publicaciones', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    },
    body: JSON.stringify({})
  })
    .then(res => res.json())
    .then(data => {
      hideLoader();
      
      if (data.exito && data.publicaciones && data.publicaciones.length > 0) {
        let optionsHtml = '';
        data.publicaciones.forEach(pub => {
          optionsHtml += `<option value="${pub.id}" selected>${pub.nombre} (${pub.autor})</option>`;
        });

        const id = 'atribucion-obras-select';
        const el = document.getElementById(id);
        if (!el) return;
        
        if (window.choicesInstances && window.choicesInstances[id]) {
          try {
            window.choicesInstances[id].destroy();
          } catch (err) {}
          delete window.choicesInstances[id];
        }
        
        el.innerHTML = optionsHtml;
        
        if (typeof Choices !== 'undefined') {
           window.choicesInstances = window.choicesInstances || {};
           const c = new Choices(el, {
              searchEnabled: true,
              itemSelectText: '',
              shouldSort: false,
              removeItemButton: true,
              allowHTML: true,
              placeholder: true,
              placeholderValue: 'Selecciona las obras a comparar...'
           });
           window.choicesInstances[id] = c;
        }

        // Ejecutar primer análisis
        ejecutarAtribucion();
      } else {
        const id = 'atribucion-obras-select';
        const el = document.getElementById(id);
        if (el) {
          const errorMsg = data.error || 'No hay publicaciones disponibles.';
          el.innerHTML = `<option disabled selected>⚠️ ${errorMsg}</option>`;
        }
      }
    })
    .catch(err => {
      hideLoader();
      const id = 'atribucion-obras-select';
      const el = document.getElementById(id);
      if (el) el.innerHTML = `<option disabled selected>❌ Error: ${err.message}</option>`;
    });
}

function ejecutarAtribucion() {
  const select = document.getElementById('atribucion-obras-select');
  if (!select) return;

  let selectedIds = [];
  const id = 'atribucion-obras-select';
  if (window.choicesInstances && window.choicesInstances[id]) {
    selectedIds = window.choicesInstances[id].getValue(true).map(val => parseInt(val));
  } else {
    selectedIds = Array.from(select.selectedOptions).map(opt => parseInt(opt.value));
  }
  
  if (selectedIds.length < 2) {
    alert('Por favor, selecciona al menos 2 obras para poder calcular el Burrows\' Delta.');
    return;
  }

  const mfwSelect = document.getElementById('atribucion-mfw-select');
  const top_n = mfwSelect ? parseInt(mfwSelect.value) : 500;

  const payload = {
    publicaciones_ids: selectedIds,
    top_n: top_n,
    limit: 1000,
    refresh: true 
  };

  showLoader();

  fetch('/api/analisis/atribucion', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    },
    body: JSON.stringify(payload)
  })
    .then(res => res.json())
    .then(data => {
      hideLoader();
      datosActuales['atribucion'] = data;
      renderAtribucion(data);
    })
    .catch(err => {
      hideLoader();
      console.error('[ERROR] Error ejecutando comparativa Delta:', err);
    });
}

function interpretarAtribucionIA() {
  const btn = document.getElementById('btn-atribucion-ai');
  const content = document.getElementById('atribucion-ai-content');
  
  if (!datosActuales || !datosActuales.matriz_delta) {
    alert("Primero debes ejecutar el análisis Delta para poder interpretarlo.");
    return;
  }
  
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Analizando...';
  content.innerHTML = '<div class="text-center p-3"><i class="fa-solid fa-gear fa-spin me-2"></i>Consultando modelos de IA PRO...</div>';

  console.log("[DEBUG] Solicitando interpretación IA con modelo:", document.getElementById('ai-model-selector')?.value || 'gemini:pro');
  
  fetch('/teatral/interpretar_atribucion', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    },
    body: JSON.stringify({
      delta_results: datosActuales,
      model: document.getElementById('ai-model-selector')?.value || 'gemini:pro'
    })
  })
    .then(res => res.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-brain me-1"></i>Generar Informe IA';
      
      if (data.exito) {
        content.innerHTML = `<div class="ai-response-text" style="font-size: 0.85rem; color: var(--ds-text-main);">${data.interpretacion.replace(/\n/g, '<br>')}</div>`;
      } else {
        content.innerHTML = `<span class="text-danger">Error: ${data.error}</span>`;
      }
    })
    .catch(err => {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-brain me-1"></i>Generar Informe IA';
      content.innerHTML = `<span class="text-danger">Error de conexión.</span>`;
    });
}
