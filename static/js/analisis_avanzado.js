/**
 * Análisis Avanzado - JavaScript
 * Proyecto Sirio
 */

// Estado global
let filtros = {
  tema: null,
  publicacion_id: null,
  pais: null,
  fecha_desde: null,
  fecha_hasta: null,
  eje_x: 'fecha',
  documentos_ids: [],
  limite: 300  // Límite por defecto (300 documentos)
};

// Helpers para Loader (Resistentes a elementos faltantes)
function showLoader() {
  const loader = document.getElementById('loading-state');
  if (loader) loader.style.display = 'flex';
}

function hideLoader() {
  const loader = document.getElementById('loading-state');
  if (loader) loader.style.display = 'none';
}

let datosActuales = {};
let chartsInstances = {};
window._ia_modelo = 'flash'; // Global model selection (flash by default)

/**
 * Cambia la potencia de la IA seleccionada y actualiza la UI
 */
window.setIAPotency = function(p, el) {
    window._ia_modelo = p;
    document.querySelectorAll('.dropdown-item').forEach(i => i.classList.remove('active'));
    el.classList.add('active');

    let label = 'Gemini Flash';
    if (p === 'pro') label = 'Gemini Pro';
    else if (p === 'gemini-3-flash') label = 'Gemini 3 Flash';
    else if (p === 'gemini-3-pro') label = 'Gemini 3 Pro';
    else if (p === 'openai') label = 'GPT-4o';
    else if (p === 'anthropic') label = 'Claude 3.5';
    else if (p === 'llama') label = 'Llama 3 Local';

    const dropdownBtnText = document.getElementById('label-ia-potency');
    if (dropdownBtnText) {
        dropdownBtnText.innerText = label.toUpperCase();
    }
};


// Helpers de Color para Temas
const UI_COLORS = {
  isLight: () => document.documentElement.getAttribute('data-theme') === 'light',
  grid: (opacity = 0.2) => UI_COLORS.isLight() ? `rgba(0,0,0,${opacity})` : `rgba(255,255,255,0.1)`,
  text: () => UI_COLORS.isLight() ? '#294a60' : '#ccc',
  legend: () => UI_COLORS.isLight() ? '#294a60' : '#fff', // Blue for light mode
  accent: () => UI_COLORS.isLight() ? '#294a60' : '#ff9800'
};

/**
 * Parchea una especificación de Vega-Lite para actualizar colores según el tema
 */
function patchVegaTheme(spec, theme) {
  if (!spec) return spec;
  const isLight = theme === 'light';
  const textColor = isLight ? '#294a60' : '#ccc';
  const accentColor = isLight ? '#0056b3' : '#ff9800';
  const gridColor = isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';
  const pointColor = isLight ? '#0056b3' : '#ffffff';

  let newSpec;
  try {
    newSpec = typeof spec === 'string' ? JSON.parse(spec) : JSON.parse(JSON.stringify(spec));
  } catch (e) {
    console.error('[DEBUG] Error inicial parseando spec Vega:', e);
    return spec;
  }

  // Función recursiva para parchear marcas (marks)
  function patchMark(mark) {
    if (!mark) return;
    if (typeof mark === 'object') {
      if (mark.type === 'circle' || mark.type === 'point' || mark.type === 'tick') mark.color = pointColor;
      else if (mark.type === 'line' || mark.type === 'area' || mark.type === 'bar') mark.color = accentColor;
    }
  }

  // Parchear configuración global
  if (newSpec.config) {
    if (newSpec.config.axis) {
      newSpec.config.axis.labelColor = textColor;
      newSpec.config.axis.titleColor = accentColor;
      newSpec.config.axis.gridColor = gridColor;
    }
    if (newSpec.config.title) {
      newSpec.config.title.color = accentColor;
    }
  }

  // Parchear marcas principales
  patchMark(newSpec.mark);

  // Parchear marcas en capas (layers) recursivamente
  if (newSpec.layer && Array.isArray(newSpec.layer)) {
    newSpec.layer.forEach(l => {
      patchMark(l.mark);
      // Recursión para capas anidadas
      if (l.layer) {
        l.layer.forEach(sl => {
          patchMark(sl.mark);
          if (sl.layer) {
            sl.layer.forEach(ssl => patchMark(ssl.mark));
          }
        });
      }
    });
  }

  // Parchear especificaciones anidadas (hconcat, vconcat, repeat, facet)
  ['hconcat', 'vconcat', 'repeat', 'facet'].forEach(concatType => {
    if (newSpec[concatType] && Array.isArray(newSpec[concatType])) {
      newSpec[concatType] = newSpec[concatType].map(item => patchVegaTheme(item, theme));
    }
  });

  // Forzar fondo transparente
  newSpec.background = "transparent";

  return newSpec;
}

// Configuración Global de Zoom para Chart.js
const CHART_ZOOM_CONFIG = {
  zoom: {
    wheel: { enabled: true, speed: 0.1 },
    pinch: { enabled: true },
    mode: 'x',
    drag: { enabled: false }
  },
  pan: {
    enabled: true,
    mode: 'x',
    threshold: 10
  }
};

// Función para resetear zoom al hacer doble clic
const resetZoomOnDoubleClick = (chart) => {
  chart.canvas.addEventListener('dblclick', () => {
    chart.resetZoom();
  });
};


// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', function () {
  // Recarga de caché
  const btnRecargarCache = document.getElementById('btn-recargar-cache');
  if (btnRecargarCache) {
    btnRecargarCache.addEventListener('click', function () {
      btnRecargarCache.disabled = true;
      btnRecargarCache.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span class="btn-text">Recargando...</span>';
      fetch('/api/analisis/recargar_cache', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        }
      })
        .then(res => res.json())
        .then(data => {
          btnRecargarCache.disabled = false;
          btnRecargarCache.innerHTML = '<i class="fa-solid fa-rotate-right"></i> <span class="btn-text">Recargar Caché</span>';
          cargarDashboard();
        })
        .catch(() => {
          btnRecargarCache.disabled = false;
          btnRecargarCache.innerHTML = '<i class="fa-solid fa-rotate-right"></i> <span class="btn-text">Recargar Caché</span>';
          alert('Error al recargar la caché');
        });
    });
  }
  // Event listeners para botones de análisis
  document.querySelectorAll('[data-analisis]').forEach(btn => {
    btn.addEventListener('click', function () {
      if (this.classList.contains('btn-sirio-inactivo')) return;

      const tipo = this.dataset.analisis;
      cambiarVista(tipo);

      // Actualizar botones activos (y checkmarks)
      document.querySelectorAll('[data-analisis]').forEach(b => {
        b.classList.remove('active');
        // Reset estilos inline para botones fuera de dropdown
        if (!b.classList.contains('dropdown-item')) {
          b.style.borderColor = '';
          b.style.color = '';
        }
      });
      
      this.classList.add('active');
      
      // Resetear visualmente todos los toggles de dropdown
      document.querySelectorAll('.dropdown-toggle').forEach(t => {
        t.classList.remove('active');
        t.style.borderColor = '';
        t.style.color = '';
      });

      // Si el botón clicado está en un dropdown, resaltar su padre
      const parentDropdown = this.closest('.dropdown');
      if (parentDropdown) {
        const toggle = parentDropdown.querySelector('.dropdown-toggle');
        if (toggle) {
          toggle.classList.add('active');
          toggle.style.borderColor = 'var(--ds-accent-primary)';
          toggle.style.color = 'var(--ds-accent-primary)';
        }
      } else {
        // Estilo activo para botones principales (Dashboard, Tópicos, etc)
        this.style.borderColor = 'var(--ds-accent-primary)';
        this.style.color = 'var(--ds-accent-primary)';
      }
    });
  });

  // Filtros
  const btnFiltros = document.getElementById('btn-filtros');
  if (btnFiltros) {
    btnFiltros.addEventListener('click', function () {
      const offcanvasElement = document.getElementById('offcanvasFiltros');
      if (offcanvasElement) {
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasElement);
        offcanvas.show();
      }
    });
  }

  const btnAplicarFiltros = document.getElementById('btn-aplicar-filtros');
  if (btnAplicarFiltros) {
    btnAplicarFiltros.addEventListener('click', function () {
      aplicarFiltros();
      const offcanvasElement = document.getElementById('offcanvasFiltros');
      if (offcanvasElement) {
        const offcanvas = bootstrap.Offcanvas.getInstance(offcanvasElement);
        if (offcanvas) offcanvas.hide();
      }
    });
  }

  // Exportar
  const btnExportar = document.getElementById('btn-exportar');
  if (btnExportar) {
    btnExportar.addEventListener('click', exportarResultados);
  }

  // Listeners para botones de n-gramas (bigramas, trigramas, 4-gramas)
  const ngramaBotones = document.querySelectorAll('#view-ngramas .btn-group [data-n]');
  console.log('[DEBUG] Botones de n-gramas encontrados:', ngramaBotones.length);

  ngramaBotones.forEach(btn => {
    console.log('[DEBUG] Registrando listener para botón n=', btn.dataset.n);
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      const n = parseInt(this.dataset.n);
      console.log('[DEBUG] Click en botón n-grama, n=', n);

      // Actualizar botones activos
      document.querySelectorAll('#view-ngramas .btn-group [data-n]').forEach(b => b.classList.remove('active'));
      this.classList.add('active');

      // Recargar n-gramas con nuevo valor de n
      cargarNgramas(n);
    });
  });

  // Listener para cambio en top_k de n-gramas
  const ngramasTopSelect = document.getElementById('ngramas-top');
  if (ngramasTopSelect) {
    ngramasTopSelect.addEventListener('change', function () {
      const btnActivo = document.querySelector('#view-ngramas .btn-group [data-n].active');
      if (btnActivo) {
        const n = parseInt(btnActivo.dataset.n);
        cargarNgramas(n);
      }
    });
  }

  if (document.getElementById('view-dashboard')) {
    cargarDashboard();
  }

  // Listener para cambio de eje X (Secuencial vs Cronológico)
  document.querySelectorAll('input[name="eje_x"]').forEach(radio => {
    radio.addEventListener('change', function () {
      const container = document.getElementById('container-filtro-documentos');
      if (this.value === 'secuencia') {
        container.style.display = 'block';
        cargarListaDocumentos();
      } else {
        container.style.display = 'none';
      }
    });
  });

  // Listener para refrescar lista de documentos si cambian otros filtros
  ['filtro-tema', 'filtro-publicacion', 'filtro-pais', 'filtro-fecha-desde', 'filtro-fecha-hasta'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', function () {
        const ejeXEl = document.querySelector('input[name="eje_x"]:checked');
        const ejeX = ejeXEl ? ejeXEl.value : 'fecha';
        if (ejeX === 'secuencia') {
          cargarListaDocumentos();
        }
      });
    }
  });

  // Clustering
  const btnRecalcularClustering = document.getElementById('btn-recalcular-clustering');
  if (btnRecalcularClustering) {
    btnRecalcularClustering.addEventListener('click', function () {
      const n = parseInt(document.getElementById('clustering-n').value) || 5;
      cargarClustering(n);
    });
  }

  // --- DETECTOR DE CAMBIO DE TEMA PARA RE-RENDERIZADO ---
  const themeObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.attributeName === 'data-theme') {
        const newTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        console.log('[DEBUG] Cambio de tema detectado:', newTheme);

        // Re-renderizar si hay datos
        if (datosActuales['dashboard']) {
          renderDashboard(datosActuales['dashboard']);
        }

        // Re-renderizar vistas específicas si están visibles
        const tipo = getVistaActiva();
        if (datosActuales[tipo]) {
          if (tipo === 'dashboard') {
            renderDashboard(datosActuales['dashboard']);
          } else {
            cambiarVista(tipo);
          }
        }
      }
    });
  });

  themeObserver.observe(document.documentElement, { attributes: true });
});

// ============================================
// NAVEGACIÓN ENTRE VISTAS
// ============================================

function getVistaActiva() {
  const views = document.querySelectorAll('.analisis-view');
  for (const view of views) {
    if (view.style.display === 'block') {
      return view.id.replace('view-', '');
    }
  }
  return 'dashboard';
}


function cambiarVista(tipo) {
  // Ocultar filtros dinámicos de sidebar por defecto
  const sidebarDyn = document.getElementById('sidebar-dynamic-filters');
  if (sidebarDyn) sidebarDyn.style.display = 'none';

  // Ocultar todas las vistas
  document.querySelectorAll('.analisis-view').forEach(view => {
    view.style.display = 'none';
  });

  // Mostrar vista seleccionada
  const vista = document.getElementById(`view-${tipo}`);
  if (vista) {
    vista.style.display = 'block';

    // Cargar datos específicos si no están cargados
    if (tipo !== 'dashboard' && !datosActuales[tipo]) {
      // Esperar un frame para que el DOM se actualice
      requestAnimationFrame(() => {
        // N-gramas usa su propia función de carga con parámetros especiales
        if (tipo === 'ngramas') {
          cargarNgramas(2); // Cargar bigramas por defecto
        } else if (tipo === 'clustering') {
          cargarClustering();
        } else if (tipo === 'estilo') {
          cargarAnalisis('estilo');
          cargarInnovador(); // Carga también la dispersión y heatmap
        } else if (tipo === 'subtexto') {
          // No cargar automáticamente, esperar clic del usuario o usar datos previos
          if (datosActuales['subtexto']) renderSubtexto(datosActuales['subtexto']);
        } else if (tipo === 'atribucion') {
          cargarObrasParaAtribucion();
        } else {
          cargarAnalisis(tipo);
        }
      });
    } else if (tipo !== 'dashboard' && datosActuales[tipo]) {
      // Si ya hay datos cargados, re-renderizar
      requestAnimationFrame(() => {
        let renderizado = false;
        switch (tipo) {
          case 'sentimiento': renderSentimiento(datosActuales[tipo]); renderizado = true; break;
          case 'retorica': renderRetorica(datosActuales[tipo]); renderizado = true; break;
          case 'periodistico': renderPeriodistico(datosActuales[tipo]); renderizado = true; break;
          case 'topics': renderTopics(datosActuales[tipo]); renderizado = true; break;
          case 'entidades': renderEntidades(datosActuales[tipo]); renderizado = true; break;
          case 'estilo':
            renderEstilo(datosActuales[tipo]);
            if (datosActuales['innovador']) renderInnovador(datosActuales['innovador']);
            renderizado = true;
            break;
          case 'ngramas': renderNgramas(datosActuales[tipo]); renderizado = true; break;
          case 'clustering': renderClustering(datosActuales[tipo]); renderizado = true; break;
          case 'semantico': renderSemantico(datosActuales[tipo]); renderizado = true; break;
          case 'emociones': renderEmociones(datosActuales[tipo]); renderizado = true; break;
          case 'sesgos': renderSesgos(datosActuales[tipo]); renderizado = true; break;
          case 'intertextualidad': renderIntertextualidad(datosActuales[tipo]); renderizado = true; break;
          case 'subtexto': renderSubtexto(datosActuales[tipo]); renderizado = true; break;
          case 'atribucion': renderAtribucion(datosActuales[tipo]); renderizado = true; break;
        }

        // Asegurarse de ocultar el loading si ya tenemos los datos
        const loader = document.getElementById('loading-state');
        if (loader && renderizado) {
          loader.style.display = 'none';
        }
      });
    }

    // Seguridad: Ocultar loading tras un tiempo si algo falla
    setTimeout(() => {
      hideLoader();
    }, 3000);
  }
}

// ============================================
// CARGA DE DATOS
// ============================================

function cargarDashboard() {
  console.log('[DEBUG] Iniciando carga del dashboard...');
  showLoader();
  console.log('[DEBUG] Intento de mostrar spinner realizado');

  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';

  fetch('/api/analisis/dashboard', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    },
    body: JSON.stringify({ ...filtros, theme: currentTheme })
  })
    .then(async res => {
      const contentType = res.headers.get('content-type');

      // Verificar si la respuesta es JSON
      if (contentType && contentType.includes('application/json')) {
        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error || `Error ${res.status}`);
        }

        return data;
      } else {
        // Si no es JSON, es HTML de error
        const text = await res.text();
        console.error('Respuesta no-JSON:', text);
        throw new Error('El servidor devolvió una respuesta inesperada. Verifica que tengas publicaciones en tu proyecto.');
      }
    })
    .then(data => {
      console.log('[DEBUG] Datos del dashboard recibidos:', data);
      const loadingEl = document.getElementById('loading-state');
      const dashboardEl = document.getElementById('view-dashboard');

      if (!loadingEl) {
        console.error('[ERROR] loading-state no encontrado al ocultar');
      } else {
        loadingEl.style.display = 'none';
        console.log('[DEBUG] Spinner ocultado');
      }

      if (!dashboardEl) {
        console.error('[ERROR] view-dashboard no encontrado');
        return;
      }

      if (data.exito) {
        try {
          datosActuales['dashboard'] = data;
          console.log('[DEBUG] Llamando a renderDashboard...');
          renderDashboard(data);
          console.log('[DEBUG] renderDashboard completado, mostrando vista...');
          dashboardEl.style.display = 'block';
          console.log('[DEBUG] Dashboard mostrado correctamente');
        } catch (error) {
          console.error('[ERROR] Error al renderizar dashboard:', error);
          console.error('[ERROR] Stack:', error.stack);
          mostrarError('Error al renderizar el dashboard: ' + error.message);
        }
      } else {
        mostrarError(data.error || 'Error desconocido al cargar el dashboard');
      }
    })
    .catch(err => {
      hideLoader();
      console.error('Error completo:', err);
      mostrarError(err.message || 'Error de conexión');
    });
}

function cargarAnalisis(tipo) {
  const endpoints = {
    'sentimiento': '/api/analisis/sentimiento-temporal',
    'retorica': '/api/analisis/retorica',
    'periodistico': '/api/analisis/periodistico',
    'topics': '/api/analisis/topic-modeling',
    'entidades': '/api/analisis/coocurrencia-entidades',
    'estilo': '/api/analisis/estilometrico',
    'ngramas': '/api/analisis/ngramas',
    'clustering': '/api/analisis/clustering',
    'dramatico': '/api/analisis/dramatico',
    'semantico': '/api/analisis/innovador/semantico',
    'intertextualidad': '/api/analisis/innovador/intertextualidad',
    'emociones': '/api/analisis/innovador/emociones',
    'sirio_chat': '/api/analisis/innovador/sirio_chat',
    'sesgos': '/api/analisis/innovador/sesgos',
    'atribucion': '/api/analisis/atribucion'
  };

  const endpoint = endpoints[tipo];
  if (!endpoint) return;

  // Cargar alias manuales para el análisis dramático
  const projectKey = `aliases_${filtros.proyecto_id || 'default'}`;
  const manual_aliases = tipo === 'dramatico' ? JSON.parse(localStorage.getItem(projectKey) || '{}') : {};

  console.log('[DEBUG] Cargando análisis:', tipo);

  fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    },
    body: JSON.stringify({ 
      ...(tipo === 'dramatico' ? { ...filtros, publicacion_id: null } : filtros),
      n: 2, 
      top_k: 20, 
      n_topics: 5, 
      n_clusters: 5,
      manual_aliases: manual_aliases
    })
  })
    .then(async res => {
      const contentType = res.headers.get('content-type');

      if (contentType && contentType.includes('application/json')) {
        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error || `Error ${res.status}`);
        }

        return data;
      } else {
        const text = await res.text();
        console.error('Respuesta no-JSON:', text);
        throw new Error('El servidor devolvió una respuesta inesperada');
      }
    })
    .then(data => {
      console.log('[DEBUG] Datos de', tipo, 'recibidos. ¿IA presente?:', data.analisis_ia !== undefined && data.analisis_ia !== null);

      if (data.exito) {
        datosActuales[tipo] = data;

        // Centralizar ocultación de loading
        const loader = document.getElementById('loading-state');
        if (loader) loader.style.display = 'none';

        // Renderizar según tipo
        switch (tipo) {
          case 'sentimiento':
            renderSentimiento(data);
            break;
          case 'retorica':
            renderRetorica(data);
            break;
          case 'periodistico':
            renderPeriodistico(data);
            break;
          case 'topics':
            renderTopics(data);
            break;
          case 'entidades':
            renderEntidades(data);
            break;
          case 'estilo':
            renderEstilo(data);
            break;
          case 'ngramas':
            renderNgramas(data);
            break;
          case 'clustering':
            renderClustering(data);
            break;
          case 'dramatico':
            loadDramatico(data);
            break;
          case 'semantico':
            renderSemantico(data);
            break;
          case 'intertextualidad':
            renderIntertextualidad(data);
            break;
          case 'emociones':
            renderEmociones(data);
            break;
          case 'sirio_chat':
            // No hay datos previos, solo prepararlo
            break;
          case 'sesgos':
            renderSesgos(data);
            break;
        }
      } else {
        mostrarError(data.error || 'Error desconocido');
      }
    })
    .catch(err => {
      console.error('[ERROR] Error al cargar', tipo, ':', err);
      mostrarError(err.message || 'Error de conexión');
    });
}

