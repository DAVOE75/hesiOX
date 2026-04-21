// ========== GLOBAL STATE (Managed by GISManager) ==========
let vectorLayers = [];
let activeVectorLayer = null;

// --- TRACING STATE (Level 2 Pro) ---
let _traceActive = false;
let _traceAnchor = null; // { feature, vertexIndex, latlng }
let _tracePreviewLine = null;

// --- SCISSORS STATE ---
let _scissorsActive = false;
let _scissorsTarget = null; // { layerId, featureIdx }

// --- THEME REACTIVITY STATE ---
let _currentSymbologyLayerId = null;
let _currentEditingFeatureInfo = null; // { layer, feature }
let _isLayersPanelOpen = false;
let _isShiftKeyPressed = false;
let _expandedFeatures = new Set(); // Set of "layerId-featureIdx" strings for Attribute Table

window.addEventListener('keydown', (e) => { if (e.key === 'Shift') _isShiftKeyPressed = true; });
window.addEventListener('keyup', (e) => { if (e.key === 'Shift') _isShiftKeyPressed = false; });
window.addEventListener('blur', () => { _isShiftKeyPressed = false; }); // Reset on focus loss

/**
 * Observador para cambios de tema instantáneos
 */
const _themeObserver = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    if (mutation.attributeName === 'data-theme') {
      console.log('[GIS] Cambio de tema detectado, refrescando UI...');
      if (typeof _refreshGISUI === 'function') _refreshGISUI();
    }
  });
});
_themeObserver.observe(document.documentElement, { attributes: true });

function _refreshGISUI() {
  // Refrescar Editor de Simbología si está abierto
  if (document.getElementById('floatLayerSymbology') && _currentSymbologyLayerId) {
    openSymbologyModal(_currentSymbologyLayerId);
  }
  // Refrescar Editor de Elementos si está abierto
  if (document.getElementById('floatFeatureEditor') && _currentEditingFeatureInfo) {
    _openFeatureEditorPanel(_currentEditingFeatureInfo.layer, _currentEditingFeatureInfo.featureIdx);
  }
  // Refrescar Gestor de Capas si está abierto
  if (_isLayersPanelOpen) {
    openManageVectorLayersPanel();
  }
}

// ========== GESTIÓN DEL MODAL DE CAPAS ==========

function refreshVectorLayersList() {
  const tbody = document.getElementById('vectorLayersTableBody');
  const layerCount = document.getElementById('layerCount');

  if (!tbody) return;

  if (vectorLayers.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center text-muted py-4">
          <i class="fa-solid fa-layer-group fa-2x mb-2 d-block opacity-50"></i>
          No hay capas vectoriales en este proyecto
        </td>
      </tr>
    `;
    if (layerCount) layerCount.textContent = '0 capas';
    return;
  }

  tbody.innerHTML = '';
  vectorLayers.forEach((layer, index) => {
    const row = document.createElement('tr');
    row.setAttribute('data-layer-id', layer.id);

    // Métricas formateadas
    let metricas = '--';
    if (layer.area_total) {
      metricas = `${layer.area_total.toFixed(2)} km²`;
    } else if (layer.longitud_total) {
      metricas = `${layer.longitud_total.toFixed(2)} km`;
    }

    row.innerHTML = `
      <td>
        <input type="checkbox" class="form-check-input layer-checkbox" data-layer-id="${layer.id}">
      </td>
      <td>
        <div style="width: 30px; height: 30px; background: ${layer.color}; border-radius: 4px; border: 1px solid rgba(255,255,255,0.2);"></div>
      </td>
      <td>
        <div class="fw-bold text-light">${layer.nombre}</div>
        <small class="text-muted">${layer.descripcion || 'Sin descripción'}</small>
      </td>
      <td>
        <span class="badge ${getTypeBadgeClass(layer.tipo_geometria)}">
          ${getTypeIcon(layer.tipo_geometria)} ${getTypeLabel(layer.tipo_geometria)}
        </span>
      </td>
      <td class="text-center">
        <span class="badge bg-secondary">${layer.num_features || 0}</span>
      </td>
      <td class="small text-muted">${metricas}</td>
      <td class="text-center">
        <div class="form-check form-switch d-inline-block">
          <input class="form-check-input" type="checkbox" ${layer.visible ? 'checked' : ''} 
                 onchange="window.GISManager.toggleVectorLayerVisibility(${layer.id}, this.checked)">
        </div>
      </td>
      <td>
        <div class="btn-group btn-group-sm" role="group">
          <button class="btn btn-outline-info" onclick="window.GISManager.editVectorLayerQuick(${layer.id})" title="Editar">
            <i class="fa-solid fa-pen"></i>
          </button>
          <button class="btn btn-outline-primary" onclick="window.GISManager.zoomToVectorLayer(${layer.id})" title="Zoom">
            <i class="fa-solid fa-crosshairs"></i>
          </button>
          <button class="btn btn-outline-success" onclick="window.GISManager.exportVectorLayerById(${layer.id})" title="Exportar">
            <i class="fa-solid fa-download"></i>
          </button>
          <button class="btn btn-outline-danger" onclick="window.GISManager.deleteVectorLayerConfirm(${layer.id})" title="Eliminar">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </td>
    `;

    tbody.appendChild(row);
  });

  if (layerCount) layerCount.textContent = `${vectorLayers.length} capa${vectorLayers.length !== 1 ? 's' : ''}`;
}

/**
 * Refresca la lista de capas en el panel lateral (sidebar)
 */
async function refreshLayersPanelUI() {
  const digitizedContainer = document.getElementById('digitized-layers-container');
  const externalContainer = document.getElementById('external-layers-container');
  
  if (digitizedContainer) digitizedContainer.innerHTML = '';
  if (externalContainer) externalContainer.innerHTML = '';

  // 1. Internas
  [...vectorLayers].reverse().forEach(layer => {
    addVectorLayerToPanel(layer);
  });

  // 2. Externas (A esperar para asegurar que no borren las internas)
  if (typeof loadExternalLayers === 'function') {
    await loadExternalLayers(false);
  }

  initGisLayersSortable();
}

function _onLayersPanelClose() {
  _isLayersPanelOpen = false;
}

function initGisLayersSortable() {
  const el = document.getElementById('digitized-layers-container');
  if (!el || typeof Sortable === 'undefined') return;

  if (window._gisSortable) window._gisSortable.destroy();

  window._gisSortable = Sortable.create(el, {
    animation: 150,
    handle: '.layer-drag-handle',
    onEnd: function () {
      applyGisLayersOrder();
    }
  });
}

function applyGisLayersOrder() {
  const container = document.getElementById('digitized-layers-container');
  if (!container) return;

  const items = Array.from(container.children);
  const total = items.length;

  // Reordenar por zIndex (de abajo a arriba en el DOM = de fondo a frente en el mapa)
  items.reverse().forEach((item, index) => {
    const layerId = item.getAttribute('data-vector-layer-id');
    
    // 1. Intentar como capa interna de GISManager
    const layer = vectorLayers.find(l => l.id == layerId);
    if (layer && layer.leafletLayer) {
        layer.leafletLayer.bringToFront();
    } 
    // 2. Intentar como capa externa de mapa_corpus (ext-ID)
    else if (layerId && layerId.startsWith('ext-')) {
        const extId = layerId.replace('ext-', '');
        const extLayer = window.mapLayers ? window.mapLayers[extId] : null;
        if (extLayer && typeof extLayer.bringToFront === 'function') {
            extLayer.bringToFront();
        }
    }
  });

  // Mantener ubicaciones al frente
  if (typeof bringLocationsToFront === 'function') bringLocationsToFront();
}

/**
 * Añade una capa al panel lateral (digitized-layers-container)
 */
/**
 * Carga las capas vectoriales desde la base de datos
 */
async function loadVectorLayersFromDB() {
  console.log('[GIS] Cargando capas vectoriales desde la DB...');
  try {
    const response = await fetch('/api/vector_layers');
    if (!response.ok) {
      if (response.status === 401 || response.status === 302) {
        console.warn('[GIS] Usuario no autenticado, omitiendo carga de capas vectoriales');
        return;
      }
      throw new Error(`Error al cargar capas: ${response.status}`);
    }

    const layers = await response.json();

    // Limpiar capas anteriores del mapa
    const targetMap = window.map || window._mapaCorpus;
    vectorLayers.forEach(layer => {
      if (layer.leafletLayer && targetMap && targetMap.hasLayer(layer.leafletLayer)) {
        targetMap.removeLayer(layer.leafletLayer);
      }
    });

    // Mutar el array para mantener referencias externas
    vectorLayers.length = 0;

    // Cargar cada capa
    layers.forEach(layerData => {
      const layer = {
        id: layerData.id,
        nombre: layerData.nombre,
        descripcion: layerData.descripcion,
        tipo_geometria: layerData.tipo_geometria,
        color: layerData.color,
        opacidad: layerData.opacidad || 0.8,
        grosor_linea: layerData.grosor_linea || 3,
        visible: layerData.visible !== false,
        bloqueada: layerData.bloqueada || false,
        num_features: layerData.num_features || 0,
        area_total: layerData.area_total,
        longitud_total: layerData.longitud_total,
        etiquetas_visibles: layerData.etiquetas_visibles || false,
        snap_enabled: layerData.snap_enabled !== false,
        geojson: layerData.geojson || { type: 'FeatureCollection', features: [] },
        leafletLayer: L.layerGroup()
      };

      // Renderizar features en el mapa
      if (layer.geojson && layer.geojson.features) {
        layer.geojson.features.forEach(feature => {
          renderFeatureOnMap(layer, feature);
        });
      }

      const targetMap = window.map || window._mapaCorpus;
      if (layer.visible && targetMap) {
        layer.leafletLayer.addTo(targetMap);
      }

      vectorLayers.push(layer);
    });

    // Actualizar el panel lateral de forma unificada
    refreshLayersPanelUI();

    // Sincronizar window.GISManager
    if (window.GISManager) window.GISManager.vectorLayers = vectorLayers;

    if (typeof refreshVectorLayersList === 'function') refreshVectorLayersList();
    if (typeof refreshQuickList === 'function') refreshQuickList(vectorLayers);

    // Asegurar que el orden visual en el mapa coincide con el del panel
    if (typeof syncLayerOrder === 'function') {
      setTimeout(() => syncLayerOrder(), 500); 
    }

    console.log(`✅ ${layers.length} capas vectoriales cargadas`);
  } catch (error) {
    console.error('Error al cargar capas vectoriales:', error);
  }
}

function calculateArea(latlngs) {
  if (latlngs.length < 3) return 0;
  let area = 0;
  const radius = 6378137; // Earth radius in meters
  const degToRad = Math.PI / 180;
  for (let i = 0; i < latlngs.length; i++) {
    let p1 = latlngs[i];
    let p2 = latlngs[(i + 1) % latlngs.length];
    area += (p2.lng - p1.lng) * degToRad * (2 + Math.sin(p1.lat * degToRad) + Math.sin(p2.lat * degToRad));
  }
  area = area * radius * radius / 2.0;
  return Math.abs(area);
}

function suggestLocationFromText() {
  const name = document.getElementById('digitize-feature-name')?.value.trim();
  if (!name) {
    if (typeof showMapMessage === 'function') showMapMessage("Introduce un nombre para buscar la ubicación", "warning");
    return;
  }

  if (typeof showMapMessage === 'function') showMapMessage(`Buscando coordenadas para "${name}"...`, "info");

  fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(name)}&limit=1`)
    .then(r => r.json())
    .then(data => {
      if (data && data.length > 0) {
        const result = data[0];
        const lat = parseFloat(result.lat);
        const lon = parseFloat(result.lon);
        const targetMap = window.map || window._mapaCorpus;

        if (confirm(`He encontrado: ${result.display_name}. ¿Deseas situar el elemento ahí?`)) {
          if (targetMap) targetMap.flyTo([lat, lon], 15);
          if (typeof createPointFeature === 'function') {
            createPointFeature(L.latLng(lat, lon));
            if (typeof showMapMessage === 'function') showMapMessage("Punto creado en la ubicación encontrada", "success");
          } else {
            if (typeof showMapMessage === 'function') showMapMessage("Mapa centrado en la ubicación. Puedes empezar a dibujar.", "info");
          }
        }
      } else {
        if (typeof showMapMessage === 'function') showMapMessage("No se encontró ninguna ubicación con ese nombre", "warning");
      }
    })
    .catch(e => console.error("Geocoding error:", e));
}

function openSpatialAnalysisPanel() {
  const existing = document.getElementById('floatLayerAnalysis');
  if (existing) existing.remove();

  const panel = L.DomUtil.create('div', 'gis-float-panel');
  panel.id = 'floatLayerAnalysis';
  panel.style.cssText = `
      width: 350px; top: 100px; right: 300px; position: fixed; z-index: 1000;
      background: var(--ds-bg-panel, #1a1a1a); border: 1px solid var(--ds-border-color, #444);
      border-radius: 6px; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    `;

  panel.innerHTML = `
      <div class="digitize-header digitize-draggable-handle" style="cursor:move; padding:8px 12px; display:flex; justify-content:space-between; align-items:center;">
        <span class="digitize-title" style="font-weight:700;">
          <i class="fa-solid fa-grip-vertical me-2" style="opacity:0.5;"></i>
          <i class="fa-solid fa-pen-nib me-2"></i>DIGITALIZADOR
        </span>
      <span class="font-mono text-uppercase" style="font-size:0.75rem;"><i class="fa-solid fa-layer-group me-2"></i>Análisis Espacial</span>
        <button class="btn-close-digitize" onclick="this.closest('.gis-float-panel').remove()">✕</button>
      </div>
      <div class="p-3">
        <label class="small font-mono mb-1 text-light">Capa Límite (Polígono)</label>
        <select id="analysisBoundaryLayer" class="form-select form-select-sm bg-dark text-light border-secondary mb-2">
          ${vectorLayers.filter(l => l.tipo_geometria === 'polygon').map(l => `<option value="${l.id}">${l.nombre}</option>`).join('')}
        </select>
        <label class="small font-mono mb-1 text-light">Capa Objetivo (Puntos)</label>
        <select id="analysisTargetLayer" class="form-select form-select-sm bg-dark text-light border-secondary mb-3">
          ${vectorLayers.filter(l => l.tipo_geometria === 'point').map(l => `<option value="${l.id}">${l.nombre}</option>`).join('')}
        </select>
        <button class="btn btn-sm btn-sirio w-100 mb-3" onclick="window.GISManager.runSpatialAnalysis()">
          <i class="fa-solid fa-play me-1"></i> Ejecutar Intersección
        </button>
        <div id="spatialAnalysisResults" style="max-height:200px; overflow-y:auto; border-top:1px solid #444; padding-top:10px; font-size:0.7rem;">
          <small class="text-muted">Los resultados aparecerán aquí...</small>
        </div>
      </div>
    `;

  document.body.appendChild(panel);
  makeDraggable(panel);
  L.DomEvent.disableClickPropagation(panel);
}

function runSpatialAnalysis() {
  const boundaryId = document.getElementById('analysisBoundaryLayer').value;
  const targetId = document.getElementById('analysisTargetLayer').value;

  const boundaryLayer = vectorLayers.find(l => l.id == boundaryId);
  const targetLayer = vectorLayers.find(l => l.id == targetId);

  if (!boundaryLayer || !targetLayer) return;

  const resultsDiv = document.getElementById('spatialAnalysisResults');
  resultsDiv.innerHTML = '<div class="text-info"><i class="fa-solid fa-spinner fa-spin me-2"></i>Procesando intersección...</div>';

  setTimeout(() => {
    let count = 0;
    targetLayer.geojson.features.forEach(f => {
      const point = [f.geometry.coordinates[1], f.geometry.coordinates[0]];
      boundaryLayer.geojson.features.forEach(poly => {
        if (isPointInPolygon(point, poly.geometry.coordinates[0])) {
          count++;
        }
      });
    });

    resultsDiv.innerHTML = `
          <div class="alert alert-info py-2 m-0" style="font-size:0.7rem;">
            <strong>Resultado:</strong> Encontrados ${count} elementos de <strong>${targetLayer.nombre}</strong> dentro de <strong>${boundaryLayer.nombre}</strong>.
          </div>
        `;
  }, 800);
}

function isPointInPolygon(point, polygon) {
  const x = point[1], y = point[0]; // [lng, lat]
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0], yi = polygon[i][1];
    const xj = polygon[j][0], yj = polygon[j][1];
    const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

/**
 * Añade una capa al panel lateral (digitized-layers-container) con UI avanzada
 */
function addVectorLayerToPanel(layer) {
  const container = document.getElementById('digitized-layers-container');
  if (!container) return;

  // Evitar duplicados
  const existing = container.querySelector(`[data-vector-layer-id="${layer.id}"]`);
  if (existing) existing.remove();

  const typeIcons = {
    point: '<span style="width: 14px; text-align: center; display: inline-block; opacity: 0.85;"><i class="fa-solid fa-location-dot text-success" style="font-size: 0.85em;"></i></span>',
    line: '<span style="width: 14px; text-align: center; display: inline-block; opacity: 0.85;"><i class="fa-solid fa-route text-primary" style="font-size: 0.85em;"></i></span>',
    polygon: '<span style="width: 14px; text-align: center; display: inline-block; opacity: 0.85;"><i class="fa-solid fa-draw-polygon text-danger" style="font-size: 0.85em;"></i></span>',
    mixed: '<span style="width: 14px; text-align: center; display: inline-block; opacity: 0.85;"><i class="fa-solid fa-layer-group text-info" style="font-size: 0.85em;"></i></span>'
  };

  const isActive = activeVectorLayer && activeVectorLayer.id == layer.id;
  const toggleRow = document.createElement('div');
  toggleRow.className = `compact-toggle-row align-items-center layer-drag-item ${isActive ? 'active-layer-sirio' : ''}`;
  toggleRow.setAttribute('data-id', layer.id);
  toggleRow.setAttribute('data-vector-layer-id', layer.id);

  const numFeatures = layer.num_features || (layer.geojson?.features?.length) || 0;

  toggleRow.innerHTML = `
    <div class="layer-drag-handle me-1" title="Arrastrar para reordenar">
      <i class="fa-solid fa-grip-vertical"></i>
    </div>

    <div class="d-flex align-items-center flex-grow-1 overflow-hidden">
      <input 
        class="form-check-input col-toggle me-2 flex-shrink-0" 
        type="checkbox" 
        id="vector-toggle-${layer.id}" 
        ${layer.visible ? 'checked' : ''}
        onchange="window.GISManager.toggleVectorLayerVisibility('${layer.id}', this.checked)"
      >
      
      <div 
        class="d-flex align-items-center flex-grow-1 overflow-hidden cursor-pointer" 
        onclick="window.GISManager.setActiveVectorLayer('${layer.id}')"
        ondblclick="window.GISManager.setActiveVectorLayer('${layer.id}')"
        style="user-select: none; transition: opacity 0.2s;"
        onmouseover="this.style.opacity='0.8'"
        onmouseout="this.style.opacity='1'"
        title="${isActive ? 'Desactivar capa' : 'Clic para activar capa'}"
      >
        <div 
          class="flex-shrink-0 me-2"
          style="width: 12px; height: 12px; border-radius: 3px; background: ${layer.color}; border: 1px solid rgba(255,255,255,0.3);"
        ></div>

        ${typeIcons[layer.tipo_geometria] || typeIcons.mixed}
        <span class="text-light text-truncate ms-2 fw-bold" style="font-size: 0.75rem; letter-spacing: 0.2px;" title="${layer.nombre}">${layer.nombre}</span>
      </div>
    </div>

    <div class="d-flex align-items-center ms-auto gap-1">
      <!-- Botón Bloquear -->
      <button 
        class="btn-gis-action ${layer.bloqueada ? 'text-warning' : 'text-muted'}" 
        onclick="window.GISManager.toggleVectorLayerLock('${layer.id}')"
        title="${layer.bloqueada ? 'Capa bloqueada. Clic para desbloquear' : 'Bloquear capa'}"
      >
        <i class="fa-solid fa-${layer.bloqueada ? 'lock' : 'unlock'}"></i>
      </button>

      <!-- Botón principal: Digitalizar (Visible para todas las capas vectoriales) -->
      <button 
        class="btn-gis-action ${isActive ? 'text-info active' : 'text-muted'}" 
        onclick="window.GISManager.editVectorLayer('${layer.id}')"
        title="${layer.bloqueada ? 'Digitalización deshabilitada' : 'Digitalizar en esta capa'}"
        ${layer.bloqueada ? 'style="opacity:0.5; cursor:not-allowed;"' : ''}
      >
        <i class="fa-solid fa-pen-nib"></i>
      </button>

      <!-- Botón Zoom -->
      <button 
        class="btn-gis-action text-muted" 
        onclick="window.GISManager.zoomToVectorLayer('${layer.id}')" 
        title="Zoom a la capa"
      >
        <i class="fa-solid fa-crosshairs"></i>
      </button>

      <!-- Menú desplegable para el resto de acciones -->
      <div class="dropdown">
        <button 
          class="btn-gis-action text-muted" 
          type="button" 
          data-bs-toggle="dropdown" 
          aria-expanded="false"
          title="Más opciones"
        >
          <i class="fa-solid fa-ellipsis-vertical"></i>
        </button>
        <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end shadow border-secondary" style="font-size: 0.8rem; min-width: 180px;">
          <li>
            <a class="dropdown-item d-flex align-items-center gap-2" href="#" onclick="window.GISManager.openAttributeTable('${layer.id}'); return false;">
              <i class="fa-solid fa-table-list text-light fa-fw me-2"></i> Tabla de Atributos
            </a>
          </li>
          <li>
            <a class="dropdown-item d-flex align-items-center gap-2 ${layer.etiquetas_visibles ? 'active' : ''}" href="#" onclick="window.GISManager.toggleLayerLabels('${layer.id}'); return false;">
              <i class="fa-solid fa-tag ${layer.etiquetas_visibles ? 'text-warning' : 'text-muted'} fa-fw me-2"></i> ${layer.etiquetas_visibles ? 'Ocultar etiquetas' : 'Mostrar etiquetas'}
            </a>
          </li>
          ${layer.tipo_geometria === 'point' ? `
          <li>
            <a class="dropdown-item d-flex align-items-center gap-2" href="#" onclick="window.GISManager.toggleHeatmap('${layer.id}'); return false;">
              <i class="fa-solid fa-fire text-danger fa-fw me-2"></i> Alternar Heatmap
            </a>
          </li>` : ''}
          <li><hr class="dropdown-divider border-secondary opacity-25"></li>
          <li>
            <a class="dropdown-item d-flex align-items-center gap-2" href="#" onclick="window.GISManager.importCSVToLayer('${layer.id}'); return false;">
              <i class="fa-solid fa-file-csv text-secondary fa-fw me-2"></i> Importar CSV
            </a>
          </li>
          <li>
            <a class="dropdown-item d-flex align-items-center gap-2" href="#" onclick="window.GISManager.exportVectorLayerById('${layer.id}'); return false;">
              <i class="fa-solid fa-download text-success fa-fw me-2"></i> Exportar GeoJSON
            </a>
          </li>
          <li>
            <a class="dropdown-item d-flex align-items-center gap-2" href="#" onclick="window.GISManager.duplicateVectorLayer('${layer.id}'); return false;">
              <i class="fa-solid fa-copy text-info fa-fw me-2"></i> Duplicar capa
            </a>
          </li>
          <li>
            <a class="dropdown-item d-flex align-items-center gap-2" href="#" onclick="window.GISManager.openSymbologyModal('${layer.id}'); return false;">
              <i class="fa-solid fa-palette text-warning fa-fw me-2"></i> Simbología Temática
            </a>
          </li>
          <li><hr class="dropdown-divider border-secondary opacity-25"></li>
          <li>
            <a class="dropdown-item d-flex align-items-center gap-2 text-danger" href="#" onclick="window.GISManager.deleteVectorLayerConfirm('${layer.id}'); return false;">
              <i class="fa-solid fa-trash fa-fw me-2"></i> Eliminar capa
            </a>
          </li>
        </ul>
      </div>
    </div>
  `;

  container.prepend(toggleRow);

  // Inicializar Sortable si no existe para este contenedor
  if (!container.dataset.sortableInitialized && typeof Sortable !== 'undefined') {
    new Sortable(container, {
      handle: '.layer-drag-handle',
      animation: 150,
      ghostClass: 'bg-primary',
      onEnd: function () {
        window.GISManager.syncLayerOrder();
      }
    });
    container.dataset.sortableInitialized = 'true';
  }
}

