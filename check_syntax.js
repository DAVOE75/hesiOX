  // --- ESTADO TERRENO ---
  let terrainLayers = {
    slope: null,
    aspect: null
  };

  function toggleTerrainAnalysis(type) {
    if (!window._mapaCorpus) return;

    const layers = {
      slope: {
        url: 'https://www.ign.es/wms-inspire/mdt',
        options: {
          layers: 'MDT.PND',
          format: 'image/png',
          transparent: true,
          version: '1.3.0',
          opacity: 0.5,
          attribution: 'IGN MDT (Pendientes)'
        }
      },
      aspect: {
        url: 'https://www.ign.es/wms-inspire/mdt',
        options: {
          layers: 'MDT.ORI',
          format: 'image/png',
          transparent: true,
          version: '1.3.0',
          opacity: 0.5,
          attribution: 'IGN MDT (Orientaciones)'
        }
      }
    };

    if (terrainLayers[type]) {
      window._mapaCorpus.removeLayer(terrainLayers[type]);
      terrainLayers[type] = null;
      showMapToast('Capa de terreno desactivada', '#ff9800');
    } else {
      terrainLayers[type] = L.tileLayer.wms(layers[type].url, layers[type].options);
      terrainLayers[type].addTo(window._mapaCorpus);
      showMapToast(`Capa de ${type === 'slope' ? 'Pendientes' : 'Orientaciones'} activada (IGN)`, '#4caf50');
    }
  }

  // --- REJILLA ARQUEOLÓGICA ---
  let currentArchaeologicalGrid = null;

  function openArchaeologicalGridModal() {
    const modal = new bootstrap.Modal(document.getElementById('modalArchaeologicalGrid'));
    modal.show();
  }

  function generateArchaeologicalGrid() {
    if (!window._mapaCorpus) return;

    const cellSize = parseFloat(document.getElementById('grid-cell-size').value);
    const count = parseInt(document.getElementById('grid-count').value);
    const rotation = parseFloat(document.getElementById('grid-rotation').value) || 0;
    const centerOrigin = document.getElementById('grid-center-origin').checked;

    if (currentArchaeologicalGrid) {
      window._mapaCorpus.removeLayer(currentArchaeologicalGrid);
    }

    const center = window._mapaCorpus.getCenter();
    const lat = center.lat;
    const lon = center.lng;

    // Grupo para todas las líneas de la rejilla
    currentArchaeologicalGrid = L.layerGroup();

    const offset = centerOrigin ? -(count * cellSize) / 2 : 0;
    const deg2rad = Math.PI / 180;
    const rotRad = -rotation * deg2rad; // Leaflet usa rotación horaria? No, trigonométrica suele ser antihoraria.

    // Dibujar líneas verticales y horizontales
    for (let i = 0; i <= count; i++) {
      // Línea Horizontal
      const pointsH = [];
      const yStart = offset + (i * cellSize);
      for (let j = 0; j <= count; j += count) { // Solo inicio y fin para optimizar
        const x = offset + (j * cellSize);
        const y = yStart;
        const rotated = rotatePoint(x, y, rotRad);
        pointsH.push(metersToLatLon(lat, lon, rotated.x, rotated.y));
      }
      L.polyline(pointsH, { color: '#00bcd4', weight: 1, opacity: 0.7, dashArray: '2, 2' }).addTo(currentArchaeologicalGrid);

      // Línea Vertical
      const pointsV = [];
      const xStart = offset + (i * cellSize);
      for (let j = 0; j <= count; j += count) {
        const x = xStart;
        const y = offset + (j * cellSize);
        const rotated = rotatePoint(x, y, rotRad);
        pointsV.push(metersToLatLon(lat, lon, rotated.x, rotated.y));
      }
      L.polyline(pointsV, { color: '#00bcd4', weight: 1, opacity: 0.7, dashArray: '2, 2' }).addTo(currentArchaeologicalGrid);
    }

    currentArchaeologicalGrid.addTo(window._mapaCorpus);
    bootstrap.Modal.getInstance(document.getElementById('modalArchaeologicalGrid')).hide();
    showMapToast(`Rejilla de ${count * cellSize}x${count * cellSize}m generada`, '#4caf50');
  }

  // Helpers Rejilla
  function rotatePoint(x, y, angle) {
    return {
      x: x * Math.cos(angle) - y * Math.sin(angle),
      y: x * Math.sin(angle) + y * Math.cos(angle)
    };
  }

  function metersToLatLon(originLat, originLon, dx, dy) {
    const R = 6378137; // Radio Tierra
    const dLat = dy / R;
    const dLon = dx / (R * Math.cos(Math.PI * originLat / 180));
    return [originLat + dLat * 180 / Math.PI, originLon + dLon * 180 / Math.PI];
  }

  // --- PERFIL DE ELEVACIÓN (PROFESSIONAL) ---
  let elevationDrawHandler = null;
  let elevationMoveHandler = null;
  let elevationLine = null;
  let elevationTempLine = null;
  let elevationMarkers = [];
  let elevationProfileChart = null;
  let hasLocalDEM = false;
  let demCoverageLayers = L.layerGroup(); // Para mostrar el área de los TIFs
  let elevationHighlightLayer = L.layerGroup(); // Para resaltar tramos en el mapa
  let allLayersIndex = {}; // Para búsqueda rápida por Leaflet ID

  /**
   * Carga el análisis detallado desde una capa ya visible en el mapa (vía Popup)
   */
  function loadElevationAnalysisFromFeature(leafletId) {
      const layer = findLayerInMapById(leafletId);
      if (!layer || !layer.feature) {
          showMapToast("Error: No se pudo localizar la capa", "#f44336");
          return;
      }

      const feature = layer.feature;
      if (feature.properties.type !== 'elevation_profile') return;

      // 1. Vincular a la línea global para que el hover funcione
      if (elevationLine && window._mapaCorpus.hasLayer(elevationLine)) {
          // Si ya hay uno activo, preguntar o limpiar
      }
      
      elevationLine = layer;
      currentElevationData = feature.properties.data;

      // 2. Mostrar y actualizar panel
      let panel = document.getElementById('elevation-profile-panel');
      if (!panel) panel = createElevationProfilePanel();
      panel.classList.remove('d-none');
      
      const name = feature.properties.nombre || "Perfil cargado";
      document.getElementById('elevation-panel-title').innerText = "ANÁLISIS: " + name;
      
      renderElevationChart(currentElevationData);
      updateElevationAnalysis();
      
      window._mapaCorpus.fitBounds(layer.getBounds());
      showMapToast("Análisis activo para: " + name, "#4caf50");
  }

  /**
   * Helper para encontrar una capa en el mapa recorriendo grupos
   */
  function findLayerInMapById(id) {
      let found = null;
      window._mapaCorpus.eachLayer(l => {
          if (l._leaflet_id == id) found = l;
      });
      return found;
  }

  function highlightElevationSegment(startIdx, endIdx, color) {
    if (!window.currentElevationData || window.currentElevationData.length === 0) return;
    elevationHighlightLayer.clearLayers();
    
    const segmentPoints = window.currentElevationData.slice(startIdx, endIdx + 1)
        .map(pt => [pt.lat, pt.lon || pt.lng]);
    
    if (segmentPoints.length < 2) return;
    
    const poly = L.polyline(segmentPoints, {
        color: color === 'inherit' ? '#ffeb3b' : color,
        weight: 8,
        opacity: 0.8,
        lineCap: 'round'
    }).addTo(elevationHighlightLayer);
    
    // Añadir un brillo exterior
    L.polyline(segmentPoints, {
        color: 'white',
        weight: 12,
        opacity: 0.3
    }).addTo(elevationHighlightLayer);
    
    elevationHighlightLayer.addTo(window._mapaCorpus);

    // Resaltar en el gráfico
    if (elevationProfileChart) {
      const data = window.currentElevationData;
      const isDarkMode = document.body.classList.contains('dark-mode') || document.documentElement.getAttribute('data-theme') === 'dark';
      
      elevationProfileChart.options.plugins.highlightPlugin = {
          startDist: data[startIdx].dist,
          endDist: data[endIdx].dist,
          fillColor: isDarkMode ? 'rgba(255,152,0,0.2)' : 'rgba(41,74,96,0.15)',
          borderColor: color === 'inherit' ? '#ffeb3b' : color
      };
      elevationProfileChart.update('none');
    }
  }

  function clearElevationHighlight() {
    elevationHighlightLayer.clearLayers();
    if (elevationProfileChart) {
        delete elevationProfileChart.options.plugins.highlightPlugin;
        elevationProfileChart.update('none');
    }
  }

  async function activateElevationProfile() {
    // 1. Verificar si ya hay MDT en el servidor
    try {
      const resp = await fetch('/api/layers/check_dem');
      const data = await resp.json();
      hasLocalDEM = data.count > 0;
      
      // Dibujar rectángulos de cobertura si existen
      demCoverageLayers.clearLayers();
      if (data.count > 0) {
        data.files.forEach(fileInfo => {
          if (fileInfo.bounds) {
            const b = fileInfo.bounds;
            const rect = L.rectangle([[b.south, b.west], [b.north, b.east]], {
              color: "#ff9800",
              weight: 2,
              fillOpacity: 0.05,
              dashArray: "5, 5",
              interactive: false
            });
            rect.addTo(demCoverageLayers);
          }
        });
        demCoverageLayers.addTo(window._mapaCorpus);
      }
    } catch (e) {
      console.warn("Error verificando MDT local:", e);
      hasLocalDEM = false;
    }

    // 2. Mostrar modal siempre según petición de confirmación, pero informando
    const notice = document.getElementById('dem-exists-notice');
    if (hasLocalDEM) {
       notice.classList.remove('d-none');
    } else {
       notice.classList.add('d-none');
    }

    const modalEl = document.getElementById('modalElevationSetup');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
  }

  function confirmStartProfileWithoutDem() {
    const modalEl = document.getElementById('modalElevationSetup');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
    startDrawingElevationProfile();
  }

  function startDrawingElevationProfile(initialLatLngs = []) {
    if (elevationDrawHandler) deactivateElevationProfile();
    elevationMarkers = [];

    if (initialLatLngs.length === 0) {
        showMapToast('Haz clic para marcar el inicio del perfil.', '#ff9800');
    } else {
        showMapToast('Ramificación iniciada. Haz clic para continuar el perfil.', '#ff9800');
    }

    // Línea real consolidada
    elevationLine = L.polyline(initialLatLngs, { color: '#ff9800', weight: 4 }).addTo(window._mapaCorpus);
    
    // Línea elástica (rubberband)
    elevationTempLine = L.polyline([], { 
        color: '#ff9800', 
        weight: 2, 
        dashArray: '5, 10', 
        opacity: 0.6 
    }).addTo(window._mapaCorpus);

    // Re-crear marcadores si hay puntos iniciales
    initialLatLngs.forEach(latlng => {
        const marker = L.circleMarker(latlng, {
            radius: 5,
            color: '#ff9800',
            fillColor: '#fff',
            fillOpacity: 1,
            weight: 2
        }).addTo(window._mapaCorpus);
        elevationMarkers.push(marker);
    });

    elevationDrawHandler = function (e) {
      const latlng = e.latlng;
      elevationLine.addLatLng(latlng);
      
      // Marcador visual para feedback inmediato
      const marker = L.circleMarker(latlng, {
        radius: 5,
        color: '#ff9800',
        fillColor: '#fff',
        fillOpacity: 1,
        weight: 2
      }).addTo(window._mapaCorpus);
      elevationMarkers.push(marker);

      if (elevationLine.getLatLngs().length === 1) {
          showMapToast('Mueve el ratón y haz clic para el siguiente punto. Doble clic para terminar.', '#ff9800');
      }
    };

    elevationMoveHandler = function (e) {
      const points = elevationLine.getLatLngs();
      if (points.length > 0) {
        const lastPoint = points[points.length - 1];
        elevationTempLine.setLatLngs([lastPoint, e.latlng]);
      }
    };

    window._mapaCorpus.on('click', elevationDrawHandler);
    window._mapaCorpus.on('mousemove', elevationMoveHandler);
    window._mapaCorpus.on('dblclick', finishElevationProfile);

    const mapContainer = document.getElementById('mapa-corpus');
    if (mapContainer) mapContainer.style.cursor = 'crosshair';
  }

  function deactivateElevationProfile() {
    if (elevationHighlightLayer) {
        elevationHighlightLayer.clearLayers();
        if (window._mapaCorpus.hasLayer(elevationHighlightLayer)) {
            window._mapaCorpus.removeLayer(elevationHighlightLayer);
        }
    }
    if (elevationDrawHandler) {
      window._mapaCorpus.off('click', elevationDrawHandler);
      window._mapaCorpus.off('mousemove', elevationMoveHandler);
      window._mapaCorpus.off('dblclick', finishElevationProfile);
      elevationDrawHandler = null;
      elevationMoveHandler = null;
    }
    if (elevationLine) {
      window._mapaCorpus.removeLayer(elevationLine);
      elevationLine = null;
    }
    if (elevationTempLine) {
      window._mapaCorpus.removeLayer(elevationTempLine);
      elevationTempLine = null;
    }
    if (elevationMarkers) {
      elevationMarkers.forEach(m => window._mapaCorpus.removeLayer(m));
      elevationMarkers = [];
    }
    // Quitar también los rectángulos de cobertura al desactivar
    if (window._mapaCorpus.hasLayer(demCoverageLayers)) {
       window._mapaCorpus.removeLayer(demCoverageLayers);
    }
    const mapContainer = document.getElementById('mapa-corpus');
    if (mapContainer) mapContainer.style.cursor = '';
    const panel = document.getElementById('elevation-profile-panel');
    if (panel) panel.remove(); 
  }

  async function finishElevationProfile() {
    const latlngs = elevationLine.getLatLngs();
    if (latlngs.length < 2) {
      deactivateElevationProfile();
      return;
    }

    // Limpiar temporales de dibujo
    if (elevationTempLine) {
      window._mapaCorpus.removeLayer(elevationTempLine);
      elevationTempLine = null;
    }
    window._mapaCorpus.off('click', elevationDrawHandler);
    window._mapaCorpus.off('mousemove', elevationMoveHandler);
    window._mapaCorpus.off('dblclick', finishElevationProfile);
    elevationDrawHandler = null;
    elevationMoveHandler = null;
    const mapContainer = document.getElementById('mapa-corpus');
    if (mapContainer) mapContainer.style.cursor = '';

    // Mostrar panel
    let panel = document.getElementById('elevation-profile-panel');
    if (!panel) panel = createElevationProfilePanel();
    panel.classList.remove('d-none');

    // Muestrear puntos - Aumentamos resolución para análisis detallado
    const samples = samplePoints(latlngs, 100);
    const data = await fetchElevationData(samples);
    currentElevationData = data;

    renderElevationChart(data);
    updateElevationAnalysis();
  }
    function createElevationProfilePanel() {
      const isDarkMode = document.body.classList.contains("dark-mode") || document.documentElement.getAttribute("data-theme") === "dark";

      // SIRIO PALETTES - Mejora Modo Oscuro
      const bg = isDarkMode ? "#121212" : "#ffffff";
      const border = isDarkMode ? "#444" : "rgba(41,74,96,0.3)";
      const textColor = isDarkMode ? "#ff9800" : "#294a60";
      const headerBg = isDarkMode ? "#1a1a1a" : "#294a60";
      const headerText = isDarkMode ? "#ff9800" : "#ffffff";
      const accentColor = isDarkMode ? "#ff9800" : "#294a60";

      const html = `
          <div id="elevation-profile-panel" class="gis-float-panel shadow-lg" 
               style="width: 1100px; height: 550px; z-index: 30000 !important; display: flex !important; flex-direction: column; position: fixed; background: ${bg}; border: 1px solid ${isDarkMode ? "#444" : border}; border-radius: 8px; overflow: visible; font-family: 'Inter', sans-serif; box-shadow: 0 10px 40px rgba(0,0,0,0.5);">
            <div class="digitize-header digitize-draggable-handle py-1 px-3 d-flex justify-content-between align-items-center" 
                 style="background: ${headerBg}; cursor: move; min-height: 28px; border-bottom: 1px solid ${isDarkMode ? "rgba(255,152,0,0.2)" : "transparent"}; border-top-left-radius: 7px; border-top-right-radius: 7px;">
              <span id="elevation-panel-title" style="font-size: 0.7rem; font-weight: 800; color: ${headerText}; letter-spacing: 1px; text-transform: uppercase;">
                <i class="fa-solid fa-chart-line me-2"></i>PERFIL DE ELEVACIÓN
              </span>
              <div class="d-flex align-items-center gap-1">
                  <div class="dropdown d-inline-block">
                    <button class="btn btn-xs btn-link text-decoration-none py-0 px-2 dropdown-toggle" 
                            style="font-size: 10px; color: ${headerText};" data-bs-toggle="dropdown" aria-expanded="false" onclick="updateRecentElevationProfilesDropdown()">
                        <i class="fa-solid fa-folder-open me-1"></i> CARGAR
                    </button>
                    <ul class="dropdown-menu dropdown-menu-dark shadow" id="elevation-load-dropdown" style="font-size: 0.72rem; min-width: 200px; border: 1px solid #444;">
                        <li><a class="dropdown-item py-1" href="#" onclick="loadElevationProfileDialog()">
                            <i class="fa-solid fa-search me-2 opacity-75"></i> Buscar todos...</a></li>
                        <li><hr class="dropdown-divider opacity-25"></li>
                        <li class="px-3 py-1 text-muted small" id="recent-profiles-header" style="font-size: 0.6rem; text-transform: uppercase;">Recientes</li>
                    </ul>
                  </div>

                  <button onclick="downloadElevationProfileImage()" class="btn btn-xs btn-link text-decoration-none py-0 px-2" style="font-size: 10px; color: ${headerText};">
                      <i class="fa-solid fa-camera me-1"></i> EXPORTAR
                  </button>
                  <button onclick="saveElevationProfile()" class="btn btn-xs btn-link text-decoration-none py-0 px-2" style="font-size: 10px; color: ${headerText};">
                      <i class="fa-solid fa-save me-1"></i> GUARDAR
                  </button>
                  <button onclick="deactivateElevationProfile()" class="ms-2" style="background:none; border:none; color:${headerText}; padding:0; line-height:1; font-size:16px; cursor:pointer; opacity:0.8;">&times;</button>
              </div>
            </div>

<div class="d-flex flex-row flex-grow-1" style="overflow: hidden; min-height: 0;">
              <!-- Main Content: Chart -->
              <div class="p-3 d-flex flex-column" style="flex: 2; border-right: 1px solid ${isDarkMode ? '#222' : '#eee'};">
               <div id="elevation-stats-display" class="d-flex justify-content-around mb-2 p-2 rounded" style="background: ${isDarkMode ? 'rgba(255,152,0,0.05)' : 'rgba(41,74,96,0.05)'}; font-size: 0.7rem; color: ${textColor}; font-weight: 600;">
                  <!-- Stats will be injected here -->
               </div>
               <div class="flex-grow-1" style="position: relative; min-height: 0;">
                  <canvas id="elevationChartCanvas"></canvas>
               </div>
            </div>

            <!-- Side Panel: Table -->
            <div class="p-0 d-flex flex-column" style="flex: 1; min-height: 0; background: ${isDarkMode ? '#0a0a0a' : '#fcfcfc'}; color: ${isDarkMode ? '#eee' : '#333'};">
               <div class="p-2 border-bottom d-flex align-items-center justify-content-between" style="background: ${isDarkMode ? '#1a1a1a' : '#f5f5f5'}; border-bottom: 1px solid ${isDarkMode ? '#333' : '#ddd'} !important;">
                  <span style="font-size: 0.65rem; font-weight: bold; color: ${textColor};">ANÁLISIS POR TRAMOS</span>
                  <select id="elevation-interval-select" onchange="updateElevationAnalysis()" 
                          class="form-select form-select-sm py-0" 
                          style="width: 90px; font-size: 0.65rem; height: 24px; background-color: ${isDarkMode ? '#333' : '#fff'}; color: ${isDarkMode ? '#fff' : '#333'}; border-color: ${isDarkMode ? '#444' : '#ccc'};">
                     <option value="50">50m</option>
                     <option value="100" selected>100m</option>
                     <option value="250">250m</option>
                     <option value="500">500m</option>
                     <option value="1000">1km</option>
                  </select>
               </div>
               <div id="elevation-table-container" class="flex-grow-1 overflow-auto" style="background: ${isDarkMode ? '#121212' : '#ffffff'}; min-height: 0;">
                  <!-- Table will be injected here -->
               </div>
            </div>
          </div>

          <div class="px-3 py-2 text-center border-top font-mono" 
               style="background: ${isDarkMode ? '#1a1a1a' : '#f8f9fa'}; font-size: 0.75rem; color: ${isDarkMode ? '#888' : '#555'}; border-top: 1px solid ${isDarkMode ? '#333' : '#ddd'} !important; border-bottom-left-radius: 7px; border-bottom-right-radius: 7px;">
            <div class="d-flex align-items-center justify-content-between mb-0 pb-1">
                <div class="text-start" style="line-height: 1.2;">
                    <button onclick="document.getElementById('elevation-dem-upload').click()" 
                            class="btn btn-sm btn-outline-warning py-0 px-2" 
                            title="Subir nuevo archivo TIFF de elevación"
                            style="font-size: 0.65rem; border-radius: 4px; height: 20px;">
                        <i class="fa-solid fa-upload me-1"></i> ACTUALIZAR MDT (.tif)
                    </button>
                    <button id="btn-refresh-elevation" onclick="refreshElevationData()" 
                            class="btn btn-sm btn-outline-info py-0 px-2 ms-1" 
                            title="Recalcular altitudes del perfil actual (útil tras cargar nuevos TIFF)"
                            style="font-size: 0.65rem; border-radius: 4px; height: 20px;">
                        <i class="fa-solid fa-arrows-rotate me-1"></i> REPROCESAR
                    </button>
                    <input type="file" id="elevation-dem-upload" style="display:none" accept=".tif,.tiff" onchange="handleElevationDemUpload(this)">
                </div>
                <div class="text-end flex-grow-1 ps-3 precision-text-indicator" style="font-size: 0.6rem; opacity: 0.8;">
                   <i class="fa-solid fa-triangle-exclamation text-warning me-1"></i>
                   Precisión: ${hasLocalDEM ? 'ALTA (MDT Local)' : 'MEDIA (Servidor IGN)'}
                </div>
            </div>
          </div>
        </div>
      `;
    document.body.insertAdjacentHTML('beforeend', html);
    const panel = document.getElementById('elevation-profile-panel');

    const w = window.innerWidth;
    const h = window.innerHeight;
      panel.style.left = Math.round((w - 1100) / 2) + 'px';
      panel.style.top = Math.round((h - 550) / 2) + 'px';
      
      if (typeof makeDraggable === 'function') makeDraggable(panel);
      return panel;
    }

    async function handleElevationDemUpload(input, isInitial = false) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);
    showMapToast('Subiendo MDT local...', '#ff9800');
    try {
      const resp = await fetch('/api/layers/upload_dem', { method: 'POST', body: formData });
      const data = await resp.json();
      if (data.success) {
        showMapToast('MDT cargado con éxito.', '#4caf50');
        hasLocalDEM = true;

        const precEl = document.querySelector('.precision-text-indicator');
        if (precEl) {
            precEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation text-warning me-1"></i> Precisión: ALTA (MDT Local)';
        }
        
        // Dibujar el nuevo rectángulo de cobertura
        if (data.bounds) {
          const b = data.bounds;
          L.rectangle([[b.south, b.west], [b.north, b.east]], {
            color: "#ff9800",
            weight: 2,
            fillOpacity: 0.05,
            dashArray: "5, 5",
            interactive: false
          }).addTo(demCoverageLayers);
          demCoverageLayers.addTo(window._mapaCorpus);
        }

        if (isInitial) {
           hasLocalDEM = true; 
           const modalEl = document.getElementById('modalElevationSetup');
           const modal = bootstrap.Modal.getInstance(modalEl);
           if (modal) modal.hide();
           startDrawingElevationProfile();
        } else {
           if (window.currentElevationData && window.currentElevationData.length > 0) {
              refreshElevationData();
           }
        }
      } else {
        showMapToast('Error: ' + data.error, '#f44336');
      }
    } catch (e) {
      console.error(e);
      showMapToast('Error de conexión al subir MDT', '#f44336');
    }
  }

  let showSlopeInChart = false;
  window.currentElevationData = [];

  function toggleElevationSlope() {
    showSlopeInChart = !showSlopeInChart;
    const isDarkMode = document.body.classList.contains('dark-mode') || document.documentElement.getAttribute('data-theme') === 'dark';
    const accentColor = isDarkMode ? '#ff9800' : '#294a60';
    const btn = document.getElementById('btn-toggle-slope');
    if (btn) {
      btn.style.background = showSlopeInChart ? accentColor : 'transparent';
      btn.style.color = showSlopeInChart ? (isDarkMode ? '#000' : '#fff') : accentColor;
    }
    renderElevationChart(currentElevationData);
  }

  function samplePoints(latlngs, numSamples) {
    const samples = [];
    let totalAccumulatedDist = 0;
    const fullPoints = [];
    for (let i = 0; i < numSamples; i++) {
      const t = i / (numSamples - 1);
      const index = t * (latlngs.length - 1);
      const lower = Math.floor(index);
      const upper = Math.ceil(index);
      const weight = index - lower;
      const p1 = L.latLng(latlngs[lower]);
      const p2 = L.latLng(latlngs[upper]);
      const pt = {
        lat: p1.lat * (1 - weight) + p2.lat * weight,
        lng: p1.lng * (1 - weight) + p2.lng * weight
      };
      if (i > 0) {
        const prev = fullPoints[i - 1];
        totalAccumulatedDist += L.latLng(prev.lat, prev.lng).distanceTo(L.latLng(pt.lat, pt.lng));
      }
      fullPoints.push(pt);
      samples.push({ lat: pt.lat, lon: pt.lng, dist: totalAccumulatedDist });
    }
    return samples;
  }

  async function fetchElevationData(samples) {
      showMapToast('Obteniendo altitudes...', '#ff9800');
      
      const results = [];
      
      // 1. Intentar primero con DEM local si existe (Acepta cualquier cantidad de puntos)
      try {
        const localResp = await fetch("/api/altitud_raster", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ points: samples.map(s => [s.lon || s.lng, s.lat]) })
        });
        if (localResp.ok) {
          const localJson = await localResp.json();
          if (localJson.success && localJson.items.length > 0) {
            console.log("[Profile] Usando datos de elevación LOCAL (Raster)");
            return localJson.items.map((item, i) => ({
              dist: samples[i].dist,
              lat: samples[i].lat,
              lon: samples[i].lon || samples[i].lng,
              alt: item.altitud,
              slope: i === 0 ? 0 : ((item.altitud - localJson.items[i-1].altitud) / (samples[i].dist - samples[i-1].dist)) * 100
            }));
          }
        }
      } catch (e) {
        console.log("[Profile] No hay DEM local o fallo, recurriendo a IGN...");
      }

      // 2. Fallback a IGN (en lotes de 50 para cumplir con su API)
      try {
        const batchSize = 50;
        const allIgnItems = [];
        
        for (let i = 0; i < samples.length; i += batchSize) {
            const batch = samples.slice(i, i + batchSize);
            const pointsStr = batch.map(s => `${parseFloat(s.lon || s.lng).toFixed(6)},${parseFloat(s.lat).toFixed(6)}`).join('|');
            const url = `https://servicios.ign.es/puntos-altitud/api/puntos?puntos=${pointsStr}&sis_coords=WGS84&precision=2`;
            
            let resp;
            try {
                resp = await fetch(url);
                if (!resp.ok) throw new Error("API Directa falló");
            } catch (e) {
                const proxyUrl = `/api/proxy/wms?url=${encodeURIComponent(url)}`;
                resp = await fetch(proxyUrl);
            }
            
            const json = await resp.json();
            const items = Array.isArray(json) ? json : (json && json.items ? json.items : []);
            allIgnItems.push(...items);
        }

        if (allIgnItems.length > 0) {
          allIgnItems.forEach((item, i) => {
            if (i < samples.length) {
              const alt = parseFloat(item.altitud);
              results.push({
                dist: samples[i].dist,
                lat: samples[i].lat,
                lon: samples[i].lon || samples[i].lng,
                alt: isNaN(alt) ? 0 : Math.round(alt * 10) / 10
              });
            }
          });
          
          // Recalcular pendientes si venimos de IGN
          results.forEach((r, idx) => {
              r.slope = idx === 0 ? 0 : ((r.alt - results[idx-1].alt) / (r.dist - results[idx-1].dist)) * 100;
          });
          
          return results;
        }
      } catch (err) {
        console.error("[Profile] Error IGN API:", err);
      }

      // 3. Fallback final: Relieve simulado (solo si todo lo anterior falla)
      if (results.length === 0) {
        console.warn("[Profile] Usando relieve simulado por fallo en servicios IGN.");
        showMapToast("Servicio IGN no disponible. Usando relieve estimado.", "#f44336");
        samples.forEach((s, idx) => {
          const baseAlt = 50;
          const wave = Math.sin(idx * 0.2) * 20;
          const noise = Math.sin(idx * 0.8) * 5;
          results.push({ 
            dist: s.dist, 
            lat: s.lat,
            lon: s.lon,
            alt: Math.max(0, Math.round((baseAlt + wave + noise) * 10) / 10) 
          });
        });
      }

      // Calcular pendientes
      for (let i = 0; i < results.length; i++) {
        if (i === 0) {
          results[i].slope = 0;
        } else {
          const dh = results[i].alt - results[i - 1].alt;
          const dd = results[i].dist - results[i - 1].dist;
          results[i].slope = dd > 0 ? (dh / dd) * 100 : 0;
        }
      }
      
    return results;
  }

  function renderElevationChart(data) {
    window.currentElevationData = data;
    const isDarkMode = document.body.classList.contains('dark-mode') || document.documentElement.getAttribute('data-theme') === 'dark';
    const canvas = document.getElementById('elevationChartCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (elevationProfileChart) elevationProfileChart.destroy();

    // Set global font for Chart
    Chart.defaults.font.family = "'Inter', sans-serif";

    const maxDist = data[data.length - 1].dist;
    const distLabel = (d) => maxDist > 2000 ? (d / 1000).toFixed(1) + ' km' : Math.round(d) + ' m';

    // SIRIO COLORS & STYLE
    const sirioOrange = isDarkMode ? '#ff9800' : '#294a60';
    const sirioSlope = isDarkMode ? '#ff5722' : '#d93025';
    const labelColor = isDarkMode ? '#ccc' : '#333';
    const gridColor = isDarkMode ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';

    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, isDarkMode ? 'rgba(255, 152, 0, 0.4)' : 'rgba(41, 74, 96, 0.4)');
    gradient.addColorStop(1, isDarkMode ? 'rgba(255, 152, 0, 0.05)' : 'rgba(41, 74, 96, 0.05)');

    elevationProfileChart = new Chart(ctx, {
      type: 'line',
      plugins: [{
          id: 'highlightPlugin',
          beforeDraw: (chart) => {
              const pluginOptions = chart.config.options.plugins.highlightPlugin;
              if (!pluginOptions) return;
              
              const {ctx, chartArea: {top, bottom}, scales: {x}} = chart;
              const xStart = x.getPixelForValue(pluginOptions.startDist);
              const xEnd = x.getPixelForValue(pluginOptions.endDist);
              
              ctx.save();
              ctx.fillStyle = pluginOptions.fillColor;
              ctx.fillRect(xStart, top, xEnd - xStart, bottom - top);
              
              ctx.strokeStyle = pluginOptions.borderColor;
              ctx.lineWidth = 2;
              ctx.setLineDash([5, 5]);
              ctx.strokeRect(xStart, top, xEnd - xStart, bottom - top);
              ctx.restore();
          }
      }],
      data: {
        datasets: [
          {
            label: 'Altitud (m)',
            data: data.map(d => ({ x: d.dist, y: d.alt })),
            borderColor: sirioOrange,
            backgroundColor: gradient,
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            borderWidth: 3,
            yAxisID: 'y'
          },
          {
            label: 'Pendiente (%)',
            data: data.map(d => ({ x: d.dist, y: d.slope })),
            borderColor: sirioSlope,
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.4,
            pointRadius: 0,
            borderWidth: 2,
            borderDash: [5, 5],
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            align: 'end',
            labels: { color: isDarkMode ? '#888' : '#555', font: { size: 10, weight: '700' }, usePointStyle: true, boxWidth: 6 }
          },
          tooltip: {
            backgroundColor: isDarkMode ? 'rgba(10,10,10,0.95)' : 'rgba(255,255,255,0.95)',
            titleColor: sirioOrange,
            bodyColor: isDarkMode ? '#fff' : '#000',
            borderColor: isDarkMode ? 'rgba(255,152,0,0.4)' : 'rgba(41,74,96,0.4)',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 4,
            usePointStyle: true,
            callbacks: {
              label: function (context) {
                let label = context.dataset.label || '';
                if (label) label += ': ';
                if (context.parsed.y !== null) {
                  label += context.parsed.y.toFixed(1) + (context.datasetIndex === 0 ? ' m' : ' %');
                }
                return label;
              }
            }
          }
        },
        scales: {
          x: {
            type: 'linear',
            grid: { color: gridColor, drawBorder: false },
            ticks: { 
              color: isDarkMode ? '#888' : '#555', 
              font: { size: 10, family: 'JetBrains Mono' }, 
              callback: function (value) { 
                return value >= 1000 ? (value / 1000).toFixed(1) + ' km' : Math.round(value) + ' m'; 
              } 
            }
          },
          y: {
            title: { display: true, text: 'Altitud (m)', color: sirioOrange, font: { size: 10, weight: 'bold' } },
            grid: { color: gridColor, drawBorder: false },
            ticks: { color: labelColor, font: { size: 10, family: 'JetBrains Mono' } }
          },
          y1: {
            position: 'right',
            title: { display: true, text: 'Pendiente (%)', color: sirioSlope, font: { size: 10, weight: 'bold' } },
            grid: { drawOnChartArea: false },
            ticks: { color: sirioSlope, font: { size: 10, family: 'JetBrains Mono' } },
            suggestedMin: -40,
          }
        }
      }
    });
  }

  function updateElevationAnalysis() {
    if (!window.currentElevationData || window.currentElevationData.length === 0) return;
    
    updateElevationStats(window.currentElevationData);
    
    const interval = parseInt(document.getElementById('elevation-interval-select')?.value || 100);
    renderIntervalTable(window.currentElevationData, interval);
  }

  function updateElevationStats(data) {
    const totalDist = data[data.length - 1].dist;
    const alts = data.map(d => d.alt);
    const minAlt = Math.min(...alts);
    const maxAlt = Math.max(...alts);
    const gain = data.reduce((acc, curr, idx) => {
        if (idx === 0) return 0;
        const diff = curr.alt - data[idx-1].alt;
        return acc + (diff > 0 ? diff : 0);
    }, 0);
    const loss = data.reduce((acc, curr, idx) => {
        if (idx === 0) return 0;
        const diff = curr.alt - data[idx-1].alt;
        return acc + (diff < 0 ? Math.abs(diff) : 0);
    }, 0);

    const avgSlope = totalDist > 0 ? (gain / totalDist) * 100 : 0; 
    const maxSlope = Math.max.apply(null, data.map(d => d.slope || 0));

    const distStr = totalDist >= 1000 ? (totalDist/1000).toFixed(2) + ' km' : Math.round(totalDist) + ' m';
    
    const statsHtml = `
        <div class="text-center">
            <div style="opacity: 0.7; font-size: 0.55rem;">DISTANCIA</div>
            <div>${distStr}</div>
        </div>
        <div class="text-center">
            <div style="opacity: 0.7; font-size: 0.55rem;">DESNIVEL +</div>
            <div class="text-success">${Math.round(gain)} m</div>
        </div>
        <div class="text-center">
            <div style="opacity: 0.7; font-size: 0.55rem;">DESNIVEL -</div>
            <div class="text-danger">${Math.round(loss)} m</div>
        </div>
        <div class="text-center">
            <div style="opacity: 0.7; font-size: 0.55rem;">PEND. MEDIA</div>
            <div>${avgSlope.toFixed(1)} %</div>
        </div>
        <div class="text-center">
            <div style="opacity: 0.7; font-size: 0.55rem;">PEND. MÁX</div>
            <div>${maxSlope.toFixed(1)} %</div>
        </div>
        <div class="text-center">
            <div style="opacity: 0.7; font-size: 0.55rem;">ALT. MÁX</div>
            <div>${Math.round(maxAlt)} m</div>
        </div>
    `;
    
    const container = document.getElementById('elevation-stats-display');
    if (container) container.innerHTML = statsHtml;
  }

  function renderIntervalTable(data, interval) {
    const container = document.getElementById('elevation-table-container');
    if (!container) return;

    const isDarkMode = document.body.classList.contains('dark-mode') || document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDarkMode ? '#eee' : '#333';

    let html = `
        <table class="table table-sm table-borderless m-0" style="color: ${textColor}; font-size: 0.75rem; border-collapse: separate; border-spacing: 0 2px;">
            <thead style="position: sticky; top: 0; background: ${isDarkMode ? '#1a1a1a' : '#f5f5f5'}; z-index: 10; border-bottom: 2px solid ${isDarkMode ? '#333' : 'rgba(128,128,128,0.2)'};">
                <tr>
                    <th class="ps-2 py-2">Distancia</th>
                    <th class="text-end py-2">Altitud</th>
                    <th class="text-end py-2">Pendiente</th>
                    <th class="text-center py-2" style="width: 30px;"><i class="fa-solid fa-code-branch"></i></th>
                </tr>
            </thead>
            <tbody>
    `;

    let currentLimit = interval;
    let startIdx = 0;
    
    for (let i = 1; i < data.length; i++) {
        if (data[i].dist >= currentLimit || i === data.length - 1) {
            const segmentDist = data[i].dist - data[startIdx].dist;
            const segmentGain = data[i].alt - data[startIdx].alt;
            const segmentSlope = segmentDist > 0 ? (segmentGain / segmentDist) * 100 : 0;
            
            const startStr = Math.round(data[startIdx].dist) + 'm';
            const endStr = Math.round(data[i].dist) + 'm';
            
            const slopeColor = segmentSlope > 12 ? '#d32f2f' : (segmentSlope > 8 ? '#f44336' : (segmentSlope > 4 ? '#ff9800' : (segmentSlope < 0 ? '#2196f3' : (isDarkMode ? '#aaa' : '#666'))));

            html += `
                <tr onmouseenter="highlightElevationSegment(${startIdx}, ${i}, '${slopeColor}'); this.style.background='${isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)'}'" 
                    onmouseleave="clearElevationHighlight(); this.style.background='${isDarkMode ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.01)'}'"
                    style="cursor: pointer; transition: background 0.2s; border-bottom: 1px solid rgba(128,128,128,0.1); background: ${isDarkMode ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.01)'};">
                    <td class="ps-2 py-2" style="font-weight: 500;">${startStr} - ${endStr}</td>
                    <td class="text-end py-2 font-mono">${Math.round(data[i].alt)}m</td>
                    <td class="text-end py-2 font-mono" style="color: ${slopeColor}; font-weight: bold; font-size: 0.8rem;">
                        ${segmentSlope > 0 ? '+' : ''}${segmentSlope.toFixed(1)}%
                    </td>
                    <td class="text-center py-2">
                        <button class="btn btn-xs btn-outline-warning border-0 p-0" title="Ramificar perfil desde este punto" onclick="branchElevationProfileAt(${i}); event.stopPropagation();">
                            <i class="fa-solid fa-code-branch" style="font-size: 0.7rem;"></i>
                        </button>
                    </td>
                </tr>
            `;
            
            startIdx = i;
            currentLimit += interval;
        }
    }

    html += `</tbody></table>`;
    container.innerHTML = html;
  }

  /**
   * Permite continuar un perfil desde un punto intermedio (ramificación)
   */
  function branchElevationProfileAt(idx) {
    if (!window.currentElevationData || !window.currentElevationData[idx]) return;
    
    const point = window.currentElevationData[idx];
    const basePoints = window.currentElevationData.slice(0, idx + 1).map(d => [d.lat, d.lon || d.lng]);
    
    const panel = document.getElementById("elevation-profile-panel");
    if (panel) panel.classList.add("d-none");
    
    deactivateElevationProfile();
    startDrawingElevationProfile(basePoints);
    
    showMapToast(`Ramificando desde ${Math.round(point.dist)}m. Continúa la ruta y haz doble clic para finalizar.`, "#4caf50");
  }

  /**
   * Recalcula las altitudes de todos los puntos del perfil actual.
   * Útil si se ha cargado un nuevo TIFF que cubre zonas que antes no tenían datos.
   */
  async function refreshElevationData() {
    if (!window.currentElevationData || window.currentElevationData.length === 0) {
      showMapToast("No hay un perfil activo para reprocesar", "#ff9800");
      return;
    }
    const btn = document.getElementById('btn-refresh-elevation');
    const originalHtml = btn ? btn.innerHTML : '';
    if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> PROCESANDO...';
    
    showMapToast("Recalculando altitudes con los MDT disponibles...", "#ff9800");
    try {
        const updatedData = await fetchElevationData(window.currentElevationData);
        if (updatedData && updatedData.length > 0) {
            window.currentElevationData = updatedData;
            renderElevationChart(updatedData);
            updateElevationAnalysis();
            showMapToast("Perfil actualizado con éxito", "#4caf50");
        }
    } catch (err) {
        console.error("Error al refrescar altitudes:", err);
        showMapToast("Error al recalcular las altitudes", "#f44336");
    } finally {
        if (btn) btn.innerHTML = originalHtml;
    }
  }

  async function loadElevationProfileDialog() {
    try {
        const resp = await fetch('/api/vector_layers');
        const data = await resp.json();
        
        // Filtrar solo las que son perfiles de elevación
        const profiles = data.filter(l => {
            try {
                const geo = typeof l.geojson === 'string' ? JSON.parse(l.geojson) : l.geojson;
                return geo.features[0]?.properties?.type === 'elevation_profile';
            } catch(e) { return false; }
        });

        if (profiles.length === 0) {
            showMapToast("No se encontraron perfiles guardados", "#ff9800");
            return;
        }

        // Crear un sencillo selector (en una futura iteración podría ser un modal más complejo)
        const nameList = profiles.map((p, i) => `${i+1}. ${p.nombre}`).join('\n');
        const choice = prompt("Selecciona el perfil a cargar (introduce el número):\n\n" + nameList);
        
        if (choice && !isNaN(choice)) {
            const idx = parseInt(choice) - 1;
            if (profiles[idx]) {
                const layer = profiles[idx];
                const geo = typeof layer.geojson === 'string' ? JSON.parse(layer.geojson) : layer.geojson;
                
                // 1. Reconstruir la línea en el mapa
                if (elevationLine && window._mapaCorpus.hasLayer(elevationLine)) window._mapaCorpus.removeLayer(elevationLine);
                if (elevationTempLine) window._mapaCorpus.removeLayer(elevationTempLine);
                elevationHighlightLayer.clearLayers();
                
                const coords = geo.features[0].geometry.coordinates;
                const latlngs = coords.map(c => [c[1], c[0]]);
                
                elevationLine = L.polyline(latlngs, {
                    color: '#ff9800',
                    weight: 4,
                    dashArray: '5, 10'
                }).addTo(window._mapaCorpus);
                
                elevationLine.feature = geo.features[0];
                window._mapaCorpus.fitBounds(elevationLine.getBounds());
                
                // 2. Cargar los datos de elevación guardados
                currentElevationData = geo.features[0].properties.data;
                
                // 3. Mostrar el panel si está oculto y actualizar
                let panel = document.getElementById('elevation-profile-panel');
                if (!panel) panel = createElevationProfilePanel();
                panel.classList.remove('d-none');
                
                document.getElementById('elevation-panel-title').innerText = "VISTA: " + layer.nombre;
                
                renderElevationChart(currentElevationData);
                updateElevationAnalysis();
                
                showMapToast("Perfil cargado: " + layer.nombre, "#4caf50");
            }
        }
    } catch (err) {
        console.error("Error cargando perfiles:", err);
        showMapToast("Error al conectar con la base de datos", "#f44336");
    }
  }

  /**
   * Actualiza el men303272 desplegable de perfiles recientes en el panel
   */
  async function updateRecentElevationProfilesDropdown() {
      try {
          const resp = await fetch("/api/vector_layers");
          const data = await resp.json();
          const profiles = data.filter(l => {
              try {
                  const geo = typeof l.geojson === "string" ? JSON.parse(l.geojson) : l.geojson;
                  return geo.features[0]?.properties?.type === "elevation_profile";
              } catch(e) { return false; }
          }).reverse().slice(0, 10);

          const listEl = document.getElementById("elevation-load-dropdown");
          if (!listEl) return;

          const itemsToRemove = listEl.querySelectorAll(".dynamic-p-item");
          itemsToRemove.forEach(i => i.remove());

          profiles.forEach(p => {
              const li = document.createElement("li");
              li.className = "dynamic-p-item";
              li.innerHTML = `<a class="dropdown-item py-1 d-flex justify-content-between align-items-center" href="#" onclick="loadElevationProfileById(${p.id})">
                                <span class="text-truncate" style="max-width: 140px;">${p.nombre}</span>
                                <small class="opacity-50" style="font-size: 0.6rem;">${new Date(p.fecha_creacion).toLocaleDateString()}</small>
                             </a>`;
              listEl.appendChild(li);
          });
          
          if (profiles.length === 0) {
              const li = document.createElement("li");
              li.className = "dynamic-p-item px-3 py-1 text-muted small";
              li.innerText = "No hay perfiles guardados";
              listEl.appendChild(li);
          }
      } catch(e) { console.error(e); }
  }

  /**
   * Carga un perfil espec303255fico por su ID de base de datos
   */
  async function loadElevationProfileById(id) {
      try {
          const resp = await fetch("/api/vector_layers");
          const data = await resp.json();
          const layer = data.find(l => l.id == id);
          if (!layer) return;

          const geo = typeof layer.geojson === "string" ? JSON.parse(layer.geojson) : layer.geojson;
          if (elevationLine && window._mapaCorpus.hasLayer(elevationLine)) window._mapaCorpus.removeLayer(elevationLine);
          if (elevationTempLine) window._mapaCorpus.removeLayer(elevationTempLine);
          elevationHighlightLayer.clearLayers();
          const coords = geo.features[0].geometry.coordinates;
          const latlngs = coords.map(c => [c[1], c[0]]);
          elevationLine = L.polyline(latlngs, { color: "#ff9800", weight: 4, dashArray: "5, 10" }).addTo(window._mapaCorpus);
          elevationLine.feature = geo.features[0];
          window._mapaCorpus.fitBounds(elevationLine.getBounds());
          currentElevationData = geo.features[0].properties.data;
          let panel = document.getElementById("elevation-profile-panel");
          if (!panel) panel = createElevationProfilePanel();
          panel.classList.remove("d-none");
          document.getElementById("elevation-panel-title").innerText = "VISTA: " + layer.nombre;
          renderElevationChart(currentElevationData);
          updateElevationAnalysis();
          
          // Asegurar que aparece en el listado de capas GIS (si está abierto)
          if (window.GISManager && typeof window.GISManager.loadVectorLayersFromDB === 'function') {
              window.GISManager.loadVectorLayersFromDB();
          }

          showMapToast("Perfil cargado: " + layer.nombre, "#4caf50");
      } catch (err) { console.error(err); }
  }

  async function downloadElevationProfileImage() {
    const panel = document.getElementById('elevation-profile-panel');
    if (!panel) return;
    
    const fileName = prompt("Nombre de la imagen:", "Perfil_Elevacion_" + new Date().toLocaleDateString());
    if (!fileName) return;

    showMapToast("Generando infografía...", "#ff9800");

    // Preparar el panel para la captura (ocultar controles temporales)
    const headerBtns = panel.querySelector('.d-flex.align-items-center.gap-2');
    const footerArea = panel.querySelector('.border-top');
    const intervalSelect = document.getElementById('elevation-interval-select')?.parentElement;

    if (headerBtns) headerBtns.style.visibility = 'hidden';
    if (footerArea) footerArea.style.display = 'none';
    if (intervalSelect) intervalSelect.style.visibility = 'hidden';

    try {
        const canvas = await html2canvas(panel, {
            backgroundColor: document.body.classList.contains('dark-mode') ? '#0c0c0c' : '#ffffff',
            scale: 2,
            useCORS: true,
            logging: false,
            allowTaint: true
        });

        const link = document.createElement('a');
        link.download = fileName.replace(/[^a-z0-9]/gi, '_') + '.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
        
        showMapToast("Imagen exportada con éxito", "#4caf50");
    } catch (err) {
        console.error("Error exportando perfil:", err);
        showMapToast("Error al generar la imagen", "#f44336");
    } finally {
        if (headerBtns) headerBtns.style.visibility = 'visible';
        if (footerArea) footerArea.style.display = '';
        if (intervalSelect) intervalSelect.style.visibility = 'visible';
    }
  }

  async function saveElevationProfile() {
    if (!currentElevationData || currentElevationData.length === 0 || !elevationLine) {
        showMapToast("No hay perfil activo para guardar", "#ff9800");
        return;
    }

    const name = prompt("Introduce un nombre para este perfil:", "Perfil de Elevación " + new Date().toLocaleDateString());
    if (!name) return;

    const typeChoice = prompt("Selecciona la naturaleza del perfil:\n1. Altigrafía (Ciclista/Ruta)\n2. Perfil Arqueológico (Corte/Terreno)\n\nIntroduce 1 o 2:", "1");
    if (!typeChoice) return;

    const isArch = typeChoice === "2";
    const profileSubtype = isArch ? "archaeological" : "cycling";
    const defaultColor = isArch ? "#00bcd4" : "#ff9800"; // Cian para arqueo, Naranja para rutas
    const finalDescription = isArch ? "Corte arqueológico generado el " : "Perfil ciclista generado el ";

    const latlngs = elevationLine.getLatLngs();
    const geojson = {
        type: "FeatureCollection",
        features: [{
            type: "Feature",
            geometry: {
                type: "LineString",
                coordinates: latlngs.map(ll => [ll.lng, ll.lat])
            },
            properties: {
                name: name,
                type: "elevation_profile",
                subtype: profileSubtype,
                stats: {
                    distance: currentElevationData[currentElevationData.length - 1].dist,
                    gain: currentElevationData.reduce((acc, curr, idx) => idx === 0 ? 0 : acc + Math.max(0, curr.alt - currentElevationData[idx-1].alt), 0),
                    loss: currentElevationData.reduce((acc, curr, idx) => idx === 0 ? 0 : acc + Math.max(0, currentElevationData[idx-1].alt - curr.alt), 0),
                    maxAlt: Math.max(...currentElevationData.map(d => d.alt)),
                    minAlt: Math.min(...currentElevationData.map(d => d.alt))
                },
                data: currentElevationData
            }
        }]
    };

    try {
        const resp = await fetch('/api/vector_layers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nombre: (isArch ? "[ARQ] " : "[ALT] ") + name,
                descripcion: finalDescription + new Date().toLocaleString(),
                tipo_geometria: "line",
                geojson: geojson,
                color: defaultColor
            })
        });
        const result = await resp.json();
        if (result.success) {
            showMapToast("Perfil guardado correctamente", "#4caf50");
            document.getElementById('elevation-panel-title').innerText = "VISTA: " + name;
            
            // Refrescar capas vectoriales para que aparezca en el listado
            if (window.GISManager && typeof window.GISManager.loadVectorLayersFromDB === 'function') {
                window.GISManager.loadVectorLayersFromDB();
            }
        } else {
            showMapToast("Error al guardar: " + result.error, "#f44336");
        }
    } catch (e) {
        console.error(e);
        showMapToast("Error de conexión al guardar", "#f44336");
    }
  }

  // Exportar funciones globales necesarias para el gestor GIS
  window.createElevationProfilePanel = createElevationProfilePanel;
  window.renderElevationChart = renderElevationChart;
  window.updateElevationAnalysis = updateElevationAnalysis;
  window.branchElevationProfileAt = branchElevationProfileAt;
    window.refreshElevationData = refreshElevationData;
</script>
<!-- Ghost controls -->
<div style="display: none !important;">
  <button type="button" id="btn-exportar-gis-top" class="d-none"></button>
  <button type="button" id="btn-measure-tool-hidden" class="d-none" onclick="toggleMeasureMode('ruler')"></button>
</div>

<!-- SVG Filter for Anaglyph Stereo Effect -->
<svg width="0" height="0" style="position: absolute;">
  <defs>
    <style>
  /* Submenus en Dropdowns de Bootstrap */
  .dropdown-submenu {
    position: relative;
  }
  .dropdown-submenu > .dropdown-menu {
    top: 0;
    left: 100%;
    margin-top: -6px;
    margin-left: -1px;
    border-radius: 0 6px 6px 6px;