// Función específica para cargar n-gramas con parámetros personalizados
function cargarNgramas(n) {
  const topK = parseInt(document.getElementById('ngramas-top').value) || 20;

  console.log('[DEBUG] Cargando n-gramas con n=', n, 'top_k=', topK);

  fetch('/api/analisis/ngramas', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    },
    body: JSON.stringify({ ...filtros, n: n, top_k: topK })
  })
    .then(async res => {
      const contentType = res.headers.get('content-type');

      if (contentType && contentType.includes('application/json')) {
        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error || `Error ${res.status}`);
        }

        return data;
      } else {
        const text = await res.text();
        console.error('Respuesta no-JSON:', text);
        throw new Error('El servidor devolvió una respuesta inesperada');
      }
    })
    .then(data => {
      console.log('[DEBUG] N-gramas recibidos:', data);

      if (data.exito) {
        datosActuales['ngramas'] = data;
        renderNgramas(data);
      } else {
        mostrarError(data.error || 'Error al cargar n-gramas');
      }
    })
    .catch(err => {
      console.error('[ERROR] Error al cargar n-gramas:', err);
      mostrarError(err.message || 'Error de conexión');
    });
}

function cargarClustering(nClusters) {
  const n = nClusters || parseInt(document.getElementById('clustering-n').value) || 5;

  console.log('[DEBUG] Cargando clustering con n_clusters=', n);

  // Mostrar loading
  const loader = document.getElementById('loading-state');
  if (loader) loader.style.display = 'flex';

  fetch('/api/analisis/clustering', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    },
    body: JSON.stringify({ ...filtros, n_clusters: n })
  })
    .then(async res => {
      const contentType = res.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
        return data;
      } else {
        const text = await res.text();
        console.error('Respuesta no-JSON:', text);
        throw new Error('El servidor devolvió una respuesta inesperada');
      }
    })
    .then(data => {
      console.log('[DEBUG] Clustering recibido:', data);
      if (data.exito) {
        datosActuales['clustering'] = data;
        const loader = document.getElementById('loading-state');
        if (loader) loader.style.display = 'none';
        renderClustering(data);
      } else {
        mostrarError(data.error || 'Error al cargar clustering');
      }
    })
    .catch(err => {
      console.error('[ERROR] Error al cargar clustering:', err);
      mostrarError(err.message || 'Error de conexión');
    });
}

// ============================================
// RENDERIZADO: DASHBOARD
// ============================================

function renderDashboard(data) {
  console.log('[DEBUG] Renderizando dashboard con datos:', data);

  try {
    // Métricas generales
    const metricas = document.getElementById('metricas-generales');

    if (!metricas) {
      throw new Error('Elemento metricas-generales no encontrado');
    }

    // Valores seguros con validación
    const sentimientoPromedio = (data.sentimiento && data.sentimiento.exito && data.sentimiento.estadisticas)
      ? data.sentimiento.estadisticas.promedio_sentimiento.toFixed(2)
      : 'N/A';

    const topicsCount = (data.topics && data.topics.exito && data.topics.n_topics)
      ? data.topics.n_topics
      : 'N/A';

    const palabrasPromedio = (data.estilometria && data.estilometria.exito && data.estilometria.estadisticas_globales)
      ? Math.round(data.estilometria.estadisticas_globales.promedio_palabras)
      : 'N/A';

    metricas.innerHTML = `
    <div class="col-md-3">
      <div class="text-center p-3 rounded" style="background: rgba(var(--ds-accent-rgb), 0.1);">
        <i class="fa-solid fa-file-lines text-accent fa-2x mb-2"></i>
        <div class="text-muted small">Documentos</div>
        <div class="h3 text-white mt-2">${data.total_documentos || 0}</div>
        <div class="text-muted opacity-75 mt-2" style="font-size: 0.65rem; line-height: 1.2;">
          <i class="fa-solid fa-circle-info me-1"></i>
          En el botón filtro se puede cambiar el número de documentos a analizar
        </div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="text-center p-3 rounded" style="background: rgba(40, 167, 69, 0.1);">
        <i class="fa-solid fa-smile text-success fa-2x mb-2"></i>
        <div class="text-muted small">Sentimiento Promedio</div>
        <div class="h3 text-white mt-2">${sentimientoPromedio}</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="text-center p-3 rounded" style="background: rgba(23, 162, 184, 0.1);">
        <i class="fa-solid fa-brain text-info fa-2x mb-2"></i>
        <div class="text-muted small">Tópicos Descubiertos</div>
        <div class="h3 text-white mt-2">${topicsCount}</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="text-center p-3 rounded" style="background: rgba(255, 193, 7, 0.1);">
        <i class="fa-solid fa-book text-warning fa-2x mb-2"></i>
        <div class="text-muted small">Palabras Promedio</div>
        <div class="h3 text-white mt-2">${palabrasPromedio}</div>
      </div>
    </div>
  `;

    // Gráfico de sentimiento (preview) - con validación
    if (data.sentimiento && data.sentimiento.exito && data.sentimiento.datos_temporales && data.sentimiento.datos_temporales.length > 0) {
      // 1. Sentimiento / Arco Narrativo
      const arcoContainer = document.getElementById('altair-sentimiento-arco');
      if (data.arco_sentimiento && arcoContainer) {
        console.log('[DEBUG] Renderizando Arco Narrativo con vegaEmbed');
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        const vegaTheme = currentTheme === 'light' ? 'default' : 'dark';

        // Parchear colores del spec para que coincidan con el tema actual
        // Eliminado JSON.parse redundante porque patchVegaTheme ya lo hace internamente
        const patchedSpec = patchVegaTheme(data.arco_sentimiento, currentTheme);

        // Limpiamos el contenedor antes de vegaEmbed para evitar duplicados o basura
        arcoContainer.innerHTML = '';

        vegaEmbed('#altair-sentimiento-arco', patchedSpec, {
          actions: false,
          theme: vegaTheme,
          width: 'container',
          background: 'transparent',
          renderer: 'canvas' // Forzar canvas para evitar problemas de SVG en algunos navegadores
        }).then(result => {
          console.log('[DEBUG] Vega-Embed completado con éxito');
        }).catch(err => {
          console.error('[ERROR] Vega-Embed falló:', err);
          // Fallback a gráfico simple si vegaEmbed falla
          if (data.sentimiento && data.sentimiento.exito) {
            arcoContainer.innerHTML = '<canvas id="chart-sentimiento-preview"></canvas>';
            renderChartSentimientoPreview(data.sentimiento.datos_temporales, data.sentimiento.estadisticas);
          }
        });
      } else if (data.sentimiento && data.sentimiento.exito && arcoContainer) {
        console.log('[DEBUG] Renderizando gráfico de sentimiento (fallback)');
        arcoContainer.innerHTML = '<canvas id="chart-sentimiento-preview"></canvas>';
        renderChartSentimientoPreview(data.sentimiento.datos_temporales, data.sentimiento.estadisticas);
      }
    } else {
      console.warn('[WARN] No hay datos de sentimiento válidos:', data.sentimiento);
      const sContainer = document.getElementById('altair-sentimiento-arco') || document.getElementById('chart-sentimiento-preview')?.parentElement;
      if (sContainer) {
        sContainer.innerHTML = `
          <h5 class="mb-3 text-info"><i class="fa-solid fa-wave-square me-2"></i>Arco Narrativo de Sentimiento</h5>
          <div class="d-flex justify-content-center align-items-center" style="height: 300px;">
            <p class="text-muted">No hay datos de sentimiento disponibles</p>
          </div>
        `;
      }
    }

    // Tópicos (preview) - con validación
    if (data.topics && data.topics.exito && data.topics.topicos && data.topics.topicos.length > 0) {
      console.log('[DEBUG] Renderizando tópicos preview');
      renderTopicsPreview(data.topics.topicos);
    } else {
      console.warn('[WARN] No hay datos de tópicos válidos:', data.topics);
      const tContainer = document.getElementById('topics-preview');
      if (tContainer) {
        tContainer.innerHTML = `
          <div class="text-center text-muted py-4">
            <p>No hay tópicos disponibles</p>
            <small>${data.topics && data.topics.error ? data.topics.error : 'Intenta con más documentos'}</small>
          </div>
        `;
      }
    }

    // N-gramas (preview) - con validación
    if (data.ngramas && data.ngramas.exito && data.ngramas.ngramas && data.ngramas.ngramas.length > 0) {
      console.log('[DEBUG] Renderizando n-gramas preview');
      renderNgramasPreview(data.ngramas.ngramas);
    } else {
      console.warn('[WARN] No hay datos de n-gramas válidos:', data.ngramas);
      const nContainer = document.getElementById('chart-ngramas-preview')?.parentElement;
      if (nContainer) {
        nContainer.innerHTML = `
          <h4 class="mb-3"><i class="fa-solid fa-spell-check me-2"></i>Frases Más Frecuentes (Bigramas)</h4>
          <div class="d-flex justify-content-center align-items-center" style="height: 300px;">
            <p class="text-muted">No hay datos de n-gramas disponibles</p>
          </div>
        `;
      }
    }

    console.log('[DEBUG] Dashboard renderizado completamente');
  } catch (error) {
    console.error('[ERROR] Error en renderDashboard:', error);
    throw error; // Re-lanzar para que lo capture el try-catch superior
  }
}

function renderChartSentimientoPreview(datos, estadisticas) {
  const ctx = document.getElementById('chart-sentimiento-preview');
  if (!ctx) return;

  if (chartsInstances['sentimiento-preview']) {
    chartsInstances['sentimiento-preview'].destroy();
  }

  chartsInstances['sentimiento-preview'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: datos.map(d => d.fecha),
      datasets: [{
        label: 'Sentimiento',
        data: datos.map(d => d.sentimiento),
        borderColor: '#ff9800',
        backgroundColor: 'rgba(255, 152, 0, 0.1)',
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: UI_COLORS.legend() }
        }
      },
      scales: {
        x: {
          ticks: { color: UI_COLORS.text() },
          grid: {
            display: true,
            color: UI_COLORS.grid(0.2)
          }
        },
        y: {
          ticks: { color: UI_COLORS.text() },
          grid: {
            display: true,
            color: UI_COLORS.grid(0.2)
          },
          min: -1,
          max: 1
        }
      }
    },
    plugins: [{
      id: 'previewStats',
      afterDatasetsDraw(chart) {
        if (!estadisticas) return;
        const { ctx, chartArea: { left, right }, scales: { y } } = chart;
        ctx.save();

        if (estadisticas.promedio_sentimiento != null) {
          const yVal = y.getPixelForValue(estadisticas.promedio_sentimiento);
          ctx.strokeStyle = 'rgba(255, 152, 0, 0.7)';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([6, 4]);
          ctx.beginPath();
          ctx.moveTo(left, yVal);
          ctx.lineTo(right, yVal);
          ctx.stroke();

          ctx.setLineDash([]);
          ctx.fillStyle = 'rgba(255, 152, 0, 0.9)';
          ctx.font = '9px Arial';
          ctx.textAlign = 'right';
          ctx.fillText('Media: ' + estadisticas.promedio_sentimiento.toFixed(2), right - 5, yVal - 5);
        }

        if (estadisticas.mediana_sentimiento != null) {
          const yVal = y.getPixelForValue(estadisticas.mediana_sentimiento);
          ctx.strokeStyle = UI_COLORS.isLight() ? 'rgba(0,0,0,0.4)' : 'rgba(255,255,255,0.4)';
          ctx.lineWidth = 1.2;
          ctx.setLineDash([4, 4]);
          ctx.beginPath();
          ctx.moveTo(left, yVal);
          ctx.lineTo(right, yVal);
          ctx.stroke();

          ctx.setLineDash([]);
          ctx.fillStyle = UI_COLORS.isLight() ? 'rgba(0,0,0,0.7)' : 'rgba(255,255,255,0.7)';
          ctx.font = '9px Arial';
          ctx.textAlign = 'left';
          ctx.fillText('Mediana: ' + estadisticas.mediana_sentimiento.toFixed(2), left + 5, yVal + 10);
        }
        ctx.restore();
      }
    }]
  });
}

function renderTopicsPreview(topicos) {
  const container = document.getElementById('topics-preview');
  container.innerHTML = '';

  topicos.slice(0, 4).forEach(topic => {
    const card = document.createElement('div');
    card.className = 'topic-card';
    card.innerHTML = `
      <div class="text-accent fw-bold mb-2">Tópico ${topic.id}</div>
      <div>
        ${topic.palabras.slice(0, 7).map(([palabra, peso]) =>
      `<span class="topic-word">${palabra}</span>`
    ).join('')}
      </div>
    `;
    container.appendChild(card);
  });
}

function renderNgramasPreview(ngramas) {
  const ctx = document.getElementById('chart-ngramas-preview');
  if (!ctx) return;

  if (chartsInstances['ngramas-preview']) {
    chartsInstances['ngramas-preview'].destroy();
  }


  const top10 = ngramas.slice(0, 10);

  chartsInstances['ngramas-preview'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: top10.map(ng => ng.texto),
      datasets: [{
        label: 'Frecuencia',
        data: top10.map(ng => ng.frecuencia),
        backgroundColor: '#ff9800'
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          ticks: { color: UI_COLORS.text() },
          grid: { color: UI_COLORS.grid(0.1) }
        },
        y: {
          ticks: { color: UI_COLORS.text() },
          grid: { display: false }
        }
      }
    }
  });
}

// ============================================
// RENDERIZADO: SENTIMIENTO TEMPORAL
// ============================================

function renderSentimiento(data) {
  console.log('[DEBUG] renderSentimiento llamado con datos:', data);

  // Verificar que la vista esté visible
  const vista = document.getElementById('view-sentimiento');
  if (!vista || vista.style.display === 'none') {
    console.warn('[WARN] Vista de sentimiento no está visible, esperando...');
    setTimeout(() => renderSentimiento(data), 100);
    return;
  }

  // Estadísticas
  if (data.estadisticas) {
    const statAvg = document.getElementById('stat-sentimiento-avg');
    const statSubj = document.getElementById('stat-subjetividad-avg');
    const statCount = document.getElementById('stat-docs-count');

    if (statAvg) statAvg.textContent = data.estadisticas.promedio_sentimiento.toFixed(3);
    if (statSubj) statSubj.textContent = data.estadisticas.promedio_subjetividad.toFixed(3);
    if (statCount) statCount.textContent = data.estadisticas.total_documentos;
  }

  // Gráfico completo
  const ctx = document.getElementById('chart-sentimiento-full');

  if (!ctx) {
    console.error('[ERROR] Elemento chart-sentimiento-full no encontrado en el DOM');
    console.log('[DEBUG] Elementos disponibles:', Array.from(document.querySelectorAll('[id*="chart"]')).map(el => el.id));
    return;
  }

  if (ctx.clientWidth === 0 || ctx.clientHeight === 0) {
    console.warn('[WARN] Canvas sentimiento tiene dimensiones 0, esperando layout...');
    setTimeout(() => renderSentimiento(data), 100);
    return;
  }

  console.log('[DEBUG] Renderizando gráfico de sentimiento en canvas:', ctx);

  if (chartsInstances['sentimiento-full']) {
    chartsInstances['sentimiento-full'].destroy();
  }

  chartsInstances['sentimiento-full'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.datos_temporales.map(d => d.fecha),
      datasets: [
        {
          label: 'Sentimiento',
          data: data.datos_temporales.map(d => d.sentimiento),
          borderColor: '#ff9800',
          backgroundColor: 'rgba(255, 152, 0, 0.2)',
          tension: 0.4,
          fill: true,
          yAxisID: 'y'
        },
        {
          label: 'Subjetividad',
          data: data.datos_temporales.map(d => d.subjetividad),
          borderColor: '#17a2b8',
          backgroundColor: 'rgba(23, 162, 184, 0.2)',
          tension: 0.4,
          fill: true,
          yAxisID: 'y'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          labels: { color: UI_COLORS.legend() }
        },
        tooltip: {
          callbacks: {
            title: (items) => `Periodo: ${items[0].label}`,
            afterLabel: (context) => {
              const idx = context.dataIndex;
              return `Documentos: ${data.datos_temporales[idx].count}`;
            }
          }
        },
        zoom: CHART_ZOOM_CONFIG.zoom,
        pan: CHART_ZOOM_CONFIG.pan
      },
      scales: {
        x: {
          ticks: { color: UI_COLORS.text() },
          grid: { color: UI_COLORS.grid(0.1) }
        },
        y: {
          type: 'linear',
          position: 'left',
          ticks: { color: UI_COLORS.text() },
          grid: { color: UI_COLORS.grid(0.1) },
          min: -1,
          max: 1
        }
      }
    },
    plugins: [{
      afterDatasetsDraw(chart) {
        const { ctx, chartArea: { left, right }, scales: { y } } = chart;
        ctx.save();

        // Línea de Media de Sentimiento
        if (data.estadisticas && data.estadisticas.promedio_sentimiento != null) {
          const yVal = y.getPixelForValue(data.estadisticas.promedio_sentimiento);
          ctx.strokeStyle = 'rgba(255, 152, 0, 0.7)';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([6, 4]);
          ctx.beginPath();
          ctx.moveTo(left, yVal);
          ctx.lineTo(right, yVal);
          ctx.stroke();

          ctx.setLineDash([]);
          ctx.fillStyle = 'rgba(255, 152, 0, 0.9)';
          ctx.font = '10px Arial';
          ctx.textAlign = 'right';
          ctx.fillText('Media: ' + data.estadisticas.promedio_sentimiento.toFixed(3), right - 5, yVal - 5);
        }

        // Línea de Mediana de Sentimiento
        if (data.estadisticas && data.estadisticas.mediana_sentimiento != null) {
          const yVal = y.getPixelForValue(data.estadisticas.mediana_sentimiento);
          ctx.strokeStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)';
          ctx.lineWidth = 1.2;
          ctx.setLineDash([4, 4]);
          ctx.beginPath();
          ctx.moveTo(left, yVal);
          ctx.lineTo(right, yVal);
          ctx.stroke();

          ctx.setLineDash([]);
          ctx.fillStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)';
          ctx.font = 'bold 10px Arial';
          ctx.textAlign = 'left';
          ctx.fillText('Mediana: ' + data.estadisticas.mediana_sentimiento.toFixed(3), left + 5, yVal + 12);
        }

        // Línea de Media de Subjetividad (usa la misma escala 'y' en este gráfico)
        if (data.estadisticas && data.estadisticas.promedio_subjetividad != null) {
          const yVal = chart.scales.y.getPixelForValue(data.estadisticas.promedio_subjetividad);
          ctx.strokeStyle = 'rgba(23, 162, 184, 0.8)';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([6, 4]);
          ctx.beginPath();
          ctx.moveTo(left, yVal);
          ctx.lineTo(right, yVal);
          ctx.stroke();

          // Etiqueta opcional para la línea
          ctx.setLineDash([]);
          ctx.fillStyle = 'rgba(23, 162, 184, 0.9)';
          ctx.font = '10px Arial';
          ctx.textAlign = 'right';
          ctx.fillText('Media: ' + data.estadisticas.promedio_subjetividad.toFixed(3), right - 5, yVal - 5);
        }

        // Línea de Mediana de Subjetividad
        if (data.estadisticas && data.estadisticas.mediana_subjetividad != null) {
          const yVal = chart.scales.y.getPixelForValue(data.estadisticas.mediana_subjetividad);
          ctx.strokeStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)';
          ctx.lineWidth = 1.2;
          ctx.setLineDash([4, 4]);
          ctx.beginPath();
          ctx.moveTo(left, yVal);
          ctx.lineTo(right, yVal);
          ctx.stroke();

          ctx.setLineDash([]);
          ctx.fillStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)';
          ctx.font = 'bold 10px Arial';
          ctx.textAlign = 'left';
          ctx.fillText('Mediana: ' + data.estadisticas.mediana_subjetividad.toFixed(3), left + 5, yVal + 12);
        }

        ctx.restore();
      }
    }]
  });
  resetZoomOnDoubleClick(chartsInstances['sentimiento-full']);
}

// ============================================
// RENDERIZADO: RETÓRICA
// ============================================