function editVectorLayer(layerId) {
  if (String(layerId).startsWith('ext-')) {
    setActiveVectorLayer(layerId, true);
    if (typeof showMapMessage === 'function') showMapMessage("Capa externa activa como referencia");
    return;
  }
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;
  setActiveVectorLayer(layer.id, true);
  if (typeof startDigitizing === 'function') {
    startDigitizing(layer.tipo_geometria);
  }
  if (typeof showMapMessage === 'function') {
    showMapMessage(`Editando capa: ${layer.nombre}`);
  }
}

/**
 * Activa una capa para digitalización
 */
function setActiveVectorLayer(id, forceActive = false) {
  // TOGGLE: Si la capa ya está activa, la desactivamos al volver a "activarla"
  // (a menos que forceActive sea true, por ejemplo al darle a Digitalizar)
  if (!forceActive && activeVectorLayer && activeVectorLayer.id == id) {
    deactivateActiveVectorLayer();
    return;
  }

  const isExternal = String(id).startsWith('ext-');
  let layer;

  if (isExternal) {
    const extId = id.replace('ext-', '');
    // Buscar en el array global de capas externas si fuera necesario, 
    // pero para la UI basta con saber que existe en el DOM
    layer = { id: id, nombre: 'Capa Externa', bloqueada: false }; 
  } else {
    layer = vectorLayers.find(l => l.id == id);
  }

  if (!layer) return;

  if (layer.bloqueada) {
    if (typeof showMapMessage === 'function') {
      showMapMessage(`No se puede activar la capa "${layer.nombre}" porque está bloqueada.`, 'warning');
    }
    return;
  }

  activeVectorLayer = layer;
  if (window.GISManager) window.GISManager.activeVectorLayer = activeVectorLayer;

  console.log(`🎯 Capa activa: ${layer.nombre}`);

  // UI updates
  document.querySelectorAll('.compact-toggle-row').forEach(row => {
    row.classList.remove('active-layer-sirio');
  });
  const activeRow = document.querySelector(`[data-vector-layer-id="${id}"]`);
  if (activeRow) activeRow.classList.add('active-layer-sirio');

  if (typeof refreshQuickList === 'function') refreshQuickList(vectorLayers);

  // Refrescar el panel para mostrar el icono de digitalización en la capa activa
  // (IMPORTANTE: Solo refrescamos si la capa realmente cambió)
  refreshLayersPanelUI();

  // Actualizar indicador flotante
  const group = document.getElementById('active-layer-header-group');
  const indicatorName = document.getElementById('active-layer-float-name');
  if (group && indicatorName) {
    indicatorName.textContent = `Capa Activa: ${layer.nombre}`;
    group.classList.remove('d-none');
    group.classList.add('d-flex');
  }

  // Si la capa está oculta, ofrecer mostrarla
  if (layer.visible === false) {
    if (confirm(`La capa "${layer.nombre}" está oculta. ¿Deseas mostrarla para digitalizar?`)) {
      toggleVectorLayerVisibility(id, true);
    }
  }
}

/**
 * Desactiva la capa actualmente activa para digitalización
 */
function deactivateActiveVectorLayer() {
  console.log(`⏹️ Desactivando capa GIS (si existe)...`);
  
  // Siempre intentar ocultar el grupo de la cabecera, por si acaso
  const group = document.getElementById('active-layer-header-group');
  if (group) {
    group.classList.add('d-none');
    group.classList.remove('d-flex');
  }

  if (!activeVectorLayer) return;

  console.log(`⏹️ Desactivando capa: ${activeVectorLayer.nombre}`);

  // Limpiar selección actual si existe
  if (typeof _clearFeatureSelection === 'function') _clearFeatureSelection();

  // Desactivar herramientas de dibujo de forma segura
  if (typeof deactivateDigitizeMode === 'function') {
    deactivateDigitizeMode();
  } else if (typeof disableDigitizeTools === 'function') {
    disableDigitizeTools();
  }

  // Reset variable
  activeVectorLayer = null;
  if (window.GISManager) window.GISManager.activeVectorLayer = null;

  // UI updates: Quitar clases 'active'
  document.querySelectorAll('.layer-drag-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.compact-toggle-row').forEach(row => row.classList.remove('active-layer-sirio'));

  // Refrescar el panel para ocultar iconos de edición
  if (typeof refreshLayersPanelUI === 'function') {
    refreshLayersPanelUI();
  }

  // El grupo ya se ocultó al inicio de la función

  const activeLayerNameEl = document.getElementById('active-layer-name');
  if (activeLayerNameEl) activeLayerNameEl.textContent = 'Ninguna capa seleccionada';

  if (typeof refreshQuickList === 'function') refreshQuickList(vectorLayers);
  if (typeof showMapMessage === 'function') showMapMessage('Edición finalizada', 'info');
}

/**
 * Alterna la visibilidad de una capa en el mapa
 */
async function toggleVectorLayerVisibility(layerId, visible) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;

  layer.visible = visible;

  const targetMap = window.map || window._mapaCorpus;
  if (visible) {
    if (targetMap) layer.leafletLayer.addTo(targetMap);
  } else {
    if (targetMap) {
      targetMap.removeLayer(layer.leafletLayer);
      // Ocultar también nodos de edición si es la capa activa
      if (window.editLayer && activeVectorLayer && activeVectorLayer.id == layerId) {
        window.editLayer.clearLayers();
        window.editingFeatureIdx = null;
      }
    }
  }

  // Sincronizar checkbox del panel lateral si existe
  const panelCb = document.getElementById(`vector-toggle-${layer.id}`);
  if (panelCb) panelCb.checked = visible;

  // Guardar en BD
  try {
    await fetch(`/api/vector_layers/${layerId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ visible })
    });
    if (typeof refreshQuickList === 'function') refreshQuickList(vectorLayers);
  } catch (error) {
    console.error('Error al actualizar visibilidad:', error);
  }
}

/**
 * Alterna el bloqueo de una capa vectorial
 */
async function toggleVectorLayerLock(layerId) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;

  const newState = !layer.bloqueada;
  layer.bloqueada = newState;

  // Desactivar si la estábamos editando
  if (newState && activeVectorLayer && activeVectorLayer.id == layerId) {
    if (typeof showMapMessage === 'function') showMapMessage('Capa bloqueada. Edición detenida.', 'warning');
    
    // Limpiar selección actual si existe
    if (typeof _clearFeatureSelection === 'function') _clearFeatureSelection();
    
    // Desactivar herramientas de dibujo
    if (typeof disableDigitizeTools === 'function') disableDigitizeTools();
    
    activeVectorLayer = null;
    
    // Quitar la clase 'active' de todos los elementos UI
    document.querySelectorAll('.layer-drag-item').forEach(el => el.classList.remove('active'));
    
    const activeLayerNameEl = document.getElementById('active-layer-name');
    if (activeLayerNameEl) activeLayerNameEl.textContent = 'Ninguna capa seleccionada';
  }

  // Actualizar UI del panel lateral (vuelve a renderizar)
  const container = document.getElementById('digitized-layers-container');
  if (container) {
    container.innerHTML = '';
    [...vectorLayers].reverse().forEach(l => {
      addVectorLayerToPanel(l);
    });
    
    // Restaurar clase active si corresponde
    if (activeVectorLayer) {
      const activeEl = container.querySelector(`[data-vector-layer-id="${activeVectorLayer.id}"]`);
      if (activeEl) activeEl.classList.add('active');
    }
  }

  // Guardar en BD
  try {
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
    await fetch(`/api/vector_layers/${layerId}`, {
      method: 'PUT',
      headers: { 
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ bloqueada: newState })
    });
  } catch (error) {
    console.error('Error al actualizar bloqueo:', error);
  }
}

/**
 * Sincroniza el orden de las capas con el backend y el mapa
 */
async function syncLayerOrder() {
  const container = document.getElementById('digitized-layers-container');
  if (!container) return;

  const items = container.querySelectorAll('.layer-drag-item');
  const orderData = [];

  // El orden en la lista va de "más arriba" (index 0) a "más abajo".
  // Para Leaflet, aplicamos bringToFront() en orden INVERSO:
  // El elemento que está en la posición 0 (arriba) debe ser el último en llamar a bringToFront()
  // para quedar por encima de todos.
  const reversedItems = Array.from(items).reverse();

  reversedItems.forEach((item, index) => {
    const id = item.dataset.id;
    // Guardamos el índice real (0 para el de arriba, 1 para el siguiente, etc.)
    orderData.push({ id: parseInt(id), orden: items.length - 1 - index });

    // Actualizar orden visual en Leaflet
    const layer = vectorLayers.find(l => l.id == id);
    if (layer && layer.leafletLayer) {
      if (typeof layer.leafletLayer.bringToFront === 'function') {
        layer.leafletLayer.bringToFront();
      } else if (typeof layer.leafletLayer.eachLayer === 'function') {
        layer.leafletLayer.eachLayer(l => {
          if (typeof l.bringToFront === 'function') l.bringToFront();
        });
      }
    }
  });

  if (orderData.length === 0) return;

  try {
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
    const response = await fetch('/api/vector_layers/reorder', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ layers: orderData })
    });

    if (response.ok) {
      console.log('✅ [GIS] Orden de capas sincronizado');
    } else {
      console.error('❌ [GIS] Error sincronizando orden de capas');
    }
  } catch (error) {
    console.error('❌ [GIS] Error:', error);
  }
}

function getTypeBadgeClass(tipo) {
  switch (tipo) {
    case 'point': return 'bg-success';
    case 'line': return 'bg-primary';
    case 'polygon': return 'bg-danger';
    default: return 'bg-secondary';
  }
}

function getTypeIcon(tipo) {
  switch (tipo) {
    case 'point': return '<i class="fa-solid fa-location-dot"></i>';
    case 'line': return '<i class="fa-solid fa-route"></i>';
    case 'polygon': return '<i class="fa-solid fa-draw-polygon"></i>';
    default: return '<i class="fa-solid fa-layer-group"></i>';
  }
}

function getTypeLabel(tipo) {
  switch (tipo) {
    case 'point': return 'Puntos';
    case 'line': return 'Líneas';
    case 'polygon': return 'Polígonos';
    default: return 'Mixta';
  }
}

// ========== EDICIÓN RÁPIDA ==========

function editVectorLayerQuick(layerId) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;

  const panel = document.getElementById('quickEditPanel');
  if (!panel) return;

  // Llenar formulario
  document.getElementById('quickEditLayerId').value = layer.id;
  document.getElementById('quickEditName').value = layer.nombre;
  document.getElementById('quickEditDesc').value = layer.descripcion || '';
  document.getElementById('quickEditColor').value = layer.color;
  document.getElementById('quickEditOpacity').value = layer.opacidad;
  document.getElementById('quickEditStroke').value = layer.grosor_linea || 3;
  document.getElementById('quickEditLabels').checked = layer.etiquetas_visibles || false;
  document.getElementById('quickEditSnap').checked = layer.snap_enabled || false;

  // Actualizar displays
  document.getElementById('opacityValue').textContent = `${Math.round(layer.opacidad * 100)}%`;
  document.getElementById('strokeValue').textContent = `${layer.grosor_linea || 3}px`;

  // Mostrar panel
  panel.classList.remove('d-none');
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  // Handlers para sliders
  document.getElementById('quickEditOpacity').oninput = function () {
    document.getElementById('opacityValue').textContent = `${Math.round(this.value * 100)}%`;
  };

  document.getElementById('quickEditStroke').oninput = function () {
    document.getElementById('strokeValue').textContent = `${this.value}px`;
  };
}

async function saveQuickEdit() {
  const layerId = parseInt(document.getElementById('quickEditLayerId').value);
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;

  const updatedData = {
    nombre: document.getElementById('quickEditName').value.trim(),
    descripcion: document.getElementById('quickEditDesc').value.trim(),
    color: document.getElementById('quickEditColor').value,
    opacidad: parseFloat(document.getElementById('quickEditOpacity').value),
    grosor_linea: parseInt(document.getElementById('quickEditStroke').value),
    etiquetas_visibles: document.getElementById('quickEditLabels').checked,
    snap_enabled: document.getElementById('quickEditSnap').checked
  };

  try {
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
    const response = await fetch(`/api/vector_layers/${layerId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(updatedData)
    });

    const result = await response.json();
    if (result.success) {
      showMapMessage(result.message, 'success');
      await loadVectorLayersFromDB();
      refreshVectorLayersList();
      cancelQuickEdit();
    } else {
      showMapMessage(result.error || 'Error al actualizar', 'error');
    }
  } catch (error) {
    console.error('Error:', error);
    showMapMessage('Error al guardar cambios', 'error');
  }
}

function cancelQuickEdit() {
  const panel = document.getElementById('quickEditPanel');
  if (panel) {
    panel.classList.add('d-none');
  }
}

function openSymbologyModal(layerId) {
  try {
    const layer = vectorLayers.find(l => l.id == layerId);
    if (!layer) {
      console.warn(`[GIS] No se encontró la capa con id ${layerId} para simbología`);
      return;
    }
    _currentSymbologyLayerId = layer.id;

    // Cerrar versión vieja si existe
    const modalEl = document.getElementById('modalLayerSymbology');
    if (modalEl && typeof bootstrap !== 'undefined') {
      const bootstrapModal = bootstrap.Modal.getInstance(modalEl);
      if (bootstrapModal) bootstrapModal.hide();
    }

    let panel = document.getElementById('floatLayerSymbology');
    
    // Si ya existe, lo refrescamos entero para asegurar que el select de campos y todo esté al día
    if (panel) panel.remove();

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || (!document.documentElement.getAttribute('data-theme') && !document.body.classList.contains('light-theme'));
    
    const html = `
      <div id="floatLayerSymbology" class="gis-float-panel" 
           style="width: 380px; z-index: 11000; display: flex; flex-direction: column; background: ${isDark ? '#111' : '#fff'}; border: 1px solid ${isDark ? '#444' : '#ccc'}; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border-radius: 6px; overflow: hidden; position: fixed;">
        <div class="digitize-header digitize-draggable-handle py-2 px-3 d-flex justify-content-between align-items-center" style="background: ${isDark ? '#ff9800' : '#294a60'}; color: ${isDark ? '#000' : '#fff'}; cursor: move;">
          <span style="font-size: 0.7rem; font-weight: 800; letter-spacing: 1px; text-transform: uppercase;">
            <i class="fa-solid fa-palette me-2"></i>SIMBOLOGÍA: <span id="symbologyLayerNameDisplay">${layer.nombre}</span>
          </span>
          <button onclick="document.getElementById('floatLayerSymbology').remove()" style="background:none; border:none; color:${isDark ? '#000' : '#fff'}; cursor:pointer; font-size:14px;">✕</button>
        </div>
        <div class="p-3" style="max-height: 500px; overflow-y: auto; background: ${isDark ? '#0c0c0c' : '#ffffff'};">
          <input type="hidden" id="symbologyLayerId" value="${layer.id}">
          <div class="mb-3">
            <label class="form-label small text-accent text-uppercase fw-bold" style="font-size: 9px; color: ${isDark ? '#888' : '#555'};">Campo de Atributo para Clasificación</label>
            <select id="symbologyField" class="form-select form-select-sm bg-input-sirio font-mono" style="font-size: 0.75rem;">
              ${_getLayerFields(layer).map(f => `<option value="${f}" ${layer.symbology?.field === f ? 'selected' : ''}>${f}</option>`).join('')}
            </select>
          </div>
          <div id="symbologyRulesContainer"></div>
          <button class="btn btn-sm btn-sirio-outline w-100 mt-3" onclick="window.GISManager.addSymbologyRule()" style="font-size: 0.7rem;">
            <i class="fa-solid fa-plus me-1"></i> AÑADIR REGLA TEMÁTICA
          </button>
        </div>
        <div class="p-2 border-top border-sirio d-flex justify-content-end gap-2" style="background: ${isDark ? '#0c0c0c' : '#f8f8f8'}; border-color: ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'};">
          <button class="btn btn-xs btn-secondary" style="font-size: 0.65rem;" onclick="document.getElementById('floatLayerSymbology').remove()">CANCELAR</button>
          <button class="btn btn-xs btn-sirio" style="font-size: 0.65rem;" onclick="window.GISManager.saveLayerSymbology()">GUARDAR Y APLICAR</button>
        </div>
      </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', html);
    panel = document.getElementById('floatLayerSymbology');
    
    // Posicionar cerca del centro
    panel.style.top = '100px';
    panel.style.left = (window.innerWidth / 2 - 190) + 'px';
    
    if (typeof makeDraggable === 'function') makeDraggable(panel);

    // Cargar reglas existentes
    const container = document.getElementById('symbologyRulesContainer');
    if (layer.symbology && layer.symbology.rules) {
      layer.symbology.rules.forEach(rule => window.GISManager.addSymbologyRule(rule));
    }
  } catch (err) {
    console.error("[GIS] Error opening symbology modal:", err);
  }
}

function addSymbologyRule(config = {}) {
  const container = document.getElementById('symbologyRulesContainer');
  if (!container) return;

  // Si config es un string (viejo código), lo tratamos como el valor
  if (typeof config === 'string') {
    const val = config;
    const color = arguments[1] || '#ff9800';
    config = { value: val, color: color };
  }

  const {
    value = '',
    color = '#ff9800',
    weight = 3,
    dashArray = '',
    icon = '',
    size = 6
  } = config;

  const ruleId = 'rule-' + Date.now() + Math.random().toString(36).substr(2, 5);
  const html = `
    <div id="${ruleId}" class="mb-3 p-2 border border-secondary rounded position-relative" style="background: rgba(255,255,255,0.03);">
      <div class="d-flex align-items-center gap-2 mb-2">
        <input type="text" class="form-control form-control-sm bg-input-sirio rule-value" placeholder="Valor (Exacto)" value="${value}" style="font-size: 0.7rem; flex: 1.5;">
        <input type="color" class="form-control form-control-sm p-1 rule-color" value="${color}" style="width: 40px; height: 30px; border:none; background:none;">
        <button class="btn btn-link btn-sm text-danger p-0" onclick="document.getElementById('${ruleId}').remove()" title="Eliminar regla">
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>
      
      <div class="d-flex flex-wrap gap-2 align-items-center">
        <!-- Grosor / Tamaño -->
        <div style="width: 70px;">
          <label style="font-size: 8px; text-transform:uppercase; color: #888; display:block; margin-bottom: 2px;">Grosor/Tam</label>
          <input type="number" class="form-control form-control-sm bg-input-sirio rule-weight" value="${weight || size}" step="0.5" style="font-size: 10px; height: 25px;">
        </div>

        <!-- Estilo de Línea -->
        <div style="flex: 1; min-width: 100px;">
          <label style="font-size: 8px; text-transform:uppercase; color: #888; display:block; margin-bottom: 2px;">Estilo Línea</label>
          <select class="form-select form-select-sm bg-input-sirio rule-dash" style="font-size: 10px; height: 25px;">
            <option value="" ${!dashArray ? 'selected' : ''}>Sólido</option>
            <option value="5, 5" ${dashArray === '5, 5' ? 'selected' : ''}>Discontinuo</option>
            <option value="2, 4" ${dashArray === '2, 4' ? 'selected' : ''}>Punteado</option>
            <option value="10, 5, 2, 5" ${dashArray === '10, 5, 2, 5' ? 'selected' : ''}>Raya-Punto</option>
          </select>
        </div>

        <!-- Icono (Solo para puntos) -->
        <div style="flex: 1.2;">
          <label style="font-size: 8px; text-transform:uppercase; color: #888; display:block; margin-bottom: 2px;">Icono (fa-icon)</label>
          <input type="text" class="form-control form-control-sm bg-input-sirio rule-icon" placeholder="Ej: fa-anchor" value="${icon}" style="font-size: 10px; height: 25px;">
        </div>
      </div>
    </div>
  `;
  container.insertAdjacentHTML('beforeend', html);
}

async function saveLayerSymbology() {
  const layerId = document.getElementById('symbologyLayerId').value;
  const field = document.getElementById('symbologyField').value;
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;

  const rules = [];
  document.querySelectorAll('#symbologyRulesContainer > div').forEach(div => {
    const val = div.querySelector('.rule-value').value;
    const color = div.querySelector('.rule-color').value;
    const weight = parseFloat(div.querySelector('.rule-weight').value) || 3;
    const dashArray = div.querySelector('.rule-dash').value;
    const icon = div.querySelector('.rule-icon').value;
    const size = weight; // Reutilizamos el campo weight para el radio de puntos por simplicidad en UI

    if (val) {
      rules.push({ 
        value: val, 
        color: color,
        weight: weight,
        dashArray: dashArray,
        icon: icon,
        size: size
      });
    }
  });

  layer.symbology = { field, rules };

  try {
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
    const response = await fetch(`/api/vector_layers/${layerId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ symbology: layer.symbology })
    });

    if (response.ok) {
      showMapMessage('Simbología guardada y aplicada', 'success');
      // Forzar re-renderizado
      if (layer.leafletLayer) {
        layer.leafletLayer.clearLayers();
        layer.geojson.features.forEach(f => renderFeatureOnMap(layer, f));
      }
      document.getElementById('floatLayerSymbology').remove();
    } else {
      showMapMessage('Error al guardar en servidor', 'error');
    }
  } catch (error) {
    console.error('Error al guardar simbología:', error);
    showMapMessage('Error al guardar simbología', 'error');
  }
}

function openCreateVectorLayerModal() {
  const form = document.getElementById('formCreateVectorLayer');
  if (form) {
    form.reset();
    document.getElementById('vectorLayerColor').value = '#ff9800';
    document.querySelectorAll('input[name="vectorLayerType"]').forEach(rb => rb.checked = false);
  }

  const modalEl = document.getElementById('modalCreateVectorLayer');
  if (modalEl && typeof bootstrap !== 'undefined') {
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }
}

