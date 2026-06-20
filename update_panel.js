    function createElevationProfilePanel() {
      const isDarkMode = document.body.classList.contains("dark-mode") || document.documentElement.getAttribute("data-theme") === "dark";
      const bg = isDarkMode ? "#000000" : "#ffffff";
      const textColor = isDarkMode ? "#ffffff" : "#294a60";
      const accentColor = isDarkMode ? "#ff9800" : "#294a60";
      const headerBg = isDarkMode ? "#1a1a1a" : "#294a60";
      const headerText = isDarkMode ? "#ff9800" : "#ffffff";
      const border = isDarkMode ? "#333" : "rgba(41,74,96,0.2)";

      const html = `
          <div id="elevation-profile-panel" class="gis-float-panel shadow-lg" 
               style="width: 900px; height: 580px; z-index: 20000; display: flex; flex-direction: column; position: fixed; background: ${bg}; border: 1px solid ${border}; border-radius: 8px; overflow: hidden; font-family: 'Inter', sans-serif; color: ${textColor};">
            
            <div class="digitize-header digitize-draggable-handle py-1 px-3 d-flex justify-content-between align-items-center" 
                 style="background: ${headerBg}; cursor: move; min-height: 32px; border-bottom: 2px solid ${isDarkMode ? "#ff9800" : "transparent"};">
              <span id="elevation-panel-title" style="font-size: 0.75rem; font-weight: 800; color: ${headerText}; letter-spacing: 1px; text-transform: uppercase;">
                <i class="fa-solid fa-chart-line me-2"></i>PERFIL DE ELEVACIÓN
              </span>
              <div class="d-flex align-items-center gap-1">
                  <div class="dropdown d-inline-block">
                    <button class="btn btn-xs btn-link text-decoration-none py-0 px-2 dropdown-toggle" 
                            style="font-size: 11px; color: ${headerText};" data-bs-toggle="dropdown" aria-expanded="false" onclick="updateRecentElevationProfilesDropdown()">
                        <i class="fa-solid fa-folder-open me-1"></i> CARGAR
                    </button>
                    <ul class="dropdown-menu dropdown-menu-dark shadow" id="elevation-load-dropdown" style="font-size: 0.75rem; min-width: 200px; border: 1px solid #444;">
                        <li><a class="dropdown-item py-1" href="#" onclick="loadElevationProfileDialog()">
                            <i class="fa-solid fa-search me-2 opacity-75"></i> Buscar todos...</a></li>
                        <li><hr class="dropdown-divider opacity-25"></li>
                        <li class="px-3 py-1 text-muted small" id="recent-profiles-header" style="font-size: 0.6rem; text-transform: uppercase;">Recientes</li>
                    </ul>
                  </div>

                  <button onclick="downloadElevationProfileImage()" class="btn btn-xs btn-link text-decoration-none py-0 px-2" style="font-size: 11px; color: ${headerText};">
                      <i class="fa-solid fa-camera me-1"></i> EXPORTAR
                  </button>
                  <button onclick="saveElevationProfile()" class="btn btn-xs btn-link text-decoration-none py-0 px-2" style="font-size: 11px; color: ${headerText};">
                      <i class="fa-solid fa-save me-1"></i> GUARDAR
                  </button>
                  <button onclick="deactivateElevationProfile()" class="ms-2" style="background:none; border:none; color:${headerText}; padding:0; line-height:1; font-size:18px; cursor:pointer; opacity:0.8;">&times;</button>
              </div>
            </div>

            <div id="elevation-stats-display" class="d-flex justify-content-around p-2" 
                 style="background: ${isDarkMode ? 'rgba(255,152,0,0.1)' : 'rgba(41,74,96,0.05)'}; 
                        font-size: 0.75rem; color: ${isDarkMode ? '#ff9800' : '#294a60'}; font-weight: 700; border-bottom: 1px solid ${border};">
            </div>

            <div class="p-3" style="height: 280px; position: relative; background: ${bg};">
               <canvas id="elevationChartCanvas"></canvas>
            </div>

            <div class="flex-grow-1 d-flex flex-column" style="min-height: 0; background: ${bg};">
               <div class="px-3 py-1 d-flex align-items-center justify-content-between" 
                    style="background: ${isDarkMode ? '#1a1a1a' : '#f5f5f5'}; border-top: 1px solid ${border}; border-bottom: 1px solid ${border};">
                  <span style="font-size: 0.7rem; font-weight: bold; color: ${accentColor};">ANÁLISIS POR TRAMOS</span>
                  <select id="elevation-interval-select" onchange="updateElevationAnalysis()" 
                          class="form-select form-select-sm py-0" 
                          style="width: 90px; font-size: 0.7rem; height: 24px; font-weight: bold; 
                                 background-color: ${isDarkMode ? '#333' : '#fff'}; 
                                 color: ${isDarkMode ? '#fff' : '#333'}; 
                                 border-color: ${accentColor};">
                     <option value="50">50m</option>
                     <option value="100" selected>100m</option>
                     <option value="250">250m</option>
                     <option value="500">500m</option>
                     <option value="1000">1km</option>
                  </select>
               </div>
               <div id="elevation-table-container" class="overflow-auto flex-grow-1" style="background: ${bg};">
               </div>
            </div>

            <div class="px-3 py-1 text-center border-top font-mono" 
                 style="background: ${isDarkMode ? '#121212' : '#f8f9fa'}; font-size: 0.65rem; color: ${isDarkMode ? '#888' : '#555'}; border-top: 1px solid ${border} !important;">
              <div class="d-flex align-items-center justify-content-between">
                  <div class="text-start">
                      <button onclick="document.getElementById('elevation-dem-upload').click()" 
                              class="btn btn-sm btn-outline-warning py-0 px-2" 
                              style="font-size: 0.6rem; border-radius: 4px; height: 20px;">
                          <i class="fa-solid fa-upload me-1"></i> MDT LOCAL (.tif)
                      </button>
                      <input type="file" id="elevation-dem-upload" style="display:none" accept=".tif,.tiff" onchange="handleElevationDemUpload(this)">
                  </div>
                  <div class="text-end" style="font-size: 0.6rem; opacity: 0.8;">
                     <i class="fa-solid fa-triangle-exclamation text-warning me-1"></i>
                     MDT: ${hasLocalDEM ? 'LOCAL (ALTA)' : 'REMOTO (MEDIA)'}
                  </div>
              </div>
            </div>
          </div>
      `;
    document.body.insertAdjacentHTML('beforeend', html);
    const panel = document.getElementById('elevation-profile-panel');
    const w = window.innerWidth, h = window.innerHeight;
    panel.style.left = Math.round((w - 900) / 2) + 'px';
    panel.style.top = Math.round((h - 580) / 2) + 'px';
    if (typeof makeDraggable === 'function') makeDraggable(panel);
    return panel;
  }