function renderRetorica(data) {
  console.log('[DEBUG] renderRetorica llamado con datos:', data);

  // Verificar que la vista esté visible
  const vista = document.getElementById('view-retorica');
  if (!vista || vista.style.display === 'none') {
    console.warn('[WARN] Vista de retórica no está visible, esperando...');
    setTimeout(() => renderRetorica(data), 100);
    return;
  }

  // Estadísticas
  if (data.estadisticas) {
    const statIronia = document.getElementById('stat-ironia-avg');
    const statMetafora = document.getElementById('stat-metafora-avg');
    const statEmocional = document.getElementById('stat-emocional-avg');

    if (statIronia) statIronia.textContent = data.estadisticas.promedio_ironia.toFixed(2);
    if (statMetafora) statMetafora.textContent = data.estadisticas.promedio_metafora_belica.toFixed(2);
    if (statEmocional) statEmocional.textContent = data.estadisticas.promedio_lenguaje_emocional.toFixed(2);
  }

  // Gráfico 1: Ironía Temporal
  const ctxIronia = document.getElementById('chart-ironia-temporal');
  if (ctxIronia) {
    // Verificar dimensiones del canvas antes de renderizar
    if (ctxIronia.clientWidth === 0 || ctxIronia.clientHeight === 0) {
      console.warn('[WARN] Canvas ironia tiene dimensiones 0, esperando layout...');
      setTimeout(() => renderRetorica(data), 100);
      return;
    }

    if (chartsInstances['ironia-temporal']) {
      chartsInstances['ironia-temporal'].destroy();
    }

    chartsInstances['ironia-temporal'] = new Chart(ctxIronia, {
      type: 'line',
      data: {
        labels: data.datos_temporales.map(d => d.fecha),
        datasets: [{
          label: 'Ironía',
          data: data.datos_temporales.map(d => d.ironia),
          borderColor: '#ff9800',
          backgroundColor: 'rgba(255, 152, 0, 0.2)',
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: UI_COLORS.legend() } },
          tooltip: {
            callbacks: {
              title: (items) => `Periodo: ${items[0].label}`,
              afterLabel: (context) => {
                const idx = context.dataIndex;
                return `Documentos: ${data.datos_temporales[idx].count}`;
              }
            }
          },
          zoom: CHART_ZOOM_CONFIG.zoom,
          pan: CHART_ZOOM_CONFIG.pan
        },
        scales: {
          x: {
            ticks: { color: UI_COLORS.text() },
            grid: { color: UI_COLORS.grid(0.1) }
          },
          y: {
            ticks: { color: UI_COLORS.text() },
            grid: { color: UI_COLORS.grid(0.1) },
            beginAtZero: true
          }
        }
      },
      plugins: [{
        id: 'averageLines',
        afterDatasetsDraw(chart) {
          const { ctx, chartArea: { left, right }, scales: { y } } = chart;
          ctx.save();

          // Línea de Media de Ironía
          if (data.estadisticas && data.estadisticas.promedio_ironia != null) {
            const yVal = y.getPixelForValue(data.estadisticas.promedio_ironia);
            ctx.strokeStyle = 'rgba(255, 152, 0, 0.7)';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([6, 4]);
            ctx.beginPath();
            ctx.moveTo(left, yVal);
            ctx.lineTo(right, yVal);
            ctx.stroke();

            ctx.setLineDash([]);
            ctx.fillStyle = 'rgba(255, 152, 0, 0.9)';
            ctx.font = '10px Arial';
            ctx.textAlign = 'right';
            ctx.fillText('Media: ' + data.estadisticas.promedio_ironia.toFixed(2), right - 5, yVal - 5);
          }

          // Línea de Mediana de Ironía
          if (data.estadisticas && data.estadisticas.mediana_ironia != null) {
            const yVal = y.getPixelForValue(data.estadisticas.mediana_ironia);
            ctx.strokeStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)';
            ctx.lineWidth = 1.2;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(left, yVal);
            ctx.lineTo(right, yVal);
            ctx.stroke();

            ctx.setLineDash([]);
            ctx.fillStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)';
            ctx.font = 'bold 10px Arial';
            ctx.textAlign = 'left';
            ctx.fillText('Mediana: ' + data.estadisticas.mediana_ironia.toFixed(2), left + 5, yVal + 12);
          }

          ctx.restore();
        }
      }]
    });
  }

  // Gráfico 2: Metáforas Bélicas
  const ctxMetaforas = document.getElementById('chart-metaforas-belicas');
  if (ctxMetaforas) {
    if (ctxMetaforas.clientHeight === 0) return; // Skip if hidden
    if (chartsInstances['metaforas-belicas']) {
      chartsInstances['metaforas-belicas'].destroy();
    }

    chartsInstances['metaforas-belicas'] = new Chart(ctxMetaforas, {
      type: 'line',
      data: {
        labels: data.datos_temporales.map(d => d.fecha),
        datasets: [{
          label: 'Metáforas Bélicas',
          data: data.datos_temporales.map(d => d.metafora_belica),
          borderColor: '#dc3545',
          backgroundColor: 'rgba(220, 53, 69, 0.2)',
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: UI_COLORS.legend() } },
          tooltip: {
            callbacks: {
              title: (items) => `Periodo: ${items[0].label}`,
              afterLabel: (context) => {
                const idx = context.dataIndex;
                return `Documentos: ${data.datos_temporales[idx].count}`;
              }
            }
          },
          zoom: CHART_ZOOM_CONFIG.zoom,
          pan: CHART_ZOOM_CONFIG.pan
        },
        scales: {
          x: {
            ticks: { color: UI_COLORS.text() },
            grid: { color: UI_COLORS.grid(0.1) }
          },
          y: {
            ticks: { color: UI_COLORS.text() },
            grid: { color: UI_COLORS.grid(0.1) },
            beginAtZero: true
          }
        }
      },
      plugins: [{
        id: 'averageLines',
        afterDatasetsDraw(chart) {
          const { ctx, chartArea: { left, right }, scales: { y } } = chart;
          ctx.save();

          // Línea de Media de Metáforas Bélicas
          if (data.estadisticas && data.estadisticas.promedio_metafora_belica != null) {
            const yVal = y.getPixelForValue(data.estadisticas.promedio_metafora_belica);
            ctx.strokeStyle = 'rgba(220, 53, 69, 0.7)';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([6, 4]);
            ctx.beginPath();
            ctx.moveTo(left, yVal);
            ctx.lineTo(right, yVal);
            ctx.stroke();

            ctx.setLineDash([]);
            ctx.fillStyle = 'rgba(220, 53, 69, 0.9)';
            ctx.font = '10px Arial';
            ctx.textAlign = 'right';
            ctx.fillText('Media: ' + data.estadisticas.promedio_metafora_belica.toFixed(2), right - 5, yVal - 5);
          }

          // Línea de Mediana de Metáforas Bélicas
          if (data.estadisticas && data.estadisticas.mediana_metafora_belica != null) {
            const yVal = y.getPixelForValue(data.estadisticas.mediana_metafora_belica);
            ctx.strokeStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)';
            ctx.lineWidth = 1.2;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(left, yVal);
            ctx.lineTo(right, yVal);
            ctx.stroke();

            ctx.setLineDash([]);
            ctx.fillStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)';
            ctx.font = 'bold 10px Arial';
            ctx.textAlign = 'left';
            ctx.fillText('Mediana: ' + data.estadisticas.mediana_metafora_belica.toFixed(2), left + 5, yVal + 12);
          }

          ctx.restore();
        }
      }]
    });
  }

  // Gráfico 3: Lenguaje Emocional
  const ctxEmocional = document.getElementById('chart-lenguaje-emocional');
  if (ctxEmocional) {
    if (ctxEmocional.clientHeight === 0) return; // Skip if hidden
    if (chartsInstances['lenguaje-emocional']) {
      chartsInstances['lenguaje-emocional'].destroy();
    }

    chartsInstances['lenguaje-emocional'] = new Chart(ctxEmocional, {
      type: 'line',
      data: {
        labels: data.datos_temporales.map(d => d.fecha),
        datasets: [{
          label: 'Intensidad Emocional',
          data: data.datos_temporales.map(d => d.lenguaje_emocional),
          borderColor: '#ffc107',
          backgroundColor: 'rgba(255, 193, 7, 0.2)',
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: UI_COLORS.legend() } },
          tooltip: {
            callbacks: {
              title: (items) => `Periodo: ${items[0].label}`,
              afterLabel: (context) => {
                const idx = context.dataIndex;
                return `Documentos: ${data.datos_temporales[idx].count}`;
              }
            }
          },
          zoom: CHART_ZOOM_CONFIG.zoom,
          pan: CHART_ZOOM_CONFIG.pan
        },
        scales: {
          x: {
            ticks: { color: UI_COLORS.text() },
            grid: { color: UI_COLORS.grid(0.1) }
          },
          y: {
            ticks: { color: UI_COLORS.text() },
            grid: { color: UI_COLORS.grid(0.1) },
            beginAtZero: true
          }
        }
      },
      plugins: [{
        id: 'averageLines',
        afterDatasetsDraw(chart) {
          const { ctx, chartArea: { left, right }, scales: { y } } = chart;
          ctx.save();

          // Línea de Media de Lenguaje Emocional
          if (data.estadisticas && data.estadisticas.promedio_lenguaje_emocional != null) {
            const yVal = y.getPixelForValue(data.estadisticas.promedio_lenguaje_emocional);
            ctx.strokeStyle = 'rgba(255, 193, 7, 0.7)';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([6, 4]);
            ctx.beginPath();
            ctx.moveTo(left, yVal);
            ctx.lineTo(right, yVal);
            ctx.stroke();

            ctx.setLineDash([]);
            ctx.fillStyle = 'rgba(255, 193, 7, 0.9)';
            ctx.font = '10px Arial';
            ctx.textAlign = 'right';
            ctx.fillText('Media: ' + data.estadisticas.promedio_lenguaje_emocional.toFixed(2), right - 5, yVal - 5);
          }

          // Línea de Mediana
          if (data.estadisticas && data.estadisticas.mediana_lenguaje_emocional != null) {
            const yVal = y.getPixelForValue(data.estadisticas.mediana_lenguaje_emocional);
            ctx.strokeStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)';
            ctx.lineWidth = 1.2;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(left, yVal);
            ctx.lineTo(right, yVal);
            ctx.stroke();

            ctx.setLineDash([]);
            ctx.fillStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)';
            ctx.font = 'bold 10px Arial';
            ctx.textAlign = 'left';
            ctx.fillText('Mediana: ' + data.estadisticas.mediana_lenguaje_emocional.toFixed(2), left + 5, yVal + 12);
          }

          ctx.restore();
        }
      }]
    });
    resetZoomOnDoubleClick(chartsInstances['ironia-temporal']);
    resetZoomOnDoubleClick(chartsInstances['metaforas-belicas']);
    resetZoomOnDoubleClick(chartsInstances['lenguaje-emocional']);
  }
}

// ============================================
// RENDERIZADO: PERIODÍSTICO
// ============================================

function renderPeriodistico(data) {
  console.log('[DEBUG] renderPeriodistico llamado con datos:', data);

  // Verificar que la vista esté visible
  const vista = document.getElementById('view-periodistico');
  if (!vista || vista.style.display === 'none') {
    console.warn('[WARN] Vista de periodístico no está visible, esperando...');
    setTimeout(() => renderPeriodistico(data), 100);
    return;
  }

  // Estadísticas
  if (data.estadisticas) {
    const statModalidad = document.getElementById('stat-modalidad-avg');
    const statPolarizacion = document.getElementById('stat-polarizacion-avg');
    const statSensacionalismo = document.getElementById('stat-sensacionalismo-avg');
    const statAgencia = document.getElementById('stat-agencia-avg');
    const statPropaganda = document.getElementById('stat-propaganda-avg');

    if (statModalidad) statModalidad.textContent = data.estadisticas.promedio_modalidad.toFixed(2);
    if (statPolarizacion) statPolarizacion.textContent = data.estadisticas.promedio_polarizacion.toFixed(2);
    if (statSensacionalismo) statSensacionalismo.textContent = data.estadisticas.promedio_sensacionalismo.toFixed(2);
    if (statAgencia) statAgencia.textContent = data.estadisticas.promedio_agencia.toFixed(2);
    if (statPropaganda) statPropaganda.textContent = data.estadisticas.promedio_propaganda.toFixed(2);
  }

  const chartOptions = (title, color, avgValue, avgColor) => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: UI_COLORS.legend() } },
      tooltip: {
        callbacks: {
          title: (items) => `Periodo: ${items[0].label}`,
          afterLabel: (context) => {
            const idx = context.dataIndex;
            return `Documentos: ${data.datos_temporales[idx].count}`;
          }
        }
      },
      zoom: CHART_ZOOM_CONFIG.zoom,
      pan: CHART_ZOOM_CONFIG.pan
    },
    scales: {
      x: {
        ticks: { color: UI_COLORS.text() },
        grid: { color: UI_COLORS.grid(0.1) }
      },
      y: {
        ticks: { color: UI_COLORS.text() },
        grid: { color: UI_COLORS.grid(0.1) },
        beginAtZero: true
      }
    }
  });

  const createAverageLinePlugin = (avgValue, medianValue, avgColor, medianColor) => ({
    id: 'averageLines',
    afterDatasetsDraw(chart) {
      const { ctx, chartArea: { left, right }, scales: { y } } = chart;
      ctx.save();

      if (avgValue != null) {
        const yVal = y.getPixelForValue(avgValue);
        ctx.strokeStyle = avgColor || 'rgba(255, 152, 0, 0.7)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(left, yVal);
        ctx.lineTo(right, yVal);
        ctx.stroke();

        ctx.setLineDash([]);
        ctx.fillStyle = avgColor || 'rgba(255, 152, 0, 0.9)';
        ctx.font = '10px Arial';
        ctx.textAlign = 'right';
        ctx.fillText('Media: ' + avgValue.toFixed(2), right - 5, yVal - 5);
      }

      if (medianValue != null) {
        const yVal = y.getPixelForValue(medianValue);
        ctx.strokeStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)';
        ctx.lineWidth = 1.2;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(left, yVal);
        ctx.lineTo(right, yVal);
        ctx.stroke();

        ctx.setLineDash([]);
        ctx.fillStyle = UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)';
        ctx.font = 'bold 10px Arial';
        ctx.textAlign = 'left';
        // Aumentamos precisión para depurar si el valor es realmente 0 o muy pequeño
        ctx.fillText('Mediana: ' + medianValue.toFixed(4), left + 5, yVal + 12);
      }

      ctx.restore();
    }
  });

  // Gráfico 1: Modalidad
  const ctxModalidad = document.getElementById('chart-modalidad');
  if (ctxModalidad) {
    // Verificar dimensiones antes de renderizar (evita error "can't acquire context")
    if (ctxModalidad.clientWidth === 0 || ctxModalidad.clientHeight === 0) {
      console.warn('[WARN] Canvas modalidad tiene dimensiones 0, esperando layout...');
      setTimeout(() => renderPeriodistico(data), 100);
      return;
    }

    if (chartsInstances['modalidad']) {
      chartsInstances['modalidad'].destroy();
    }
    chartsInstances['modalidad'] = new Chart(ctxModalidad, {
      type: 'line',
      data: {
        labels: data.datos_temporales.map(d => d.fecha),
        datasets: [{
          label: 'Modalidad',
          data: data.datos_temporales.map(d => d.modalidad),
          borderColor: '#3498db',
          backgroundColor: 'rgba(52, 152, 219, 0.2)',
          tension: 0.4,
          fill: true
        }]
      },
      options: chartOptions('Modalidad', '#3498db'),
      plugins: [createAverageLinePlugin(
        data.estadisticas.promedio_modalidad,
        data.estadisticas.mediana_modalidad,
        'rgba(52, 152, 219, 0.7)',
        UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)'
      )]
    });
    resetZoomOnDoubleClick(chartsInstances['modalidad']);
  }

  // Gráfico 2: Polarización
  const ctxPolarizacion = document.getElementById('chart-polarizacion');
  if (ctxPolarizacion) {
    if (chartsInstances['polarizacion']) chartsInstances['polarizacion'].destroy();
    chartsInstances['polarizacion'] = new Chart(ctxPolarizacion, {
      type: 'line',
      data: {
        labels: data.datos_temporales.map(d => d.fecha),
        datasets: [{
          label: 'Polarización',
          data: data.datos_temporales.map(d => d.polarizacion),
          borderColor: '#e74c3c',
          backgroundColor: 'rgba(231, 76, 60, 0.2)',
          tension: 0.4,
          fill: true
        }]
      },
      options: chartOptions('Polarización', '#e74c3c'),
      plugins: [createAverageLinePlugin(
        data.estadisticas.promedio_polarizacion,
        data.estadisticas.mediana_polarizacion,
        'rgba(231, 76, 60, 0.7)',
        UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)'
      )]
    });
    resetZoomOnDoubleClick(chartsInstances['polarizacion']);
  }

  // Gráfico 3: Sensacionalismo
  const ctxSensacionalismo = document.getElementById('chart-sensacionalismo');
  if (ctxSensacionalismo) {
    if (chartsInstances['sensacionalismo']) chartsInstances['sensacionalismo'].destroy();
    chartsInstances['sensacionalismo'] = new Chart(ctxSensacionalismo, {
      type: 'line',
      data: {
        labels: data.datos_temporales.map(d => d.fecha),
        datasets: [{
          label: 'Sensacionalismo',
          data: data.datos_temporales.map(d => d.sensacionalismo),
          borderColor: '#f1c40f',
          backgroundColor: 'rgba(241, 196, 15, 0.2)',
          tension: 0.4,
          fill: true
        }]
      },
      options: chartOptions('Sensacionalismo', '#f1c40f'),
      plugins: [createAverageLinePlugin(
        data.estadisticas.promedio_sensacionalismo,
        data.estadisticas.mediana_sensacionalismo,
        'rgba(241, 196, 15, 0.7)',
        UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)'
      )]
    });
    resetZoomOnDoubleClick(chartsInstances['sensacionalismo']);
  }

  // Gráfico 4: Voz y Agencia
  const ctxAgencia = document.getElementById('chart-agencia');
  if (ctxAgencia) {
    if (chartsInstances['agencia']) chartsInstances['agencia'].destroy();
    chartsInstances['agencia'] = new Chart(ctxAgencia, {
      type: 'line',
      data: {
        labels: data.datos_temporales.map(d => d.fecha),
        datasets: [{
          label: 'Voz y Agencia',
          data: data.datos_temporales.map(d => d.agencia),
          borderColor: '#9b59b6',
          backgroundColor: 'rgba(155, 89, 182, 0.2)',
          tension: 0.4,
          fill: true
        }]
      },
      options: chartOptions('Voz y Agencia', '#9b59b6'),
      plugins: [createAverageLinePlugin(
        data.estadisticas.promedio_agencia,
        data.estadisticas.mediana_agencia,
        'rgba(155, 89, 182, 0.7)',
        UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)'
      )]
    });
    resetZoomOnDoubleClick(chartsInstances['agencia']);
  }

  // Gráfico 5: Propaganda
  const ctxPropaganda = document.getElementById('chart-propaganda');
  if (ctxPropaganda) {
    if (chartsInstances['propaganda']) chartsInstances['propaganda'].destroy();
    chartsInstances['propaganda'] = new Chart(ctxPropaganda, {
      type: 'line',
      data: {
        labels: data.datos_temporales.map(d => d.fecha),
        datasets: [{
          label: 'Propaganda',
          data: data.datos_temporales.map(d => d.propaganda),
          borderColor: '#1abc9c',
          backgroundColor: 'rgba(26, 188, 156, 0.2)',
          tension: 0.4,
          fill: true
        }]
      },
      options: chartOptions('Propaganda', '#1abc9c'),
      plugins: [createAverageLinePlugin(
        data.estadisticas.promedio_propaganda,
        data.estadisticas.mediana_propaganda,
        'rgba(26, 188, 156, 0.7)',
        UI_COLORS.isLight() ? 'rgba(0, 0, 0, 0.4)' : 'rgba(255, 255, 255, 0.4)'
      )]
    });
    resetZoomOnDoubleClick(chartsInstances['propaganda']);
  }
}
// ============================================
// RENDERIZADO: TOPICS
// ============================================