function openManageVectorLayersPanel() {
  _isLayersPanelOpen = true;

  // Cerrar modal de Bootstrap si estuviera abierto (por compatibilidad)
  const modalEl = document.getElementById('modalManageVectorLayers');
  if (modalEl && typeof bootstrap !== 'undefined') {
    bootstrap.Modal.getInstance(modalEl)?.hide();
  }

  // Si ya existe el panel flotante, vaciarlo y reconstruirlo (para reactividad de tema)
  let panel = document.getElementById('floatManageLayers');
  if (panel) panel.remove();

  panel = document.createElement('div');
  panel.id = 'floatManageLayers';
  panel.className = 'gis-float-panel digitize-panel-floating';

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || (!document.documentElement.getAttribute('data-theme') && !document.body.classList.contains('light-theme'));
  const sirioBlue = '#294a60';
  const sirioOrange = '#ff9800';
  const carbonBg = isDark ? '#0c0c0c' : '#ffffff';
  const titleColor = isDark ? sirioOrange : '#fff';

  // Centrar panel
  const width = 850;
  const left = (window.innerWidth - width) / 2;
  const top = 100;

  panel.style.cssText = `
    position: fixed; top: ${top}px; left: ${left}px;
    width: ${width}px; max-height: 80vh; z-index: 10500;
    background: ${carbonBg};
    border: 1px solid ${isDark ? sirioOrange : sirioBlue};
    border-radius: 8px; box-shadow: 0 15px 50px rgba(0,0,0,0.6);
    font-family: var(--ds-font-mono,'Inter',sans-serif);
    overflow: hidden; display: flex; flex-direction: column;
  `;

  panel.innerHTML = `
    <div class="digitize-header digitize-draggable-handle" style="cursor:move; background: ${isDark ? '#050505' : sirioBlue}; color: ${titleColor}; border-bottom: 1px solid ${isDark ? 'rgba(255,152,0,0.4)' : 'transparent'}; flex-shrink: 0;">
      <span class="digitize-title" style="color: ${titleColor}; font-weight:800; letter-spacing:0.5px;">
        <i class="fa-solid fa-layer-group me-2" style="color: ${titleColor}; font-size:0.8rem;"></i>GESTOR DE CAPAS VECTORIALES
      </span>
      <button class="btn-close-digitize" style="color:${titleColor}; opacity:0.8;" onclick="document.getElementById('floatManageLayers').remove(); window.GISManager._onLayersPanelClose()">✕</button>
    </div>
    
    <div class="p-3" style="overflow-y: auto; flex-grow: 1; background: ${carbonBg}; color: ${isDark ? '#eee' : '#333'};">
      <div class="d-flex mb-3 flex-wrap">
        <button class="btn btn-sirio btn-sm" style="width: auto !important; margin-right: 5px !important;" onclick="window.GISManager.openCreateVectorLayerModal()">
          <i class="fa-solid fa-plus me-1"></i>Nueva Capa
        </button>
        <button class="btn btn-sirio btn-sm" style="width: auto !important; margin-right: 5px !important;" onclick="window.GISManager.refreshVectorLayersList()">
          <i class="fa-solid fa-rotate me-1"></i>Actualizar
        </button>
        <button class="btn btn-sirio btn-sm" style="width: auto !important; margin-right: 5px !important;" onclick="window.GISManager.exportAllVectorLayers()">
          <i class="fa-solid fa-download me-1"></i>Exportar Todas
        </button>
        <button class="btn btn-sirio btn-sm" style="width: auto !important; margin-right: 5px !important;" onclick="window.GISManager.toggleAllVectorLayersVisibility()">
          <i class="fa-solid fa-eye me-1"></i>Mostrar/Ocultar Todas
        </button>
        <div class="ms-auto d-flex gap-2 align-items-center">
          <span class="badge bg-secondary" id="layerCount" style="font-size:0.7rem;">0 capas</span>
        </div>
      </div>

      <div class="table-responsive" style="max-height: 400px; border: 1px solid ${isDark ? 'rgba(255,255,255,0.05)' : '#eee'}; border-radius: 4px;">
        <table class="table ${isDark ? 'table-dark' : 'table-light'} table-hover align-middle mb-0" id="vectorLayersTable" style="font-size: 0.75rem;">
          <thead class="sticky-top" style="top: 0; z-index: 10; background: ${isDark ? '#1a1a1a' : '#f8f9fa'};">
            <tr>
              <th style="width: 40px;"><input type="checkbox" class="form-check-input" onchange="window.GISManager.toggleSelectAllLayers(this.checked)"></th>
              <th style="width: 50px;">Color</th>
              <th>Nombre</th>
              <th style="width: 100px;">Tipo</th>
              <th style="width: 70px;" class="text-center">Feat.</th>
              <th style="width: 100px;">Métricas</th>
              <th style="width: 70px;" class="text-center">Vis.</th>
              <th style="width: 140px;" class="text-center">Acciones</th>
            </tr>
          </thead>
          <tbody id="vectorLayersTableBody">
            <!-- Cargado por refreshVectorLayersList -->
          </tbody>
        </table>
      </div>

      <div id="quickEditPanel" class="mt-3 p-3 border rounded d-none" style="background: ${isDark ? 'rgba(255,152,0,0.05)' : 'rgba(41,74,96,0.05)'}; border-color: ${isDark ? 'rgba(255,152,0,0.2)' : 'rgba(41,74,96,0.2)'} !important;">
        <h6 class="fw-bold mb-3" style="font-size:0.8rem; color:${isDark ? sirioOrange : sirioBlue};"><i class="fa-solid fa-pen me-2"></i>Edición Rápida</h6>
        <input type="hidden" id="quickEditLayerId">
        <div class="row g-2">
          <div class="col-md-6">
            <label class="form-label mb-1" style="font-size:0.65rem; font-weight:700;">Nombre</label>
            <input type="text" class="form-control form-control-sm" id="quickEditName" style="background:${isDark ? '#000' : '#fff'}; color:${isDark ? '#fff' : '#000'}; border-color:${isDark ? 'rgba(255,255,255,0.1)' : '#ccc'};">
          </div>
          <div class="col-md-3">
            <label class="form-label mb-1" style="font-size:0.65rem; font-weight:700;">Color</label>
            <input type="color" class="form-control form-control-sm form-control-color w-100" id="quickEditColor" style="height:31px;">
          </div>
          <div class="col-md-3">
            <label class="form-label mb-1" style="font-size:0.65rem; font-weight:700;">Opacidad (<span id="opacityValue">70%</span>)</label>
            <input type="range" class="form-range" id="quickEditOpacity" min="0" max="1" step="0.1" value="0.7">
          </div>
          <div class="col-md-4">
            <label class="form-label mb-1" style="font-size:0.65rem; font-weight:700;">Grosor (<span id="strokeValue">3px</span>)</label>
            <input type="range" class="form-range" id="quickEditStroke" min="1" max="10" step="1" value="3">
          </div>
          <div class="col-md-4 d-flex align-items-center pt-2">
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" id="quickEditLabels">
              <label class="form-check-label small" style="font-size:0.65rem;">Etiquetas</label>
            </div>
          </div>
          <div class="col-md-4 d-flex align-items-center pt-2">
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" id="quickEditSnap">
              <label class="form-check-label small" style="font-size:0.65rem;">Snap</label>
            </div>
          </div>
          <div class="col-12">
            <label class="form-label mb-1" style="font-size:0.65rem; font-weight:700;">Descripción</label>
            <textarea class="form-control form-control-sm" id="quickEditDesc" rows="2" style="background:${isDark ? '#000' : '#fff'}; color:${isDark ? '#fff' : '#000'}; border-color:${isDark ? 'rgba(255,255,255,0.1)' : '#ccc'};"></textarea>
          </div>
          <div class="col-12 text-end mt-2">
            <button class="btn btn-secondary btn-sm me-2" onclick="document.getElementById('quickEditPanel').classList.add('d-none')">CANCELAR</button>
            <button class="btn btn-sirio btn-sm" onclick="window.GISManager.saveQuickEdit()">
              <i class="fa-solid fa-save me-1"></i>Guardar Cambios
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(panel);
  if (typeof makeDraggable === 'function') makeDraggable(panel);

  refreshVectorLayersList();

  // Re-vincular eventos para sliders
  const opSlider = document.getElementById('quickEditOpacity');
  if (opSlider) {
    opSlider.oninput = function() {
      document.getElementById('opacityValue').textContent = `${Math.round(this.value * 100)}%`;
    };
  }
  const stSlider = document.getElementById('quickEditStroke');
  if (stSlider) {
    stSlider.oninput = function() {
      document.getElementById('strokeValue').textContent = `${this.value}px`;
    };
  }
}

function openManageVectorLayersModal() {
  // Ahora es un panel flotante
  openManageVectorLayersPanel();
}

function _onLayersPanelClose() {
  _isLayersPanelOpen = false;
}

// ========== ACCIONES MASIVAS ==========

function toggleSelectAllLayers(checked) {
  document.querySelectorAll('.layer-checkbox').forEach(cb => {
    cb.checked = checked;
  });
}

function exportAllVectorLayers() {
  const checkedIds = Array.from(document.querySelectorAll('.layer-checkbox:checked'))
    .map(cb => parseInt(cb.dataset.layerId));

  if (checkedIds.length === 0) {
    showMapMessage('Selecciona al menos una capa para exportar', 'warning');
    return;
  }

  checkedIds.forEach(id => exportVectorLayerById(id));
}

function toggleAllVectorLayersVisibility() {
  const allVisible = vectorLayers.every(l => l.visible);
  const newVisibility = !allVisible;

  vectorLayers.forEach(layer => {
    toggleVectorLayerVisibility(layer.id, newVisibility);
  });

  refreshVectorLayersList();
}

// ========== OPERACIONES INDIVIDUALES ==========

// toggleVectorLayerVisibility fue movida arriba y deduplicada

function zoomToVectorLayer(layerId) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.leafletLayer) return;

  let bounds = null;
  if (typeof layer.leafletLayer.getBounds === 'function') {
    bounds = layer.leafletLayer.getBounds();
  } else if (typeof layer.leafletLayer.getLayers === 'function') {
    // Es un LayerGroup, intentar combinar bounds de subcapas
    const sublayers = layer.leafletLayer.getLayers();
    if (sublayers.length > 0 && typeof sublayers[0].getBounds === 'function') {
      bounds = sublayers[0].getBounds();
      for (let i = 1; i < sublayers.length; i++) {
        if (typeof sublayers[i].getBounds === 'function') {
          bounds = bounds.extend(sublayers[i].getBounds());
        }
      }
    }
  }

  const targetMap = window.map || window._mapaCorpus;
  if (bounds && bounds.isValid && bounds.isValid() && targetMap) {
    targetMap.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
    showMapMessage(`Vista ajustada a "${layer.nombre}"`, 'info');
  } else {
    showMapMessage('No se pudo calcular la extensión de la capa (puede estar vacía o mal formada)', 'warning');
  }
}

async function exportVectorLayerById(layerId) {
  try {
    const response = await fetch(`/api/vector_layers/${layerId}/export`);
    if (!response.ok) throw new Error('Error al exportar');

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `capa_${layerId}.geojson`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    showMapMessage('Capa exportada correctamente', 'success');
  } catch (error) {
    console.error('Error al exportar:', error);
    showMapMessage('Error al exportar capa', 'error');
  }
}

function deleteVectorLayerConfirm(layerId) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;

  if (!confirm(`¿Estás seguro de eliminar la capa "${layer.nombre}"?\n\nEsta acción no se puede deshacer.`)) {
    return;
  }

  deleteVectorLayerById(layerId);
}

async function deleteVectorLayerById(layerId) {
  try {
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
    const response = await fetch(`/api/vector_layers/${layerId}`, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': csrfToken }
    });

    const result = await response.json();
    if (result.success) {
      showMapMessage(result.message, 'success');
      await loadVectorLayersFromDB();
      refreshVectorLayersList();
    } else {
      showMapMessage(result.error || 'Error al eliminar', 'error');
    }
  } catch (error) {
    console.error('Error:', error);
    showMapMessage('Error al eliminar capa', 'error');
  }
}

async function duplicateVectorLayer(layerId) {
  const original = vectorLayers.find(l => l.id == layerId);
  if (!original) return;

  try {
    if (typeof showMapMessage === 'function') showMapMessage(`Duplicando "${original.nombre}"...`, 'info');
    
    // Generar un color aleatorio para diferenciar la copia
    const randomColor = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');

    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
    const response = await fetch('/api/vector_layers', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({
        nombre: `${original.nombre} (Copia)`,
        tipo_geometria: original.tipo_geometria,
        color: randomColor,
        descripcion: original.descripcion || '',
        geojson: {
          type: 'FeatureCollection',
          features: (original.geojson?.features || []).map(f => ({
            type: 'Feature',
            geometry: f.geometry,
            properties: JSON.parse(JSON.stringify(f.properties || {}))
          }))
        }
      })
    });

    const result = await response.json();
    if (result.success && result.layer) {
      showMapMessage(`Capa duplicada correctamente`, 'success');
      await loadVectorLayersFromDB();
      refreshVectorLayersList();
      
      // Opcional: Activar la nueva capa
      setActiveVectorLayer(result.layer.id);
    } else {
      showMapMessage(result.error || 'Error al duplicar capa', 'error');
    }
  } catch (error) {
    console.error('Error al duplicar:', error);
    showMapMessage('Error al duplicar capa', 'error');
  }
}

// ========== RENDERIZADO DE FEATURES ==========

/**
 * Mapea un color hexadecimal o nombre a un color compatible con leaflet-color-markers
 */
function getMarkerColor(hex) {
  if (!hex) return 'blue';
  const color = hex.toLowerCase();
  
  // Mapeo directo de nombres comunes y hexes típicos
  const mapping = {
    '#ff4444': 'red', '#e53e3e': 'red', 'red': 'red',
    '#4caf50': 'green', '#2aad27': 'green', 'green': 'green',
    '#ff9800': 'orange', '#cb8427': 'orange', 'orange': 'orange',
    '#ffeb3b': 'yellow', '#cac428': 'yellow', 'yellow': 'yellow',
    '#ffd700': 'gold', '#ffd326': 'gold', 'gold': 'gold',
    '#9c2bcb': 'violet', '#8e44ad': 'violet', 'violet': 'violet',
    '#7b7b7b': 'grey', '#999999': 'grey', 'grey': 'grey',
    '#000000': 'black', '#333333': 'black', 'black': 'black'
  };

  if (mapping[color]) return mapping[color];

  // Búsqueda aproximada por categorías si no hay match exacto
  if (color.includes('red') || color.startsWith('#f') && color.length === 7 && parseInt(color.substring(3,5), 16) < 100) return 'red';
  if (color.includes('green')) return 'green';
  if (color.includes('blue') || color.startsWith('#2196f3')) return 'blue';
  if (color.includes('orange')) return 'orange';
  if (color.includes('yellow')) return 'yellow';
  
  return 'blue'; // Default
}

/**
 * Obtiene todos los campos disponibles en las propiedades de una capa
 */
function _getLayerFields(layer) {
  const fields = new Set(['name', 'description']);
  if (layer.geojson && layer.geojson.features) {
    layer.geojson.features.slice(0, 100).forEach(f => {
      if (f.properties) {
        Object.keys(f.properties).forEach(k => fields.add(k));
      }
    });
  }
  return Array.from(fields);
}

function renderFeatureOnMap(layer, feature) {
  const geom = feature.geometry;
  // Detección de tema (Respetar modo claro si el atributo es 'light')
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || (!document.documentElement.getAttribute('data-theme') && !document.body.classList.contains('light-theme'));
  if (!geom || !geom.type) return;

  let featureColor = layer.color;
  let featureWeight = layer.grosor_linea || 3;
  let featureDash = null;
  let featureIcon = null;
  let featureSize = 6; 

  // APLICAR SIMBOLOGÍA TEMÁTICA
  if (layer.symbology && layer.symbology.rules && layer.symbology.field) {
    const field = layer.symbology.field;
    const val = (feature.properties && feature.properties[field]) ? String(feature.properties[field]).toLowerCase() : '';

    for (const rule of layer.symbology.rules) {
      if (val.includes(rule.value.toLowerCase())) {
        featureColor = rule.color || featureColor;
        if (rule.weight) featureWeight = rule.weight;
        if (rule.dashArray) featureDash = rule.dashArray;
        if (rule.icon) featureIcon = rule.icon;
        if (rule.size) featureSize = rule.size;
        break;
      }
    }
  }

  const style = {
    color: featureColor,
    weight: featureWeight,
    opacity: layer.opacidad || 0.7,
    fillOpacity: (layer.opacidad || 0.7) * 0.5,
    dashArray: featureDash
  };

  let leafletFeature;

  if (geom.type === 'Point') {
    if (featureIcon) {
      // ICONO FontAwesome
      leafletFeature = L.marker([geom.coordinates[1], geom.coordinates[0]], {
        icon: L.divIcon({
          className: 'sirio-custom-icon',
          html: `<i class="fa-solid ${featureIcon}" style="color:${featureColor}; font-size:${featureSize}px; text-shadow: 0 0 3px ${isDark ? '#000' : '#fff'};"></i>`,
          iconSize: [featureSize, featureSize],
          iconAnchor: [featureSize / 2, featureSize / 2]
        })
      });
    } else {
      // ESTILO QGIS (Punto sólido)
      leafletFeature = L.circleMarker([geom.coordinates[1], geom.coordinates[0]], {
        radius: featureSize,
        fillColor: featureColor,
        fillOpacity: 1,
        color: isDark ? '#fff' : '#222',
        weight: 1.5,
        opacity: 0.8
      });
    }
  } else if (geom.type === 'LineString') {
    const coords = geom.coordinates.map(c => [c[1], c[0]]);
    leafletFeature = L.polyline(coords, {
      ...style,
      fill: false,
      fillColor: 'transparent',
      fillOpacity: 0
    });
  } else if (geom.type === 'Polygon') {
    const coords = geom.coordinates[0].map(c => [c[1], c[0]]);
    leafletFeature = L.polygon(coords, style);
  }

  if (leafletFeature) {
    // Vincular referencias mutualmente
    leafletFeature.feature = feature;
    feature.leafletLayer = leafletFeature;

    // Popup / Tooltip con información enriquecida (Atributos + Coordenadas)
    if (feature.properties) {
      const title = feature.properties.name || feature.properties.nombre || layer.nombre;
      const headerColor = isDark ? '#ff9800' : '#294a60';
      const headerText = isDark ? '#000' : '#fff';
      const bodyBg = isDark ? '#0f0f0f' : '#fff'; // Más oscuro para premium
      const bodyText = isDark ? '#eee' : '#333';
      
      // Construir lista de atributos excluyendo campos internos
      const exclude = ['name', 'nombre', 'description', 'desc', 'length', 'area', 'distancia'];
      const attributes = Object.entries(feature.properties)
        .filter(([key]) => !exclude.includes(key.toLowerCase()))
        .map(([key, val]) => `<div><strong style="color:${headerColor}; opacity:0.8;">${key}:</strong> ${val}</div>`)
        .join('');

      let popupHTML = `
        <div class="sirio-gis-popup" style="margin:-1px; border-radius:4px; overflow:hidden; font-family:var(--ds-font-mono,'Inter',sans-serif); border: 1px solid ${isDark ? 'rgba(255,152,0,0.5)' : headerColor}; box-shadow: ${isDark ? '0 0 20px rgba(0,0,0,0.5)' : 'none'};">
          <div style="background:${headerColor}; color:${headerText}; padding:4px 10px; font-weight:800; font-size:0.75rem; border-bottom:1px solid rgba(0,0,0,0.1); display:flex; justify-content:space-between; align-items:center; letter-spacing:0.5px;">
            <span style="text-transform:uppercase;">${title}</span>
            <button class="gis-popup-close-btn" style="color:${headerText};" onclick="window.map.closePopup()">✕</button>
          </div>
          <div style="padding:10px; background:${bodyBg}; color:${bodyText}; font-size:0.7rem; line-height:1.4;">
            ${feature.properties.description || feature.properties.desc ? `<div class="mb-2" style="border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:5px;">${feature.properties.description || feature.properties.desc}</div>` : ''}
            
            ${attributes ? `<div class="mb-2">${attributes}</div>` : ''}

            ${geom.type === 'Point' ? `
            <div style="margin-top:5px; padding-top:5px; border-top:1px solid rgba(255,255,255,0.1); font-size:0.65rem; color:${headerColor};">
              <strong>Lat:</strong> ${geom.coordinates[1].toFixed(6)}<br>
              <strong>Lng:</strong> ${geom.coordinates[0].toFixed(6)}
            </div>` : ''}
          </div>
        </div>
      `;
      leafletFeature.bindPopup(popupHTML, { className: 'sirio-popup-custom', minWidth: 180, maxWidth: 300 });
    }

    layer.leafletLayer.addLayer(leafletFeature);

    // Eventos de Selección y Menú Contextual
    leafletFeature.on('click', (e) => {
      L.DomEvent.stopPropagation(e);
      _onFeatureSelectClick(e);
    });

    leafletFeature.on('contextmenu', (e) => {
      L.DomEvent.stopPropagation(e);
      _onFeatureContextMenu(e, layer);
    });
  }
}

/**
 * Menú contextual para elementos del mapa (Eliminar / Reubicar)
 */
function _onFeatureContextMenu(e, layer) {
  const leafletFeature = e.target;
  const feature = leafletFeature.feature;
  if (!feature) return;

  const featureIdx = layer.geojson.features.indexOf(feature);
  if (featureIdx === -1) return;

  // BLOQUEO: Si la capa está bloqueada, no mostrar opciones de edición
  if (layer.bloqueada) {
    const popup = L.popup({ offset: [0, -5], className: 'gis-feature-context-menu' })
      .setLatLng(e.latlng)
      .setContent(`
        <div class="p-2 text-center" style="min-width:140px; font-family:var(--ds-font-mono, 'Inter', sans-serif);">
          <div class="mb-2 fw-bold text-muted" style="font-size:0.75rem; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:4px; text-transform:uppercase;">
            <i class="fa-solid fa-lock me-1"></i> ${feature.properties.name || feature.properties.nombre || 'Elemento'}
          </div>
          <div style="font-size:0.65rem; color:#aaa; margin-top:5px;">Capa Bloqueada</div>
        </div>
      `)
      .openOn(window.map || window._mapaCorpus);
    return;
  }

  const isPoint = feature.geometry.type === 'Point';
  
  const popup = L.popup({ offset: [0, -5], className: 'gis-feature-context-menu' })
    .setLatLng(e.latlng)
    .setContent(`
      <div class="p-2 text-center" style="min-width:140px; font-family:var(--ds-font-mono, 'Inter', sans-serif);">
        <div class="mb-2 fw-bold text-warning" style="font-size:0.75rem; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:4px; text-transform:uppercase;">
          ${feature.properties.name || feature.properties.nombre || 'Elemento'}
        </div>
        
        ${!isPoint ? `
        <button class="btn btn-xs btn-sirio w-100 mb-2 d-flex align-items-center justify-content-center gap-1" style="font-size:0.7rem; padding: 5px;"
                onclick="window.GISManager.activateScissorsTool('${layer.id}', ${featureIdx})">
          <i class="fa-solid fa-scissors" style="font-size:0.65rem;"></i> Cortar (Tijeras)
        </button>
        ` : ''}

        <button class="btn btn-xs btn-danger w-100 d-flex align-items-center justify-content-center gap-1" style="font-size:0.7rem; padding: 5px;"
                onclick="window.GISManager.deleteFeature('${layer.id}', ${featureIdx})">
          <i class="fa-solid fa-trash-can" style="font-size:0.65rem;"></i> Eliminar
        </button>
      </div>
    `)
    .openOn(window.map || window._mapaCorpus);
}

function startRelocatingFeature(layerId, featureIdx) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.geojson?.features[featureIdx]) return;

  if (layer.bloqueada) {
    if (typeof showMapMessage === 'function') showMapMessage("La capa está bloqueada", "warning");
    return;
  }

  const feature = layer.geojson.features[featureIdx];
  const lf = feature.leafletLayer;

  const targetMap = window.map || window._mapaCorpus;
  if (targetMap) targetMap.closePopup();

  if (feature.geometry.type === 'Point' && lf) {
    if (typeof showMapMessage === 'function') showMapMessage("Arrastra el punto a su nueva posición", "info");
    
    // Resaltar visualmente
    if (lf._icon) lf._icon.style.filter = 'brightness(1.5) drop-shadow(0 0 8px #ff9800)';
    
    lf.dragging.enable();
    
    lf.once('dragend', (e) => {
      const newLatLng = e.target.getLatLng();
      feature.geometry.coordinates = [newLatLng.lng, newLatLng.lat];
      
      saveVectorLayerToDatabase(layer).then(() => {
        lf.dragging.disable();
        if (lf._icon) lf._icon.style.filter = '';
        if (typeof showMapMessage === 'function') showMapMessage("Posición corregida", "success");
        if (document.getElementById('floatAttributeTable')) {
          openAttributeTable(layerId);
        }
      });
    });
  } else {
    // Para líneas/polígonos, simplemente abrir el editor de vértices
    toggleVertexEditing(layerId, featureIdx);
  }
}

// ========== GUARDAR CAMBIOS AL DIGITALIZAR ==========

async function saveVectorLayerToDatabase(layer) {
  if (!layer || !layer.id) return;

  // Construir GeoJSON desde el leafletLayer
  const features = [];
  layer.leafletLayer.eachLayer(leafletFeature => {
    // ONLY save if it's a real feature recognized by the system (has .feature property)
    // This prevents stray markers or temporary lines from being persisted.
    if (!leafletFeature.feature) return;

    let geometry;

    if (leafletFeature instanceof L.CircleMarker || leafletFeature instanceof L.Marker) {
      const latlng = leafletFeature.getLatLng();
      geometry = {
        type: 'Point',
        coordinates: [latlng.lng, latlng.lat]
      };
    } else if (leafletFeature instanceof L.Polyline && !(leafletFeature instanceof L.Polygon)) {
      const latlngs = leafletFeature.getLatLngs();
      geometry = {
        type: 'LineString',
        coordinates: latlngs.map(ll => [ll.lng, ll.lat])
      };
    } else if (leafletFeature instanceof L.Polygon) {
      const latlngs = leafletFeature.getLatLngs()[0];
      geometry = {
        type: 'Polygon',
        coordinates: [latlngs.map(ll => [ll.lng, ll.lat])]
      };
    }

    if (geometry) {
      features.push({
        type: 'Feature',
        geometry: geometry,
        properties: leafletFeature.feature?.properties || {}
      });
    }
  });

  const geojson = {
    type: 'FeatureCollection',
    features: features
  };

  try {
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
    const response = await fetch(`/api/vector_layers/${layer.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ geojson })
    });

    const result = await response.json();
    if (result.success) {
      console.log(`✅ Capa "${layer.nombre}" guardada (${features.length} features)`);
      return true;
    }
  } catch (error) {
    console.error('Error al guardar capa:', error);
  }

  return false;
}

// ========== ACTUALIZAR LISTA RÁPIDA EN MODAL UNIFICADO ==========

function refreshQuickList(layers) {
  const tbody = document.getElementById('vectorLayersQuickList');
  if (!tbody) return;

  if (!layers || layers.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="text-center text-muted py-3">
          <i class="fa-solid fa-layer-group opacity-50 mb-2 d-block"></i>
          <small>No hay capas vectoriales</small>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = '';
  layers.forEach(layer => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>
        <div style="width: 24px; height: 24px; background: ${layer.color}; border-radius: 3px; border: 1px solid rgba(255,255,255,0.2);"></div>
      </td>
      <td>
        <div class="fw-bold small">${layer.nombre}</div>
        <small class="text-muted" style="font-size: 0.7rem;">${layer.descripcion || ''}</small>
      </td>
      <td>
        <span class="badge ${getTypeBadgeClass(layer.tipo_geometria)} badge-sm">
          ${getTypeIcon(layer.tipo_geometria)} ${getTypeLabel(layer.tipo_geometria)}
        </span>
      </td>
      <td class="text-center">
        <span class="badge bg-secondary badge-sm">${layer.num_features || 0}</span>
      </td>
      <td>
        <div class="btn-group btn-group-sm" role="group">
          <button class="btn btn-outline-info btn-sm py-0" onclick="zoomToVectorLayer(${layer.id})" title="Zoom">
            <i class="fa-solid fa-crosshairs"></i>
          </button>
          <button class="btn btn-outline-success btn-sm py-0" onclick="exportVectorLayerById(${layer.id})" title="Exportar">
            <i class="fa-solid fa-download"></i>
          </button>
          <button class="btn btn-outline-danger btn-sm py-0" onclick="deleteVectorLayerConfirm(${layer.id})" title="Eliminar">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}


/**
 * Activa una capa para digitalización
 */
// setActiveVectorLayer consolidado arriba

// toggleVectorLayerVisibility consolidada arriba


// ========== TABLA DE ATRIBUTOS Y EDICIÓN AVANZADA ==========

function openAttributeTable(layerId) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) {
    if (typeof showMapMessage === 'function') showMapMessage("Capa no encontrada", "error");
    return;
  }

  const features = layer.geojson?.features || [];
  const isActive = activeVectorLayer && activeVectorLayer.id == layerId;
  if (features.length === 0) {
    if (typeof showMapMessage === 'function') showMapMessage("Esta capa no tiene elementos todavía", "info");
    return;
  }

  // Create floating panel
  const panelId = 'floatAttributeTable';
  const existing = document.getElementById(panelId);
  let prevTop = '80px', prevLeft = null;
  if (existing) {
    prevTop = existing.style.top;
    prevLeft = existing.style.left;
    existing.remove();
  }

  const panel = document.createElement('div');
  panel.id = panelId;
  panel.className = 'gis-float-panel digitize-panel-floating';

  const panelWidth = Math.min(950, window.innerWidth * 0.92);
  const panelLeft = prevLeft || ((window.innerWidth - panelWidth) / 2 + 'px');

  panel.style.cssText = `
      position: fixed;
      top: ${prevTop}; left: ${panelLeft};
      width: ${panelWidth}px;
      z-index: 10500;
      background: var(--ds-bg-panel, rgba(22,22,22,0.97));
      border: 1px solid var(--ds-border-color, #444);
      border-radius: 6px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.55);
      font-family: var(--ds-font-mono,'Inter',sans-serif);
      font-size: 0.72rem;
      overflow: hidden;
      display: flex; flex-direction: column;
    `;

  panel.innerHTML = `
      <div class="gis-float-header digitize-draggable-handle digitize-header" style="cursor:move; user-select:none;">
        <span class="digitize-title">
          <i class="fa-solid fa-table me-2"></i>Tabla de Atributos: ${layer.nombre}
        </span>
        <button class="btn-close-digitize" onclick="document.getElementById('${panelId}').remove()">✕</button>
      </div>
      <div style="overflow:auto; flex: 1; max-height:60vh;" id="attributeTableContentArea">
        <table class="table table-dark table-sm table-hover mb-0" style="font-size:0.68rem; border-collapse: separate; border-spacing: 0;">
          <thead class="sticky-top" style="top:0; background:var(--ds-bg-panel,#1a1a1a); z-index:10;">
            <tr>
              <th style="width:25px;"></th>
              <th style="width:30px;">#</th>
              <th style="width:40px;">Tipo</th>
              <th style="width:180px;">Coordenadas (Lat / Lon)</th>
              <th style="width:120px;">Nombre</th>
              <th>Descripción</th>
              ${Object.keys(features[0].properties || {}).filter(k => k !== 'name' && k !== 'description' && k !== 'length' && k !== 'area').map(k => `
                <th style="min-width:100px;">
                  <div class="d-flex align-items-center justify-content-between">
                    <span>${k}</span>
                    <button class="btn btn-link btn-sm p-0 m-0 text-danger" onclick="window.GISManager.deleteAttributeColumn(${layerId}, '${k}')" title="Borrar Columna">
                      <i class="fa-solid fa-minus-circle"></i>
                    </button>
                  </div>
                </th>
              `).join('')}
              <th style="width:130px;" class="text-end pe-3">
                <button class="btn btn-xs btn-sirio py-1 px-2" style="font-weight: 800; font-size: 0.65rem;" onclick="window.GISManager.addAttributeColumn(${layerId})">
                  <i class="fa-solid fa-plus me-1"></i>CAMPO
                </button>
              </th>
            </tr>
          </thead>
          <tbody id="attributeTableBody">
            ${features.map((f, idx) => {
    const isPoint = f.geometry.type === 'Point';
    const lon = isPoint ? (typeof f.geometry.coordinates[0] === 'number' ? f.geometry.coordinates[0].toFixed(6) : f.geometry.coordinates[0]) : '';
    const lat = isPoint ? (typeof f.geometry.coordinates[1] === 'number' ? f.geometry.coordinates[1].toFixed(6) : f.geometry.coordinates[1]) : '';
    const typeLabel = f.geometry.type === 'LineString' ? `Polilínea (${f.geometry.coordinates.length} vérts.)` :
      f.geometry.type === 'Polygon' ? `Polígono (${f.geometry.coordinates[0].length} vérts.)` : 'Punto';

    const customProps = Object.keys(f.properties || {}).filter(k => k !== 'name' && k !== 'description' && k !== 'length' && k !== 'area');
    const isExpanded = _expandedFeatures.has(`${layerId}-${idx}`);
    const canExpand = !isPoint;

    let rowHtml = `
                <tr data-feature-idx="${idx}" style="vertical-align:middle;">
                  <td class="text-center">
                    ${canExpand ? `
                      <button class="btn btn-link btn-xs p-0 text-muted" style="text-decoration:none;" onclick="window.GISManager.toggleFeatureExpansion('${layerId}', ${idx})">
                        <i class="fa-solid fa-chevron-${isExpanded ? 'down' : 'right'}"></i>
                      </button>
                    ` : ''}
                  </td>
                  <td>${idx + 1}</td>
                  <td class="text-center">
                    <i class="fa-solid fa-${f.geometry.type === 'Point' ? 'location-dot' : f.geometry.type === 'LineString' ? 'route' : 'draw-polygon'}" 
                       title="${f.geometry.type === 'Point' ? 'Punto' : f.geometry.type === 'LineString' ? 'Polilínea' : 'Polígono'}"></i>
                  </td>
                  <td>
                    ${isPoint ? `
                      <div class="d-flex gap-1">
                        <input type="text" class="form-control form-control-sm p-1 font-mono gis-attr-input" style="font-size:0.65rem; flex:1;"
                                value="${lat}" placeholder="Lat"
                                onchange="window.GISManager.updateFeatureCoordinateComponent(${layerId}, ${idx}, 1, this.value)">
                        <input type="text" class="form-control form-control-sm p-1 font-mono gis-attr-input" style="font-size:0.65rem; flex:1;"
                                value="${lon}" placeholder="Lon"
                                onchange="window.GISManager.updateFeatureCoordinateComponent(${layerId}, ${idx}, 0, this.value)">
                      </div>
                    ` : `<span class="text-muted" style="font-size:0.65rem;">${typeLabel}</span>`}
                  </td>
                  <td><input type="text" class="form-control form-control-sm p-1 gis-attr-input" style="font-size:0.68rem;"
                       value="${f.properties.name || ''}"
                       onchange="window.GISManager.updateFeatureProperty(${layerId}, ${idx}, 'name', this.value)"></td>
                  <td><input type="text" class="form-control form-control-sm p-1 gis-attr-input" style="font-size:0.68rem;"
                       value="${f.properties.description || ''}"
                       onchange="window.GISManager.updateFeatureProperty(${layerId}, ${idx}, 'description', this.value)"></td>
                  ${customProps.map(k => `
                    <td><input type="text" class="form-control form-control-sm p-1 gis-attr-input" style="font-size:0.68rem;"
                         value="${f.properties[k] || ''}"
                         onchange="window.GISManager.updateFeatureProperty(${layerId}, ${idx}, '${k}', this.value)"></td>
                  `).join('')}
                  <td style="font-size:0.65rem; position: relative; min-width:85px;">
                    ${(() => {
        const geom = f.geometry;
        let lengthKm = null, areaHa = null;

        if (geom.type === 'LineString') {
          // Use stored value or compute on-the-fly from coordinates
          if (f.properties.length) {
            lengthKm = parseFloat(f.properties.length);
          } else {
            let totalM = 0;
            const coords = geom.coordinates;
            for (let i = 0; i < coords.length - 1; i++) {
              const [lng1, lat1] = coords[i];
              const [lng2, lat2] = coords[i + 1];
              const R = 6371000;
              const dLat = (lat2 - lat1) * Math.PI / 180;
              const dLon = (lng2 - lng1) * Math.PI / 180;
              const sinDLat = Math.sin(dLat / 2);
              const sinDLon = Math.sin(dLon / 2);
              const a = sinDLat * sinDLat + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * sinDLon * sinDLon;
              totalM += R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
            }
            lengthKm = totalM / 1000;
            // Persist for future use
            f.properties.length = lengthKm.toFixed(2);
          }
        } else if (geom.type === 'Polygon') {
          if (f.properties.area) {
            areaHa = parseFloat(f.properties.area);
          } else {
            // Shoelace formula for area
            const coords = geom.coordinates[0];
            const R = 6371000;
            let area = 0;
            for (let i = 0; i < coords.length - 1; i++) {
              const [lng1, lat1] = coords[i], [lng2, lat2] = coords[i + 1];
              area += (lng2 - lng1) * Math.PI / 180 * (2 + Math.sin(lat1 * Math.PI / 180) + Math.sin(lat2 * Math.PI / 180));
            }
            areaHa = Math.abs(area * R * R / 2) / 10000;
            f.properties.area = areaHa.toFixed(2);
          }
        } else if (geom.type === 'Point') {
          // Show distance to next point if next feature is also a Point
          const next = features[idx + 1];
          if (next && next.geometry.type === 'Point') {
            const [lng1, lat1] = geom.coordinates;
            const [lng2, lat2] = next.geometry.coordinates;
            const R = 6371000;
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lng2 - lng1) * Math.PI / 180;
            const sinDLat = Math.sin(dLat / 2);
            const sinDLon = Math.sin(dLon / 2);
            const a = sinDLat * sinDLat + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * sinDLon * sinDLon;
            const distM = R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
            const distKm = distM / 1000;
            return `<div class="text-warning" style="font-size:0.6rem; line-height:1.2;" title="Distancia al siguiente punto">
                            <i class="fa-solid fa-arrow-down-long me-1" style="font-size:0.55rem;"></i>${distKm < 1 ? (distM).toFixed(0) + ' m' : distKm.toFixed(2) + ' km'}
                          </div>`;
          }
          return '<span class="text-muted" style="font-size:0.6rem;">—</span>';
        }

        let out = '';
        if (lengthKm !== null) {
          const segs = f.geometry.coordinates.length - 1;
          const avgKm = segs > 0 ? lengthKm / segs : 0;
          const dispLen = lengthKm >= 1 ? lengthKm.toFixed(2) + ' km' : (lengthKm * 1000).toFixed(0) + ' m';
          out += `<div class="text-info fw-bold" title="Longitud total (${segs} tramos, media: ${avgKm.toFixed(2)} km/tramo)">
                          <i class="fa-solid fa-ruler-combined me-1"></i>${dispLen}
                        </div>
                        <div class="text-muted" style="font-size:0.58rem;">${segs} seg · ⌀${(avgKm >= 1 ? avgKm.toFixed(2) + ' km' : (avgKm * 1000).toFixed(0) + ' m')}</div>`;
        }
        if (areaHa !== null) {
          const dispArea = areaHa >= 1 ? areaHa.toFixed(2) + ' ha' : (areaHa * 10000).toFixed(0) + ' m²';
          out += `<div class="text-success fw-bold" title="Área">
                          <i class="fa-solid fa-draw-polygon me-1"></i>${dispArea}
                        </div>`;
        }
        return out || '<span class="text-muted" style="font-size:0.6rem;">—</span>';
      })()}
                  </td>
                  <td class="text-end pe-3" style="white-space:nowrap;">
                    <!-- Edit Vertices (Pencil) -->
                    ${!isPoint ? `
                    <button class="btn btn-link btn-sm p-0 m-0 text-info me-2 ${(_editingFeatureId === `${layerId}-${idx}`) ? 'bg-info text-dark rounded-circle' : ''}" 
                            style="text-decoration:none; width:22px; height:22px; border:none; background:none; vertical-align:middle;"
                            onclick="window.GISManager.toggleVertexEditing('${layerId}', ${idx}); event.stopPropagation();" title="Editar Vértices">
                        <i class="fa-solid fa-pencil"></i>
                    </button>
                    ` : ''}

                    <!-- Scissors (Line only) -->
                    ${layer.tipo_geometria === 'line' ? `
                    <button class="btn btn-link btn-sm p-0 m-0 text-warning me-2" 
                            style="text-decoration:none; width:22px; height:22px; border:none; background:none; vertical-align:middle;"
                            onclick="window.GISManager.activateScissorsTool('${layerId}', ${idx}); event.stopPropagation();" title="Cortar con Tijeras">
                        <i class="fa-solid fa-scissors"></i>
                    </button>` : ''}

                    <!-- Relocate (Move) -->
                    <button class="btn btn-link btn-sm p-0 m-0 text-light me-2" 
                            style="text-decoration:none; width:22px; height:22px; border:none; background:none; vertical-align:middle;"
                            onclick="window.GISManager.startRelocatingFeature('${layerId}', ${idx}); event.stopPropagation();" title="Reposicionar">
                        <i class="fa-solid fa-arrows-up-down-left-right"></i>
                    </button>

                    <!-- Simplify -->
                    <button class="btn btn-link btn-sm p-0 m-0 text-warning me-2" 
                            style="text-decoration:none; width:22px; height:22px; border:none; background:none; vertical-align:middle;" 
                            onclick="window.GISManager.simplifyFeature('${layerId}', ${idx}); event.stopPropagation();" title="Simplificar Geometría">
                      <i class="fa-solid fa-wand-magic-sparkles"></i>
                    </button>

                    <!-- Save -->
                    <button class="btn btn-link btn-sm p-0 m-0 text-success me-2" 
                            style="text-decoration:none; width:22px; height:22px; border:none; background:none; vertical-align:middle;" 
                            onclick="window.GISManager.saveVectorLayerManual('${layerId}'); event.stopPropagation();" title="Guardar Cambios">
                      <i class="fa-solid fa-floppy-disk"></i>
                    </button>

                    <!-- Zoom -->
                    <button class="btn btn-link btn-sm p-0 m-0 text-info me-2" 
                            style="text-decoration:none; width:22px; height:22px; border:none; background:none; vertical-align:middle; color: #3498db !important;" 
                            onclick="window.GISManager.zoomToFeature('${layerId}', ${idx}); event.stopPropagation();" title="Zoom">
                      <i class="fa-solid fa-crosshairs"></i>
                    </button>

                    <!-- Delete (Two-Step Confirmation UI) -->
                    <button class="btn btn-link btn-sm p-0 m-0 text-danger" 
                            style="text-decoration:none; width:22px; height:22px; border:none; background:none; vertical-align:middle;" 
                            onclick="event.stopPropagation(); window.GISManager.confirmDeleteFeature(this, '${layerId}', ${idx});"
                            title="Eliminar">
                      <i class="fa-solid fa-trash"></i>
                    </button>
                  </td>
                </tr>`;

    if (isExpanded && (f.geometry.type === 'LineString' || f.geometry.type === 'Polygon')) {
      const coords = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates;
      rowHtml += `
                <tr class="vertex-list-row" style="background: rgba(0,0,0,0.2) !important;">
                  <td colspan="100" style="padding: 0;">
                    <div class="p-2 border-start border-4 border-info ms-4 my-1" style="max-height: 250px; overflow-y: auto;">
                      <div class="d-flex align-items-center mb-2 gap-2">
                        <span class="badge bg-info text-dark">Vértices (${coords.length})</span>
                        <small class="text-muted" style="font-size:0.65rem;">Edición manual de precisión</small>
                      </div>
                      <table class="table table-sm table-borderless mb-0 text-light" style="font-size: 0.65rem; background:transparent;">
                        <thead>
                          <tr class="text-muted opacity-75" style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <th style="width: 30px;">#</th>
                            <th class="ps-2">Latitud (Y)</th>
                            <th class="ps-2">Longitud (X)</th>
                            <th style="width: 40px;"></th>
                          </tr>
                        </thead>
                        <tbody>
                          ${coords.map((c, vIdx) => `
                            <tr>
                              <td class="align-middle text-info text-center" style="cursor:pointer; font-weight:bold;" 
                                  onclick="window.GISManager.centerOnVertex('${layerId}', ${idx}, ${vIdx})" title="Centrar mapa en este vértice">
                                ${vIdx + 1}
                              </td>
                              <td class="ps-2">
                                <input type="text" class="form-control form-control-sm p-1 font-mono bg-dark border-secondary text-info text-center" 
                                       style="font-size:0.62rem; height:22px;" value="${c[1]}" 
                                       onchange="window.GISManager.updateVertexCoordinate('${layerId}', ${idx}, ${vIdx}, 1, this.value)">
                              </td>
                              <td class="ps-2">
                                <input type="text" class="form-control form-control-sm p-1 font-mono bg-dark border-secondary text-info text-center" 
                                       style="font-size:0.62rem; height:22px;" value="${c[0]}" 
                                       onchange="window.GISManager.updateVertexCoordinate('${layerId}', ${idx}, ${vIdx}, 0, this.value)">
                              </td>
                              <td class="text-center align-middle">
                                <button class="btn btn-link btn-sm p-0 text-danger" onclick="window.GISManager.deleteVertex('${layerId}', ${idx}, ${vIdx})" title="Borrar Vértice">
                                  <i class="fa-solid fa-xmark"></i>
                                </button>
                              </td>
                            </tr>
                          `).join('')}
                        </tbody>
                      </table>
                    </div>
                  </td>
                </tr>`;
    }
    return rowHtml;
  }).join('')}
          </tbody>
        </table>
      </div>
      <div style="padding:10px 16px; display:flex; gap:10px; justify-content:flex-end;
                  background: var(--ds-bg-panel, rgba(20,20,20,0.95));
                  border-top:1px solid var(--ds-border-color,rgba(255,255,255,0.1));
                  position: relative;">
        <button class="btn btn-sm btn-info px-3 font-mono" onclick="window.GISManager.exportAttributeTable(${layerId})" style="height:32px; font-weight:700;">
          <i class="fa-solid fa-download me-1"></i>CSV
        </button>
        <button class="btn btn-sm btn-outline-secondary px-3 font-mono" onclick="document.getElementById('${panelId}').remove()" style="height:32px;">
          Cerrar
        </button>
        <div class="gj-resizable-handle"></div>
      </div>
    `;

  document.body.appendChild(panel);
  makeDraggable(panel);
  makeResizable(panel);

  // Prevent map interaction below panel
  if (typeof L !== 'undefined') {
    L.DomEvent.disableClickPropagation(panel);
    L.DomEvent.disableScrollPropagation(panel);
  }
}

function makeDraggable(element) {
  const handle = element.querySelector('.digitize-draggable-handle') || element;
  let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

  handle.onmousedown = dragMouseDown;

  function dragMouseDown(e) {
    e = e || window.event;
    e.preventDefault();
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    document.onmousemove = elementDrag;
  }

  function elementDrag(e) {
    e = e || window.event;
    e.preventDefault();
    pos1 = pos3 - e.clientX;
    pos2 = pos4 - e.clientY;
    pos3 = e.clientX;
    pos4 = e.clientY;
    element.style.top = (element.offsetTop - pos2) + "px";
    element.style.left = (element.offsetLeft - pos1) + "px";
  }

  function closeDragElement() {
    document.onmouseup = null;
    document.onmousemove = null;
  }
}

function makeResizable(element) {
  const handle = element.querySelector('.gj-resizable-handle');
  if (!handle) return;

  handle.addEventListener('mousedown', initResize, false);

  function initResize(e) {
    window.addEventListener('mousemove', resize, false);
    window.addEventListener('mouseup', stopResize, false);
    e.preventDefault();
  }

  function resize(e) {
    const rect = element.getBoundingClientRect();
    element.style.width = Math.max(400, (e.clientX - rect.left)) + 'px';
    const newHeight = Math.max(200, (e.clientY - rect.top));
    element.style.height = newHeight + 'px';
    const content = element.querySelector('#attributeTableContentArea');
    if (content) {
      content.style.maxHeight = 'none';
      content.style.height = (newHeight - 90) + 'px';
    }
  }

  function stopResize(e) {
    window.removeEventListener('mousemove', resize, false);
    window.removeEventListener('mouseup', stopResize, false);
  }
}

function addAttributeColumn(layerId) {
  const colNameRaw = prompt("Introduce el nombre de la nueva columna (solo letras y números):");
  if (!colNameRaw || colNameRaw.trim() === '') return;

  const colName = colNameRaw.trim().replace(/[^a-zA-Z0-9 _-]/g, '');
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.geojson?.features) return;

  layer.geojson.features.forEach(f => {
    if (!f.properties) f.properties = {};
    f.properties[colName] = '';
  });

  saveVectorLayerToDatabase(layer).then(() => {
    openAttributeTable(layerId);
  });
}

function deleteAttributeColumn(layerId, colName) {
  if (!confirm(`¿Estás seguro/a de querer borrar la columna "${colName}"?`)) return;
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.geojson?.features) return;

  layer.geojson.features.forEach(f => {
    if (f.properties) delete f.properties[colName];
  });

  saveVectorLayerToDatabase(layer).then(() => {
    openAttributeTable(layerId);
  });
}

function updateFeatureProperty(layerId, featureIdx, property, value) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.geojson?.features[featureIdx]) return;
  const feature = layer.geojson.features[featureIdx];
  feature.properties[property] = value;
  
  // Sync with Leaflet layer to ensure saveVectorLayerToDatabase sees the change
  if (feature.leafletLayer && feature.leafletLayer.feature) {
    if (!feature.leafletLayer.feature.properties) feature.leafletLayer.feature.properties = {};
    feature.leafletLayer.feature.properties[property] = value;
  }
  
  saveVectorLayerToDatabase(layer);
}