function renderTopics(data) {
  // Lista de tópicos
  const container = document.getElementById('topics-list');
  container.innerHTML = '';

  data.topicos.forEach(topic => {
    const card = document.createElement('div');
    card.className = 'topic-card mb-3';
    card.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-2">
        <div class="text-accent fw-bold fs-5">Tópico ${topic.id}</div>
        <div class="text-muted small">${topic.palabras.length} palabras</div>
      </div>
      <div class="mb-2">
        ${topic.palabras.map(([palabra, peso]) =>
      `<span class="topic-word">${palabra}</span>`
    ).join('')}
      </div>
      <div class="text-muted small mt-2">
        ${data.documentos.filter(d => d.topico === topic.id).length} documentos asignados
      </div>
    `;
    container.appendChild(card);
  });

  // Gráfico de distribución
  const ctx = document.getElementById('chart-topics-distribution');

  if (chartsInstances['topics-dist']) {
    chartsInstances['topics-dist'].destroy();
  }

  const distribucion = data.topicos.map(t => {
    return data.documentos.filter(d => d.topico === t.id).length;
  });

  chartsInstances['topics-dist'] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.topicos.map(t => `Tópico ${t.id}`),
      datasets: [{
        data: distribucion,
        backgroundColor: [
          '#ff9800',  // Naranja brillante
          '#4d4d4d',  // Gris medio
          '#ff6f00',  // Naranja intenso
          '#6b6b6b',  // Gris claro
          '#e65100',  // Naranja oscuro
          '#3a3a3a',  // Gris oscuro
          '#ffab40',  // Naranja claro
          '#5a5a5a',  // Gris medio-claro
          '#bf360c',  // Naranja profundo
          '#2d2d2d'   // Gris carbón
        ],
        borderWidth: 2,
        borderColor: '#0f0f0f'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: UI_COLORS.legend(),
            font: { size: 12, weight: '500' },
            padding: 12,
            usePointStyle: true,
            pointStyle: 'circle'
          }
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          titleColor: '#ff9800',
          bodyColor: '#fff',
          borderColor: '#ff9800',
          borderWidth: 1,
          padding: 12,
          displayColors: true
        }
      }
    }
  });
}

// ============================================
// RENDERIZADO: RED DE ENTIDADES
// ============================================

function renderEntidades(data) {
  const container = document.getElementById('network-entidades');

  const nodes = new vis.DataSet(data.nodos.map(n => ({
    id: n.id,
    label: n.name,
    shape: 'dot',
    size: 20,
    color: {
      background: '#ff6600',
      border: '#cc5200',
      highlight: { background: '#ff8800', border: '#ff6600' }
    },
    font: { color: UI_COLORS.text(), size: 13, face: 'Arial', bold: { color: '#ff9800' } }
  })));

  const edges = new vis.DataSet(data.enlaces.map(e => ({
    from: e.source,
    to: e.target,
    value: e.value,
    width: 1.5,
    color: { color: 'rgba(255, 255, 255, 0.2)', highlight: '#ff6600' },
    smooth: { type: 'continuous' }
  })));

  const network = new vis.Network(container, { nodes, edges }, {
    physics: {
      stabilization: { iterations: 150 },
      barnesHut: { gravitationalConstant: -8000, springLength: 150 }
    },
    interaction: { hover: true },
    nodes: {
      font: { color: UI_COLORS.text() }
    }
  });
}

// ============================================
// RENDERIZADO: ESTILOMETRÍA
// ============================================

function renderEstilo(data) {
  // Palabras por oración
  const ctx1 = document.getElementById('chart-palabras-oracion');

  if (chartsInstances['palabras-oracion']) {
    chartsInstances['palabras-oracion'].destroy();
  }

  chartsInstances['palabras-oracion'] = new Chart(ctx1, {
    type: 'bar',
    data: {
      labels: data.documentos.slice(0, 15).map(d => d.titulo.substring(0, 30) + '...'),
      datasets: [{
        label: 'Palabras/Oración',
        data: data.documentos.slice(0, 15).map(d => d.palabras_por_oracion),
        backgroundColor: '#ff6600',
        borderWidth: 1,
        borderColor: '#cc5200'
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: UI_COLORS.text(),
            usePointStyle: true,
            pointStyle: 'circle',
            font: { size: 12, weight: '500' }
          }
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          titleColor: '#ff9800',
          bodyColor: '#fff',
          borderColor: '#ff9800',
          borderWidth: 1
        }
      },
      scales: {
        x: { ticks: { color: UI_COLORS.text() }, grid: { color: UI_COLORS.grid(0.1) } },
        y: { ticks: { color: UI_COLORS.text() }, grid: { display: false } }
      }
    }
  });

  // Diversidad léxica
  const ctx2 = document.getElementById('chart-diversidad-lexica');

  if (chartsInstances['diversidad-lexica']) {
    chartsInstances['diversidad-lexica'].destroy();
  }

  chartsInstances['diversidad-lexica'] = new Chart(ctx2, {
    type: 'scatter',
    data: {
      datasets: [{
        label: 'Documentos',
        data: data.documentos.map(d => ({
          x: d.total_palabras,
          y: d.diversidad_lexica
        })),
        backgroundColor: '#0099cc',
        borderColor: '#0077aa',
        borderWidth: 1,
        pointRadius: 4,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: UI_COLORS.text(),
            usePointStyle: true,
            pointStyle: 'circle',
            font: { size: 12, weight: '500' }
          }
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          titleColor: '#ff9800',
          bodyColor: '#fff',
          borderColor: '#ff9800',
          borderWidth: 1,
          callbacks: {
            label: (context) => {
              const doc = data.documentos[context.dataIndex];
              return [
                `Palabras: ${doc.total_palabras}`,
                `Diversidad: ${doc.diversidad_lexica.toFixed(3)}`,
                `Título: ${doc.titulo.substring(0, 40)}...`
              ];
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: 'Total de Palabras', color: UI_COLORS.text() },
          ticks: { color: UI_COLORS.text() },
          grid: { color: UI_COLORS.grid(0.1) }
        },
        y: {
          title: { display: true, text: 'Diversidad Léxica (TTR)', color: UI_COLORS.text() },
          ticks: { color: UI_COLORS.text() },
          grid: { color: UI_COLORS.grid(0.1) }
        }
      }
    }
  });

  // Comparación entre publicaciones
  const ctx3 = document.getElementById('chart-estilo-comparativo');

  if (chartsInstances['estilo-comparativo']) {
    chartsInstances['estilo-comparativo'].destroy();
  }

  // Agrupar métricas por publicación
  const publicacionesMap = {};
  data.documentos.forEach(doc => {
    const pub = doc.publicacion || 'Sin publicación';
    if (!publicacionesMap[pub]) {
      publicacionesMap[pub] = {
        palabras_por_oracion: [],
        diversidad_lexica: [],
        total_palabras: []
      };
    }
    publicacionesMap[pub].palabras_por_oracion.push(doc.palabras_por_oracion);
    publicacionesMap[pub].diversidad_lexica.push(doc.diversidad_lexica);
    publicacionesMap[pub].total_palabras.push(doc.total_palabras);
  });

  // Calcular promedios por publicación
  const publicaciones = Object.keys(publicacionesMap).slice(0, 10); // Top 10 publicaciones
  const avgPalabrasOracion = publicaciones.map(pub => {
    const valores = publicacionesMap[pub].palabras_por_oracion;
    return valores.reduce((a, b) => a + b, 0) / valores.length;
  });
  const avgDiversidad = publicaciones.map(pub => {
    const valores = publicacionesMap[pub].diversidad_lexica;
    return valores.reduce((a, b) => a + b, 0) / valores.length;
  });
  const avgPalabras = publicaciones.map(pub => {
    const valores = publicacionesMap[pub].total_palabras;
    return valores.reduce((a, b) => a + b, 0) / valores.length;
  });

  chartsInstances['estilo-comparativo'] = new Chart(ctx3, {
    type: 'bar',
    data: {
      labels: publicaciones.map(p => p.substring(0, 25)),
      datasets: [
        {
          label: 'Palabras/Oración',
          data: avgPalabrasOracion,
          backgroundColor: '#ff6600',
          borderWidth: 1,
          borderColor: '#cc5200',
          yAxisID: 'y'
        },
        {
          label: 'Diversidad Léxica',
          data: avgDiversidad,
          backgroundColor: '#0099cc',
          borderWidth: 1,
          borderColor: '#0077aa',
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          labels: {
            color: UI_COLORS.text(),
            usePointStyle: true,
            pointStyle: 'circle',
            font: { size: 12, weight: '500' }
          },
          position: 'top'
        },
        title: {
          display: true,
          text: 'Comparación de Estilo entre Publicaciones',
          color: '#ff9800',
          font: { size: 14 }
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          titleColor: '#ff9800',
          bodyColor: '#fff',
          borderColor: '#ff9800',
          borderWidth: 1
        }
      },
      scales: {
        x: {
          ticks: { color: UI_COLORS.text() },
          grid: { display: false }
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          title: { display: true, text: 'Palabras/Oración', color: '#ff6600' },
          ticks: { color: '#ff6600' },
          grid: { color: 'rgba(255,102,0,0.1)' }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          title: { display: true, text: 'Diversidad Léxica', color: '#0099cc' },
          ticks: { color: '#0099cc' },
          grid: { drawOnChartArea: false }
        }
      }
    }
  });
}

// ============================================
// RENDERIZADO: N-GRAMAS
// ============================================

function renderNgramas(data) {
  const ctx = document.getElementById('chart-ngramas-full');

  if (chartsInstances['ngramas-full']) {
    chartsInstances['ngramas-full'].destroy();
  }

  chartsInstances['ngramas-full'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.ngramas.map(ng => ng.texto),
      datasets: [{
        label: 'Frecuencia',
        data: data.ngramas.map(ng => ng.frecuencia),
        backgroundColor: '#ff6600',
        borderWidth: 1,
        borderColor: '#cc5200'
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        title: {
          display: true,
          text: `Top ${data.ngramas.length} ${data.n}-gramas más frecuentes`,
          color: UI_COLORS.text(),
          font: { size: 14, weight: '500' }
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          titleColor: '#ff9800',
          bodyColor: '#fff',
          borderColor: '#ff9800',
          borderWidth: 1
        }
      },
      scales: {
        x: { ticks: { color: UI_COLORS.text() }, grid: { color: UI_COLORS.grid(0.1) } },
        y: { ticks: { color: UI_COLORS.text(), font: { size: 11 } }, grid: { display: false } }
      }
    }
  });
}

// ============================================
// RENDERIZADO: CLUSTERING
// ============================================

function renderClustering(data) {
  // Scatter plot t-SNE
  const ctx = document.getElementById('chart-clustering-scatter');

  if (chartsInstances['clustering-scatter']) {
    chartsInstances['clustering-scatter'].destroy();
  }

  // Agrupar por cluster
  const clusters = {};
  data.documentos.forEach(doc => {
    if (!clusters[doc.cluster]) {
      clusters[doc.cluster] = [];
    }
    clusters[doc.cluster].push(doc);
  });

  // Colores con gama naranja a gris carbón
  const colores = [
    '#ff9800',  // Naranja brillante
    '#4d4d4d',  // Gris medio
    '#ff6f00',  // Naranja intenso
    '#6b6b6b',  // Gris claro
    '#e65100',  // Naranja oscuro
    '#3a3a3a',  // Gris oscuro
    '#ffab40',  // Naranja claro
    '#5a5a5a',  // Gris medio-claro
    '#bf360c',  // Naranja profundo
    '#2d2d2d'   // Gris carbón
  ];

  const datasets = Object.keys(clusters).map(clusterId => ({
    label: `Cluster ${parseInt(clusterId) + 1}`,
    data: clusters[clusterId].map(d => ({ x: d.x, y: d.y, titulo: d.titulo })),
    backgroundColor: colores[parseInt(clusterId) % colores.length],
    pointRadius: 4,          // Círculos más pequeños (antes era 6)
    pointHoverRadius: 7      // Hover también más pequeño (antes era 8)
  }));

  chartsInstances['clustering-scatter'] = new Chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: UI_COLORS.text() } },
        tooltip: {
          callbacks: {
            label: (context) => {
              const doc = context.raw;
              return `${doc.titulo.substring(0, 50)}...`;
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: 't-SNE Dim 1', color: UI_COLORS.text() },
          ticks: { color: UI_COLORS.text() },
          grid: { color: UI_COLORS.grid(0.1) }
        },
        y: {
          title: { display: true, text: 't-SNE Dim 2', color: UI_COLORS.text() },
          ticks: { color: UI_COLORS.text() },
          grid: { color: UI_COLORS.grid(0.1) }
        }
      }
    }
  });

  // Keywords por cluster
  const container = document.getElementById('cluster-keywords');
  container.innerHTML = '';

  Object.keys(data.cluster_keywords).forEach(clusterId => {
    const card = document.createElement('div');
    card.className = 'cluster-card';
    card.innerHTML = `
      <div class="fw-bold mb-2" style="color: ${colores[parseInt(clusterId) % colores.length]}">
        Cluster ${parseInt(clusterId) + 1}
      </div>
      <div>
        ${data.cluster_keywords[clusterId].map(palabra =>
      `<span class="topic-word">${palabra}</span>`
    ).join('')}
      </div>
      <div class="text-muted small mt-2">
        ${clusters[clusterId].length} documentos
      </div>
    `;
    container.appendChild(card);
  });
}

// ============================================
// UTILIDADES
// ============================================

function aplicarFiltros() {
  filtros.tema = document.getElementById('filtro-tema').value || null;
  filtros.publicacion_id = document.getElementById('filtro-publicacion').value || null;
  filtros.pais = document.getElementById('filtro-pais').value || null;
  filtros.fecha_desde = document.getElementById('filtro-fecha-desde').value || null;
  filtros.fecha_hasta = document.getElementById('filtro-fecha-hasta').value || null;

  // Capturar opción de eje X
  const ejeXOption = document.querySelector('input[name="eje_x"]:checked');
  filtros.eje_x = ejeXOption ? ejeXOption.value : 'fecha';

  // Capturar documentos seleccionados si estamos en modo secuencia
  if (filtros.eje_x === 'secuencia') {
    const selectDocs = document.getElementById('filtro-documentos');
    filtros.documentos_ids = Array.from(selectDocs.selectedOptions).map(opt => parseInt(opt.value));
  } else {
    filtros.documentos_ids = [];
  }

  filtros.limite = parseInt(document.getElementById('filtro-limite').value) || 0;
  filtros.conceptos = document.getElementById('filtro-conceptos')?.value || null;

  console.log('[DEBUG] Filtros aplicados:', filtros);

  // Recargar vista actual
  datosActuales = {};  // Limpiar caché local

  // Si estamos en una vista específica, recargar esa vista. Si no, recargar dashboard.
  const tipo = getVistaActiva();

  if (tipo === 'dashboard') {
    cargarDashboard();
  } else if (tipo === 'ngramas') {
    const btnActivo = document.querySelector('#view-ngramas .btn-group [data-n].active');
    const n = btnActivo ? parseInt(btnActivo.dataset.n) : 2;
    cargarNgramas(n);
  } else if (tipo === 'clustering') {
    cargarClustering();
  } else {
    cargarAnalisis(tipo);
  }
}

/**
 * Helper para recolectar los filtros actuales desde los inputs de la UI
 * Útil para recargar análisis sin pasar por el flujo de 'aplicarFiltros' global
 */
function getFiltrosActuales() {
    const f = { ...filtros }; // Copia de los filtros globales
    
    // Capturar valores actuales (por si el usuario cambió selectores pero no dio a Aplicar)
    const pubEl = document.getElementById('filtro-publicacion');
    if (pubEl) f.publicacion_id = pubEl.value ? parseInt(pubEl.value) : null;
    
    const temaEl = document.getElementById('filtro-tema');
    if (temaEl) f.tema = temaEl.value || null;
    
    const fDesde = document.getElementById('filtro-fecha-desde');
    if (fDesde) f.fecha_desde = fDesde.value || null;
    
    const fHasta = document.getElementById('filtro-fecha-hasta');
    if (fHasta) f.fecha_hasta = fHasta.value || null;

    const ejeXOption = document.querySelector('input[name="eje_x"]:checked');
    f.eje_x = ejeXOption ? ejeXOption.value : 'fecha';

    if (f.eje_x === 'secuencia') {
        const selectDocs = document.getElementById('filtro-documentos');
        if (selectDocs) f.documentos_ids = Array.from(selectDocs.selectedOptions).map(opt => parseInt(opt.value));
    } else {
        f.documentos_ids = [];
    }

    return f;
}

function cargarListaDocumentos() {
  const select = document.getElementById('filtro-documentos');
  if (!select) return;

  // Mostrar estado de carga
  select.innerHTML = '<option disabled>Cargando documentos...</option>';

  // Filtros actuales para la búsqueda
  const payload = {
    tema: document.getElementById('filtro-tema').value || null,
    publicacion_id: document.getElementById('filtro-publicacion').value || null,
    pais: document.getElementById('filtro-pais').value || null,
    fecha_desde: document.getElementById('filtro-fecha-desde').value || null,
    fecha_hasta: document.getElementById('filtro-fecha-hasta').value || null,
    limit: 1000
  };

  fetch('/api/analisis/lista-documentos', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    },
    body: JSON.stringify(payload)
  })
    .then(res => res.json())
    .then(data => {
      if (data.exito) {
        select.innerHTML = '';
        if (data.documentos.length === 0) {
          select.innerHTML = '<option disabled>No se encontraron documentos</option>';
        } else {
          data.documentos.forEach(doc => {
            const opt = document.createElement('option');
            opt.value = doc.id;
            opt.textContent = doc.titulo;
            // Mantener seleccionados si ya estaban (opcional, por ahora limpialo)
            select.appendChild(opt);
          });
        }
      } else {
        select.innerHTML = `<option disabled class="text-danger">Error: ${data.error}</option>`;
      }
    })
    .catch(err => {
      console.error('[ERROR] Error al cargar lista de documentos:', err);
      select.innerHTML = '<option disabled class="text-danger">Error de conexión</option>';
    });
}

function exportarResultados() {
  const tipo = getVistaActiva();

  const datos = datosActuales[tipo];
  if (!datos) {
    alert('No hay datos para exportar');
    return;
  }

  const dataStr = JSON.stringify(datos, null, 2);
  const dataBlob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(dataBlob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `sirio_analisis_${tipo}_${new Date().toISOString().split('T')[0]}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

// Loading se maneja visualmente sin destruir el DOM
// Las vistas mantienen su estructura HTML intacta

function mostrarError(mensaje) {
  console.error('[ERROR]', mensaje);

  // Ocultar loading
  hideLoader();

  // Buscar un contenedor de error o crearlo (evita destruir el DOM de views)
  let errorContainer = document.getElementById('error-overlay-container');
  if (!errorContainer) {
    errorContainer = document.createElement('div');
    errorContainer.id = 'error-overlay-container';
    errorContainer.style = 'position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 2000; background: rgba(10, 10, 10, 0.95); display: flex; align-items: center; justify-content: center;';
    document.getElementById('analisis-container').appendChild(errorContainer);
  } else {
    errorContainer.style.display = 'flex';
  }

  errorContainer.innerHTML = `
    <div class="d-flex flex-column justify-content-center align-items-center text-center px-4">
      <i class="fa-solid fa-exclamation-triangle text-warning fa-4x mb-4"></i>
      <h3 class="text-white mb-3">Error al Cargar Análisis</h3>
      <p class="text-muted mb-4" style="max-width: 600px;">${mensaje}</p>
      <div class="d-flex gap-3">
        <button class="btn btn-sirio-primary" onclick="this.closest('#error-overlay-container').style.display='none'; location.reload()">
          <i class="fa-solid fa-refresh me-2"></i>Reintentar
        </button>
        <button class="btn btn-sirio" onclick="this.closest('#error-overlay-container').style.display='none'">
          <i class="fa-solid fa-arrow-left me-2"></i>Cerrar Aviso
        </button>
      </div>
      <div class="mt-4 p-3 rounded" style="background: rgba(255,255,255,0.05); max-width: 800px;">
        <p class="text-muted small mb-2"><strong>Sugerencias:</strong></p>
        <ul class="text-muted small text-start">
          <li>Asegúrate de tener publicaciones en tu proyecto activo</li>
          <li>Verifica que las publicaciones tengan contenido (no solo título)</li>
          <li>Intenta aplicar filtros para limitar el corpus</li>
        </ul>
      </div>
    </div>
  `;
}

// ============================================
// REPRESENTACIÓN VISUAL: ANÁLISIS INNOVADOR
// ============================================

function renderSemantico(data) {
  const ctx = document.getElementById('chart-semantico');
  if (!ctx) return;

  // Feedback visual de modo
  const titulo = document.querySelector('#view-semantico h3');
  if (titulo) {
    const existingBadge = titulo.querySelector('.badge-modo');
    if (existingBadge) existingBadge.remove();
    
    if (data.data.modo === 'manual') {
      const badge = document.createElement('span');
      badge.className = 'badge bg-info ms-2 badge-modo';
      badge.style.fontSize = '10px';
      badge.innerHTML = '<i class="fa-solid fa-hand-pointer me-1"></i> Seguimiento Manual';
      titulo.appendChild(badge);
    }
  }

  // Gestionar instancia del gráfico
  if (chartsInstances['semantico']) {
    chartsInstances['semantico'].destroy();
  }

  // Renderizar gráfico de líneas
  chartsInstances['semantico'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.data.labels,
      datasets: data.data.datasets.map(ds => ({
        ...ds,
        tension: 0.4,
        fill: false,
        pointRadius: 4
      }))
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: UI_COLORS.text(), font: { size: 10 } } }
      },
      scales: {
        y: { 
          grid: { color: UI_COLORS.grid(0.05) }, 
          border: { display: false }, 
          ticks: { color: '#888' },
          title: { display: true, text: 'Freq. Relativa (1k pal.)', color: '#666', font: { size: 10 } }
        },
        x: { grid: { display: false }, ticks: { color: '#888' } }
      }
    }
  });

  // Renderizar lista de términos
  const lista = document.getElementById('semantico-lista');
  if (lista) {
    lista.innerHTML = data.data.top_displaced.length > 0 ? data.data.top_displaced.map(item => `
      <div class="list-group-item bg-transparent border-0 px-0 py-2 d-flex justify-content-between align-items-center">
        <span class="text-light small">${item.term}</span>
        <span class="badge rounded-pill" style="background: rgba(155, 89, 182, 0.2); color: #9b59b6; font-family: var(--ds-font-mono); font-size: 11px;">Var: ${item.shift}</span>
      </div>
    `).join('') : '<div class="text-muted small p-2">No se detectaron desplazamientos significativos.</div>';
  }
}

function renderIntertextualidad(data) {
  const container = document.getElementById('intertextualidad-red');
  if (!container) return;

  const vis_data = {
    nodes: new vis.DataSet(data.data.nodes),
    edges: new vis.DataSet(data.data.edges)
  };

  const options = {
    nodes: {
      borderWidth: 2,
      shadow: true,
      font: { color: UI_COLORS.text(), size: 12 }
    },
    edges: {
      color: { inherit: 'from' },
      smooth: { type: 'continuous' }
    },
    physics: {
      forceAtlas2Based: { gravitationalConstant: -50, centralGravity: 0.01, springLength: 100 },
      maxVelocity: 50,
      solver: 'forceAtlas2Based',
      timestep: 0.35,
      stabilization: { iterations: 150 }
    }
  };

  new vis.Network(container, vis_data, options);
}