function centerOnVertex(layerId, featureIdx, vIdx) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.geojson?.features[featureIdx]) return;
  
  const f = layer.geojson.features[featureIdx];
  const coords = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates;
  const p = coords[vIdx];
  
  if (p) {
    const targetMap = window.map || window._mapaCorpus;
    if (targetMap) {
      targetMap.setView([p[1], p[0]], 18);
      
      // Visual feedback: brief pulse
      const pulse = L.circleMarker([p[1], p[0]], {
        radius: 10, color: '#00fbff', weight: 3, opacity: 1, fillOpacity: 0.2
      }).addTo(targetMap);
      
      let r = 10;
      const int = setInterval(() => {
        r += 2;
        pulse.setRadius(r);
        pulse.setStyle({ opacity: 1 - (r-10)/20, fillOpacity: 0.2 - (r-10)/100 });
        if (r > 30) {
          clearInterval(int);
          targetMap.removeLayer(pulse);
        }
      }, 30);
    }
  }
}

function saveVectorLayerManual(layerId) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;
  
  if (typeof showMapMessage === 'function') {
    showMapMessage("Guardando cambios...", "info");
  }
  
  saveVectorLayerToDatabase(layer).then(() => {
    if (typeof showMapMessage === 'function') {
      showMapMessage("Cambios guardados correctamente", "success");
    }
  }).catch(err => {
    if (typeof showMapMessage === 'function') {
      showMapMessage("Error al guardar cambios", "danger");
    }
  });
}

function updateFeatureCoordinateComponent(layerId, featureIdx, axis, value) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.geojson?.features[featureIdx]) return;

  const feature = layer.geojson.features[featureIdx];
  if (feature.geometry.type !== 'Point') return;

  const numValue = parseFloat(value.replace(',', '.'));
  if (isNaN(numValue)) return;

  // Actualizar geometría GeoJSON
  feature.geometry.coordinates[axis] = numValue;
  const lon = feature.geometry.coordinates[0];
  const lat = feature.geometry.coordinates[1];

  // Actualizar marcador visual en el mapa (Mover el existente, no crear uno nuevo)
  if (feature.leafletLayer) {
    feature.leafletLayer.setLatLng([lat, lon]);
    
    // Actualizar popup si tiene coordenadas visibles
    const layerName = layer.nombre;
    const featName = feature.properties.nombre || feature.properties.name || '';
    let popupHTML = `<strong>${layerName}</strong><br>`;
    if (featName) popupHTML += `${featName}<br>`;
    
    if (feature.geometry.type === 'Point') {
      popupHTML += `<small>Lat: ${lat.toFixed(6)}, Lng: ${lon.toFixed(6)}</small>`;
    }
    
    if (feature.leafletLayer.getPopup()) {
      // Si el popup tiene un formato especial (como el que acabamos de implementar), 
      // regenerar el contenido o simplemente cerrar/abrir.
      // Para simplificar y mantener el nuevo diseño, volvemos a llamar a render para este elemento
      renderFeatureOnMap(layer, feature);
    } else {
      feature.leafletLayer.bindPopup(popupHTML);
    }
  }

  // Persistir cambios
  saveVectorLayerToDatabase(layer);
}

function zoomToFeature(layerId, featureIdx) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;
  const feature = layer.geojson.features[featureIdx];
  const geom = feature.geometry;
  const targetMap = window.map || window._mapaCorpus;
  if (!targetMap) return;

  if (geom.type === 'Point') {
    targetMap.setView([geom.coordinates[1], geom.coordinates[0]], 16);
  } else {
    const coords = (geom.type === 'Polygon') ? geom.coordinates[0] : geom.coordinates;
    const bounds = L.latLngBounds(coords.map(c => [c[1], c[0]]));
    targetMap.fitBounds(bounds, { padding: [50, 50] });
  }
}

function deleteFeature(layerId, featureIdx, skipConfirm = false) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.geojson?.features[featureIdx]) return;

  if (layer.bloqueada) {
    if (typeof showMapMessage === 'function') showMapMessage("La capa está bloqueada y no se puede editar", "warning");
    return;
  }

  if (!skipConfirm && !confirm('¿Eliminar este elemento?')) return;

  // Cleanup vertex editing if this is the feature being edited
  const currentId = `${layerId}-${featureIdx}`;
  if (typeof _editingFeatureId !== 'undefined' && _editingFeatureId === currentId) {
    stopVertexEditing();
  }

  // Obtener referencia al feature y su capa Leaflet antes de borrar del array
  const feature = layer.geojson.features[featureIdx];
  const leafletFeature = feature.leafletLayer;

  // 1. Eliminar del array GeoJSON
  layer.geojson.features.splice(featureIdx, 1);
  layer.num_features = layer.geojson.features.length;

  // 2. Eliminar de la capa Leaflet (Group) para que no se re-calcule al guardar
  if (leafletFeature && layer.leafletLayer) {
    layer.leafletLayer.removeLayer(leafletFeature);
  }

  // 3. Guardar cambios en DB
  saveVectorLayerToDatabase(layer).then(() => {
    // 4. Refrescar interfaz
    openAttributeTable(layerId);
    // Opcional: recargar capas para asegurar sincronía perfecta
    // loadVectorLayersFromDB(); 
  }).catch(err => {
    console.error("Error al eliminar elemento:", err);
    if (typeof showMapMessage === 'function') showMapMessage("Error al eliminar elemento", "error");
  });
}

function exportAttributeTable(layerId) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;
  const headers = ['ID', 'Tipo', 'Nombre', 'Descripción'];
  const rows = layer.geojson.features.map((f, idx) => [idx + 1, f.geometry.type, f.properties.name || '', f.properties.description || '']);
  const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `atributos_${layer.nombre}.csv`;
  link.click();
}

// ========== SNAPPING, MEDICIÓN Y ANÁLISIS ESPACIAL ==========

let snappingEnabled = true;
const SNAP_TOLERANCE_PIXELS = 15;

function findNearestVertex(latlng) {
  if (!snappingEnabled) return latlng;

  let nearestPoint = null;
  let minDistance = Infinity;
  const targetMap = window.map || window._mapaCorpus;
  if (!targetMap) return latlng;

  const zoom = targetMap.getZoom();
  const snapTolerance = (SNAP_TOLERANCE_PIXELS / Math.pow(2, zoom)) * 0.1;

  vectorLayers.forEach(layer => {
    if (!layer.visible || !layer.geojson?.features) return;

    layer.geojson.features.forEach(feature => {
      const geom = feature.geometry;
      
      // 1. Check direct vertices first (higher priority/exact points)
      let coords = [];
      if (geom.type === 'Point') {
        coords = [[geom.coordinates[1], geom.coordinates[0]]];
      } else if (geom.type === 'LineString') {
        coords = geom.coordinates.map(c => [c[1], c[0]]);
      } else if (geom.type === 'Polygon') {
        coords = geom.coordinates[0].map(c => [c[1], c[0]]);
      }

      coords.forEach(([lat, lng]) => {
        const dist = Math.sqrt(Math.pow(latlng.lat - lat, 2) + Math.pow(latlng.lng - lng, 2));
        if (dist < minDistance && dist < snapTolerance) {
          minDistance = dist;
          nearestPoint = L.latLng(lat, lng);
        }
      });

      // 2. Check segments (Vertex-to-Line Snapping)
      if (geom.type === 'LineString' || geom.type === 'Polygon') {
        try {
          // Usamos turf para encontrar el punto más cercano en la línea/perímetro
          const pt = turf.point([latlng.lng, latlng.lat]);
          let line;
          if (geom.type === 'LineString') {
            line = turf.lineString(geom.coordinates);
          } else {
            line = turf.lineString(geom.coordinates[0]);
          }

          const snapped = turf.nearestPointOnLine(line, pt);
          if (snapped && snapped.properties.dist !== undefined) {
              // Convertir distancia de turf (km) a grados aproximados para comparar con snapTolerance
              // 0.1 grados es aprox 11km. snapTolerance es pequeño.
              // Mejor comparar directamente en grados si es posible o usar turf.distance
              const distInDegrees = Math.sqrt(Math.pow(latlng.lat - snapped.geometry.coordinates[1], 2) + Math.pow(latlng.lng - snapped.geometry.coordinates[0], 2));
              
              if (distInDegrees < minDistance && distInDegrees < snapTolerance) {
                minDistance = distInDegrees;
                nearestPoint = L.latLng(snapped.geometry.coordinates[1], snapped.geometry.coordinates[0]);
              }
          }
        } catch (e) {
          console.warn("Error in segment snapping:", e);
        }
      }
    });
  });

  if (nearestPoint) {
    return nearestPoint;
  }
  return latlng;
}

/**
 * Finds the nearest point on any feature to a given latlng.
 * Returns { feature, vertexIndex, latlng }
 */
function _findNearestFeaturePoint(latlng) {
  const targetMap = window.map || window._mapaCorpus;
  if (!targetMap) return null;

  let nearest = null;
  let minDistance = Infinity;
  const zoom = targetMap.getZoom();
  const snapTolerance = (SNAP_TOLERANCE_PIXELS / Math.pow(2, zoom)) * 0.15; // Slightly more generous for tracing

  vectorLayers.forEach(layer => {
    if (!layer.visible || !layer.geojson?.features) return;
    layer.geojson.features.forEach(feature => {
      const geom = feature.geometry;
      if (geom.type === 'Point') return; // Points are harder to trace along

      const coords = geom.type === 'Polygon' ? geom.coordinates[0] : geom.coordinates;
      coords.forEach((c, idx) => {
        const dist = Math.sqrt(Math.pow(latlng.lat - c[1], 2) + Math.pow(latlng.lng - c[0], 2));
        if (dist < minDistance && dist < snapTolerance) {
          minDistance = dist;
          nearest = { feature, vertexIndex: idx, latlng: L.latLng(c[1], c[0]) };
        }
      });
    });
  });
  return nearest;
}

/**
 * Extracts a range of vertices between two indices.
 * For polygons, handles wrapping and finds the shortest path.
 */
function _getTracePath(feature, startIdx, endIdx) {
  const coords = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates[0] : feature.geometry.coordinates;
  const len = coords.length;

  // Convert to Leaflet LatLngs
  const points = coords.map(c => L.latLng(c[1], c[0]));

  if (feature.geometry.type === 'Polygon') {
    // Find shortest path around the ring
    const path1 = [];
    let i = startIdx;
    while (i !== endIdx) {
      path1.push(points[i]);
      i = (i + 1) % (len - 1); // Skip the duplicate last point in ring calc
    }
    path1.push(points[endIdx]);

    const path2 = [];
    i = startIdx;
    while (i !== endIdx) {
      path2.push(points[i]);
      i = (i - 1 + (len - 1)) % (len - 1);
    }
    path2.push(points[endIdx]);

    return (path1.length <= path2.length) ? path1 : path2;
  } else {
    // Simple linear range
    const step = startIdx < endIdx ? 1 : -1;
    const path = [];
    for (let i = startIdx; i !== endIdx; i += step) {
      path.push(points[i]);
    }
    path.push(points[endIdx]);
    return path;
  }
}

function toggleTraceMode() {
  _traceActive = !_traceActive;
  _traceAnchor = null;
  if (_tracePreviewLine && window.map) window.map.removeLayer(_tracePreviewLine);
  _tracePreviewLine = null;

  const btn = document.getElementById('btn-toggle-trace');
  if (btn) {
    btn.classList.toggle('active', _traceActive);
    btn.innerHTML = `<i class="fa-solid fa-route"></i> Trazado: ${_traceActive ? 'ON' : 'OFF'}`;
  }

  if (typeof showMapMessage === 'function') {
    showMapMessage(_traceActive ? "Modo Trazado ACTIVO: Haz clic en un vértice existente para empezar" : "Modo Trazado DESACTIVADO", "info");
  }
}

function toggleSnapping() {
  snappingEnabled = !snappingEnabled;
  const btn = document.getElementById('btn-toggle-snap');
  if (btn) {
    btn.classList.toggle('active', snappingEnabled);
    btn.innerHTML = `<i class="fa-solid fa-magnet"></i> Snap: ${snappingEnabled ? 'ON' : 'OFF'}`;
  }
  if (typeof showMapMessage === 'function') showMapMessage(`Snapping ${snappingEnabled ? 'activado' : 'desactivado'}`, "info");
}

let measurementDisplay = null;
let currentDistUnit = 'km';
let currentAreaUnit = 'ha';

function updateRealTimeMeasurement(digitizeMode, digitizePoints) {
  if (!digitizePoints || digitizePoints.length === 0) return;

  let measurement = '';
  if (digitizeMode === 'line') {
    let totalLength = 0;
    let lastSegment = 0;
    for (let i = 0; i < digitizePoints.length - 1; i++) {
      const d = digitizePoints[i].distanceTo(digitizePoints[i + 1]);
      totalLength += d;
      if (i === digitizePoints.length - 2) lastSegment = d;
    }

    const distUnits = {
      'm': { val: totalLength, sVal: lastSegment, label: 'm' },
      'km': { val: totalLength / 1000, sVal: lastSegment / 1000, label: 'km' },
      'mi': { val: totalLength / 1609.34, sVal: lastSegment / 1609.34, label: 'mi' },
      'nmi': { val: totalLength / 1852, sVal: lastSegment / 1852, label: 'nm' }
    };

    const unitKey = currentDistUnit || 'km';
    const u = distUnits[unitKey] || distUnits['km'];
    // We don't include the unit label here because the dropdown already displays it
    measurement = `<span title="Total">${u.val.toFixed(u.val < 10 ? 3 : 2)}</span>`;
    if (digitizePoints.length > 1) {
      measurement += ` <small class="text-muted" style="font-size:0.65em; font-weight:normal;" title="Último tramo">(+${u.sVal.toFixed(u.sVal < 10 ? 3 : 2)})</small>`;
    }

  } else if (digitizeMode === 'polygon' && digitizePoints.length >= 3) {
    if (typeof calculateArea === 'function') {
      const areaM2 = calculateArea(digitizePoints);
      const areaUnits = {
        'm2': { val: areaM2, label: 'm²' },
        'km2': { val: areaM2 / 1000000, label: 'km²' },
        'ha': { val: areaM2 / 10000, label: 'ha' },
        'ac': { val: areaM2 / 4046.86, label: 'ac' }
      };
      const u = areaUnits[currentAreaUnit] || areaUnits['ha'];
      measurement = `${u.val.toFixed(u.val < 10 ? 3 : 2)}`;
    }
  }

  const measureEl = document.getElementById('realtime-measurement');
  if (measureEl && measurement) {
    measureEl.innerHTML = `<i class="fa-solid fa-ruler"></i> ${measurement}`;
  }
}

function setMeasurementUnit(type, unit) {
  if (type === 'dist') currentDistUnit = unit;
  if (type === 'area') currentAreaUnit = unit;

  // Immediate update if digitizing
  // We use window.digitizeMode and window.digitizePoints to access the state from mapa_corpus.html
  if (typeof window.digitizeMode !== 'undefined' && window.digitizeMode && typeof window.digitizePoints !== 'undefined') {
    updateRealTimeMeasurement(window.digitizeMode, window.digitizePoints);
  }
}

function openBufferAnalysisModal() {
  if (!activeVectorLayer) {
    if (typeof showMapMessage === 'function') showMapMessage("Selecciona una capa vectorial primero", "warning");
    return;
  }
  const features = activeVectorLayer.geojson?.features || [];
  const pointFeatures = features.filter(f => f.geometry.type === 'Point');

  if (pointFeatures.length === 0) {
    if (typeof showMapMessage === 'function') showMapMessage("La capa no tiene puntos para analizar", "info");
    return;
  }

  const panelId = 'floatBufferAnalysis';
  const existing = document.getElementById(panelId);
  if (existing) existing.remove();

  // Detección de tema (Respetar modo claro si el atributo es 'light')
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || (!document.documentElement.getAttribute('data-theme') && !document.body.classList.contains('light-theme'));
  const sirioColor = isDark ? '#ff9800' : '#3498db';
  const sirioText = isDark ? '#000' : '#fff';

  const panel = document.createElement('div');
  panel.id = panelId;
  panel.className = 'gis-float-panel digitize-panel-sirio digitize-panel-floating';
  panel.style.cssText = `
      position: fixed; top: 100px; right: 20px; width: 340px; z-index: 10500;
    `;

  let pointSelectorHTML = '';
  if (pointFeatures.length > 1) {
    pointSelectorHTML = `
      <div class="mb-3">
        <label class="stat-label mb-1" style="display:block; font-size: 0.65rem; text-transform: uppercase; opacity: 0.7;">Elemento a Analizar</label>
        <select id="bufferPointTarget" class="digitize-input w-100" style="height: 32px; font-size: 0.75rem; background: rgba(0,0,0,0.3); color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 0 8px;">
          <option value="all">--- Todos los puntos ---</option>
          ${pointFeatures.map((f, i) => `<option value="${i}">${f.properties.name || f.properties.nombre || `Punto ${i + 1}`}</option>`).join('')}
        </select>
      </div>`;
  }

  panel.innerHTML = `
      <div class="digitize-header digitize-draggable-handle" style="cursor:move; padding: 10px 12px; display:flex; align-items:center; gap:10px;">
        <i class="fa-solid fa-grip-vertical" style="opacity: 0.3; font-size: 0.8rem;"></i>
        <div class="flex-grow-1">
          <div class="d-flex align-items-center justify-content-between">
            <span class="digitize-title" style="font-size: 0.85rem; letter-spacing: 0.5px; font-weight:700;">
              <i class="fa-solid fa-circle-dot me-2"></i>BUFFER / ZONAS
            </span>
            <button class="btn-close-digitize" style="font-size: 0.7rem; opacity: 0.6;" onclick="document.getElementById('${panelId}').remove()">✕</button>
          </div>
        </div>
      </div>

      <div class="digitize-stats px-3 py-2">
         <div class="d-flex justify-content-between align-items-center">
            <span class="stat-label" style="font-size: 0.6rem; text-transform: uppercase; opacity: 0.6;">Capa activa</span>
            <span class="stat-value fw-bold text-warning" style="font-size: 0.75rem;">${activeVectorLayer.nombre}</span>
         </div>
      </div>
      
      <div class="digitize-form p-3">
        ${pointSelectorHTML}

        <div class="mb-3">
          <label class="stat-label mb-1" style="display:block; font-size: 0.65rem; text-transform: uppercase; opacity: 0.7;">Radio del Buffer</label>
          <div class="input-group">
            <input type="number" id="bufferRadius" class="digitize-input flex-grow-1" value="1" min="0.1" step="0.1" 
                   style="height: 34px; font-size: 0.85rem; background: rgba(0,0,0,0.3); border-right:none; border-top-right-radius:0; border-bottom-right-radius:0;">
            <select id="bufferUnit" class="digitize-input" 
                    style="width: 100px; height: 34px; font-size: 0.75rem; background: ${sirioColor}; color: ${sirioText}; border-color: ${sirioColor}; font-weight:bold; border-top-left-radius:0; border-bottom-left-radius:0;">
              <option value="m">metros</option>
              <option value="km">km</option>
              <option value="nm">nm</option>
            </select>
          </div>
        </div>

        <div class="mb-3">
          <label class="stat-label mb-1" style="display:block; font-size: 0.65rem; text-transform: uppercase; opacity: 0.7;">Nombre del Resultado</label>
          <input type="text" id="bufferLayerName" class="digitize-input w-100" value="Buffer ${activeVectorLayer.nombre}" 
                 style="height: 32px; font-size: 0.75rem; background: rgba(0,0,0,0.3);">
        </div>

        <div class="mb-1">
          <label class="stat-label mb-1" style="display:block; font-size: 0.65rem; text-transform: uppercase; opacity: 0.7;">Color de la zona</label>
          <input type="color" id="bufferColor" class="form-control form-control-color w-100" value="${sirioColor}" 
                 style="height:32px; padding:2px; border:1px solid rgba(255,255,255,0.1); background:rgba(0,0,0,0.2);">
        </div>
      </div>

      <div class="digitize-actions p-3 d-flex gap-2" style="background: rgba(0,0,0,0.15); border-top: 1px solid rgba(255,255,255,0.05);">
        <button class="btn btn-sm btn-outline-secondary flex-grow-1" style="height: 36px; font-size: 0.75rem; border-color: rgba(255,255,255,0.1); color:#aaa; font-weight:700;" 
                onclick="document.getElementById('${panelId}').remove()">
          CANCELAR
        </button>
        <button class="btn btn-sm btn-warning flex-grow-1 fw-bold" 
                style="height: 36px; font-size: 0.75rem; background:${sirioColor} !important; color:${sirioText} !important; border:none; box-shadow: 0 4px 15px rgba(0,0,0,0.3);" 
                onclick="window.GISManager.executeBufferAnalysis()">
          <i class="fa-solid fa-play me-1"></i>CREAR BUFFER
        </button>
      </div>
    `;

  document.body.appendChild(panel);
  makeDraggable(panel);
}

async function executeBufferAnalysis() {
  const radius = parseFloat(document.getElementById('bufferRadius').value);
  const unit = document.getElementById('bufferUnit').value;
  const layerName = document.getElementById('bufferLayerName').value;
  const color = document.getElementById('bufferColor').value;
  const targetIdxAttr = document.getElementById('bufferPointTarget')?.value;

  if (!radius || radius <= 0) {
    if (typeof showMapMessage === 'function') showMapMessage("Ingresa un radio válido", "warning");
    return;
  }

  // Conversión a metros
  let bufferMeters = radius;
  if (unit === 'km') bufferMeters = radius * 1000;
  if (unit === 'nm') bufferMeters = radius * 1852; // Millas Náuticas

  const bufferDegrees = bufferMeters / 111000;

  const bufferFeatures = [];
  const pointFeatures = activeVectorLayer.geojson.features.filter(f => f.geometry.type === 'Point');

  pointFeatures.forEach((feature, idx) => {
    // Filtrar si se ha seleccionado un punto específico
    if (targetIdxAttr !== undefined && targetIdxAttr !== 'all' && parseInt(targetIdxAttr) !== idx) return;

    const geom = feature.geometry;
    const center = [geom.coordinates[1], geom.coordinates[0]];
    const circlePoints = [];
    for (let i = 0; i <= 32; i++) {
        const angle = (i / 32) * 2 * Math.PI;
        const lat = center[0] + bufferDegrees * Math.cos(angle);
        const lng = center[1] + bufferDegrees * Math.sin(angle);
        circlePoints.push([lng, lat]);
    }
    bufferFeatures.push({
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [circlePoints] },
        properties: {
          name: `Buffer ${feature.properties.name || feature.properties.nombre || 'Sin nombre'}`,
          description: `Zona de influencia ${radius} ${unit}`,
          buffer_radius: radius, buffer_unit: unit,
          original_id: feature.id || null
        }
    });
  });

  if (bufferFeatures.length === 0) {
    if (typeof showMapMessage === 'function') showMapMessage("No se pudieron crear buffers (solo soportado para puntos)", "error");
    return;
  }

  try {
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
    const response = await fetch('/api/vector_layers', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({
        proyecto_id: window.proyectoActivo?.id,
        nombre: layerName,
        tipo_geometria: 'polygon',
        color: color,
        opacidad: 0.5,
        grosor_linea: 2,
        visible: true,
        geojson: { type: 'FeatureCollection', features: bufferFeatures }
      })
    });

    if (response.ok) {
      if (typeof showMapMessage === 'function') showMapMessage(`Buffer creado: ${bufferFeatures.length} zonas`, "success");
      const floatBuffer = document.getElementById('floatBufferAnalysis');
      if (floatBuffer) floatBuffer.remove();
      loadVectorLayersFromDB();
    }
  } catch (error) {
    console.error('Error creating buffer:', error);
  }
}