function renderEmociones(data) {
  const ctxRadar = document.getElementById('chart-emociones-radar');

  if (chartsInstances['emociones-radar']) {
    chartsInstances['emociones-radar'].destroy();
  }

  if (ctxRadar) {
    chartsInstances['emociones-radar'] = new Chart(ctxRadar, {
      type: 'radar',
      data: {
        labels: data.data.radar.labels,
        datasets: [{
          label: 'Perfil Emocional',
          data: data.data.radar.values,
          backgroundColor: 'rgba(155, 89, 182, 0.2)',
          borderColor: '#9b59b6',
          pointBackgroundColor: '#9b59b6'
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          r: {
            angleLines: { color: UI_COLORS.grid(0.1) },
            grid: { color: UI_COLORS.grid(0.1) },
            pointLabels: { color: '#888', font: { size: 10 } },
            ticks: { display: false, backdropColor: 'transparent' }
          }
        }
      }
    });
  }

  // Evolución Lineal
  const ctxLines = document.getElementById('chart-emociones-lineas');

  if (chartsInstances['emociones-lineas']) {
    chartsInstances['emociones-lineas'].destroy();
  }

  if (ctxLines) {
    chartsInstances['emociones-lineas'] = new Chart(ctxLines, {
      type: 'line',
      data: {
        labels: data.data.timeline.labels,
        datasets: (() => {
          const colores = {
            'Ira': '#e74c3c',
            'Miedo': '#8e44ad',
            'Tristeza': '#3498db',
            'Asco': '#2c3e50',
            'Sorpresa': '#f1c40f',
            'Anticipación': '#e67e22',
            'Confianza': '#2ecc71',
            'Alegría': '#f39c12'
          };
          const lineas = [];
          for (let emo in data.data.timeline) {
            if (emo !== 'labels') {
              lineas.push({
                label: emo,
                data: data.data.timeline[emo],
                borderColor: colores[emo] || '#95a5a6',
                tension: 0.4
              });
            }
          }
          return lineas;
        })()
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'top', labels: { color: UI_COLORS.legend(), boxWidth: 10 } } },
        scales: {
          y: { grid: { color: UI_COLORS.grid(0.05) }, ticks: { color: '#888' } },
          x: { grid: { display: false }, ticks: { color: '#888' } }
        }
      }
    });
  }
}

function renderSesgos(data) {
  const ctx = document.getElementById('chart-sesgos-radar');
  if (!ctx) return;

  if (chartsInstances['sesgos']) {
    chartsInstances['sesgos'].destroy();
  }

  chartsInstances['sesgos'] = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: data.data.labels,
      datasets: [{
        label: 'Perfil de Sesgos y Perspectiva',
        data: data.data.values,
        backgroundColor: 'rgba(52, 152, 219, 0.2)',
        borderColor: '#3498db',
        pointBackgroundColor: '#3498db',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { 
        legend: { display: false } 
      },
      scales: {
        r: {
          angleLines: { color: UI_COLORS.grid(0.1) },
          grid: { color: UI_COLORS.grid(0.1) },
          pointLabels: { color: '#ccc', font: { size: 11, family: 'Inter' } },
          ticks: { display: false }
        }
      }
    }
  });
}

// Handler para Sirio Chat (Corpus Chat)
document.addEventListener('click', function (e) {
  if (e.target && (e.target.id === 'btn-sirio-chat-send' || e.target.closest('#btn-sirio-chat-send'))) {
    const input = document.getElementById('sirio-chat-input');
    const box = document.getElementById('sirio-chat-box');
    if (!input || !box || !input.value.trim()) return;

    const msg = input.value;
    input.value = '';

    // Añadir mensaje de usuario
    box.innerHTML += `
      <div class="chat-message user mb-3 text-end">
        <div class="message-content d-inline-block p-2 rounded bg-white bg-opacity-10 border border-white border-opacity-10 text-white small">
          ${msg}
        </div>
      </div>
    `;

    // Simular respuesta del bot
    box.innerHTML += `
      <div class="chat-message bot mb-3" id="typing-indicator">
        <div class="message-content p-2 rounded bg-accent bg-opacity-10 text-muted small italic">
          <i class="fa-solid fa-spinner fa-spin me-2"></i>Consultando corpus...
        </div>
      </div>
    `;
    box.scrollTop = box.scrollHeight;

    setTimeout(() => {
      const indicator = document.getElementById('typing-indicator');
      if (indicator) indicator.remove();

      box.innerHTML += `
        <div class="chat-message bot mb-3">
          <div class="message-content p-2 rounded bg-accent bg-opacity-10 border border-accent border-opacity-20 text-light small">
            <i class="fa-solid fa-robot me-2"></i><b>Sirio AI:</b> Basado en el análisis de los documentos seleccionados, he encontrado que el término "${msg}" aparece con alta frecuencia en contextos asociados a la modernización industrial de finales del siglo XIX.
          </div>
        </div>
      `;
      box.scrollTop = box.scrollHeight;
    }, 1500);
  }
});

// ============================================
// CARGA Y RENDER: ANÁLISIS INNOVADOR (LITERARIO)
// ============================================

function cargarInnovador() {
  const loader = document.getElementById('loading-state');
  if (loader) loader.style.display = 'flex';

  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';

  fetch('/api/analisis/innovador/literario', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
    },
    body: JSON.stringify({ ...filtros, theme: currentTheme })
  })
    .then(res => res.json())
    .then(data => {
      if (data.exito) {
        datosActuales['innovador'] = data;
        renderInnovador(data);
      } else {
        mostrarError(data.error);
      }
      if (loader) loader.style.display = 'none';
    })
    .catch(err => {
      console.error('[ERROR] Error al cargar análisis innovador:', err);
      mostrarError('Error de conexión al cargar el análisis literario.');
    });
}

function renderInnovador(data) {
  console.log('[DEBUG] renderInnovador llamado');

  if (!data.charts) return;

  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  const vegaTheme = currentTheme === 'light' ? 'default' : 'dark';

  // 1. Dispersión Léxica
  if (data.charts.dispersion) {
    const patchedSpec = patchVegaTheme(data.charts.dispersion, currentTheme);
    vegaEmbed('#altair-dispersion', patchedSpec, {
      actions: false,
      theme: vegaTheme,
      background: 'transparent'
    }).catch(e => console.error('[ERROR] Vega dispersión:', e));
  }

  // 2. Arco de Sentimiento
  if (data.charts.arco_sentimiento) {
    const patchedSpec = patchVegaTheme(data.charts.arco_sentimiento, currentTheme);
    vegaEmbed('#altair-sentimiento-arco', patchedSpec, {
      actions: false,
      theme: vegaTheme,
      background: 'transparent'
    }).catch(e => console.error('[ERROR] Vega arco:', e));
  }

  // 3. Heatmap Estilístico
  if (data.charts.heatmap_estilo) {
    const patchedSpec = patchVegaTheme(data.charts.heatmap_estilo, currentTheme);
    vegaEmbed('#altair-estilo-heatmap', patchedSpec, {
      actions: false,
      theme: vegaTheme,
      background: 'transparent'
    }).catch(e => console.error('[ERROR] Vega heatmap:', e));
  }
}

// -------------------------------------------------------------------------
// FUNCIONES DE INTERPRETACIÓN IA PARA EMOCIONES
// -------------------------------------------------------------------------

function interpretarEmocionesIA(tipo) {
  const btn = document.getElementById(`btn-ia-${tipo}`);
  const resultDiv = document.getElementById(`resultado-ia-${tipo}`);
  const modeloIA = window._ia_modelo || 'gemini-1.5-pro';
  
  const chartId = tipo === 'radar' ? 'emociones-radar' : 'emociones-lineas';
  
  if (!chartsInstances[chartId]) {
    alert("El gráfico aún no está completamente cargado.");
    return;
  }
  
  const chartInstance = chartsInstances[chartId];
  let chartDataToSend = {};
  
  if (tipo === 'radar') {
    chartInstance.data.labels.forEach((label, index) => {
      chartDataToSend[label] = chartInstance.data.datasets[0].data[index];
    });
  } else {
    chartDataToSend.labels = chartInstance.data.labels;
    chartInstance.data.datasets.forEach(ds => {
      chartDataToSend[ds.label] = ds.data;
    });
  }
  
  // UX: Loading state
  btn.disabled = true;
  const originalHtml = btn.innerHTML;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Procesando Neurolectura...`;
  resultDiv.style.display = 'none';
  resultDiv.innerHTML = '';

  fetch('/api/analisis/innovador/interpretar_emociones', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      chart_type: tipo,
      chart_data: chartDataToSend,
      modelo: modeloIA
    })
  })
  .then(res => res.json())
  .then(data => {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    
    if (data.exito) {
      resultDiv.style.display = 'block';
      let formattedText = data.interpretacion.replace(/\n/g, '<br/>');
      formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      formattedText = formattedText.replace(/\*(.*?)\*/g, '<em>$1</em>');
      
      resultDiv.innerHTML = `<div class="mb-2"><span class="badge" style="background: rgba(155, 89, 182, 0.3); border: 1px solid #9b59b6;"><i class="fa-solid fa-microchip me-1"></i> ${modeloIA}</span></div>` + formattedText;
    } else {
      alert("No se pudo generar la interpretación. Motivo: " + data.error);
    }
  })
  .catch(err => {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    console.error(err);
    alert("Error de conexión con el servicio de IA.");
  });
}

function interpretarSemanticaIA() {
  const btn = document.getElementById(`btn-ia-semantica`);
  const resultDiv = document.getElementById(`resultado-ia-semantica`);
  const modeloIA = window._ia_modelo || 'gemini-1.5-pro';
  
  if (!chartsInstances['semantico']) {
    alert("El gráfico semántico aún no está cargado.");
    return;
  }
  
  const chartInstance = chartsInstances['semantico'];
  let chartDataToSend = {
    labels: chartInstance.data.labels,
    series: {}
  };
  
  chartInstance.data.datasets.forEach(ds => {
    chartDataToSend.series[ds.label] = ds.data;
  });
  
  // UX: Loading state
  btn.disabled = true;
  const originalHtml = btn.innerHTML;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Analizando Deriva Semántica...`;
  resultDiv.style.display = 'none';
  resultDiv.innerHTML = '';

  fetch('/api/analisis/innovador/interpretar_semantica', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      chart_data: chartDataToSend,
      modelo: modeloIA
    })
  })
  .then(response => response.json())
  .then(data => {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    
    if (data.exito) {
      resultDiv.style.display = 'block';
      let formattedText = data.interpretacion.replace(/\n/g, '<br/>');
      formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      formattedText = formattedText.replace(/\*(.*?)\*/g, '<em>$1</em>');
      
      resultDiv.innerHTML = `
        <div class="ia-response-header d-flex align-items-center mb-2">
            <span class="badge bg-primary px-2 py-1" style="font-size: 10px; font-family: var(--ds-font-mono);">
                <i class="fa-solid fa-microchip me-1"></i> ${modeloIA}
            </span>
        </div>
        <div class="ia-content-markdown">${formattedText}</div>
      `;
    } else {
      alert("Error: " + data.error);
    }
  })
  .catch(err => {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    console.error(err);
    alert("Error de conexión con el servicio de IA.");
  });
}
function interpretarIntertextualidadIA() {
  const btn = document.getElementById('btn-ia-intertextualidad');
  const resultDiv = document.getElementById('resultado-ia-intertextualidad');
  const modeloIA = window._ia_modelo || 'gemini-1.5-pro';

  // UX: Loading state
  btn.disabled = true;
  const originalHtml = btn.innerHTML;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Analizando Red Transmedia...`;
  resultDiv.style.display = 'none';
  resultDiv.innerHTML = '';

  // Obtenemos los datos actuales (nodos/bordes)
  const data = datosActuales['intertextualidad'] || {};

  fetch('/api/analisis/innovador/interpretar_intertextualidad', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      chart_data: data.data,
      modelo: modeloIA
    })
  })
  .then(res => res.json())
  .then(data => {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    if (data.exito) {
      resultDiv.style.display = 'block';
      let formattedText = data.interpretacion.replace(/\n/g, '<br/>');
      formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      formattedText = formattedText.replace(/\*(.*?)\*/g, '<em>$1</em>');
      resultDiv.innerHTML = `<div class="mb-2"><span class="badge bg-primary px-2 py-1" style="font-size: 10px;"><i class="fa-solid fa-microchip me-1"></i> ${modeloIA}</span></div><div class="ia-content-markdown">${formattedText}</div>`;
    } else {
      alert("Error: " + data.error);
    }
  })
  .catch(err => {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    console.error(err);
    alert("Error de conexión con el servicio de IA.");
  });
}

function interpretarSesgosIA() {
  const btn = document.getElementById('btn-ia-sesgos');
  const resultDiv = document.getElementById('resultado-ia-sesgos');
  const modeloIA = window._ia_modelo || 'gemini-1.5-pro';

  if (!chartsInstances['sesgos']) {
    alert("El gráfico de sesgos aún no está cargado.");
    return;
  }

  const chartInstance = chartsInstances['sesgos'];
  let chartDataToSend = {};
  chartInstance.data.labels.forEach((label, index) => {
    chartDataToSend[label] = chartInstance.data.datasets[0].data[index];
  });

  // UX: Loading state
  btn.disabled = true;
  const originalHtml = btn.innerHTML;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Detectando Sesgos Críticos...`;
  resultDiv.style.display = 'none';
  resultDiv.innerHTML = '';

  fetch('/api/analisis/innovador/interpretar_sesgos', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      chart_data: chartDataToSend,
      modelo: modeloIA
    })
  })
  .then(res => res.json())
  .then(data => {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    if (data.exito) {
      resultDiv.style.display = 'block';
      let formattedText = data.interpretacion.replace(/\n/g, '<br/>');
      formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      formattedText = formattedText.replace(/\*(.*?)\*/g, '<em>$1</em>');
      resultDiv.innerHTML = `<div class="mb-2"><span class="badge bg-primary px-2 py-1" style="font-size: 10px;"><i class="fa-solid fa-microchip me-1"></i> ${modeloIA}</span></div><div class="ia-content-markdown">${formattedText}</div>`;
    } else {
      alert("Error: " + data.error);
    }
  })
  .catch(err => {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    console.error(err);
    alert("Error de conexión con el servicio de IA.");
  });
}
/**
 * ANALISIS DRAMÁTICO (TEATRO)
 * Migrado y robustecido para trabajar en la vista avanzada.
 */

/**
 * Función centralizada que renderiza todos los componentes dramáticos con capacidad de filtrado
 */
window.renderDramaticoFull = function(data, filterActo = 'all', filterEscena = 'all', filterObra = 'all') {
    const light = UI_COLORS.isLight();
    const textWhite = light ? '#212121' : '#fff';
    const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
    const borderColor = light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)';
    const accentColor = UI_COLORS.accent();
    const accentAlpha = light ? 'rgba(41, 74, 96, 0.1)' : 'rgba(255, 152, 0, 0.1)';

    // 0. Obtener personajes a ignorar/ocultar
    const ignoreKey = `ignored_${filtros.proyecto_id || 'default'}`;
    const ignoredChars = JSON.parse(localStorage.getItem(ignoreKey) || '[]');
    const deleteKey = `deleted_${filtros.proyecto_id || 'default'}`;
    const deletedChars = JSON.parse(localStorage.getItem(deleteKey) || '[]');
    
    // 1. Filtrar Índices de Bloques (Segmentación)
    let indicesFiltrados = [];
    const filteredTension = (data.sentimiento_temporal || []).filter((s, idx) => {
        const matchesActo = filterActo === 'all' || String(s.acto) === filterActo;
        const matchesEscena = filterEscena === 'all' || String(s.escena) === filterEscena;
        const matchesObra = (filterObra === 'all' || filterObra === '') || String(s.publicacion_id) === String(filterObra);
        if (matchesActo && matchesEscena && matchesObra) {
            indicesFiltrados.push(idx);
            return true;
        }
        return false;
    });

    // 2. RE-AGREGACIÓN DINÁMICA (Protagonismo, Tácticas, Red, Heatmap)
    const segmentStats = {};
    const segmentCooc = new Map();
    
    indicesFiltrados.forEach(idx => {
        const block = data.sentimiento_temporal[idx];
        const presentes = new Set();
        
        (block.locuciones || []).forEach(l => {
            const charName = l.p;
            if (ignoredChars.includes(charName) || deletedChars.includes(charName)) return;
            
            if (!segmentStats[charName]) {
                segmentStats[charName] = { palabras: 0, intervenciones: 0, tacticas: {} };
            }
            
            segmentStats[charName].intervenciones++;
            const words = l.t ? l.t.trim().split(/\s+/).length : 0;
            segmentStats[charName].palabras += words;
            
            const tac = l.tac || 'Informar';
            segmentStats[charName].tacticas[tac] = (segmentStats[charName].tacticas[tac] || 0) + 1;
            
            presentes.add(charName);
        });
        
        const presentesList = Array.from(presentes);
        for (let i = 0; i < presentesList.length; i++) {
            for (let j = i + 1; j < presentesList.length; j++) {
                const par = [presentesList[i], presentesList[j]].sort().join('|');
                segmentCooc.set(par, (segmentCooc.get(par) || 0) + 1);
            }
        }
    });

    // Filtrar y actualizar Reparto: Solo los que intervienen en el segmento
    const filteredReparto = (data.reparto_detalle || [])
        .filter(p => !ignoredChars.includes(p.nombre) && !deletedChars.includes(p.nombre) && segmentStats[p.nombre])
        .map(p => {
            const s = segmentStats[p.nombre];
            return {
                ...p,
                palabras: s.palabras,
                intervenciones: s.intervenciones,
                palabras_por_intervencion: s.intervenciones > 0 ? (s.palabras / s.intervenciones).toFixed(1) : 0,
                perfil_tactico: s.tacticas
            };
        })
        .sort((a, b) => b.palabras - a.palabras);

    let totalPalabras = 0;
    filteredReparto.forEach(p => totalPalabras += (p.palabras || 0));

    // Actualizar KPIs de cabecera
    const charStatEl = document.getElementById('stat-drama-chars');
    const segmentStatEl = document.getElementById('stat-drama-segments');
    const wordStatEl = document.getElementById('stat-drama-words');
    
    if (charStatEl) charStatEl.innerText = filteredReparto.length;
    if (segmentStatEl) segmentStatEl.innerText = indicesFiltrados.length;
    if (wordStatEl) wordStatEl.innerHTML = `${totalPalabras.toLocaleString('es-ES')} <span class="fs-6 opacity-50 fw-normal" style="font-size: 11px;">palabras</span>`;

    // Filtrar y actualizar Red
    const activeCharNames = new Set(filteredReparto.map(p => p.nombre));
    const filteredNodes = (data.nodos || [])
        .filter(n => activeCharNames.has(n.id))
        .map(n => ({
            ...n,
            influencia: segmentStats[n.id] ? segmentStats[n.id].intervenciones : 0
        }));

    const filteredEdges = [];
    segmentCooc.forEach((value, key) => {
        const [p1, p2] = key.split('|');
        if (activeCharNames.has(p1) && activeCharNames.has(p2)) {
            filteredEdges.push({ source: p1, target: p2, value: value });
        }
    });

    const labels = filteredTension.map(s => s.label);
    const dataTensionValues = filteredTension.map(s => s.sentimiento);

    const tableContainer = document.getElementById('drama-table-body');
    if (tableContainer) {
        tableContainer.innerHTML = filteredReparto.map(p => `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td class="fw-bold py-3" style="color: var(--ds-accent);">${p.nombre}</td>
                <td class="text-center font-monospace" style="color: ${textWhite};">${p.intervenciones || 0}</td>
                <td class="text-center font-monospace" style="color: ${textWhite};">${p.palabras_por_intervencion || 0}</td>
                <td class="small">
                    ${(p.distinctive_words || []).map(w => `<span class="badge bg-warning bg-opacity-10 text-warning border border-warning border-opacity-25 me-1 fw-bold" style="font-size: 10px !important;">${w}</span>`).join('')}
                    <div class="mt-1 opacity-50" style="font-size: 9px;">
                        Dominantes: ${(p.top_words || []).slice(0,3).map(w => typeof w === 'object' ? w.term : w).join(', ')}
                    </div>
                </td>
                <td class="small opacity-75">
                    ${(p.top_frases || []).map(f => {
                        const term = typeof f === 'object' ? f.term : f;
                        const count = typeof f === 'object' ? f.count : '?';
                        return `<span class="badge bg-sirio-dim me-1 fw-normal border border-secondary border-opacity-10" style="font-size: 10px; color: var(--ds-accent-primary); opacity: 0.8; font-style: italic; cursor: help;" title="Frecuencia: ${count} veces">"${term}"</span>`;
                    }).join('')}
                </td>
            </tr>
        `).join('');
    }

    // 2. Red de Personajes (Vis.js)
    const networkContainer = document.getElementById('drama-network');
    if (networkContainer && typeof vis !== 'undefined') {
        const colorPalette = [
            { bg: accentColor, border: light ? '#1d3545' : '#e65100' }, 
            { bg: '#ffffff', border: '#aaaaaa' }, 
            { bg: '#2196f3', border: '#0d47a1' }, 
            { bg: '#4caf50', border: '#1b5e20' }, 
            { bg: '#9c27b0', border: '#4a148c' }, 
            { bg: '#f44336', border: '#b71c1c' }  
        ];

        const gruposPresencia = [...new Set(data.nodos.map(n => n.grupo))].sort();
        const getGroupColor = (groupId) => {
            const idx = gruposPresencia.indexOf(groupId);
            return colorPalette[idx % colorPalette.length];
        };

        const visData = {
            nodes: filteredNodes.map(n => {
                const colors = getGroupColor(n.grupo);
                return {
                    id: n.id,
                    label: n.name,
                    size: 15 + Math.sqrt(n.influencia) * 4,
                    color: { 
                        background: colors.bg, 
                        border: 'rgba(255,255,255,0.2)', 
                        highlight: { background: '#fff', border: colors.bg } 
                    },
                    font: { color: textWhite, size: 11, face: 'JetBrains Mono' },
                    shadow: true
                };
            }),
            edges: filteredEdges.map(e => ({
                from: e.source, to: e.target,
                width: 2 + Math.log1p(e.value) * 1.5,
                color: { 
                    color: UI_COLORS.isLight() ? 'rgba(41, 74, 96, 0.45)' : 'rgba(255, 152, 0, 0.5)', 
                    highlight: accentColor,
                    hover: accentColor 
                },
                smooth: { type: 'continuous' },
                shadow: { enabled: true, color: 'rgba(0,0,0,0.4)', size: 3 }
            }))
        };
        new vis.Network(networkContainer, visData, { 
            nodes: { shape: 'dot' },
            physics: { forceAtlas2Based: { gravitationalConstant: -80, springLength: 120 }, solver: 'forceAtlas2Based', stabilization: { iterations: 100 } } 
        });
    }

    // 3. Gráfico de Protagonismo
    const ctxP = document.getElementById('chart-drama-protagonismo');
    if (ctxP) {
        let chartP = Chart.getChart('chart-drama-protagonismo');
        if (chartP) chartP.destroy();
        new Chart(ctxP, {
            type: 'bar',
            data: {
                labels: filteredReparto.slice(0, 8).map(p => p.nombre),
                datasets: [{
                    label: 'Palabras Habladas',
                    data: filteredReparto.slice(0, 8).map(p => p.palabras),
                    backgroundColor: accentAlpha, borderColor: accentColor, borderWidth: 1.5, borderRadius: 6
                }]
            },
            options: { 
                indexAxis: 'y', responsive: true, maintainAspectRatio: false, 
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: borderColor, borderDash: [4, 4] }, ticks: { color: textMuted } },
                    y: { ticks: { color: textWhite }, grid: { display: false } }
                }
            }
        });
    }

    // 4. Gráfico de Tensión
    const ctxT = document.getElementById('drama-tension-convergence');
    if (ctxT) {
        let chartT = Chart.getChart('drama-tension-convergence');
        if (chartT) chartT.destroy();
        new Chart(ctxT, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sentimiento General',
                    data: dataTensionValues,
                    borderColor: accentColor, backgroundColor: accentAlpha, fill: true, tension: 0.4,
                    borderWidth: 2, pointRadius: 4, pointBackgroundColor: accentColor
                }]
            },
            options: { 
                responsive: true, maintainAspectRatio: false,
                scales: { 
                    y: { min: -1, max: 1, grid: { color: borderColor, borderDash: [4, 4] }, ticks: { color: textMuted } },
                    x: { grid: { color: borderColor, borderDash: [4, 4] }, ticks: { color: textMuted, maxRotation: 45, minRotation: 45, font: { size: 10 } } }
                },
                plugins: { legend: { display: false } },
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const idx = elements[0].index;
                        const block = filteredTension[idx];
                        if (block && block.texto) {
                            const detail = document.getElementById('drama-block-detail');
                            const text = document.getElementById('drama-block-text');
                                if (detail && text) {
                                    detail.style.display = 'block';
                                    const readerBtn = document.getElementById('drama-reader-btn');
                                    if (readerBtn) readerBtn.href = `/noticias/lector?id=${block.doc_id}`;
                                    let html = (block.locuciones || []).map(l => `<span class="text-warning"><b>${l.p}:</b></span> ${l.t}`).join('<br>');
                                    if (!html) html = block.texto;
                                    text.innerHTML = html;
                                detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                            }
                        }
                    }
                }
            }
        });
    }

    // 5. Arcos de Personajes
    const ctxS = document.getElementById('drama-individual-trajectories');
    if (ctxS) {
        let chartS = Chart.getChart('drama-individual-trajectories');
        if (chartS) chartS.destroy();
        const palette = ['#ff9800', '#2196f3', '#4caf50', '#9c27b0', '#f44336', '#00bcd4'];
        new Chart(ctxS, {
            type: 'line',
            data: {
                labels: labels,
                datasets: filteredReparto.slice(0, 10).map((p, i) => {
                    const fullArc = p.sentimiento_arc || [];
                    const filteredArc = indicesFiltrados.map(idx => fullArc[idx] !== undefined ? fullArc[idx] : null);
                    return {
                        label: p.nombre, data: filteredArc, borderColor: palette[i % palette.length], 
                        backgroundColor: palette[i % palette.length] + '22',
                        tension: 0.3, fill: false, spanGaps: true, borderWidth: 2,
                        pointRadius: indicesFiltrados.length > 50 ? 0 : 3
                    };
                })
            },
            options: { 
                responsive: true, maintainAspectRatio: false, 
                plugins: { legend: { labels: { color: textWhite, font: { size: 10 } } } },
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const idx = elements[0].index;
                        const block = filteredTension[idx];
                        if (block && block.texto) {
                            const detail = document.getElementById('drama-block-detail');
                            const text = document.getElementById('drama-block-text');
                                if (detail && text) {
                                    detail.style.display = 'block';
                                    const readerBtn = document.getElementById('drama-reader-btn');
                                    if (readerBtn) readerBtn.href = `/noticias/lector?id=${block.doc_id}`;
                                    const datasetIdx = elements[0].datasetIndex;
                                    const charName = e.chart.data.datasets[datasetIdx].label;
                                    const upperChar = charName.toUpperCase();
                                    const relevant = (block.locuciones || []).filter(l => {
                                        const lp = l.p.toUpperCase();
                                        return lp === upperChar || upperChar.includes(lp) || lp.includes(upperChar);
                                    });
                                    let html = "";
                                    if (relevant.length > 0) {
                                        html = relevant.map(l => `<span class="text-warning"><b>${l.p}:</b></span> ${l.t}`).join('<br><br>');
                                    } else {
                                        const lines = block.texto.split('\n');
                                        const mentions = lines.filter(line => line.toUpperCase().includes(upperChar));
                                        if (mentions.length > 0) {
                                            html = `<i class="text-muted small d-block mb-3 border-bottom border-warning border-opacity-10 pb-2">Menciones detectadas:</i>`;
                                            html += mentions.map(m => m.replace(new RegExp(`(${charName})`, 'gi'), '<span class="text-warning fw-bold">$1</span>')).join('<br><br>');
                                        } else {
                                            html = `<i class="text-muted small">No se detectaron diálogos de <b>${charName}</b> en este bloque.</i>`;
                                        }
                                    }
                                    text.innerHTML = html;
                                detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                            }
                        }
                    }
                }
            }
        });
    }

    // 6. Matriz de Presencia
    const presenceTarget = document.getElementById('drama-presence-matrix');
    if (data.reparto_detalle && presenceTarget && typeof vegaEmbed !== 'undefined') {
        const presenceData = [];
        filteredReparto.slice(0, 10).forEach(p => {
            (p.presencia_matriz || []).forEach((val, idx) => {
                if (val > 0 && indicesFiltrados.includes(idx)) {
                    const bloq = data.sentimiento_temporal[idx];
                    presenceData.push({ "Personaje": p.nombre, "Bloque": (bloq && bloq.label) ? bloq.label : `S${idx+1}`, "Presente": val });
                }
            });
        });
        if (presenceData.length > 0) {
            const spec = {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "data": { "values": presenceData },
                "width": "container", "height": "container",
                "mark": { "type": "circle", "size": 100 },
                "encoding": {
                    "x": { "field": "Bloque", "type": "nominal", "sort": null, "axis": { "labelColor": textMuted, "labelFontSize": 9, "title": null, "grid": true, "gridColor": borderColor } },
                    "y": { "field": "Personaje", "type": "nominal", "axis": { "labelColor": textWhite, "labelFontSize": 10, "title": null, "grid": true, "gridColor": borderColor } },
                    "color": { "value": accentColor }
                },
                "background": "transparent",
                "config": { "view": { "stroke": "transparent" }, "axis": { "domain": false, "ticks": false } }
            };
            vegaEmbed('#drama-presence-matrix', spec, { actions: false });
        }
    }
    
    // 7. Heatmap de Interacciones (Re-calculado para el segmento)
    const heatmapTarget = document.getElementById('drama-heatmap-words');
    const heatmapData = [];
    segmentCooc.forEach((value, key) => {
        const [p1, p2] = key.split('|');
        heatmapData.push({ p1, p2, valor: value });
    });
    if (heatmapData.length > 0 && heatmapTarget && typeof vegaEmbed !== 'undefined') {
        const spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "data": { "values": heatmapData },
            "width": "container", "height": "container",
            "mark": "rect",
            "encoding": {
                "y": { "field": "p1", "type": "nominal", "axis": { "labelColor": textWhite, "labelFontSize": 10, "title": null } },
                "x": { "field": "p2", "type": "nominal", "axis": { "labelColor": textWhite, "labelFontSize": 10, "labelAngle": -45, "title": null } },
                "color": { "field": "valor", "type": "quantitative", "scale": { "range": [accentAlpha, accentColor] } }
            },
            "background": "transparent",
            "config": { "view": { "stroke": "transparent" }, "axis": { "grid": false, "domain": false, "ticks": false } }
        };
        vegaEmbed('#drama-heatmap-words', spec, { actions: false });
    }

    // 8. Ritmo Dramático
    const ctxR = document.getElementById('drama-rhythm-sync');
    if (ctxR && data.metricas_avanzadas) {
        let chartR = Chart.getChart('drama-rhythm-sync');
        if (chartR) chartR.destroy();
        const ritmoData = data.metricas_avanzadas.ritmo_bloques || [];
        const filteredRitmo = indicesFiltrados.map(idx => ritmoData[idx]);
        new Chart(ctxR, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Ritmo', data: filteredRitmo.map(r => r ? r.intervenciones : 0), borderColor: accentColor, backgroundColor: accentAlpha, fill: true, tension: 0.4, yAxisID: 'y' },
                    { label: 'Acotaciones', data: filteredRitmo.map(r => r ? r.sent_acotaciones : 0), borderColor: '#2196f3', borderDash: [5, 5], fill: false, tension: 0.4, yAxisID: 'y1' }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    y: { type: 'linear', position: 'left', grid: { color: borderColor, borderDash: [4, 4] }, ticks: { color: textMuted } },
                    y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#2196f3' } },
                    x: { grid: { color: borderColor, borderDash: [4, 4] }, ticks: { color: textMuted, font: { size: 9 } } }
                }
            }
        });
    }

    // 9. Sincronía Emocional - Filtrar por personajes activos en el segmento
    const syncContainer = document.getElementById('sync-list');
    const syncHeatmap = document.getElementById('heatmap-sincronia');
    if (syncContainer && data.metricas_avanzadas) {
        const rawSyncs = (data.metricas_avanzadas.sincronia_pares || [])
            .filter(s => activeCharNames.has(s.p1) && activeCharNames.has(s.p2));
        const syncsMatrix = [];
        rawSyncs.forEach(s => { syncsMatrix.push(s); syncsMatrix.push({ p1: s.p2, p2: s.p1, score: s.score }); });
        [...new Set(rawSyncs.flatMap(s => [s.p1, s.p2]))].forEach(p => { syncsMatrix.push({ p1: p, p2: p, score: 1.0 }); });
        
        if (syncHeatmap && typeof vegaEmbed !== 'undefined' && syncsMatrix.length > 0) {
            const syncSpec = {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "width": "container", "height": "container",
                "data": { "values": syncsMatrix },
                "mark": { "type": "rect", "stroke": borderColor, "strokeWidth": 0.5 },
                "encoding": {
                    "y": { "field": "p1", "type": "nominal", "axis": { "labelFontSize": 8, "labelColor": textWhite } },
                    "x": { "field": "p2", "type": "nominal", "axis": { "labelFontSize": 8, "labelColor": textWhite, "labelAngle": -45 } },
                    "color": { "field": "score", "type": "quantitative", "scale": { "domain": [-1, 0, 1], "range": ["#ef4444", "#333", "#22c55e"] } }
                },
                "background": "transparent"
            };
            vegaEmbed('#heatmap-sincronia', syncSpec, { actions: false });
        }
        syncContainer.innerHTML = rawSyncs.slice(0, 10).map(s => `
            <div class="d-flex justify-content-between align-items-center mb-1 p-2 rounded border border-warning border-opacity-10" style="background: rgba(255,152,0,0.05) !important; font-size: 11px;">
                <div class="text-truncate" style="max-width: 180px;"><span class="fw-bold">${s.p1}</span> <i class="fa-solid fa-arrows-left-right mx-1 text-warning opacity-50"></i> <span class="fw-bold">${s.p2}</span></div>
                <div class="badge bg-warning text-dark font-monospace">${Math.round(s.score * 100)}%</div>
            </div>
        `).join('');
    }

    // 10. Evolución del Flujo Táctico (Streamgraph) - Filtrado por segmento
    const tacticalStreamTarget = document.getElementById('drama-tactical-stream');
    const labelsFiltrados = new Set(filteredTension.map(s => s.label));
    const tacticalData = ((data.metricas_avanzadas || {}).flujo_tactico || [])
        .filter(t => labelsFiltrados.has(t.Bloque));
    
    console.log("[DEBUG] Tactical Data for Streamgraph:", tacticalData);

    if (tacticalStreamTarget && tacticalData.length > 0 && typeof vegaEmbed !== 'undefined') {
        const streamSpec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "data": { "values": tacticalData },
            "width": "container", 
            "height": 300,
            "mark": { "type": "area", "interpolate": "monotone", "fillOpacity": 0.85 },
            "encoding": {
                "x": { 
                    "field": "Bloque", 
                    "type": "nominal", 
                    "sort": null, 
                    "axis": { 
                        "labelColor": textMuted, 
                        "labelFontSize": 10, 
                        "title": null, 
                        "labelAngle": -45,
                        "grid": true,
                        "gridColor": light ? "rgba(0,0,0,0.4)" : "rgba(255,255,255,0.4)",
                        "gridDash": [2, 2]
                    } 
                },
                "y": { 
                    "field": "Valor", 
                    "type": "quantitative", 
                    "stack": "center", 
                    "axis": {
                        "grid": true,
                        "gridColor": light ? "rgba(0,0,0,0.2)" : "rgba(255,255,255,0.2)",
                        "labels": false,
                        "ticks": false,
                        "title": null
                    } 
                },
                "color": { 
                    "field": "Táctica", 
                    "type": "nominal", 
                    "scale": { "scheme": "spectral" }, 
                    "legend": { "title": "Tácticas", "labelColor": textWhite, "titleColor": textWhite, "orient": "bottom" } 
                },
                "tooltip": [
                    { "field": "Bloque", "type": "nominal" },
                    { "field": "Táctica", "type": "nominal" },
                    { "field": "Valor", "type": "quantitative" }
                ]
            },
            "background": "transparent",
            "config": { "view": { "stroke": "transparent" } }
        };
        vegaEmbed('#drama-tactical-stream', streamSpec, { actions: false })
            .catch(err => console.error("[VEGA ERROR]", err));
    } else if (tacticalStreamTarget) {
        tacticalStreamTarget.innerHTML = '<div class="text-muted small italic opacity-50 p-5 text-center">No hay datos tácticos suficientes para generar el flujo.</div>';
    }

    // 11. Perfiles Tácticos del Reparto (Radar) - Usar reparto filtrado
    const radarContainer = document.getElementById('radar-containers');
    if (radarContainer) {
        radarContainer.innerHTML = '';
        const topChars = filteredReparto.slice(0, 12);
        
        // Categorías tácticas fijas para asegurar que el radar sea comparable
        const fixedLabels = ["Atacar", "Persuadir", "Seducir", "Manipular", "Informar"];
        
        topChars.forEach((p, idx) => {
            const charId = `drama-radar-${idx}`;
            const col = document.createElement('div');
            col.className = 'col-md-3 col-sm-6 mb-3';
            col.innerHTML = `
                <div class="glass-panel p-3 text-center h-100" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);">
                    <div class="small fw-bold text-truncate mb-2" style="color: ${accentColor}; letter-spacing: 1px;">${p.nombre}</div>
                    <div style="height: 160px; position: relative;">
                        <canvas id="${charId}"></canvas>
                    </div>
                    <div class="mt-2 pt-2 border-top border-secondary border-opacity-10">
                        <span class="badge bg-sirio-dim text-accent-primary" style="font-size: 8px;">PERFIL DRAMÁTICO</span>
                    </div>
                </div>
            `;
            radarContainer.appendChild(col);

            // Retraso para asegurar que el DOM está listo
            setTimeout(() => {
                const canvas = document.getElementById(charId);
                if (canvas) {
                    const ctxR = canvas.getContext('2d');
                    const tacticas = p.perfil_tactico || {};
                    
                    // Mapear valores a las etiquetas fijas
                    const values = fixedLabels.map(label => tacticas[label] || 0);
                    
                    // Solo renderizar si hay algún dato táctico
                    if (values.some(v => v > 0)) {
                        new Chart(ctxR, {
                            type: 'radar',
                            data: {
                                labels: fixedLabels,
                                datasets: [{
                                    data: values,
                                    backgroundColor: 'rgba(255, 152, 0, 0.2)',
                                    borderColor: accentColor,
                                    borderWidth: 2,
                                    pointRadius: 2,
                                    pointBackgroundColor: accentColor
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: { legend: { display: false } },
                                scales: {
                                    r: {
                                        min: 0,
                                        grid: { color: borderColor, borderDash: [3, 3] },
                                        angleLines: { color: borderColor },
                                        pointLabels: { 
                                            color: textMuted, 
                                            font: { size: 9, family: 'JetBrains Mono', weight: 'bold' } 
                                        },
                                        ticks: { display: false, backdropColor: 'transparent' }
                                    }
                                }
                            }
                        });
                    } else {
                        ctxR.font = "10px JetBrains Mono";
                        ctxR.fillStyle = "rgba(255,255,255,0.3)";
                        ctxR.textAlign = "center";
                        ctxR.fillText("Sin tácticas detectadas", canvas.width/2, canvas.height/2);
                    }
                }
            }, 100);
        });
    }
};


function loadDramatico(data) {
  const container = document.getElementById('view-dramatico');
  if (!container) return;
  
  const oldIaContainer = document.getElementById('ia-report-container');
  if (oldIaContainer) oldIaContainer.innerHTML = '';
  
  const light = UI_COLORS.isLight();
  const textWhite = light ? '#212121' : '#fff';
  const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
  const accentColor = UI_COLORS.accent();
  const accentAlpha = light ? 'rgba(41, 74, 96, 0.1)' : 'rgba(255, 152, 0, 0.1)';
  const cardBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.15)';

  const filtros_raw = data.filtros_aplicados || {};
  const filtroInfoHtml = data.filtro_nombre ? `
    <div class="alert alert-info border-0 shadow-sm d-flex align-items-center mb-4 py-3" style="background: ${accentAlpha} !important; border-left: 4px solid ${accentColor} !important; backdrop-filter: blur(5px);">
        <i class="fa-solid fa-circle-info me-3 fs-4 text-info"></i>
        <div>
            <div class="small fw-bold text-uppercase opacity-75" style="letter-spacing: 1px;">Conjunto de Datos</div>
            <div class="fw-bold" style="color: ${textWhite};">${data.filtro_nombre}</div>
        </div>
    </div>
  ` : '';

  const iaInsightsHtml = (data.analisis_ia) ? `
    <div class="mb-5 p-4 rounded border border-warning border-opacity-20 animate__animated animate__fadeIn" style="background: rgba(255,152,0,0.05) !important;">
        <div class="d-flex align-items-center mb-3">
            <i class="fa-solid fa-sparkles text-warning me-2 fs-5"></i>
            <h5 class="mb-0 fw-bold text-warning" style="letter-spacing: 1px;">SÍNTESIS ESTRATÉGICA IA</h5>
        </div>
        <div class="markdown-content" style="color: ${textWhite}; line-height: 1.6;">
            ${marked.parse(data.analisis_ia)}
        </div>
    </div>
  ` : '';

  container.innerHTML = `
    <div class="p-0">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h3 class="text-accent mb-0"><i class="fa-solid fa-masks-theater me-2"></i>Laboratorio de Dramaturgia Computacional</h3>
            <div class="d-flex gap-2">
                <button class="btn btn-outline-warning btn-sm fw-bold px-3 d-flex align-items-center" onclick="refrescarAnalisisDramatico()" style="height: 36px; border-opacity: 0.3;">
                    <i class="fa-solid fa-arrows-rotate me-2"></i>RECALCULAR
                </button>
                <button class="btn btn-warning btn-sm fw-bold px-3 d-flex align-items-center" onclick="generarInformeDramaticoIA()" style="height: 36px; box-shadow: 0 4px 15px rgba(255,152,0,0.2);">
                    <i class="fa-solid fa-file-waveform me-2"></i>INFORME IA
                </button>
            </div>
        </div>
        
        ${filtroInfoHtml}
        ${iaInsightsHtml}
        <div id="ia-report-container"></div>

        <div class="row g-4 mb-5">

            <div class="col-lg-8">
                <div class="p-4 h-100 rounded border border-warning border-opacity-20" style="background: ${cardBg} !important; backdrop-filter: blur(10px); background: linear-gradient(to right, ${accentAlpha}, transparent) !important;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div style="flex: 1;">
                            <div class="small fw-bold mb-2" style="color: ${accentColor};"><i class="fa-solid fa-circle-info me-2"></i>Objetivo del Análisis</div>
                            <p class="small mb-0 opacity-75" style="line-height: 1.5; color: ${textMuted} !important;">
                                Sistema de interpretación diacrónica basado en la micro-segmentación de actos y escenas. 
                                Este módulo desglosa la jerarquía de poder discursivo, la red de influencias sociales y la trayectoria emocional de los personajes.
                            </p>
                            

                            <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top border-warning border-opacity-10 flex-wrap gap-3">
                                <div class="d-flex gap-4">
                                    <div>
                                        <div class="xsmall text-uppercase fw-bold opacity-50" style="font-size: 10px; color: ${textWhite} !important;">Personajes Activos</div>
                                        <div id="stat-drama-chars" class="fs-4 fw-bold text-accent" style="color: ${accentColor} !important;">-</div>
                                    </div>
                                    <div>
                                        <div class="xsmall text-uppercase fw-bold opacity-50" style="font-size: 10px; color: ${textWhite} !important;">Segmentos Analizados</div>
                                        <div id="stat-drama-segments" class="fs-4 fw-bold text-accent" style="color: ${accentColor} !important;">-</div>
                                    </div>
                                    <div>
                                        <div class="xsmall text-uppercase fw-bold opacity-50" style="font-size: 10px; color: ${textWhite} !important;">Volumen Discursivo</div>
                                        <div id="stat-drama-words" class="fs-4 fw-bold text-accent" style="color: ${accentColor} !important;">-</div>
                                    </div>
                                </div>
                                

                                <!-- Panel de Biografía y Datos del Autor / Estreno (a la derecha) -->
                                <div id="author-bio-container" style="display: none; flex: 1;" class="animate__animated animate__fadeIn ms-3"></div>

                            </div>

                        </div>
                        <div class="ms-3">
                            <button class="btn btn-sm fw-bold px-3" onclick="openAliasManager()" title="Unificar personajes" style="background: ${accentColor}; color: ${light ? '#fff' : '#000'};">
                               <i class="fa-solid fa-users-gear me-2"></i>Gestor Identidades
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="p-4 h-100 rounded border border-secondary border-opacity-20 bg-dark bg-opacity-25" style="backdrop-filter: blur(10px);">
                    <div class="small fw-bold mb-3 text-uppercase opacity-75" style="letter-spacing: 1px; color: ${textWhite} !important;">
                        <i class="fa-solid fa-sliders me-2"></i>Segmentación Dramática
                    </div>
                    
                    <div class="mb-3">
                        <label class="xsmall text-uppercase fw-bold opacity-50 d-block mb-1" style="font-size: 9px; color: ${textWhite} !important;">Obra / Publicación</label>
                        <select id="filtro-obra" class="form-select form-select-sm bg-dark text-white border-secondary border-opacity-25">
                            <option value="">(Todas las publicaciones)</option>
                        </select>
                    </div>

                    <div class="row g-2">
                        <div class="col-6">
                            <label class="xsmall text-uppercase fw-bold opacity-50 d-block mb-1" style="font-size: 9px; color: ${textWhite} !important;">Acto</label>
                            <select id="filtro-acto" class="form-select form-select-sm bg-dark text-white border-secondary border-opacity-25">
                                <option value="all">Todos</option>
                            </select>
                        </div>
                        <div class="col-6">
                            <label class="xsmall text-uppercase fw-bold opacity-50 d-block mb-1" style="font-size: 9px; color: ${textWhite} !important;">Escena</label>
                            <select id="filtro-escena" class="form-select form-select-sm bg-dark text-white border-secondary border-opacity-25">
                                <option value="all">Todas</option>
                            </select>
                        </div>
                    </div>
                    <p class="xsmall text-muted mt-2 mb-0" style="font-size: 10px;"><i class="fa-solid fa-circle-info me-1"></i> Filtra la cronología y redes del análisis.</p>
                </div>
            </div>
        </div>

        <div id="drama-main-content">
            <!-- Row 1: Network & Protagonismo -->
            <div class="row g-4 mb-4">
                <div class="col-lg-7">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10 h-100">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Red de Influencia de Personajes
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('interacciones', 'network')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div id="drama-network" style="height: 500px; width: 100%;"></div>
                        <div id="ai-res-network" class="mt-3" style="display:none"></div>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10 h-100">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Protagonismo Discursivo
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('protagonismo', 'protagonismo')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div style="height: 400px; position: relative;"><canvas id="chart-drama-protagonismo"></canvas></div>
                        <div id="ai-res-protagonismo" class="mt-3" style="display:none"></div>
                    </div>
                </div>
            </div>

            <!-- Row 2: Detailed Stats Table -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="p-4 rounded bg-dark border border-secondary border-opacity-10">
                        <h5 class="fw-bold text-uppercase mb-4" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                            <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Análisis Lexicométrico del Reparto
                        </h5>
                        <div class="table-responsive">
                            <table class="table table-dark table-hover mb-0" style="--bs-table-bg: transparent;">
                                <thead>
                                    <tr class="text-secondary small text-uppercase" style="border-bottom: 2px solid rgba(255,255,255,0.1);">
                                        <th class="py-3">Personaje</th>
                                        <th class="text-center">Intervenciones</th>
                                        <th class="text-center">Palabras/Int.</th>
                                        <th>Campos Semánticos Dominantes</th>
                                        <th>Locuciones Clave</th>
                                    </tr>
                                </thead>
                                <tbody id="drama-table-body"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            
            <!-- Row NEW: Tactical Analysis -->
            <div class="row g-4 mb-4">
                <div class="col-lg-12">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-warning border-opacity-10">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; color: ${textWhite} !important;">
                                <i class="fa-solid fa-fire-glow me-2 text-warning"></i> Evolución del Flujo Táctico (Streamgraph)
                            </h5>
                            <button class="btn btn-xs btn-outline-warning" style="font-size: 9px;" onclick="interpretarSeccionDramatica('tactica_flujo', 'tactica-stream')">DECONSTRUIR TÁCTICAS</button>
                        </div>
                        <div id="drama-tactical-stream" style="height: 350px; width: 100%;"></div>
                        <div id="ai-res-tactica-stream" class="mt-3" style="display:none"></div>
                        <p class="xsmall text-muted mt-3 mb-0">Distribución de intenciones comunicativas (Atacar, Persuadir, Seducir, etc.) a lo largo de la obra.</p>
                    </div>
                </div>
            </div>

            <div class="row g-4 mb-4">
                <div class="col-12">
                    <div class="p-4 rounded bg-dark border border-secondary border-opacity-10">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; color: ${textWhite} !important;">
                                <i class="fa-solid fa-bullseye me-2 text-warning"></i> Perfiles Tácticos del Reparto (Radar)
                            </h5>
                            <div class="d-flex gap-2">
                                <span class="badge bg-opacity-10 text-danger border border-danger border-opacity-25" style="font-size: 8px;">A: ATACAR</span>
                                <span class="badge bg-opacity-10 text-info border border-info border-opacity-25" style="font-size: 8px;">P: PERSUADIR</span>
                                <span class="badge bg-opacity-10 text-success border border-success border-opacity-25" style="font-size: 8px;">S: SEDUCIR</span>
                                <span class="badge bg-opacity-10 text-warning border border-warning border-opacity-25" style="font-size: 8px;">M: MANIPULAR</span>
                                <span class="badge bg-opacity-10 text-secondary border border-secondary border-opacity-25" style="font-size: 8px;">I: INFORMAR</span>
                            </div>
                        </div>
                        <div id="radar-containers" class="row g-3">
                            <!-- Los radares se inyectarán aquí -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- Row 3: Heatmaps -->
            <div class="row g-4 mb-4">
                <div class="col-lg-6">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10 h-100">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Densidad de Interacción (Heatmap)
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('interacciones', 'heatmap')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div id="drama-heatmap-words" style="height: 350px; width: 100%;"></div>
                        <div id="ai-res-heatmap" class="mt-3" style="display:none"></div>
                    </div>
                </div>
                <div class="col-lg-6">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10 h-100">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Matriz de Presencia Escénica
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('presencia', 'presencia')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div id="drama-presence-matrix" style="height: 350px; width: 100%;"></div>
                        <div id="ai-res-presencia" class="mt-3" style="display:none"></div>
                    </div>
                </div>
            </div>

            <!-- Row 4: Rhythm & Cronía -->
            <div class="row g-4 mb-4">
                <div class="col-12">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Ritmo Dramático y Cronía Antropológica
                            </h5>
                             <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('ritmo', 'ritmo')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div style="height: 350px; position: relative;"><canvas id="drama-rhythm-sync"></canvas></div>
                        <div id="ai-res-ritmo" class="mt-3" style="display:none"></div>
                        <p class="xsmall text-muted mt-3 mb-0">Correlación entre la velocidad de diálogos y el sentimiento de las acotaciones del autor.</p>
                    </div>
                </div>
            </div>

            <!-- Row 5: Interaction Function & Emotional Sync -->
            <div class="row g-4 mb-4">
                <div class="col-lg-7">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10 h-100">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Convergencia de la Tensión Dramática
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('tension', 'tension')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div style="height: 350px; position: relative;"><canvas id="drama-tension-convergence"></canvas></div>
                        <div id="ai-res-tension" class="mt-3" style="display:none"></div>
                        <p class="xsmall text-muted mt-3 mb-0">Evolución emocional de la obra bloque a bloque.</p>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10 h-100">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Sincronía Emocional (Entrainment)
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('sincronia', 'sincronia')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div id="heatmap-sincronia" style="height: 250px; width: 100%;"></div>
                        <div id="sync-list" class="mt-3"></div>
                        <div id="ai-res-sincronia" class="mt-3" style="display:none"></div>
                        <p class="xsmall text-muted mt-3 mb-0">Parejas de personajes con mayor correlación afectiva en escena.</p>
                    </div>
                </div>
            </div>

            <!-- Row 6: Individual Trajectories -->
            <div class="row g-4 mb-4">
                <div class="col-12">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Trayectoria Emocional por Personaje
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('trayectoria', 'trayectoria')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div style="height: 450px; position: relative;"><canvas id="drama-individual-trajectories"></canvas></div>
                        <div id="ai-res-trayectoria" class="mt-3" style="display:none"></div>
                        <p class="xsmall text-muted mt-3 mb-0">Evolución del sentimiento individual para los protagonistas más relevantes.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Detail Panel (Fixed/Floating) -->
        <div id="drama-block-detail" class="glass-panel p-4 shadow-lg border border-warning" style="display: none; position: fixed; top: 100px; right: 20px; width: 400px; max-height: 80vh; overflow-y: auto; z-index: 1050; background: rgba(15, 15, 15, 0.95) !important; backdrop-filter: blur(15px);">
            <div class="d-flex justify-content-between align-items-center mb-3 border-bottom border-warning border-opacity-20 pb-2">
                <a id="drama-reader-btn" href="#" target="_blank" class="text-warning text-decoration-none fw-bold" style="font-size: 11px; letter-spacing: 0.5px;">
                    <i class="fa-solid fa-book-open me-2"></i>ABRIR EN LECTOR
                </a>
                <div class="d-flex align-items-center gap-3">
                    <h6 class="text-warning fw-bold mb-0 text-uppercase opacity-50" id="drama-block-title" style="font-size: 10px;"></h6>
                    <button class="btn btn-sm btn-link text-muted p-0" onclick="document.getElementById('drama-block-detail').style.display='none'"><i class="fa-solid fa-xmark"></i></button>
                </div>
            </div>
            <div id="drama-block-text" style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--ds-text-main); line-height: 1.6; white-space: pre-wrap;"></div>
        </div>
    </div>
  `;

  const temp = (data.sentimiento_temporal || []);

  const safeUpdateSelect = (id, optionsHtml, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    
    if (window.choicesInstances && window.choicesInstances[id]) {
      window.choicesInstances[id].destroy();
      delete window.choicesInstances[id];
    }
    
    el.innerHTML = optionsHtml;
    if (value !== undefined) el.value = value;
    
    if (typeof Choices !== 'undefined') {
       window.choicesInstances = window.choicesInstances || {};
       const c = new Choices(el, {
          searchEnabled: true,
          itemSelectText: '',
          shouldSort: false,
          removeItemButton: false,
          allowHTML: true
       });
       window.choicesInstances[id] = c;
       
       el.addEventListener('change', () => {
          if (id === 'filtro-obra') { updateActosEscenas(); window.filterDramaticoCharts(); }
          else window.filterDramaticoCharts();
       });
       
       el.addEventListener('choice', () => {
          setTimeout(() => {
              if (id === 'filtro-obra') { updateActosEscenas(); window.filterDramaticoCharts(); }
              else window.filterDramaticoCharts();
          }, 50);
       });
    }
  };

  const smartSort = (a, b) => {
    const romanToInt = (s) => {
        if (!s || typeof s !== 'string') return 0;
        const romVal = { 'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000 };
        let res = 0;
        for (let i = 0; i < s.length; i++) {
            if (romVal[s[i]] < romVal[s[i+1]]) res -= romVal[s[i]];
            else res += romVal[s[i]];
        }
        return res;
    };
    const valA = romanToInt(a) || parseInt(a) || 0;
    const valB = romanToInt(b) || parseInt(b) || 0;
    return valA - valB;
  };


  // Mapear obras para acceso rápido
  const mapObras = {};
  temp.forEach(s => { 
    if (s.publicacion_id && s.titulo_obra) {
      mapObras[s.publicacion_id] = String(s.titulo_obra).trim(); 
    } 
  });

  const updateActosEscenas = () => {
    const obraId = document.getElementById('filtro-obra').value;
    const isAll = obraId === '' || obraId === 'all';
    const filtered = isAll ? temp : temp.filter(s => String(s.publicacion_id) === String(obraId));
    
    // Inyección de biografía del autor
    const bioContainer = document.getElementById('author-bio-container');
    if (bioContainer) {
        if (isAll) {
            bioContainer.style.display = 'none';
            bioContainer.innerHTML = '';
        } else {
            const obraNombre = mapObras[obraId];
            if (obraNombre) {
                fetch('/api/analisis/dramatico/autor', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                    },
                    body: JSON.stringify({ obra: obraNombre })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.exito) {
                        const fotoSrc = data.foto ? data.foto : '';
                        const bioHtml = `

                            <div class="d-flex gap-3 align-items-center p-2 rounded bg-dark bg-opacity-25 border border-secondary border-opacity-10 animate__animated animate__fadeIn" style="width: 100%;">
                                ${fotoSrc ? `<img src="${fotoSrc}" class="rounded-circle border border-warning" style="width: 55px; height: 55px; object-fit: cover;" alt="${data.nombre_autor}">` : `<div class="rounded-circle border border-secondary border-opacity-25 d-flex align-items-center justify-content-center bg-dark bg-opacity-50" style="width: 55px; height: 55px; color: ${accentColor}; font-size: 18px;"><i class="fa-solid fa-user-pen"></i></div>`}
                                <div style="flex: 1;">
                                    <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-1">
                                        <h6 class="mb-0 text-warning fw-bold" style="font-size: 0.85rem;"><i class="fa-solid fa-feather-pointed text-warning me-2" style="font-size: 0.75rem;"></i>${data.nombre_autor}</h6>
                                        <div class="d-flex gap-1">
                                            ${data.fecha_estreno ? `<span class="badge bg-dark bg-opacity-75 border border-warning border-opacity-20 text-warning" style="font-size: 8px; padding: 2px 4px;"><i class="fa-solid fa-calendar-days me-1"></i>${data.fecha_estreno}</span>` : ''}
                                            ${data.teatro_estreno ? `<span class="badge bg-dark bg-opacity-75 border border-warning border-opacity-20 text-warning" style="font-size: 8px; padding: 2px 4px;"><i class="fa-solid fa-masks-theater me-1"></i>${data.teatro_estreno}</span>` : ''}
                                        </div>
                                    </div>
                                    <p class="small text-muted mb-0" style="line-height: 1.3; font-size: 11px;">${data.biografia || 'Biografía no registrada.'}</p>
                                </div>


                            </div>
                        `;
                        bioContainer.innerHTML = bioHtml;
                        bioContainer.style.display = 'block';
                    }
                })
                .catch(err => console.error('Error al recuperar información del autor:', err));
            }
        }
    }
    
    const actosUnicos = [...new Set(filtered.map(s => s.acto).filter(a => a && a !== 'None' && a !== ''))].sort(smartSort);
    const escenasUnicas = [...new Set(filtered.map(s => s.escena).filter(e => e && e !== 'None' && e !== ''))].sort(smartSort);

    const prevActo = document.getElementById('filtro-acto')?.value || 'all';
    const prevEscena = document.getElementById('filtro-escena')?.value || 'all';

    let actoHtml = '<option value="all">Todos</option>';
    actosUnicos.forEach(a => { actoHtml += `<option value="${a}">Acto ${a}</option>`; });
    const targetActo = [...actosUnicos].some(a => String(a) === String(prevActo)) ? prevActo : 'all';
    safeUpdateSelect('filtro-acto', actoHtml, targetActo);

    let escenaHtml = '<option value="all">Todas</option>';
    escenasUnicas.forEach(e => { escenaHtml += `<option value="${e}">Escena ${e}</option>`; });
    const targetEscena = [...escenasUnicas].some(e => String(e) === String(prevEscena)) ? prevEscena : 'all';
    safeUpdateSelect('filtro-escena', escenaHtml, targetEscena);
  };

  let obraHtml = '<option value="">(Todas las publicaciones)</option>';
  Object.entries(mapObras).sort((a,b) => a[1].localeCompare(b[1])).forEach(([id, nombre]) => {
    obraHtml += `<option value="${id}">${nombre}</option>`;
  });


  const initialObra = '';
  safeUpdateSelect('filtro-obra', obraHtml, initialObra);
  
  updateActosEscenas();
  window.renderDramaticoFull(data, 'all', 'all', initialObra);
}