async function suggestLocationFromText() {
  const name = document.getElementById('digitize-feature-name')?.value.trim();
  if (!name) {
    if (typeof showMapMessage === 'function') showMapMessage("Introduce un nombre para buscar la ubicación", "warning");
    return;
  }

  if (typeof showMapMessage === 'function') showMapMessage(`Buscando "${name}"...`, "info");

  try {
    const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(name)}&limit=1`);
    const data = await response.json();

    if (data && data.length > 0) {
      const result = data[0];
      const lat = parseFloat(result.lat);
      const lon = parseFloat(result.lon);
      const targetMap = window.map || window._mapaCorpus;

      if (confirm(`He encontrado: ${result.display_name}. ¿Deseas situar el elemento ahí?`)) {
        if (targetMap) targetMap.flyTo([lat, lon], 15);
        if (typeof createPointFeature === 'function') {
          createPointFeature(L.latLng(lat, lon));
        }
      }
    } else {
      if (typeof showMapMessage === 'function') showMapMessage("No se encontró la ubicación", "warning");
    }
  } catch (e) {
    console.error("Geocoding error:", e);
  }
}


// ========== PRO FEATURES ==========

// -------- 1. CSV IMPORT --------
// Triggers a file input dialog to import CSV with lat,lon,name,description
function importCSVToLayer(layerId) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) {
    if (typeof showMapMessage === 'function') showMapMessage('Capa no encontrada', 'error');
    return;
  }

  // Create hidden file input
  let input = document.createElement('input');
  input.type = 'file';
  input.accept = '.csv,text/csv';
  input.style.display = 'none';
  document.body.appendChild(input);

  input.onchange = function () {
    const file = input.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (e) {
      const text = e.target.result;
      const lines = text.trim().split('\n');
      if (lines.length < 2) {
        if (typeof showMapMessage === 'function') showMapMessage('El CSV está vacío o sin datos', 'warning');
        return;
      }

      // Auto-detect header row
      const header = lines[0].toLowerCase().split(/[,;]/).map(h => h.trim().replace(/"/g, ''));
      const latIdx = header.findIndex(h => h.includes('lat'));
      const lonIdx = header.findIndex(h => h.includes('lon') || h.includes('lng'));
      const nameIdx = header.findIndex(h => h.includes('name') || h.includes('nombre'));
      const descIdx = header.findIndex(h => h.includes('desc'));

      if (latIdx === -1 || lonIdx === -1) {
        if (typeof showMapMessage === 'function') showMapMessage('El CSV debe tener columnas de latitud y longitud', 'error');
        return;
      }

      if (!layer.geojson) layer.geojson = { type: 'FeatureCollection', features: [] };
      if (!layer.geojson.features) layer.geojson.features = [];

      let imported = 0, skipped = 0;
      lines.slice(1).forEach((line, idx) => {
        const cols = line.split(/[,;]/).map(c => c.trim().replace(/"/g, ''));
        const lat = parseFloat(cols[latIdx]);
        const lon = parseFloat(cols[lonIdx]);
        if (isNaN(lat) || isNaN(lon)) { skipped++; return; }

        const name = nameIdx >= 0 ? (cols[nameIdx] || `Punto ${imported + 1}`) : `Punto ${imported + 1}`;
        const description = descIdx >= 0 ? (cols[descIdx] || '') : '';

        const feature = {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [lon, lat] },
          properties: { name, description }
        };

        layer.geojson.features.push(feature);
        renderFeatureOnMap(layer, feature);
        imported++;
      });

      layer.num_features = layer.geojson.features.length;
      saveVectorLayerToDatabase(layer).then(() => {
        addVectorLayerToPanel(layer);
        if (typeof showMapMessage === 'function') {
          showMapMessage(`✅ Importados ${imported} puntos${skipped > 0 ? ` (${skipped} filas omitidas)` : ''}`, 'success');
        }
      });
    };
    reader.readAsText(file);
    document.body.removeChild(input);
  };

  input.click();
}

// -------- 2. FEATURE LABELS (toggle) --------
function toggleLayerLabels(layerId) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.leafletLayer) return;

  layer.etiquetas_visibles = !layer.etiquetas_visibles;

  layer.leafletLayer.eachLayer(leafletFeature => {
    if (layer.etiquetas_visibles) {
      const name = leafletFeature.feature?.properties?.name;
      if (name) {
        leafletFeature.bindTooltip(name, {
          permanent: true,
          direction: 'top',
          className: 'gis-label-tooltip',
          offset: [0, -6]
        }).openTooltip();
      }
    } else {
      leafletFeature.unbindTooltip();
    }
  });

  // Persist the toggle state
  const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
  fetch(`/api/vector_layers/${layerId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({ etiquetas_visibles: layer.etiquetas_visibles })
  }).catch(console.error);

  // Update the sidebar button state
  const btn = document.querySelector(`[data-vector-layer-id="${layerId}"] .btn-labels-toggle`);
  if (btn) {
    btn.classList.toggle('active', layer.etiquetas_visibles);
    btn.title = layer.etiquetas_visibles ? 'Ocultar etiquetas' : 'Mostrar etiquetas en el mapa';
  }

  if (typeof showMapMessage === 'function') {
    showMapMessage(layer.etiquetas_visibles ? 'Etiquetas activadas' : 'Etiquetas desactivadas', 'info');
  }
}

// -------- 3. HEATMAP (point layers only) --------
let _activeHeatmaps = {}; // layerId -> heatLayer

function toggleHeatmap(layerId) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;

  const targetMap = window.map || window._mapaCorpus;
  if (!targetMap) return;

  if (!window.L || typeof L.heatLayer === 'undefined') {
    if (typeof showMapMessage === 'function') showMapMessage('Leaflet.heat no está disponible', 'error');
    return;
  }

  const btn = document.querySelector(`[data-vector-layer-id="${layerId}"] .btn-heatmap-toggle`);

  if (_activeHeatmaps[layerId]) {
    // Turn off: remove heat, show markers again
    targetMap.removeLayer(_activeHeatmaps[layerId]);
    delete _activeHeatmaps[layerId];
    if (layer.leafletLayer) layer.leafletLayer.addTo(targetMap);
    if (btn) { btn.classList.remove('active'); btn.title = 'Activar Heatmap'; }
    if (typeof showMapMessage === 'function') showMapMessage('Heatmap desactivado', 'info');
  } else {
    // Turn on: hide markers, show heat
    const points = [];
    layer.geojson?.features?.forEach(f => {
      if (f.geometry?.type === 'Point') {
        const [lon, lat] = f.geometry.coordinates;
        points.push([lat, lon, 1]);
      }
    });

    if (points.length === 0) {
      if (typeof showMapMessage === 'function') showMapMessage('Solo capas de puntos soportan heatmap', 'warning');
      return;
    }

    if (layer.leafletLayer) targetMap.removeLayer(layer.leafletLayer);
    const heat = L.heatLayer(points, {
      radius: 28, blur: 18, maxZoom: 18,
      gradient: { 0.2: '#0d47a1', 0.4: '#1565c0', 0.6: '#ffa000', 0.8: '#e65100', 1.0: '#b71c1c' }
    }).addTo(targetMap);
    _activeHeatmaps[layerId] = heat;

    if (btn) { btn.classList.add('active'); btn.title = 'Desactivar Heatmap'; }
    if (typeof showMapMessage === 'function') showMapMessage(`🔥 Heatmap activado (${points.length} puntos)`, 'success');
  }
}

// -------- 4. SELECTION MODE --------
let _selectionModeActive = false;
let _selectedFeatures = []; // Array for multi-selection

function toggleSelectionMode() {
  const targetMap = window.map || window._mapaCorpus;
  if (!targetMap) return;

  _selectionModeActive = !_selectionModeActive;

  const btn = document.getElementById('btn-gis-selection-mode');
  if (btn) btn.classList.toggle('active', _selectionModeActive);

  if (_selectionModeActive) {
    if (typeof window.deactivateDigitizeMode === 'function') {
      window.deactivateDigitizeMode(true);
    }
    console.log('🔵 Selection Mode ON');
    const container = targetMap.getContainer();
    container.style.cssText += 'cursor: default !important;';

    // Disable map movement while selecting
    if (targetMap.dragging) targetMap.dragging.disable();
    if (targetMap.boxZoom) targetMap.boxZoom.disable();
    if (targetMap.doubleClickZoom) targetMap.doubleClickZoom.disable();

    if (typeof showMapMessage === 'function') showMapMessage('Modo selección: arrastra para crear un recuadro o haz clic', 'info');

    // Setup Box Selection Events
    targetMap.on('mousedown', _onBoxMouseDown);

    // Listen for feature clicks
    vectorLayers.forEach(layer => {
      if (layer.leafletLayer) {
        if (layer.leafletLayer.eachLayer) {
          layer.leafletLayer.eachLayer(f => {
            f.off('click', _onFeatureSelectClick);
            f.on('click', _onFeatureSelectClick);
            if (f.setStyle) f.setStyle({ interactive: true });
            if (f.getElement) {
              const el = f.getElement();
              if (el) el.style.cursor = 'pointer';
            }
          });
        }
      }
    });

    // Actualizar el panel si existe para reflejar el modo selección
    const panel = document.querySelector('.digitize-panel-sirio');
    if (panel) {
      const sub = panel.querySelector('.digitize-subtitle');
      if (sub) sub.textContent = 'Modo Selección';
      const icon = panel.querySelector('.digitize-title i');
      if (icon) {
        icon.className = 'fa-solid fa-mouse-pointer me-2';
      }
    }
  } else {
    console.log('⚪ Selection Mode OFF');
    targetMap.getContainer().style.cursor = '';

    // Cleanup Box Selection Events
    targetMap.off('mousedown', _onBoxMouseDown);
    _clearBoxSelection();

    // Re-enable map movement
    if (targetMap.dragging) targetMap.dragging.enable();
    if (targetMap.boxZoom) targetMap.boxZoom.enable();
    if (targetMap.doubleClickZoom) targetMap.doubleClickZoom.enable();

    vectorLayers.forEach(layer => {
      if (layer.leafletLayer && layer.leafletLayer.eachLayer) {
        layer.leafletLayer.eachLayer(f => {
          f.off('click', _onFeatureSelectClick);
          if (f.getElement) {
            const el = f.getElement();
            if (el) el.style.cursor = '';
          }
        });
      }
    });
    _clearFeatureSelection();
    document.getElementById('floatFeatureEditor')?.remove();
  }
}

// Box Selection Internal State
let _boxSelectStart = null;
let _boxSelectRect = null;

function _onBoxMouseDown(e) {
  if (!_selectionModeActive) return;
  _boxSelectStart = e.latlng;
  const targetMap = window.map || window._mapaCorpus;

  targetMap.on('mousemove', _onBoxMouseMove);
  targetMap.once('mouseup', _onBoxMouseUp);

  // Prevent map dragging if it managed to stay enabled
  if (e.originalEvent) e.originalEvent.preventDefault();
}

function _onBoxMouseMove(e) {
  if (!_boxSelectStart) return;
  const targetMap = window.map || window._mapaCorpus;

  const bounds = L.latLngBounds(_boxSelectStart, e.latlng);

  if (!_boxSelectRect) {
    _boxSelectRect = L.rectangle(bounds, {
      color: "#ff9800",
      weight: 1,
      fillOpacity: 0.1,
      dashArray: '5, 5',
      interactive: false
    }).addTo(targetMap);
  } else {
    _boxSelectRect.setBounds(bounds);
  }
}

function _onBoxMouseUp(e) {
  const targetMap = window.map || window._mapaCorpus;
  targetMap.off('mousemove', _onBoxMouseMove);

  if (!_boxSelectStart) return;

  const endPoint = e.latlng;
  const bounds = L.latLngBounds(_boxSelectStart, endPoint);

  // Minimal distance check to distinguish from a simple click
  const dist = _boxSelectStart.distanceTo(endPoint);
  if (dist > 10) {
    _performBoxSelection(bounds);
  }

  _clearBoxSelection();
  _boxSelectStart = null;
}

function _clearBoxSelection() {
  const targetMap = window.map || window._mapaCorpus;
  if (_boxSelectRect && targetMap) {
    targetMap.removeLayer(_boxSelectRect);
  }
  _boxSelectRect = null;
}

function _performBoxSelection(bounds) {
  console.log('📦 Performing box selection with bounds:', bounds);
  const center = bounds.getCenter();
  const _turf = window.turf || turf;
  const hasTurf = typeof _turf !== 'undefined';
  let boxPoly = null;
  if (hasTurf) {
    boxPoly = _turf.bboxPolygon([bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()]);
  }

  const foundThisPass = [];

  vectorLayers.forEach(layer => {
    if (layer.leafletLayer && layer.leafletLayer.eachLayer) {
      layer.leafletLayer.eachLayer(f => {
        let intersects = false;
        if (hasTurf && f.feature) {
          try {
            // Support for all geometry types via booleanIntersects
            intersects = _turf.booleanIntersects(f.feature, boxPoly);
          } catch (err) {
            console.warn("Turf intersection check failed for feature:", f.feature, err);
            // Fallback to simpler bounds check if Turf fails or geometry is invalid (e.g. unclosed ring)
            if (f.getBounds) {
              intersects = bounds.intersects(f.getBounds());
            } else if (f.getLatLng) {
              intersects = bounds.contains(f.getLatLng());
            }
          }
        } else if (f.getBounds) {
          intersects = bounds.intersects(f.getBounds());
        } else if (f.getLatLng) {
          intersects = bounds.contains(f.getLatLng());
        }

        if (intersects) {
          foundThisPass.push({ target: f, layer });
        }
      });
    }
  });

  if (foundThisPass.length > 0) {
    _clearFeatureSelection();
    foundThisPass.forEach(item => {
      _onFeatureSelectClick({ target: item.target, stopPropagation: () => { } }, false);
    });
    if (typeof showMapMessage === 'function') {
      showMapMessage(`Seleccionados ${foundThisPass.length} elementos. Pulsa REDUCIR para simplificar.`, 'info');
    }
  }
}

function _onFeatureSelectClick(e, openEditor = true) {
  // console.log('🎯 _onFeatureSelectClick hit', e.target, 'Editor:', openEditor);
  
  // PRIORIDAD: Si hay alguna herramienta de medición o inspección activa, ignorar clic en geometría
  if (window._activeMeasureMode || window._magnifyingGlass || window._radiusQueryActive) {
    return;
  }

  if (e.stopPropagation) e.stopPropagation();

  // GUARDA TIJERAS: Bloquear el editor si estamos cortando
  if (typeof _scissorsActive !== 'undefined' && _scissorsActive) {
    console.log('✂️ Scissors active, ignoring selection');
    return;
  }

  const leafletFeature = e.target;
  const feature = leafletFeature.feature;
  if (!feature) return;

  // Find which layer owns this feature
  let ownerLayer = null, featureIdx = -1;
  vectorLayers.forEach(layer => {
    const idx = layer.geojson?.features?.indexOf(feature);
    if (idx !== undefined && idx >= 0) {
      ownerLayer = layer;
      featureIdx = idx;
    }
  });

  if (!ownerLayer || featureIdx < 0) return;

  // REQUISITO: Solo reaccionar si la capa propietaria es la ACTIVA
  if (!activeVectorLayer || activeVectorLayer.id !== ownerLayer.id) {
    return;
  }

  // BLOQUEO: Si la capa está bloqueada, no permitir selección para edición
  if (ownerLayer.bloqueada) {
    if (openEditor && typeof showMapMessage === 'function') {
      showMapMessage("La capa está bloqueada", "info");
    }
    return;
  }

  // If not opening editor, we might be adding to a multi-selection
  if (openEditor) _clearFeatureSelection();

  // Highlight selected feature
  if (typeof leafletFeature.setStyle === 'function') {
    leafletFeature.setStyle({
      color: '#ffc107',
      weight: 6,
      fillOpacity: 0.5,
      dashArray: '0'
    });
  }

  _selectedFeatures.push({ layer: ownerLayer, idx: featureIdx, leafletFeature });

  // Resaltar Marcadores (Pins) ya que no tienen setStyle
  if (leafletFeature instanceof L.Marker && leafletFeature._icon) {
    leafletFeature._icon.style.filter = 'brightness(1.2) drop-shadow(0 0 5px #ff9800)';
    leafletFeature._icon.style.transition = 'filter 0.2s';
  }

  if (openEditor) {
    _openFeatureEditorPanel(ownerLayer, featureIdx);
  }
}

function _clearFeatureSelection() {
  _selectedFeatures.forEach(info => {
    const lf = info.leafletFeature;
    const layer = info.layer;
    
    if (lf instanceof L.Marker && lf._icon) {
      lf._icon.style.filter = '';
    }

    if (lf && typeof lf.setStyle === 'function') {
      lf.setStyle({
        color: layer.color || '#3388ff',
        weight: layer.grosor_linea || 3,
        fillOpacity: 0.3,
        dashArray: null
      });
    }
  });
  _selectedFeatures = [];
  
  // Also stop vertex editing if selection is cleared
  if (typeof stopVertexEditing === 'function') {
    stopVertexEditing();
  }
}

function _openFeatureEditorPanel(layer, featureIdx) {
  _currentEditingFeatureInfo = { layer, featureIdx };
  document.getElementById('floatFeatureEditor')?.remove();

  const feature = layer.geojson.features[featureIdx];
  const props = feature.properties || {};

  const panel = document.createElement('div');
  panel.id = 'floatFeatureEditor';
  panel.className = 'gis-float-panel digitize-panel-floating';

  // Set explicit width and center it without transform to avoid drag jumps
  const width = 455;
  const left = (window.innerWidth - width) / 2;
  const top = window.innerHeight - 450;

  // Detección de tema (Respetar modo claro si el atributo es 'light')
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || (!document.documentElement.getAttribute('data-theme') && !document.body.classList.contains('light-theme'));
  const sirioBlue = '#294a60';
  const sirioOrange = '#ff9800';
  const carbonBg = isDark ? '#0c0c0c' : '#ffffff';
  
  const inputBorder = isDark ? 'rgba(255,152,0,0.2)' : '#ccc';
  const titleColor = isDark ? sirioOrange : '#fff';
  
  const saveBtnStyle = isDark ? 
    'background: #ff9800; color:#000; border:none; box-shadow: 0 0 15px rgba(255, 152, 0, 0.4);' : 
    'background: #e0e0e0; color:#333; border: 1px solid #ccc; box-shadow: 0 0 10px rgba(41, 74, 96, 0.3);'; // Gray with Sirio Blue reflection

  panel.style.cssText = `
    position: fixed; top: ${top}px; left: ${left}px;
    width: ${width}px; z-index: 10600;
    background: ${carbonBg};
    border: 1px solid ${isDark ? sirioOrange : sirioBlue};
    border-radius: 8px; box-shadow: 0 15px 50px rgba(0,0,0,0.6);
    font-family: var(--ds-font-mono,'Inter',sans-serif);
    font-size: 0.72rem; overflow: hidden;
  `;

  const geomType = feature.geometry.type === 'Point' ? 'PUNTO' :
    feature.geometry.type === 'LineString' ? 'LÍNEA' : 'POLÍGONO';
  const displayTitle = props.name || `${geomType} ${featureIdx + 1}`;

  panel.innerHTML = `
    <div class="digitize-header digitize-draggable-handle" style="cursor:move; background: ${isDark ? '#050505' : sirioBlue}; color: ${titleColor}; border-bottom: 1px solid ${isDark ? 'rgba(255,152,0,0.4)' : 'transparent'};">
      <span class="digitize-title" style="color: ${titleColor}; font-weight:800; letter-spacing:0.5px;">
        <i class="fa-solid fa-pen-nib me-2" style="color: ${titleColor}; font-size:0.8rem;"></i>EDITAR: ${displayTitle}
      </span>
      <button class="btn-close-digitize" style="color:${titleColor}; opacity:0.8;" onclick="document.getElementById('floatFeatureEditor').remove(); window.GISManager._clearFeatureSelection()">✕</button>
    </div>
    
    <div class="digitize-stats" style="padding: 6px 12px; font-size: 0.65rem; color: ${isDark ? sirioOrange : '#666'}; background: ${isDark ? '#070707' : '#f0f0f0'}; display:flex; justify-content:space-between; border-bottom: 1px solid ${isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'};">
       <div class="stat-item" style="text-align:left; font-weight:700;">
         <i class="fa-solid fa-layer-group me-1"></i> ${layer.nombre}
       </div>
       <div class="stat-item" style="text-align:right; font-weight:700;">
         ${props.length ? `<span>${props.length} km</span>` : props.area ? `<span>${props.area} ha</span>` : ''}
       </div>
    </div>

    <div class="digitize-form" style="padding: 15px; border:none; background:${carbonBg};">
      <div class="mb-3">
        <label class="stat-label" style="margin-bottom:4px; color:${isDark ? '#888' : '#555'}; text-transform:uppercase; font-size:0.6rem; letter-spacing:1px; font-weight:800;">Nombre del elemento</label>
        <input id="featureEditorName" class="digitize-input" value="${props.name || ''}" placeholder="Ej: Ruta Norte..." style="border: 1px solid ${inputBorder}; background:${isDark ? 'rgba(0,0,0,0.2)' : '#fff'}; color:${isDark ? '#eee' : '#333'};">
      </div>
      
      <div class="mb-3">
        <label class="stat-label" style="margin-bottom:4px; color:${isDark ? '#888' : '#555'}; text-transform:uppercase; font-size:0.6rem; letter-spacing:1px; font-weight:800;">Descripción / Notas</label>
        <textarea id="featureEditorDesc" class="digitize-input" rows="2" style="resize:none; border: 1px solid ${inputBorder}; background:${isDark ? 'rgba(0,0,0,0.2)' : '#fff'}; color:${isDark ? '#eee' : '#333'};" placeholder="Detalles opcionales...">${props.description || ''}</textarea>
      </div>

      <div class="digitize-actions px-3 pb-3" style="padding:0; margin-top:12px; display:flex; gap:8px;">
        <button class="btn-digitize" 
                style="flex:1; border:1px solid ${isDark ? 'rgba(255,255,255,0.1)' : '#ccc'}; background:${isDark ? 'rgba(255,255,255,0.02)' : '#f8f8f8'}; color: ${isDark ? '#aaa' : '#666'}; font-weight: 700; font-size: 0.62rem; letter-spacing: 0.6px; text-transform: uppercase;" 
                onclick="document.getElementById('floatFeatureEditor').remove(); window.GISManager._clearFeatureSelection()">
          CANCELAR
        </button>
        <button class="btn-digitize ${(_editingFeatureId === `${layer.id}-${featureIdx}`) ? 'active' : ''}" 
                style="flex:1.2; background: ${isDark ? '#ff9800' : sirioBlue}; color:#fff; border:none; border-radius:4px; font-weight: 700; font-size: 0.62rem; letter-spacing: 0.6px; text-transform: uppercase; transition: all 0.2s;" 
                onclick="window.GISManager.toggleVertexEditing('${layer.id}', ${featureIdx})">
          <i class="fa-solid fa-vector-square me-1"></i>VÉRTICES
        </button>
        ${feature.geometry.type === 'LineString' ? `
        <button class="btn-digitize" 
                style="flex:1.5; background:rgba(67, 160, 71, 0.1); color:#4caf50; border:1px solid rgba(67, 160, 71, 0.3); border-radius:4px; font-weight: 700; font-size: 0.62rem; letter-spacing: 0.6px; text-transform: uppercase;" 
                onclick="window.GISManager.continueLineDigitizing('${layer.id}', ${featureIdx})">
          <i class="fa-solid fa-plus me-1"></i>CONTINUAR
        </button>` : ''}
        <button class="btn-digitize" 
                style="flex:1.5; ${saveBtnStyle} border-radius:4px; font-weight: 800; font-size: 0.62rem; letter-spacing: 0.6px; text-transform: uppercase;" 
                onclick="window.GISManager._saveFeatureEditorPanel('${layer.id}', ${featureIdx})">
          <i class="fa-solid fa-check me-1"></i>GUARDAR
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(panel);
  if (typeof makeDraggable === 'function') makeDraggable(panel);
  if (typeof L !== 'undefined') {
    L.DomEvent.disableClickPropagation(panel);
    L.DomEvent.disableScrollPropagation(panel);
  }
}

function _saveFeatureEditorPanel(layerId, featureIdx) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;

  const feature = layer.geojson.features[featureIdx];
  if (!feature) return;

  const name = document.getElementById('featureEditorName')?.value || '';
  const desc = document.getElementById('featureEditorDesc')?.value || '';

  // 1. Sincronizar con el objeto GeoJSON de la capa
  feature.properties.name = name;
  feature.properties.description = desc;

  // 2. Sincronizar con el objeto Leaflet (CRÍTICO para que saveVectorLayerToDatabase lo vea)
  const selectedInfo = _selectedFeatures.find(s => s.layer.id == layerId && s.idx == featureIdx);
  if (!selectedInfo || !selectedInfo.leafletFeature) {
    console.warn('⚠️ No leaflet feature found in selection for sync');
    saveVectorLayerToDatabase(layer).then(() => {
      document.getElementById('floatFeatureEditor')?.remove();
      _clearFeatureSelection();
    });
    return;
  }

  const lf = selectedInfo.leafletFeature;
  if (!lf.feature) lf.feature = { type: 'Feature', properties: {} };
  lf.feature.properties.name = name;
  lf.feature.properties.description = desc;

  // 3. Actualizar el Tooltip visual
  lf.unbindTooltip();
  if (layer.etiquetas_visibles && name) {
    lf.bindTooltip(name, { permanent: true, direction: 'top', className: 'gis-label-tooltip', offset: [0, -6] }).openTooltip();
  }

  saveVectorLayerToDatabase(layer).then(() => {
    document.getElementById('floatFeatureEditor')?.remove();
    _clearFeatureSelection();
    if (typeof showMapMessage === 'function') showMapMessage('✅ Feature actualizado', 'success');
  });
}

/**
 * Inicia el digitador con la geometría de una línea existente para continuarla
 */
function continueLineDigitizing(layerId, featureIdx) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;

  const feature = layer.geojson.features[featureIdx];
  if (!feature || feature.geometry.type !== 'LineString') return;

  // 1. Cerrar editor
  document.getElementById('floatFeatureEditor')?.remove();
  window.GISManager._clearFeatureSelection();

  // 2. Preparar el digitador para continuar
  window.GISManager.setActiveVectorLayer(layer.id);

  if (typeof startDigitizing === 'function') {
    startDigitizing('line');

    // 3. Inyectar coordenadas existentes
    if (typeof window.continueExistingLine === 'function') {
      window.continueExistingLine(feature.geometry.coordinates);
      // Marcamos que estamos en modo "edición/continuación"
      window.isContinuingFeature = { layerId, featureIdx };

      if (typeof showMapMessage === 'function') {
        showMapMessage("Continuando línea: Haz clic para añadir nuevos puntos", "success");
      }
    }
  }
}

/**
 * Simplifica la geometría de un feature existente (Línea o Polígono)
 */
function simplifyFeature(layerId, featureIdx) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.geojson?.features[featureIdx]) return;

  const feature = layer.geojson.features[featureIdx];
  if (feature.geometry.type === 'Point') return;

  const originalCount = feature.geometry.type === 'LineString' ?
    feature.geometry.coordinates.length :
    feature.geometry.coordinates[0].length;

  try {
    const _turf = window.turf || turf;
    if (!_turf) {
      console.error("Turf.js not found");
      if (typeof showMapMessage === 'function') showMapMessage("Turf.js no disponible", "error");
      return;
    }

    console.log(`🔄 Simplifying ${feature.geometry.type} (${originalCount} pts)...`);
    const tolerance = 0.0005; // ~50 meters, much more noticeable
    const simplified = _turf.simplify(feature, { tolerance: tolerance, highQuality: true });

    const newCount = simplified.geometry.type === 'LineString' ?
      simplified.geometry.coordinates.length :
      simplified.geometry.coordinates[0].length;

    if (newCount >= originalCount) {
      if (typeof showMapMessage === 'function') showMapMessage("Geometría optimizada al máximo", "info");
      // Still open editor to show current data
      _onFeatureSelectClick({ target: feature.leafletLayer, stopPropagation: () => { } }, true);
      return;
    }

    // Actualizar GeoJSON
    feature.geometry.coordinates = simplified.geometry.coordinates;

    // Actualizar visualización en Leaflet
    if (feature.leafletLayer) {
      const latlngs = feature.geometry.type === 'LineString' ?
        feature.geometry.coordinates.map(c => [c[1], c[0]]) :
        feature.geometry.coordinates[0].map(c => [c[1], c[0]]);

      feature.leafletLayer.setLatLngs(latlngs);

      // Re-calcular medida (longitud o área)
      if (feature.geometry.type === 'LineString') {
        let totalM = 0;
        for (let i = 0; i < latlngs.length - 1; i++) {
          totalM += L.latLng(latlngs[i]).distanceTo(L.latLng(latlngs[i + 1]));
        }
        feature.properties.length = (totalM / 1000).toFixed(2);
      } else {
        // El área es más compleja, pero Leaflet Gehoman o similares podrían ayudar o dejarlo para el refresh
        // Por simplicidad, avisamos que se ha simplificado
      }
    }

    // Guardar en BD
    saveVectorLayerToDatabase(layer).then(() => {
      if (typeof showMapMessage === 'function') {
        showMapMessage(`Simplificado: ${originalCount} → ${newCount} puntos`, "success");
      }
      // Abrir editor automáticamente para ver cambios (longitud, etc)
      _onFeatureSelectClick({ target: feature.leafletLayer, stopPropagation: () => { } }, true);

      // Refrescar tabla si está abierta
      if (typeof openAttributeTable === 'function') openAttributeTable(layerId);
    });

  } catch (err) {
    console.error("Error al simplificar feature:", err);
    if (typeof showMapMessage === 'function') showMapMessage("Error al simplificar geometría", "error");
  }
}

let _activeVertexMarkers = [];
let _editingFeatureId = null; // layerId-featureIdx

function toggleFeatureExpansion(layerId, featureIdx) {
  const key = `${layerId}-${featureIdx}`;
  if (_expandedFeatures.has(key)) {
    _expandedFeatures.delete(key);
  } else {
    _expandedFeatures.add(key);
  }
  openAttributeTable(layerId); // Refresh table
}

async function updateVertexCoordinate(layerId, featureIdx, vertexIdx, axis, value) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;
  const feature = layer.geojson.features[featureIdx];
  if (!feature) return;

  const val = parseFloat(value);
  if (isNaN(val)) return;

  const geom = feature.geometry;
  const isPolygon = geom.type === 'Polygon';
  const coords = isPolygon ? geom.coordinates[0] : geom.coordinates;

  if (!coords[vertexIdx]) return;
  coords[vertexIdx][axis] = val;

  // Handle polygon closure
  if (isPolygon && (vertexIdx === 0 || vertexIdx === coords.length - 1)) {
    const otherIdx = (vertexIdx === 0) ? coords.length - 1 : 0;
    coords[otherIdx][axis] = val;
  }

  // Update map layer geometry
  if (feature.leafletLayer) {
    feature.leafletLayer.setLatLngs(isPolygon ? [coords.map(p => [p[1], p[0]])] : coords.map(p => [p[1], p[0]]));
  }

  // If we are currently editing this feature on map, refresh markers
  if (_editingFeatureId === `${layerId}-${featureIdx}`) {
    _renderVertexEditorMarkers(layer, feature);
  }

  await saveVectorLayerToDatabase(layer);
}

async function deleteVertex(layerId, featureIdx, vertexIdx) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) return;
  const feature = layer.geojson.features[featureIdx];
  if (!feature) return;

  const geom = feature.geometry;
  const isPolygon = geom.type === 'Polygon';
  const coords = isPolygon ? geom.coordinates[0] : geom.coordinates;

  const minPoints = isPolygon ? 4 : 2; // Polygon needs 3 points + 1 closure, Line needs 2 points
  if (coords.length <= minPoints) {
    if (typeof showMapMessage === 'function') showMapMessage("No se pueden borrar más vértices (mínimo alcanzado)", "warning");
    return;
  }

  coords.splice(vertexIdx, 1);

  // Handle polygon closure if first/last point was deleted
  if (isPolygon && (vertexIdx === 0 || vertexIdx === coords.length)) {
    coords[coords.length - 1] = [...coords[0]];
  }

  // Update map layer geometry
  if (feature.leafletLayer) {
    feature.leafletLayer.setLatLngs(isPolygon ? [coords.map(p => [p[1], p[0]])] : coords.map(p => [p[1], p[0]]));
  }

  // If we are currently editing this feature on map, refresh markers
  if (_editingFeatureId === `${layerId}-${featureIdx}`) {
    _renderVertexEditorMarkers(layer, feature);
  }

  await saveVectorLayerToDatabase(layer);
  
  // Refresh table ONLY if it's already open
  if (document.getElementById('floatAttributeTable')) {
    openAttributeTable(layerId);
  }

  // Close any open popups (like the vertex delete confirmation)
  const targetMap = window.map || window._mapaCorpus;
  if (targetMap) targetMap.closePopup();
}

function toggleVertexEditing(layerId, featureIdx) {
  // console.log(`🔍 toggleVertexEditing called for layer: ${layerId}, feature: ${featureIdx}`);
  const currentId = `${layerId}-${featureIdx}`;
  if (_editingFeatureId === currentId) {
    console.log('⏹️ Stopping vertex editing (already active)');
    stopVertexEditing();
    return;
  }
  stopVertexEditing();

  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer) {
    console.warn(`❌ Layer not found: ${layerId}`);
    return;
  }
  if (!layer.geojson?.features[featureIdx]) {
    console.warn(`❌ Feature at index ${featureIdx} not found in layer ${layerId}`);
    return;
  }

  const feature = layer.geojson.features[featureIdx];
  const geom = feature.geometry;
  if (geom.type === 'Point') {
    console.log('ℹ️ Vertex editing not supported for Point features.');
    return;
  }

  const targetMap = window.map || window._mapaCorpus;
  if (!targetMap) {
    console.error('❌ Map instance not found.');
    return;
  }

  // Set cursor to default (arrow) for precision editing
  targetMap.getContainer().style.cursor = 'default';

  _editingFeatureId = currentId;
  // console.log(`🛠️ Advanced Vertex Editing STARTED: ${geom.type} [${currentId}]`);

  // Refresh UI to show active state on buttons WITHOUT re-rendering panels
  _updateEditorUIStates();

  _renderVertexEditorMarkers(layer, feature);

  if (typeof showMapMessage === 'function')
    showMapMessage("Edición pro: arrastra amarillos para mover, blancos para añadir, Alt+Clic para borrar.", "info");
}

/**
 * Helper to calculate a rounded corner (fillet) between three points.
 */
function _getFilletPoints(p1, p2, p3, radiusInMeters) {
  // Convert to Cartesian-like for small areas or use spherical trig. 
  // For simplicity and since these are small edits, we'll use a local linear approximation
  const latFactor = 111320; // meters per degree lat
  const lngFactor = 111320 * Math.cos(p2[1] * Math.PI / 180);

  const toCart = p => [p[0] * lngFactor, p[1] * latFactor];
  const toLatLon = c => [c[0] / lngFactor, c[1] / latFactor];

  const c1 = toCart(p1), c2 = toCart(p2), c3 = toCart(p3);

  const v1 = [c1[0] - c2[0], c1[1] - c2[1]];
  const v2 = [c3[0] - c2[0], c3[1] - c2[1]];

  const d1 = Math.sqrt(v1[0] ** 2 + v1[1] ** 2);
  const d2 = Math.sqrt(v2[0] ** 2 + v2[1] ** 2);

  if (d1 < 1 || d2 < 1) return [p2]; // Too small

  const u1 = [v1[0] / d1, v1[1] / d1];
  const u2 = [v2[0] / d2, v2[1] / d2];

  const dot = u1[0] * u2[0] + u1[1] * u2[1];
  const angle = Math.acos(Math.max(-1, Math.min(1, dot)));

  // Distance from B to tangent points
  const tDist = radiusInMeters / Math.tan(angle / 2);

  // Clamp tDist to half of the shortest segment to avoid overlaps
  const maxT = Math.min(d1, d2) * 0.45;
  const actualT = Math.min(tDist, maxT);
  const actualR = actualT * Math.tan(angle / 2);

  const t1 = [c2[0] + u1[0] * actualT, c2[1] + u1[1] * actualT];
  const t2 = [c2[0] + u2[0] * actualT, c2[1] + u2[1] * actualT];

  // Center of the circle
  const bisector = [u1[0] + u2[0], u1[1] + u2[1]];
  const bLen = Math.sqrt(bisector[0] ** 2 + bisector[1] ** 2);
  if (bLen < 0.0001) return [p2];

  const ub = [bisector[0] / bLen, bisector[1] / bLen];
  const distToCenter = actualR / Math.sin(angle / 2);
  const center = [c2[0] + ub[0] * distToCenter, c2[1] + ub[1] * distToCenter];

  // Generate points
  const startAng = Math.atan2(t1[1] - center[1], t1[0] - center[0]);
  const endAng = Math.atan2(t2[1] - center[1], t2[0] - center[0]);

  let diff = endAng - startAng;
  while (diff > Math.PI) diff -= 2 * Math.PI;
  while (diff < -Math.PI) diff += 2 * Math.PI;

  const steps = 8;
  const points = [];
  for (let i = 0; i <= steps; i++) {
    const a = startAng + diff * (i / steps);
    const px = center[0] + Math.cos(a) * actualR;
    const py = center[1] + Math.sin(a) * actualR;
    points.push(toLatLon([px, py]));
  }

  return points;
}

function _renderVertexEditorMarkers(layer, feature) {
  const targetMap = window.map || window._mapaCorpus;
  _activeVertexMarkers.forEach(m => targetMap.removeLayer(m));
  _activeVertexMarkers = [];

  const geom = feature.geometry;
  const coords = geom.type === 'Polygon' ? geom.coordinates[0] : geom.coordinates;
  const isPolygon = geom.type === 'Polygon';

  // 1. Create Vertex Markers
  coords.forEach((c, idx) => {
    // For polygons, skip the last point if it's the same as first to avoid double markers
    if (isPolygon && idx === coords.length - 1) return;

    const handleIcon = L.divIcon({
      className: 'vertex-handle-sirio',
      html: '<div class="vertex-dot" oncontextmenu="return false;"></div>',
      iconSize: [20, 20], iconAnchor: [10, 10]
    });

    const marker = L.marker([c[1], c[0]], {
      icon: handleIcon,
      draggable: true,
      zIndexOffset: 1000
    }).addTo(targetMap);

    marker._vertexIndex = idx; // TAGGED

    marker.on('drag', (e) => {
      let latlng = e.target.getLatLng();
      
      // 1. MODO ORTO (Shift pulsado): Forzar trayectoria 0, 90, 180, 270 grados
      if (_isShiftKeyPressed) {
        let refPoint = null;
        if (idx > 0) {
          refPoint = coords[idx - 1]; // Referencia al anterior
        } else if (coords.length > 1) {
          refPoint = coords[idx + 1]; // Referencia al siguiente si es el primero
        }

        if (refPoint) {
          const deltaLat = Math.abs(latlng.lat - refPoint[1]);
          const deltaLng = Math.abs(latlng.lng - refPoint[0]);

          if (deltaLat > deltaLng) {
            // Más vertical que horizontal -> Forzar VERTICAL (misma longitud)
            latlng = L.latLng(latlng.lat, refPoint[0]);
          } else {
            // Más horizontal que vertical -> Forzar HORIZONTAL (misma latitud)
            latlng = L.latLng(refPoint[1], latlng.lng);
          }
          e.target.setLatLng(latlng);
        }
      }

      // 2. AÑADIR SNAPPING MAGNÉTICO EN TIEMPO REAL
      const snapped = _findNearestFeaturePoint(latlng);
      if (snapped && snapped.feature !== feature) {
        latlng = snapped.latlng;
        e.target.setLatLng(latlng);
        marker._snappedTo = snapped; // Guardar referencia para dragend
      } else {
        marker._snappedTo = null;
      }

      const newCoord = [latlng.lng, latlng.lat];
      coords[idx] = newCoord;
      if (isPolygon && idx === 0) coords[coords.length - 1] = [...newCoord];

      feature.leafletLayer.setLatLngs(isPolygon ? [coords.map(p => [p[1], p[0]])] : coords.map(p => [p[1], p[0]]));
      // Midpoints need to follow, but for performance we refresh them on dragend
    });

    marker.on('dragend', () => {
      // Intentar fusión si hay snapping y estamos en un extremo de línea
      if (marker._snappedTo && geom.type === 'LineString' && marker._snappedTo.feature.geometry.type === 'LineString') {
        const isEndpoint = (idx === 0 || idx === coords.length - 1);
        if (isEndpoint) {
          _attemptFeatureMerge(layer, marker._snappedTo.feature, feature, marker._snappedTo.vertexIndex, idx);
          return; // La función de fusión ya refresca todo
        }
      }

      saveVectorLayerToDatabase(layer);
      _renderVertexEditorMarkers(layer, feature); // Recalculate everything
    });

    marker.on('click', (e) => {
      if (e.originalEvent.altKey) {
        L.DomEvent.stopPropagation(e);
        if (coords.length <= (isPolygon ? 4 : 2)) {
          showMapMessage("No se pueden borrar más vértices", "warning");
          return;
        }
        coords.splice(idx, 1);
        if (isPolygon && idx === 0) coords[coords.length - 1] = [...coords[0]];

        feature.leafletLayer.setLatLngs(isPolygon ? [coords.map(p => [p[1], p[0]])] : coords.map(p => [p[1], p[0]]));
        saveVectorLayerToDatabase(layer);
        _renderVertexEditorMarkers(layer, feature);
      }
    });

    marker.on('contextmenu', (e) => {
      // Usar e.originalEvent para prevenir el menú del navegador
      if (e.originalEvent) {
        L.DomEvent.stopPropagation(e.originalEvent);
        L.DomEvent.preventDefault(e.originalEvent);
      }
      const featureIdx = layer.geojson.features.indexOf(feature);
      const headerColor = isDark ? '#ff9800' : '#294a60';
      const popup = L.popup({ offset: [0, -5], className: 'gis-vertex-popup sirio-popup-custom' })
        .setLatLng(marker.getLatLng())
        .setContent(`
          <div class="sirio-gis-popup" style="margin:-1px; border-radius:4px; overflow:hidden; font-family:var(--ds-font-mono,'Inter',sans-serif); min-width:140px;">
            <div style="background:${headerColor}; color:${isDark ? '#000' : '#fff'}; padding:4px 10px; font-weight:700; font-size:0.75rem; border-bottom:1px solid rgba(0,0,0,0.1); text-align:center;">
              VÉRTICE #${idx + 1}
            </div>
            <div style="padding:10px; background:rgba(20,20,20,0.95); display:flex; flex-direction:column; gap:8px;">
              ${(geom.type === 'LineString' && idx > 0 && idx < coords.length - 1) ? `
              <button class="btn btn-xs btn-sirio w-100 d-flex align-items-center justify-content-center gap-1" style="font-size:0.7rem; padding: 5px;"
                      onclick="window.GISManager.splitLineAtVertex('${layer.id}', ${featureIdx}, ${idx})">
                <i class="fa-solid fa-scissors" style="font-size:0.65rem;"></i> Cortar aquí
              </button>` : ''}
              
              <button class="btn btn-xs btn-danger w-100 d-flex align-items-center justify-content-center gap-1" style="font-size:0.7rem; padding: 5px;"
                      onclick="window.GISManager.deleteVertex('${layer.id}', ${featureIdx}, ${idx})">
                <i class="fa-solid fa-trash-can" style="font-size:0.65rem;"></i> Eliminar Vértice
              </button>
              
              <div class="text-center mt-1" style="opacity:0.5; font-size:0.55rem; color:#ccc;">
                [${e.latlng.lat.toFixed(6)}, ${e.latlng.lng.toFixed(6)}]
              </div>
            </div>
          </div>
        `)
        .openOn(targetMap);
    });

    _activeVertexMarkers.push(marker);
  });

  // 1.5 Create Rounding Handles (Fillet)
  coords.forEach((c, i) => {
    let pPrev, pNext;
    if (isPolygon) {
      pPrev = (i === 0) ? coords[coords.length - 2] : coords[i - 1];
      pNext = coords[i + 1]; // coords.length-1 is same as 0, so i+1 is always valid for i < len-1
      if (i === coords.length - 1) return;
    } else {
      if (i === 0 || i === coords.length - 1) return;
      pPrev = coords[i - 1];
      pNext = coords[i + 1];
    }

    if (!pPrev || !pNext) return;

    // Calculate bisector for handle placement
    const latFactor = 111320;
    const lngFactor = 111320 * Math.cos(c[1] * Math.PI / 180);
    const toCart = p => [p[0] * lngFactor, p[1] * latFactor];
    const toLatLon = xy => [xy[0] / lngFactor, xy[1] / latFactor];

    const cc = toCart(c), cp = toCart(pPrev), cn = toCart(pNext);
    const v1 = [cp[0] - cc[0], cp[1] - cc[1]], v2 = [cn[0] - cc[0], cn[1] - cc[1]];
    const d1 = Math.sqrt(v1[0] ** 2 + v1[1] ** 2), d2 = Math.sqrt(v2[0] ** 2 + v2[1] ** 2);
    if (d1 < 5 || d2 < 5) return;

    const u1 = [v1[0] / d1, v1[1] / d1], u2 = [v2[0] / d2, v2[1] / d2];
    const bisector = [u1[0] + u2[0], u1[1] + u2[1]];
    const bLen = Math.sqrt(bisector[0] ** 2 + bisector[1] ** 2);
    if (bLen < 0.1) return; // Straight line

    const ub = [bisector[0] / bLen, bisector[1] / bLen];
    const initialOffset = 8; // meters
    const handlePos = toLatLon([cc[0] + ub[0] * initialOffset, cc[1] + ub[1] * initialOffset]);

    const roundIcon = L.divIcon({
      className: 'vertex-round-handle',
      html: '<div class="round-dot" title="Arrastra para redondear esquina"></div>',
      iconSize: [16, 16], iconAnchor: [8, 8]
    });

    const roundMarker = L.marker([handlePos[1], handlePos[0]], {
      icon: roundIcon,
      draggable: true,
      zIndexOffset: 2000,
      interactive: true
    }).addTo(targetMap);
    let tempCoords = null;

    roundMarker.on('dragstart', () => {
      // Hide handles being replaced to avoid "ghosting"
      _activeVertexMarkers.forEach(m => {
        if (m._vertexIndex === i) m.setOpacity(0);
        // Also hide midpoint markers around this vertex
        if (m._midpointIndex === i || m._midpointIndex === i - 1) m.setOpacity(0);
      });
    });

    roundMarker.on('drag', (e) => {
      const latlng = e.target.getLatLng();
      const dragPos = toCart([latlng.lng, latlng.lat]);
      const dist = Math.sqrt((dragPos[0] - cc[0]) ** 2 + (dragPos[1] - cc[1]) ** 2);

      const dot = u1[0] * u2[0] + u1[1] * u2[1];
      const angle = Math.acos(Math.max(-1, Math.min(1, dot)));
      const radius = dist * Math.sin(angle / 2) / (1 - Math.sin(angle / 2));

      console.log(`🌀 Rounding: angle=${(angle * 180 / Math.PI).toFixed(1)}°, radius=${radius.toFixed(2)}m`);

      const arcPoints = _getFilletPoints(pPrev, c, pNext, Math.max(0.1, radius));

      tempCoords = [...coords];
      tempCoords.splice(i, 1, ...arcPoints);

      feature.leafletLayer.setLatLngs(isPolygon ? [tempCoords.map(p => [p[1], p[0]])] : tempCoords.map(p => [p[1], p[0]]));
    });

    roundMarker.on('dragend', () => {
      if (tempCoords) {
        if (isPolygon) {
          feature.geometry.coordinates[0] = tempCoords;
        } else {
          feature.geometry.coordinates = tempCoords;
        }
        saveVectorLayerToDatabase(layer);
        _renderVertexEditorMarkers(layer, feature);
      }
    });

    _activeVertexMarkers.push(roundMarker);
  });

  // 2. Create Midpoint Markers (Splitters)
  const numSegments = isPolygon ? coords.length - 1 : coords.length - 1;
  for (let i = 0; i < numSegments; i++) {
    const p1 = coords[i];
    const p2 = coords[i + 1];
    if (!p1 || !p2) continue;

    const midLat = (p1[1] + p2[1]) / 2;
    const midLng = (p1[0] + p2[0]) / 2;

    const midIcon = L.divIcon({
      className: 'vertex-midpoint-handle',
      html: '<div class="midpoint-dot"></div>',
      iconSize: [16, 16], iconAnchor: [8, 8]
    });

    const midMarker = L.marker([midLat, midLng], { icon: midIcon, draggable: true, opacity: 0.8 }).addTo(targetMap);
    midMarker._midpointIndex = i; // TAGGED

    midMarker.on('dragstart', () => {
      // On start of drag, we convert this to a real vertex
      coords.splice(i + 1, 0, [midLng, midLat]);
      // We don't save yet, just update markers after this drag
    });

    midMarker.on('drag', (e) => {
      let latlng = e.target.getLatLng();

      // MODO ORTO para puntos medios
      if (_isShiftKeyPressed) {
        const refPoint = coords[i];
        if (refPoint) {
          const deltaLat = Math.abs(latlng.lat - refPoint[1]);
          const deltaLng = Math.abs(latlng.lng - refPoint[0]);
          if (deltaLat > deltaLng) {
            latlng = L.latLng(latlng.lat, refPoint[0]);
          } else {
            latlng = L.latLng(refPoint[1], latlng.lng);
          }
          e.target.setLatLng(latlng);
        }
      }

      coords[i + 1] = [latlng.lng, latlng.lat];
      feature.leafletLayer.setLatLngs(isPolygon ? [coords.map(p => [p[1], p[0]])] : coords.map(p => [p[1], p[0]]));
    });

    midMarker.on('dragend', () => {
      saveVectorLayerToDatabase(layer);
      _renderVertexEditorMarkers(layer, feature);
    });

    _activeVertexMarkers.push(midMarker);
  }
}

/**
 * FUSIONAR LÍNEAS: featureA absorbe a featureB
 */
function _attemptFeatureMerge(layer, featureA, featureB, vertexAIdx, vertexBIdx) {
  if (featureA === featureB) return;
  if (featureA.geometry.type !== 'LineString' || featureB.geometry.type !== 'LineString') return;

  const coordsA = featureA.geometry.coordinates;
  const coordsB = featureB.geometry.coordinates;
  const isAStart = (vertexAIdx === 0);
  const isAEnd = (vertexAIdx === coordsA.length - 1);
  const isBStart = (vertexBIdx === 0);
  const isBEnd = (vertexBIdx === coordsB.length - 1);

  // Solo fusionamos si el snapping ocurre en extremos de ambas líneas (por ahora)
  if (!(isAStart || isAEnd) || !(isBStart || isBEnd)) {
    console.log("Fusión cancelada: Snapping debe ocurrir en extremos de línea.");
    saveVectorLayerToDatabase(layer);
    _renderVertexEditorMarkers(layer, featureB);
    return;
  }

  if (!confirm(`¿Fucionar "${featureB.properties.name || 'Línea B'}" con "${featureA.properties.name || 'Línea A'}"?`)) {
    saveVectorLayerToDatabase(layer);
    _renderVertexEditorMarkers(layer, featureB);
    return;
  }

  let finalCoords = [];
  
  if (isBStart && isAEnd) {
    // B sigue a A: [A0..An, B1..Bn]
    finalCoords = coordsA.concat(coordsB.slice(1));
  } else if (isBEnd && isAStart) {
    // B precede a A: [B0..Bi, A1..An]
    finalCoords = coordsB.concat(coordsA.slice(1));
  } else if (isBStart && isAStart) {
    // A invertida + B: [An..A0, B1..Bn]
    finalCoords = [...coordsA].reverse().concat(coordsB.slice(1));
  } else if (isBEnd && isAEnd) {
    // A + B invertida: [A0..An, Bi..B0]
    finalCoords = coordsA.concat([...coordsB].reverse().slice(1));
  }

  if (finalCoords.length > 0) {
    // 1. Actualizar feature A
    featureA.geometry.coordinates = finalCoords;
    featureA.leafletLayer.setLatLngs(finalCoords.map(p => [p[1], p[0]]));
    
    // 2. Eliminar feature B
    const idxB = layer.geojson.features.indexOf(featureB);
    if (idxB !== -1) {
      layer.geojson.features.splice(idxB, 1);
      if (featureB.leafletLayer && layer.leafletLayer) {
        layer.leafletLayer.removeLayer(featureB.leafletLayer);
      }
    }

    layer.num_features = layer.geojson.features.length;
    
    // 3. Persistir y Limpiar
    saveVectorLayerToDatabase(layer).then(() => {
      stopVertexEditing(); // Cerramos edición para evitar punteros huérfanos
      if (typeof showMapMessage === 'function') {
        showMapMessage(`Líneas fusionadas en: ${featureA.properties.name}`, "success");
      }
      // Reabrir edición automática en la nueva línea combinada
      setTimeout(() => {
        const newIdx = layer.geojson.features.indexOf(featureA);
        if (newIdx !== -1) toggleVertexEditing(layer.id, newIdx);
      }, 500);
    });
  }
}

function stopVertexEditing() {
  const targetMap = window.map || window._mapaCorpus;
  const oldId = _editingFeatureId;

  _activeVertexMarkers.forEach(m => {
    if (targetMap) targetMap.removeLayer(m);
  });
  _activeVertexMarkers = [];
  _editingFeatureId = null;

  // Restore cursor if map exists
  if (targetMap) targetMap.getContainer().style.cursor = '';

  // Refresh UI to clear active state on buttons
  _updateEditorUIStates();
}

/**
 * Updates the visual state (active/inactive) of vertex editing buttons
 * in any open panels without re-rendering the whole panel.
 */
function _updateEditorUIStates() {
  const activeId = _editingFeatureId; // "layerId-featureIdx" or null

  // Update Buttons in Attribute Table
  const attrTable = document.getElementById('floatAttributeTable');
  if (attrTable) {
    const buttons = attrTable.querySelectorAll('button[onclick*="toggleVertexEditing"]');
    buttons.forEach(btn => {
      // Extract parameters from onclick: toggleVertexEditing('layerId', index)
      const match = btn.getAttribute('onclick').match(/toggleVertexEditing\('([^']+)',\s*(\d+)\)/);
      if (match) {
        const id = `${match[1]}-${match[2]}`;
        btn.classList.toggle('btn-vertex-active', id === activeId);
      }
    });
  }

  // Update Button in Feature Editor
  const featEditor = document.getElementById('floatFeatureEditor');
  if (featEditor) {
    const btn = featEditor.querySelector('button[onclick*="toggleVertexEditing"]');
    if (btn) {
      const match = btn.getAttribute('onclick').match(/toggleVertexEditing\('([^']+)',\s*(\d+)\)/);
      if (match) {
        const id = `${match[1]}-${match[2]}`;
        btn.classList.toggle('btn-vertex-active', id === activeId);
      }
    }
  }
}

// Exportar funciones globales

/**
 * MODO TIJERAS: Permite cortar una línea pulsando sobre ella.
 */
function activateScissorsTool(layerId, featureIdx) {
  _scissorsActive = true;
  _scissorsTarget = { layerId, featureIdx };
  
  const targetMap = window.map || window._mapaCorpus;
  if (!targetMap) return;

  // Forzar cerrar popup
  targetMap.closePopup();

  // Cambiar cursor (intentar imagen de tijeras, fallback a crosshair)
  const mapContainer = targetMap.getContainer();
  mapContainer.style.cursor = 'crosshair';
  
  if (typeof showMapMessage === 'function') {
    showMapMessage("MODO TIJERAS: Haz clic en el punto exacto de la línea para cortarla", "info");
  }

  // Listener para el clic de corte
  targetMap.once('click', (e) => {
    if (!_scissorsActive) return;
    _executeScissorsSplit(e.latlng);
    deactivateScissorsTool();
  });

  // Permitir cancelar con Escape o click derecho fuera
  const cancelHandler = (e) => {
    if (e.key === 'Escape') {
      deactivateScissorsTool();
      window.removeEventListener('keydown', cancelHandler);
    }
  };
  window.addEventListener('keydown', cancelHandler);
}

function deactivateScissorsTool() {
  _scissorsActive = false;
  _scissorsTarget = null;
  const targetMap = window.map || window._mapaCorpus;
  if (targetMap) targetMap.getContainer().style.cursor = '';
}

function _executeScissorsSplit(latlng) {
  if (!_scissorsTarget) return;
  const { layerId, featureIdx } = _scissorsTarget;
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.geojson?.features[featureIdx]) return;

  const feature = layer.geojson.features[featureIdx];
  const res = _findNearestSegmentPoint(latlng, feature);

  // Tolerancia: el click debe estar relativamente cerca de la línea (aprox 20-30 metros en escala local)
  if (res && res.distance < 0.0005) { 
    // 1. Insertamos el nuevo vértice en el punto proyectado
    const coords = feature.geometry.coordinates;
    coords.splice(res.segmentIndex + 1, 0, res.point);
    
    // 2. Ejecutamos el split en ese nuevo vértice
    splitLineAtVertex(layerId, featureIdx, res.segmentIndex + 1);
  } else {
    if (typeof showMapMessage === 'function') {
      showMapMessage("No se detectó la línea bajo el cursor. Intenta pulsar más cerca.", "warning");
    }
  }
}

function _findNearestSegmentPoint(latlng, feature) {
  const coords = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates[0] : feature.geometry.coordinates;
  let minDistance = Infinity;
  let bestPoint = null;
  let bestSegmentIdx = -1;

  for (let i = 0; i < coords.length - 1; i++) {
    const p1 = coords[i];
    const p2 = coords[i + 1];
    
    const projected = _projectPointToSegment([latlng.lng, latlng.lat], p1, p2);
    const dist = Math.sqrt(Math.pow(latlng.lng - projected[0], 2) + Math.pow(latlng.lat - projected[1], 2));
    
    if (dist < minDistance) {
      minDistance = dist;
      bestPoint = projected;
      bestSegmentIdx = i;
    }
  }
  return { point: bestPoint, segmentIndex: bestSegmentIdx, distance: minDistance };
}

function _projectPointToSegment(p, a, b) {
  const x = p[0], y = p[1], x1 = a[0], y1 = a[1], x2 = b[0], y2 = b[1];
  const dx = x2 - x1, dy = y2 - y1;
  if (dx === 0 && dy === 0) return [x1, y1];
  const t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy);
  if (t < 0) return [x1, y1];
  if (t > 1) return [x2, y2];
  return [x1 + t * dx, y1 + t * dy];
}

function splitLineAtVertex(layerId, featureIdx, vertexIdx) {
  const layer = vectorLayers.find(l => l.id == layerId);
  if (!layer || !layer.geojson?.features[featureIdx]) return;

  const feature = layer.geojson.features[featureIdx];
  if (feature.geometry.type !== 'LineString') {
    if (typeof showMapMessage === 'function') showMapMessage("Solo se pueden cortar líneas", "warning");
    return;
  }

  const coords = feature.geometry.coordinates;
  if (vertexIdx <= 0 || vertexIdx >= coords.length - 1) {
    if (typeof showMapMessage === 'function') showMapMessage("No se puede cortar en los extremos", "warning");
    return;
  }

  const nameInput = document.getElementById('digitize-feature-name');
  const baseName = (nameInput && nameInput.value.trim()) || 
                   (feature.properties.name || feature.properties.nombre || "Línea").replace(/\s*\(Parte \d+\)/g, "").replace(/\s*\d+$/, "").trim();

  if (!confirm(`¿Dividir esta línea en dos elementos independientes?`)) return;

  // 1. Crear coordenadas para las dos nuevas líneas
  const coords1 = coords.slice(0, vertexIdx + 1);
  const coords2 = coords.slice(vertexIdx);

  // 2. Duplicar propiedades para la nueva línea con nombre inteligente
  const props2 = JSON.parse(JSON.stringify(feature.properties));
  props2.name = _getNextSequentialName(layer, baseName);
  
  const feature2 = {
    type: 'Feature',
    geometry: { type: 'LineString', coordinates: coords2 },
    properties: props2
  };

  // 3. Actualizar la línea original (Parte 1)
  feature.geometry.coordinates = coords1;
  const name1 = feature.properties.name || "Línea";
  if (!name1.includes("(Parte 1)")) feature.properties.name = name1 + " (Parte 1)";

  // 4. Añadir la nueva feature al GeoJSON
  layer.geojson.features.splice(featureIdx + 1, 0, feature2);
  layer.num_features = layer.geojson.features.length;

  // 5. Renderizar y persistir
  saveVectorLayerToDatabase(layer).then(() => {
    const targetMap = window.map || window._mapaCorpus;
    if (targetMap) targetMap.closePopup();
    
    // Forzar re-renderizado de todo el layer para limpiar visualmente
    if (layer.leafletLayer && targetMap.hasLayer(layer.leafletLayer)) {
      layer.leafletLayer.clearLayers();
      layer.geojson.features.forEach(f => renderFeatureOnMap(layer, f));
    }

    stopVertexEditing();

    // 6. Refrescar TODOS los paneles abiertos para esta capa
    refreshAttributeTableIfOpen(layerId);
    refreshVectorLayersList();

    if (typeof showMapMessage === 'function') {
      showMapMessage("Línea dividida correctamente", "success");
    }
  });
}

/**
 * Encuentra el siguiente nombre secuencial disponible para un elemento (ej: "Línea 3")
 */
function _getNextSequentialName(layer, baseName) {
  if (!layer || !layer.geojson?.features) return `${baseName} 1`;
  
  const cleanBase = baseName.replace(/\s*\d+$/, "").trim();
  const existingNames = layer.geojson.features.map(f => (f.properties.name || f.properties.nombre || "").toLowerCase());
  
  let nextNum = 1;
  // Si la capa está vacía o el baseName es nuevo, empezamos en 1
  // Pero si el usuario introdujo "Línea 2" y queremos la siguiente, buscamos el hueco
  while (existingNames.includes(`${cleanBase} ${nextNum}`.toLowerCase())) {
    nextNum++;
  }
  return `${cleanBase} ${nextNum}`;
}

/**
 * Maneja la confirmación en dos pasos para el borrado de elementos
 */
function confirmDeleteFeature(btn, layerId, idx) {
  if (btn.dataset.conf === '1') {
    deleteFeature(layerId, idx, true);
  } else {
    // Primer paso: Cambiar a modo confirmación
    const originalHtml = btn.innerHTML;
    const originalClass = btn.className;
    const originalTitle = btn.title;

    btn.innerHTML = '<i class="fa-solid fa-circle-check"></i>';
    btn.dataset.conf = '1';
    btn.classList.remove('text-danger');
    btn.classList.add('text-success', 'fw-bold');
    btn.title = 'Confirmar Borrado';

    // Auto-reset después de 3 segundos
    setTimeout(() => {
      if (btn && btn.dataset.conf === '1') {
        btn.innerHTML = originalHtml;
        btn.className = originalClass;
        btn.title = originalTitle;
        btn.dataset.conf = '';
      }
    }, 3000);
  }
}

/**
 * Refresca la tabla de atributos si está abierta para el layer indicado
 */
function refreshAttributeTableIfOpen(layerId) {
  if (document.getElementById('floatAttributeTable')) {
    openAttributeTable(layerId);
  }
}

window.GISManager = {
  vectorLayers,
  activeVectorLayer,
  loadVectorLayersFromDB,
  refreshVectorLayersList,
  editVectorLayer,
  editVectorLayerQuick,
  openSymbologyModal,
  addSymbologyRule,
  saveLayerSymbology,
  saveQuickEdit,
  cancelQuickEdit,
  toggleSelectAllLayers,
  exportAllVectorLayers,
  toggleAllVectorLayersVisibility,
  toggleVectorLayerVisibility,
  toggleVectorLayerLock,
  zoomToVectorLayer,
  exportVectorLayerById,
  duplicateVectorLayer,
  deleteVectorLayerConfirm,
  syncLayerOrder,
  setActiveVectorLayer,
  deactivateActiveVectorLayer,
  renderFeatureOnMap,
  saveVectorLayerToDatabase,
  saveVectorLayerManual,
  centerOnVertex,
  refreshQuickList,
  addVectorLayerToPanel,
  openAttributeTable,
  addAttributeColumn,
  deleteAttributeColumn,
  updateFeatureProperty,
  updateFeatureCoordinateComponent,
  splitLineAtVertex,
  _getNextSequentialName,
  refreshAttributeTableIfOpen,
  confirmDeleteFeature,
  startRelocatingFeature,
  zoomToFeature,
  deleteFeature,
  simplifyFeature,
  continueLineDigitizing,
  exportAttributeTable,
  activateScissorsTool,
  mergeSelectedFeatures,
  toggleVertexEditing: typeof toggleVertexEditing !== 'undefined' ? toggleVertexEditing : null,
  toggleFeatureExpansion,
  updateVertexCoordinate,
  deleteVertex,
  toggleTraceMode,
  openBufferAnalysisModal,
  executeBufferAnalysis,
  suggestLocationFromText,
  calculateArea,
  openSpatialAnalysisPanel,
  runSpatialAnalysis,
  openCreateVectorLayerModal,
  openManageVectorLayersModal,
  importCSVToLayer,
  toggleLayerLabels,
  toggleHeatmap,
  toggleSelectionMode,
  _clearFeatureSelection,
  _saveFeatureEditorPanel,
  _setTraceAnchor: (a) => { _traceAnchor = a; },
  get snappingEnabled() { return snappingEnabled; },
  get traceActive() { return _traceActive; },
  get traceAnchor() { return _traceAnchor; },
  get selectionModeActive() { return _selectionModeActive; },
  get selectedFeatureInfo() { return _selectedFeatures[0] || null; },
  get selectedFeatures() { return _selectedFeatures; },
  get currentDistUnit() { return currentDistUnit; },
  get currentAreaUnit() { return currentAreaUnit; },
  // Internal helper for templates
  _findNearestFeaturePoint,
  _getTracePath,
  _onLayersPanelClose,
  refreshLayersPanelUI
};

let _deleteKeyTimeout = null;
let _deleteKeyArmed = false;

// Global key handler for GIS operations
window.addEventListener('keydown', function (e) {
  // If we are in an input/textarea, don't trigger GIS delete
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
    return;
  }

  // Escape: Desactivar capa activa
  if (e.key === 'Escape') {
    if (activeVectorLayer) {
      deactivateActiveVectorLayer();
    }
  }

  // Delete/Supr key
  if (e.key === 'Delete' || e.key === 'Del' || e.key === 'Backspace') {
    if (_selectedFeatures && _selectedFeatures.length > 0) {
      e.preventDefault();
      e.stopPropagation();

      const count = _selectedFeatures.length;
      
      if (!_deleteKeyArmed) {
        _deleteKeyArmed = true;
        if (typeof showMapMessage === 'function') {
          showMapMessage('Presiona Suprimir otra vez para BORRAR los ' + count + ' elementos seleccionados', 'warning', 3000);
        }
        _deleteKeyTimeout = setTimeout(() => { _deleteKeyArmed = false; }, 3000);
        return;
      }

      clearTimeout(_deleteKeyTimeout);
      _deleteKeyArmed = false;

      // Multi-delete logic
      const targets = [..._selectedFeatures];
      _clearFeatureSelection();

      let processedLayers = new Set();

      targets.forEach(info => {
        const layer = info.layer;
        
        // BLOQUEO: Ignorar elementos de capas bloqueadas
        if (layer.bloqueada) return;

        const leafletFeature = info.leafletFeature;
        const feature = leafletFeature.feature;
        
        // Buscar el índice actual (puede haber cambiado si borramos varios)
        const idx = layer.geojson.features.indexOf(feature);

        if (idx !== -1) {
          // Remove from GeoJSON
          layer.geojson.features.splice(idx, 1);
          layer.num_features = layer.geojson.features.length;

          // Remove from Map
          if (leafletFeature && layer.leafletLayer) {
              layer.leafletLayer.removeLayer(leafletFeature);
            }
            
            processedLayers.add(layer);
          }
        });

        // Save each affected layer
        processedLayers.forEach(layer => {
          saveVectorLayerToDatabase(layer).then(() => {
            if (typeof refreshVectorLayersList === 'function') refreshVectorLayersList();
            // Try updating the sidebar badge via a direct call if available
            const row = document.querySelector(`[data-vector-layer-id="${layer.id}"]`);
            if (row) {
              const badge = row.querySelector('.badge');
              if (badge) badge.textContent = layer.num_features;
            }
          });
        });

        if (typeof showMapMessage === 'function') {
          showMapMessage(`${count} elementos eliminados`, 'success');
        }

        // Close editor if open
        document.getElementById('floatFeatureEditor')?.remove();

        // Ensure vertex editing markers are removed
        if (typeof stopVertexEditing === 'function') {
          stopVertexEditing();
        }
    }
  }
});

/**
 * FUSIONAR: Une dos polilíneas seleccionadas en una sola.
 */
async function mergeSelectedFeatures() {
  if (!_selectedFeatures || _selectedFeatures.length !== 2) {
    if (typeof showMapMessage === 'function') showMapMessage("Selecciona exactamente dos líneas para fusionarlas", "warning");
    return;
  }

  const f1Info = _selectedFeatures[0];
  const f2Info = _selectedFeatures[1];

  if (f1Info.layer.id !== f2Info.layer.id) {
    if (typeof showMapMessage === 'function') showMapMessage("Las líneas deben pertenecer a la misma capa", "warning");
    return;
  }

  const feat1 = f1Info.leafletFeature.feature;
  const feat2 = f2Info.leafletFeature.feature;

  if (feat1.geometry.type !== 'LineString' || feat2.geometry.type !== 'LineString') {
    if (typeof showMapMessage === 'function') showMapMessage("Solo se pueden fusionar polilíneas", "warning");
    return;
  }

  const layer = f1Info.layer;
  if (layer.bloqueada) {
    if (typeof showMapMessage === 'function') showMapMessage("La capa está bloqueada", "warning");
    return;
  }

  if (!confirm(`¿Fusionar "${feat1.properties.name || 'Línea 1'}" y "${feat2.properties.name || 'Línea 2'}" en un solo elemento?`)) return;

  const coords1 = [...feat1.geometry.coordinates];
  const coords2 = [...feat2.geometry.coordinates];

  const s1 = coords1[0];
  const e1 = coords1[coords1.length - 1];
  const s2 = coords2[0];
  const e2 = coords2[coords2.length - 1];

  // Distancias entre extremos (Simple L2 para navegación local)
  const dist = (p1, p2) => Math.sqrt(Math.pow(p1[0] - p2[0], 2) + Math.pow(p1[1] - p2[1], 2));

  const d_e1s2 = dist(e1, s2);
  const d_e1e2 = dist(e1, e2);
  const d_s1s2 = dist(s1, s2);
  const d_s1e2 = dist(s1, e2);

  const minD = Math.min(d_e1s2, d_e1e2, d_s1s2, d_s1e2);

  let finalCoords = [];
  if (minD === d_e1s2) {
    // E1 -> S2 (Normal)
    finalCoords = [...coords1, ...coords2.slice(1)];
  } else if (minD === d_e1e2) {
    // E1 -> E2 (Revertir 2)
    finalCoords = [...coords1, ...coords2.reverse().slice(1)];
  } else if (minD === d_s1s2) {
    // S2 -> S1 (Revertir 1)
    finalCoords = [...coords2.reverse(), ...coords1.slice(1)];
  } else {
    // E2 -> S1 (Revertir 2 y 1 o simplemente pegar)
    finalCoords = [...coords2, ...coords1.slice(1)];
  }

  // Actualizar objeto GeoJSON
  feat1.geometry.coordinates = finalCoords;
  // Añadir log de fusión a descripción si existe
  feat1.properties.description = (feat1.properties.description || "") + ` [Fusionado con ${feat2.properties.name || 'Línea'}]`;

  // Eliminar la segunda feature
  const idx2 = layer.geojson.features.indexOf(feat2);
  if (idx2 !== -1) {
    layer.geojson.features.splice(idx2, 1);
    layer.num_features = layer.geojson.features.length;
  }

  // Persistir y refrescar
  try {
    await saveVectorLayerToDatabase(layer);
    
    // Limpiar mapa y redibujar capa
    if (layer.leafletLayer) {
      layer.leafletLayer.clearLayers();
      layer.geojson.features.forEach(f => renderFeatureOnMap(layer, f));
    }

    _clearFeatureSelection();
    document.getElementById('floatFeatureEditor')?.remove();
    refreshVectorLayersList();
    refreshAttributeTableIfOpen(layer.id);

    if (typeof showMapMessage === 'function') showMapMessage("Líneas fusionadas correctamente", "success");
  } catch (err) {
    console.error("Error fusionando líneas:", err);
    if (typeof showMapMessage === 'function') showMapMessage("Error al guardar la fusión", "error");
  }
}