window.generarInformeDramaticoIA = function() {
    const container = document.getElementById('ia-report-container');
    if (!container) return;

    // UX: Asegurar visibilidad del contenedor y Loading
    container.style.display = 'block';
    container.innerHTML = `
        <div class="glass-panel p-4 mb-4 border-warning border-opacity-25" style="background: rgba(255,152,0,0.05);">
            <div class="d-flex align-items-center">
                <div class="spinner-border spinner-border-sm me-3 text-warning" role="status"></div>
                <div class="fw-bold small" style="letter-spacing: 1px; color: var(--ds-text-main);">GENERANDO INFORME NARRATOLÓGICO CON IA...</div>
            </div>
            <div class="mt-2 small opacity-75" style="color: var(--ds-text-main);">Esto puede tardar unos segundos mientras Gemini analiza los actos y personajes.</div>
        </div>
    `;

    const filtros = getFiltrosActuales();
    const dramaObraEl = document.getElementById('filtro-obra');
    if (dramaObraEl && dramaObraEl.value) {
        filtros.publicacion_id = parseInt(dramaObraEl.value);
    } else {
        filtros.publicacion_id = null;
    }
    const projectKey = `aliases_${filtros.proyecto_id || 'default'}`;
    const manual_aliases = JSON.parse(localStorage.getItem(projectKey) || '{}');

    fetch('/api/analisis/dramatico', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify({
            ...filtros,
            manual_aliases: manual_aliases,
            generar_ia: true,
            modelo: window._ia_modelo || 'flash'
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.analisis_ia) {
            const isLight = UI_COLORS.isLight();
            const textColor = isLight ? '#212121' : '#fff';
            const formatted = (typeof marked !== 'undefined') ? marked.parse(data.analisis_ia) : data.analisis_ia.replace(/\n/g, '<br>');
            
            container.innerHTML = `
                <div class="p-4 mb-4 animate__animated animate__fadeIn border border-warning border-opacity-20 rounded" 
                     style="background-color: ${isLight ? '#ffffff' : '#000000'} !important;">
                    <div class="text-warning mb-3 small fw-bold" style="letter-spacing: 1px;">
                        <i class="fa-solid fa-wand-magic-sparkles me-2"></i>INTERPRETACIÓN NARRATOLÓGICA (IA)
                    </div>
                    <div class="ai-report-content" style="color: ${textColor}; line-height: 1.7; font-size: 0.85rem;">
                        ${formatted}
                    </div>
                </div>
            `;
        } else {
            container.innerHTML = `<div class="alert alert-danger p-3 small">${data.error || 'No se pudo generar el informe.'}</div>`;
        }
    })
    .catch(err => {
        container.innerHTML = `<div class="alert alert-danger p-3 small">Error de servidor al generar informe.</div>`;
    });
};

window.refrescarAnalisisDramatico = function() {
    // Mostrar loader global en el contenedor de vista
    const container = document.getElementById('view-dramatico');
    if (!container) return;
    
    container.innerHTML = `
        <div class="d-flex flex-column align-items-center justify-content-center" style="min-height: 400px; color: var(--ds-text-main);">
            <div class="spinner-border text-warning mb-3" style="width: 3rem; height: 3rem;" role="status"></div>
            <h5 class="fw-bold animate__animated animate__pulse animate__infinite" style="color: var(--ds-accent-primary);">RECALCULANDO ANÁLISIS DRAMÁTICO...</h5>
            <p class="small opacity-75">Ignorando caché y re-procesando diálogos para actualizar estadísticas.</p>
        </div>
    `;

    const filtros = getFiltrosActuales();
    const projectKey = `aliases_${filtros.proyecto_id || 'default'}`;
    const manual_aliases = JSON.parse(localStorage.getItem(projectKey) || '{}');

    fetch('/api/analisis/dramatico', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
        },
        body: JSON.stringify({
            ...filtros, publicacion_id: null,
            manual_aliases: manual_aliases,
            refresh: true // Forzamos bypass de caché en backend
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.exito !== false) {
            datosActuales['dramatico'] = data;
            loadDramatico(data);
        } else {
            mostrarError(container, data.error || 'Error al recalcular datos.');
        }
    })
    .catch(err => {
        mostrarError(container, 'Error de servidor al recalcular.');
    });
};

/**
 * Filtra dinámicamente las gráficas de tensión y sentimiento por acto/escena
 */
window.filterDramaticoCharts = function() {
    const data = datosActuales['dramatico'];
    if (!data) return;
    
    const obraEl = document.getElementById('filtro-obra');
    const actoEl = document.getElementById('filtro-acto');
    const escenaEl = document.getElementById('filtro-escena');
    
    if (!obraEl || !actoEl || !escenaEl) return;
    
    const obraSel = obraEl.value;
    const actoSel = actoEl.value;
    const escenaSel = escenaEl.value;
    
    console.log(`[DRAMA] Aplicando filtros: Obra=${obraSel}, Acto=${actoSel}, Escena=${escenaSel}`);
    
    // Forzar limpieza de contenedores antes de re-renderizar para evitar duplicados visuales
    // (Aunque renderDramaticoFull ya hace destroy() en Chart.js, esto ayuda con Vega y Vis.js)
    window.renderDramaticoFull(data, actoSel, escenaSel, obraSel);
}

window.interpretarSeccionDramatica = function(tipo, targetId) {
    const resDiv = document.getElementById(`ai-res-${targetId}`);
    if (!resDiv) {
        console.error(`Contenedor no encontrado: ai-res-${targetId}`);
        return;
    }

    resDiv.style.display = 'block';
    resDiv.innerHTML = `
        <div class="d-flex align-items-center p-2 rounded" style="background: rgba(255,152,0,0.1); border: 1px dashed rgba(255,152,0,0.3);">
            <div class="spinner-border spinner-border-sm text-warning me-2"></div>
            <span class="xsmall text-warning fw-bold" style="font-size: 10px;">SOLICITANDO INTERPRETACIÓN IA...</span>
        </div>
    `;

    const filtros = getFiltrosActuales();
    const dramaObraEl = document.getElementById('filtro-obra');
    if (dramaObraEl && dramaObraEl.value) {
        filtros.publicacion_id = parseInt(dramaObraEl.value);
    } else {
        filtros.publicacion_id = null;
    }
    const chartData = datosActuales['dramatico'];

    fetch('/api/analisis/dramatico/interpretar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
        },
        body: JSON.stringify({
            seccion: tipo,
            chart_data: chartData,
            ...filtros,
            modelo: window._ia_modelo || 'flash'
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.interpretacion) {
            const isLight = UI_COLORS.isLight();
            const formatted = (typeof marked !== 'undefined') ? marked.parse(data.interpretacion) : data.interpretacion.replace(/\n/g, '<br>');
            resDiv.innerHTML = `
                <div class="p-3 rounded border border-warning border-opacity-20 animate__animated animate__fadeIn" 
                     style="background: ${isLight ? 'rgba(255,152,0,0.05)' : 'rgba(0,0,0,0.3)'};">
                    <div class="markdown-content small" style="color: ${isLight ? '#333' : '#eee'}; line-height: 1.5; font-size: 0.8rem;">
                        ${formatted}
                    </div>
                    <div class="text-end mt-2">
                        <button class="btn btn-link btn-xs text-muted p-0 text-decoration-none" onclick="document.getElementById('ai-res-${targetId}').style.display='none'"><i class="fa-solid fa-eye-slash me-1"></i>Ocultar</button>
                    </div>
                </div>
            `;
        } else {
            resDiv.innerHTML = `<div class="alert alert-danger py-2 xsmall">${data.error || 'Error en interpretación'}</div>`;
        }
    })
    .catch(err => {
        console.error(err);
        resDiv.innerHTML = `<div class="alert alert-danger py-2 xsmall">Error de conexión con el servidor.</div>`;
    });
};

/* --- GESTOR DE ALIAS / IDENTIDADES --- */
window.openAliasManager = function() {
  const data = datosActuales['dramatico'];
  if (!data) {
     alert('Primero debes realizar un Análisis Dramático para detectar personajes.');
     return;
  }
  
  const modalEl = document.getElementById('modalAlias');
  if (!modalEl) return;
  
  const modal = new bootstrap.Modal(modalEl);
  const tableBody = document.getElementById('alias-table-body');
  
  // Cargamos alias actuales
  const projectKey = `aliases_${filtros.proyecto_id || 'default'}`;
  const currentAliases = JSON.parse(localStorage.getItem(projectKey) || '{}');
  
  // Cargamos personajes ignorados y eliminados
  const ignoreKey = `ignored_${filtros.proyecto_id || 'default'}`;
  const ignoredChars = JSON.parse(localStorage.getItem(ignoreKey) || '[]');
  const deleteKey = `deleted_${filtros.proyecto_id || 'default'}`;
  const deletedChars = JSON.parse(localStorage.getItem(deleteKey) || '[]');
  
  // Extraer nombres de personajes (ID) de los nodos, excluyendo los eliminados
  const personajes = (data.nodos || []).map(n => n.id).filter(p => !deletedChars.includes(p)).sort();
  
  tableBody.innerHTML = personajes.map(p => {
    const canonical = currentAliases[p] || '';
    const isIgnored = ignoredChars.includes(p);
    return `
      <tr data-row-char="${p}" class="${isIgnored ? 'opacity-50' : ''}">
        <td class="text-info small fw-bold">
           ${p}
           ${isIgnored ? '<span class="badge bg-danger ms-2" style="font-size: 8px;">OCULTO</span>' : ''}
        </td>
        <td class="text-center text-muted"><i class="fa-solid fa-arrow-right-long small"></i></td>
        <td>
          <input type="text" class="form-control form-control-sm bg-dark text-light border-secondary border-opacity-50 alias-input" 
                 data-original="${p}" value="${canonical}" placeholder="Nombre unificado (opcional)"
                 style="background: rgba(255,255,255,0.05) !important;">
        </td>
        <td class="text-center">
            <div class="form-check form-switch d-inline-block">
                <input class="form-check-input ignore-checkbox" type="checkbox" role="switch" 
                       data-personaje="${p}" ${isIgnored ? 'checked' : ''} title="Ocultar de la tabla y gráficos">
            </div>
        </td>
        <td class="text-center">
            <button type="button" class="btn btn-sm btn-outline-danger border-0 py-0" onclick="window.deleteCharacterPermanently('${p.replace(/'/g, "\\'")}')" title="Eliminar permanentemente">
                <i class="fa-solid fa-trash-can"></i>
            </button>
        </td>
      </tr>
    `;
  }).join('');
  
  modal.show();
};

window.saveAndApplyAliases = function() {
  const inputs = document.querySelectorAll('.alias-input');
  
  const projectKey = `aliases_${filtros.proyecto_id || 'default'}`;
  const existingAliases = JSON.parse(localStorage.getItem(projectKey) || '{}');
  const newAliases = { ...existingAliases };
  
  inputs.forEach(input => {
    const val = input.value.trim().toUpperCase();
    if (val && val !== input.dataset.original.toUpperCase()) {
      newAliases[input.dataset.original] = val;
    } else {
      delete newAliases[input.dataset.original];
    }
  });
  
  const ignoreKey = `ignored_${filtros.proyecto_id || 'default'}`;
  const existingIgnored = JSON.parse(localStorage.getItem(ignoreKey) || '[]');
  const currentModalCharacters = new Set();
  
  document.querySelectorAll('.ignore-checkbox').forEach(cb => {
    currentModalCharacters.add(cb.dataset.personaje);
  });
  
  // Mantener los personajes ignorados existentes que NO estaban en el modal
  const newIgnored = existingIgnored.filter(p => !currentModalCharacters.has(p));
  // Añadir los del modal que SÍ están marcados
  document.querySelectorAll('.ignore-checkbox').forEach(cb => {
    if (cb.checked) {
      newIgnored.push(cb.dataset.personaje);
    }
  });
  
  localStorage.setItem(projectKey, JSON.stringify(newAliases));
  localStorage.setItem(ignoreKey, JSON.stringify(newIgnored));
  
  const modalInstance = bootstrap.Modal.getInstance(document.getElementById('modalAlias'));
  if (modalInstance) modalInstance.hide();
  
  // Forzar recarga del análisis dramático
  const loader = document.getElementById('loading-state');
  if (loader) loader.style.display = 'flex';
  cargarAnalisis('dramatico');
};

window.deleteCharacterPermanently = function(personaje) {
    if (!confirm(`¿Estás seguro de que deseas eliminar a "${personaje}" de forma permanente? No aparecerá en gráficos ni listas.`)) {
        return;
    }
    const deleteKey = `deleted_${filtros.proyecto_id || 'default'}`;
    const deletedChars = JSON.parse(localStorage.getItem(deleteKey) || '[]');
    if (!deletedChars.includes(personaje)) {
        deletedChars.push(personaje);
        localStorage.setItem(deleteKey, JSON.stringify(deletedChars));
    }
    
    // Ocultar la fila visualmente usando CSS.escape para evitar fallos por caracteres especiales
    const row = document.querySelector(`tr[data-row-char="${CSS.escape(personaje)}"]`);
    if (row) {
        row.style.transition = 'all 0.3s';
        row.style.opacity = '0';
        row.style.transform = 'translateX(20px)';
        setTimeout(() => row.remove(), 300);
    }
};

window.resetAliases = function() {
  if (confirm('¿Estás seguro de que deseas borrar todas las unificaciones personalizadas para este proyecto?')) {
    const projectKey = `aliases_${filtros.proyecto_id || 'default'}`;
    const ignoreKey = `ignored_${filtros.proyecto_id || 'default'}`;
    const deleteKey = `deleted_${filtros.proyecto_id || 'default'}`;
    localStorage.removeItem(projectKey);
    localStorage.removeItem(ignoreKey);
    localStorage.removeItem(deleteKey);
    
    // Limpiar inputs visualmente
    document.querySelectorAll('.alias-input').forEach(input => input.value = '');
    document.querySelectorAll('.ignore-checkbox').forEach(cb => cb.checked = false);
  }
};

/* --- ANÁLISIS DE SUBTEXTO E INTENCIONALIDAD AI --- */

window.analizarSubtexto = function() {
    const empty = document.getElementById('subtexto-empty');
    const results = document.getElementById('subtexto-resultados');
    const grid = document.getElementById('subtexto-personajes-grid');
    
    if (empty) empty.style.display = 'none';
    if (results) results.style.display = 'block';
    
    grid.innerHTML = `
        <div class="col-12 text-center py-5">
            <div class="spinner-border text-accent mb-3" style="color: #9b59b6 !important;"></div>
            <p class="text-muted animate__animated animate__pulse animate__infinite">La IA está deconstruyendo el subtexto de la obra...</p>
        </div>
    `;

    const filtrosActuales = getFiltrosActuales();
    const dramaObraEl = document.getElementById('filtro-obra');
    if (dramaObraEl && dramaObraEl.value) {
        filtrosActuales.publicacion_id = parseInt(dramaObraEl.value);
    } else {
        filtrosActuales.publicacion_id = null;
    }
    const projectKey = `aliases_${filtrosActuales.proyecto_id || 'default'}`;
    const manual_aliases = JSON.parse(localStorage.getItem(projectKey) || '{}');

    fetch('/api/analisis/dramatico/subtexto', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
        },
        body: JSON.stringify({
            ...filtrosActuales,
            manual_aliases: manual_aliases,
            modelo: window._ia_modelo || 'pro'
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.exito) {
            datosActuales['subtexto'] = data.analisis;
            renderSubtexto(data.analisis);
        } else {
            grid.innerHTML = `<div class="alert alert-danger w-100">${data.error || 'Error al analizar subtexto.'}</div>`;
        }
    })
    .catch(err => {
        grid.innerHTML = `<div class="alert alert-danger w-100">Error de conexión con el servidor.</div>`;
    });
};

window.renderSubtexto = function(data) {
    if (!data) return;
    
    const results = document.getElementById('subtexto-resultados');
    const empty = document.getElementById('subtexto-empty');
    if (results) results.style.display = 'block';
    if (empty) empty.style.display = 'none';

    // Renderizar Clima y Conflicto
    const clima = document.getElementById('subtexto-clima');
    const conflicto = document.getElementById('subtexto-conflicto');
    
    if (clima) clima.innerHTML = `<i class="fa-solid fa-cloud-sun me-2" style="color: #9b59b6;"></i> <strong>Clima Escénico:</strong> ${data.clima_escenico}`;
    if (conflicto) conflicto.innerHTML = `<p><strong>Conflicto Dominante:</strong></p>${data.conflicto_dominante}`;

    // Renderizar Grid de Personajes
    const grid = document.getElementById('subtexto-personajes-grid');
    if (grid) {
        grid.innerHTML = '';
        Object.entries(data.personajes || {}).forEach(([nombre, info], idx) => {
            const charId = `chart-subtexto-radar-${idx}`;
            const card = document.createElement('div');
            card.className = 'col-md-6';
            card.innerHTML = `
                <div class="glass-panel p-3 h-100" style="background: rgba(255,255,255,0.03);">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="text-accent small fw-bold m-0" style="color: #9b59b6 !important;">${nombre}</h6>
                        <span class="badge bg-dark border border-secondary border-opacity-20" style="font-size: 9px;">ARQUETIPO AI</span>
                    </div>
                    <div style="height: 200px;">
                        <canvas id="${charId}"></canvas>
                    </div>
                    <div class="mt-3 small text-muted" style="font-size: 11px; line-height: 1.4;">
                        <p class="mb-1 text-light"><strong>Meta:</strong> ${info.resumen_estrategico}</p>
                        <p class="mb-0 italic opacity-75">"${info.evolucion}"</p>
                    </div>
                </div>
            `;
            grid.appendChild(card);

            // Crear Radar Chart para este personaje
            setTimeout(() => {
                const ctx = document.getElementById(charId);
                if (ctx) {
                    const tacticasLabels = Object.keys(info.tacticas || {});
                    const tacticasValues = Object.values(info.tacticas || {});
                    
                    new Chart(ctx, {
                        type: 'radar',
                        data: {
                            labels: tacticasLabels,
                            datasets: [{
                                data: tacticasValues,
                                backgroundColor: 'rgba(155, 89, 182, 0.2)',
                                borderColor: '#9b59b6',
                                borderWidth: 2,
                                pointRadius: 2
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: false } },
                            scales: {
                                r: {
                                    grid: { color: 'rgba(255,255,255,0.05)' },
                                    angleLines: { color: 'rgba(255,255,255,0.05)' },
                                    pointLabels: { color: 'rgba(255,255,255,0.5)', font: { size: 8 } },
                                    ticks: { display: false, backdropColor: 'transparent' }
                                }
                            }
                        }
                    });
                }
            }, 100);
        });
    }

    // Renderizar gráfico de barras de Dominancia Táctica (Opcional/Extra)
    const evolutionContainer = document.getElementById('chart-subtexto-evolution');
    if (evolutionContainer) {
        if (data.streamgraph_spec) {
            // Usar Vega-Lite para el Streamgraph
            const spec = typeof data.streamgraph_spec === 'string' ? JSON.parse(data.streamgraph_spec) : data.streamgraph_spec;
            const patchedSpec = patchVegaTheme(spec, UI_COLORS.isLight() ? 'light' : 'dark');
            vegaEmbed('#chart-subtexto-evolution', patchedSpec, {actions: false});
        } else {
            // Fallback a barras si no hay spec
            evolutionContainer.innerHTML = '<canvas id="chart-subtexto-global-bar"></canvas>';
            const ctxGlobal = document.getElementById('chart-subtexto-global-bar');
            
            const globales = {};
            Object.values(data.personajes || {}).forEach(p => {
                Object.entries(p.tacticas || {}).forEach(([t, v]) => {
                    globales[t] = (globales[t] || 0) + v;
                });
            });

            new Chart(ctxGlobal, {
                type: 'bar',
                data: {
                    labels: Object.keys(globales),
                    datasets: [{
                        label: 'Peso Táctico Global',
                        data: Object.values(globales),
                        backgroundColor: 'rgba(155, 89, 182, 0.4)',
                        borderColor: '#9b59b6',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#666' } },
                        x: { grid: { display: false }, ticks: { color: '#888', font: { size: 9 } } }
                    }
                }
            });
        }
    }
};

function renderAtribucion(data) {
  const deltaBody = document.getElementById('atribucion-delta-body');
  const vocabList = document.getElementById('atribucion-vocab-list');
  const ctxRadar = document.getElementById('chart-atribucion-radar');

  if (!data || !data.exito) {
    if (deltaBody) deltaBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">${data.error || 'Error al cargar datos'}</td></tr>`;
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

  // 3. Gráfico Radar
  if (chartsInstances['atribucion-radar']) {
    chartsInstances['atribucion-radar'].destroy();
  }

  if (ctxRadar && data.metricas_comparativas && data.metricas_comparativas.length > 0) {
    const labels = [
      'Riqueza Léxica',
      'Palabras/Oración',
      'Longitud Palabra',
      'Puntuación (%)',
      'Pronombres (%)'
    ];

    const colors = [
      { border: 'rgba(255, 152, 0, 0.8)', bg: 'rgba(255, 152, 0, 0.1)' },
      { border: 'rgba(3, 169, 244, 0.8)', bg: 'rgba(3, 169, 244, 0.1)' },
      { border: 'rgba(233, 30, 99, 0.8)', bg: 'rgba(233, 30, 99, 0.1)' },
      { border: 'rgba(76, 175, 80, 0.8)', bg: 'rgba(76, 175, 80, 0.1)' }
    ];

    const maxVals = { ttr: 0, ppo: 0, lp: 0, punt: 0, pron: 0 };
    data.metricas_comparativas.forEach(doc => {
      const m = doc.metricas;
      maxVals.ttr = Math.max(maxVals.ttr, m.diversidad_lexica || 0.001);
      maxVals.ppo = Math.max(maxVals.ppo, m.palabras_por_oracion || 0.001);
      maxVals.lp = Math.max(maxVals.lp, m.longitud_promedio_palabra || 0.001);
      maxVals.punt = Math.max(maxVals.punt, m.densidad_puntuacion || 0.001);
      maxVals.pron = Math.max(maxVals.pron, m.ratio_pronombres || 0.001);
    });

    const datasets = data.metricas_comparativas.slice(0, 4).map((doc, idx) => {
      const m = doc.metricas;
      const color = colors[idx % colors.length];

      const dataValues = [
        ((m.diversidad_lexica || 0) / maxVals.ttr) * 100,
        ((m.palabras_por_oracion || 0) / maxVals.ppo) * 100,
        ((m.longitud_promedio_palabra || 0) / maxVals.lp) * 100,
        ((m.densidad_puntuacion || 0) / maxVals.punt) * 100,
        ((m.ratio_pronombres || 0) / maxVals.pron) * 100
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
            angleLines: { color: 'rgba(255,255,255,0.05)' },
            grid: { color: 'rgba(255,255,255,0.05)' },
            pointLabels: { color: 'rgba(255,255,255,0.7)', font: { size: 10 } },
            ticks: { display: false },
            suggestedMin: 0,
            suggestedMax: 100
          }
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#fff', font: { size: 11 }, padding: 10, boxWidth: 12 }
          }
        }
      }
    });
  }
}

function cargarObrasParaAtribucion() {
  const select = document.getElementById('atribucion-obras-select');
  if (!select) return;

  const payload = {
    tema: document.getElementById('filtro-tema')?.value || null,
    publicacion_id: document.getElementById('filtro-publicacion')?.value || null,
    pais: document.getElementById('filtro-pais')?.value || null,
    fecha_desde: document.getElementById('filtro-fecha-desde')?.value || null,
    fecha_hasta: document.getElementById('filtro-fecha-hasta')?.value || null,
    limit: 1000
  };

  showLoader();

  // Asegurar que el botón ejecute la comparativa
  const btn = document.getElementById('btn-atribucion-comparar');
  if (btn && !btn.dataset.bound) {
    btn.addEventListener('click', ejecutarAtribucion);
    btn.dataset.bound = 'true';
  }

  fetch('/api/analisis/lista-documentos', {
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
      if (data.exito && data.documentos) {
        select.innerHTML = '';
        data.documentos.forEach(doc => {
          const opt = document.createElement('option');
          opt.value = doc.id;
          opt.innerText = `${doc.autor || 'Anónimo'} - ${doc.titulo}`;
          select.appendChild(opt);
        });

        // Seleccionar todos por defecto la primera vez
        for (let i = 0; i < select.options.length; i++) {
          select.options[i].selected = true;
        }

        // Ejecutar primer análisis
        ejecutarAtribucion();
      }
    })
    .catch(err => {
      hideLoader();
      console.error('[ERROR] Error cargando documentos para atribución:', err);
    });
}

function ejecutarAtribucion() {
  const select = document.getElementById('atribucion-obras-select');
  if (!select) return;

  const selectedIds = Array.from(select.selectedOptions).map(opt => parseInt(opt.value));
  
  if (selectedIds.length < 2) {
    alert('Por favor, selecciona al menos 2 obras para poder calcular el Burrows\' Delta.');
    return;
  }

  const payload = {
    documentos_ids: selectedIds,
    tema: document.getElementById('filtro-tema')?.value || null,
    publicacion_id: document.getElementById('filtro-publicacion')?.value || null,
    pais: document.getElementById('filtro-pais')?.value || null,
    fecha_desde: document.getElementById('filtro-fecha-desde')?.value || null,
    fecha_hasta: document.getElementById('filtro-fecha-hasta')?.value || null
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
