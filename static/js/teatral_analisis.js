/**
 * Módulo Teatral - Análisis Dramático Standalone
 */

let filtros = {
  proyecto_id: null,
  publicacion_id: null,
  refresh: false
};

let datosActuales = {};
let chartsInstances = {};

const UI_COLORS = {
  isLight: () => document.documentElement.getAttribute('data-theme') === 'light',
  grid: (opacity = 0.2) => UI_COLORS.isLight() ? `rgba(0,0,0,${opacity})` : `rgba(255,255,255,0.1)`,
  text: () => UI_COLORS.isLight() ? '#294a60' : '#ccc',
  legend: () => UI_COLORS.isLight() ? '#294a60' : '#fff',
  accent: () => UI_COLORS.isLight() ? '#294a60' : '#e6a23c',
  tactics: {
    "Atacar": "#c44545",   // Muted Red
    "Persuadir": "#d98d45", // Soft Ochre
    "Seducir": "#45a37a",   // Sage Green
    "Manipular": "#457ba3", // Steel Blue
    "Informar": "#7b8c94"   // Muted Pewter
  }
};

function showLoader() {
    const view = document.getElementById('view-dramatico');
    if (view && !document.getElementById('internal-spinner')) {
        view.innerHTML = `
            <div id="internal-spinner" class="d-flex flex-column align-items-center justify-content-center" style="min-height: 400px; color: var(--ds-text-main);">
                <div class="spinner-border text-warning mb-3" style="width: 3rem; height: 3rem;" role="status"></div>
                <h5 class="fw-bold animate__animated animate__pulse animate__infinite" style="color: var(--ds-accent-primary);">PROCESANDO DATOS TEATRALES...</h5>
            </div>
        `;
    }
}

function hideLoader() {
    const spinner = document.getElementById('internal-spinner');
    if (spinner) spinner.remove();
}

function getFiltrosActuales() {
    return { ...filtros };
}

function mostrarError(container, msg) {
    if (container) {
        container.innerHTML = `<div class="alert alert-danger p-3 small"><i class="fa-solid fa-triangle-exclamation me-2"></i>${msg}</div>`;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const activeProj = document.body.dataset.proyectoId || '';
    filtros.proyecto_id = activeProj;
    
    // Carga inicial
    const projectKey = `aliases_${filtros.proyecto_id || 'default'}`;
    const manual_aliases = JSON.parse(localStorage.getItem(projectKey) || '{}');

    // Persistencia del Selector de IA
    const aiSelector = document.getElementById('ai-model-selector');
    if (aiSelector) {
        const savedModel = sessionStorage.getItem('hesi_teatral_ai_model');
        if (savedModel) aiSelector.value = savedModel;
        
        aiSelector.addEventListener('change', function() {
            sessionStorage.setItem('hesi_teatral_ai_model', this.value);
        });
    }
    
    fetch('/api/analisis/dramatico', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
        },
        body: JSON.stringify({
            ...filtros,
            manual_aliases: manual_aliases,
            refresh: false
        })
    })
    .then(async res => {
        const contentType = res.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.error || `Error ${res.status}`);
            }
            return data;
        }

        const text = await res.text();
        console.error('[DRAMATICO] Respuesta no-JSON en carga inicial:', text);
        throw new Error('El servidor devolvió una respuesta inesperada');
    })
    .then(data => {
        if (data.exito !== false) {
            datosActuales['dramatico'] = data;
            try {
                loadDramatico(data);
            } catch (renderErr) {
                console.error('[DRAMATICO] Error al renderizar datos:', renderErr);
                const container = document.getElementById('view-dramatico');
                mostrarError(container, 'Los datos se cargaron, pero no pudieron pintarse en pantalla.');
            }
        } else {
            const container = document.getElementById('view-dramatico');
            mostrarError(container, data.error || 'Error al cargar análisis teatral.');
        }
    })
    .catch(err => {
        const container = document.getElementById('view-dramatico');
        mostrarError(container, 'Error de servidor al cargar datos.');
    });
});

window.refrescarAnalisisDramatico = function() {
    const container = document.getElementById('view-dramatico');
    if (!container) return;
    
    // Sincronizar filtros con la UI antes de recalcular para evitar estados stale
    const obraEl = document.getElementById('filtro-obra');
    if (obraEl) {
        const val = obraEl.value;
        filtros.publicacion_id = (val === 'all' || val === '') ? null : parseInt(val);
    }
    
    container.innerHTML = `
        <div class="d-flex flex-column align-items-center justify-content-center" style="min-height: 400px; color: var(--ds-text-main);">
            <div class="spinner-border text-warning mb-3" style="width: 3rem; height: 3rem;" role="status"></div>
            <h5 class="fw-bold animate__animated animate__pulse animate__infinite" style="color: var(--ds-accent-primary);">RECALCULANDO ANÁLISIS DRAMÁTICO...</h5>
            <p class="small opacity-75">Ignorando caché y re-procesando diálogos para actualizar estadísticas.</p>
        </div>
    `;

    const projectKey = `aliases_${filtros.proyecto_id || 'default'}`;
    const manual_aliases = JSON.parse(localStorage.getItem(projectKey) || '{}');

    fetch('/api/analisis/dramatico', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
        },
        body: JSON.stringify({
            ...filtros,
            publicacion_id: filtros.publicacion_id,
            manual_aliases: manual_aliases,
            refresh: true 
        })
    })
    .then(async res => {
        const contentType = res.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.error || `Error ${res.status}`);
            }
            return data;
        }

        const text = await res.text();
        console.error('[DRAMATICO] Respuesta no-JSON en recálculo:', text);
        throw new Error('El servidor devolvió una respuesta inesperada');
    })
    .then(data => {
        if (data.exito !== false) {
            datosActuales['dramatico'] = data;
            try {
                loadDramatico(data);
            } catch (renderErr) {
                console.error('[DRAMATICO] Error al renderizar datos recalculados:', renderErr);
                mostrarError(container, 'Los datos se recalcularon, pero no pudieron pintarse en pantalla.');
            }
        } else {
            mostrarError(container, data.error || 'Error al recalcular datos.');
        }
    })
    .catch(err => {
        mostrarError(container, 'Error de servidor al recalcular.');
    });
};

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
    
    filtros.publicacion_id = (obraSel === 'all' || obraSel === '') ? null : parseInt(obraSel);
    
    window.renderDramaticoFull(data, actoSel, escenaSel, obraSel);
};

window.interpretarSeccionDramatica = function(tipo, targetId) {
    const resDiv = document.getElementById(`ai-res-${targetId}`);
    if (!resDiv) return;

    resDiv.style.display = 'block';
    resDiv.innerHTML = `
        <div class="d-flex align-items-center p-2 rounded" style="background: ${UI_COLORS.isLight() ? 'rgba(41, 74, 96, 0.1)' : 'rgba(255,152,0,0.1)'}; border: 1px dashed ${UI_COLORS.isLight() ? 'rgba(41, 74, 96, 0.3)' : 'rgba(255,152,0,0.3)'};">
            <div class="spinner-border spinner-border-sm text-warning me-2"></div>
            <span class="xsmall text-warning fw-bold" style="font-size: 10px;">SOLICITANDO INTERPRETACIÓN IA...</span>
        </div>
    `;

    const dramaObraEl = document.getElementById('filtro-obra');
    const publicacion_id = (dramaObraEl && dramaObraEl.value && dramaObraEl.value !== 'all' && dramaObraEl.value !== '') ? parseInt(dramaObraEl.value) : null;
    
    // Filtrar los datos para que la IA solo vea la obra seleccionada si hay un filtro activo
    let chartData = JSON.parse(JSON.stringify(datosActuales['dramatico'] || {})); 
    
    if (publicacion_id) {
        // 1. Filtrar sentimiento_temporal (el corazón del análisis)
        chartData.sentimiento_temporal = (chartData.sentimiento_temporal || []).filter(s => String(s.publicacion_id) === String(publicacion_id));
        
        // 2. Identificar personajes que realmente aparecen en esta obra filtrada
        const personajesEnObra = new Set();
        chartData.sentimiento_temporal.forEach(s => {
            (s.locuciones || []).forEach(l => {
                if (l.p) personajesEnObra.add(String(l.p).trim().toLowerCase());
            });
        });
        
        // 3. Filtrar reparto_detalle basado en los personajes encontrados
        if (chartData.reparto_detalle) {
            chartData.reparto_detalle = chartData.reparto_detalle.filter(p => {
                const norm = String(p.nombre).trim().toLowerCase();
                return personajesEnObra.has(norm);
            });
        }

        // 4. Filtrar métricas avanzadas si están presentes
        if (chartData.metricas_avanzadas) {
             const filterKeys = (list) => (list || []).filter(item => {
                 const pName = item.p || item.p1 || item.p2 || "";
                 return pName ? personajesEnObra.has(String(pName).trim().toLowerCase()) : true;
             });
             
             if (chartData.metricas_avanzadas.flujo_tactico) {
                 // El flujo táctico suele estar segmentado por bloques, la IA ya verá solo los bloques de la obra
             }
        }
    }

    fetch('/api/analisis/dramatico/interpretar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
        },
        body: JSON.stringify({
            seccion: tipo,
            chart_data: chartData,
            proyecto_id: filtros.proyecto_id,
            publicacion_id: publicacion_id,
            modelo: document.getElementById('ai-model-selector')?.value || 'gemini:pro'
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.interpretacion) {
            const isLight = UI_COLORS.isLight();
            const formatted = (typeof marked !== 'undefined') ? marked.parse(data.interpretacion) : data.interpretacion.replace(/\n/g, '<br>');
            resDiv.innerHTML = `
                <div class="p-3 rounded border border-warning border-opacity-20 animate__animated animate__fadeIn" 
                     style="background: ${isLight ? 'rgba(41, 74, 96, 0.05)' : 'rgba(0,0,0,0.3)'};">
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
        resDiv.innerHTML = `<div class="alert alert-danger py-2 xsmall">Error de conexión con el servidor.</div>`;
    });
};

function loadDramatico(data) {
  const container = document.getElementById('view-dramatico');
  if (!container) return;
  
  const light = UI_COLORS.isLight();
  const textWhite = light ? '#212121' : '#fff';
  const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
  const accentColor = UI_COLORS.accent();
  const accentAlpha = light ? 'rgba(41, 74, 96, 0.1)' : 'rgba(255, 152, 0, 0.1)';
  const cardBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.15)';

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
    <div class="mb-5 p-4 rounded border border-warning border-opacity-20 animate__animated animate__fadeIn" style="background: ${light ? 'rgba(41, 74, 96, 0.05)' : 'rgba(255,152,0,0.05)'} !important;">
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
            <h3 class="text-accent mb-0" style="color: var(--ds-accent-primary) !important;"><i class="fa-solid fa-masks-theater me-2"></i>Laboratorio de Dramaturgia Computacional</h3>
            <div class="d-flex gap-2">
                <button class="btn btn-outline-warning btn-sm fw-bold px-3 d-flex align-items-center" onclick="refrescarAnalisisDramatico()" style="height: 36px; border-opacity: 0.3;">
                    <i class="fa-solid fa-arrows-rotate me-2"></i>RECALCULAR
                </button>
            </div>
        </div>
        
        ${filtroInfoHtml}
        ${iaInsightsHtml}

        <div class="row g-4 mb-5">
            <div class="col-lg-8">
                <div class="p-4 h-100 rounded border border-warning border-opacity-20" style="backdrop-filter: blur(10px); background: linear-gradient(to right, ${accentAlpha}, transparent) !important;">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div class="small fw-bold" style="color: ${accentColor};"><i class="fa-solid fa-circle-info me-2"></i>Objetivo del Análisis</div>
                        <div>
                            <button class="btn btn-sm fw-bold px-3" onclick="openAliasManager()" title="Unificar personajes" style="background: ${accentColor}; color: ${light ? '#fff' : '#000'};">
                               <i class="fa-solid fa-users-gear me-2"></i>Gestor Identidades
                            </button>
                        </div>
                    </div>
                    <p class="small mb-0 opacity-75" style="line-height: 1.5; color: ${textMuted} !important;">
                        Sistema de interpretación diacrónica basado en la micro-segmentación de actos y escenas. 
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
                </div>
            </div>
        </div>

        <!-- El resto de contenedores para gráficos -->
        <div id="drama-main-content">
            <!-- Row 1: Graph & Protagonismo -->
            <div class="row g-4 mb-4">
                <div class="col-12 col-xl-7">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10 h-100">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Red de Influencia de Personajes
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('interacciones', 'network')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div id="drama-network" style="height: 450px; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px;"></div>
                        <div id="ai-res-network" class="mt-3" style="display:none"></div>
                        <p class="xsmall text-muted mt-3 mb-0">Los nodos representan personajes; el grosor de las aristas es proporcional al número de escenas compartidas.</p>
                    </div>
                </div>
                
                <div class="col-12 col-xl-5">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10 h-100">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Protagonismo Discursivo
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('protagonismo', 'centrality')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div style="height: 450px; position: relative;"><canvas id="drama-centrality"></canvas></div>
                        <div id="ai-res-centrality" class="mt-3" style="display:none"></div>
                    </div>
                </div>
            </div>

            <!-- Row 2: Tactical Analysis (Streamgraph) -->
            <div class="row g-4 mb-4">
                <div class="col-12">
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

            <!-- Row 3: Tactical Radar Charts -->
            <div class="row g-4 mb-4">
                <div class="col-12">
                    <div class="p-4 rounded bg-dark border border-secondary border-opacity-10">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; color: ${textWhite} !important;">
                                <i class="fa-solid fa-bullseye me-2 text-warning"></i> Perfiles Tácticos del Reparto (Radar)
                            </h5>
                            <div class="d-flex gap-2">
                                <span class="badge bg-opacity-10 border border-opacity-25" style="font-size: 8px; color: ${UI_COLORS.tactics['Atacar']}; border-color: ${UI_COLORS.tactics['Atacar']};">A: ATACAR</span>
                                <span class="badge bg-opacity-10 border border-opacity-25" style="font-size: 8px; color: ${UI_COLORS.tactics['Persuadir']}; border-color: ${UI_COLORS.tactics['Persuadir']};">P: PERSUADIR</span>
                                <span class="badge bg-opacity-10 border border-opacity-25" style="font-size: 8px; color: ${UI_COLORS.tactics['Seducir']}; border-color: ${UI_COLORS.tactics['Seducir']};">S: SEDUCIR</span>
                                <span class="badge bg-opacity-10 border border-opacity-25" style="font-size: 8px; color: ${UI_COLORS.tactics['Manipular']}; border-color: ${UI_COLORS.tactics['Manipular']};">M: MANIPULAR</span>
                                <span class="badge bg-opacity-10 border border-opacity-25" style="font-size: 8px; color: ${UI_COLORS.tactics['Informar']}; border-color: ${UI_COLORS.tactics['Informar']};">I: INFORMAR</span>
                            </div>
                        </div>
                        <div id="radar-containers" class="row g-3">
                            <!-- Los radares se inyectarán aquí -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- Row 4: Detailed Stats Table -->
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

            <!-- Row 5: Matrix -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10 h-100">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Matriz de Co-Presencia Temporal
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('presencia', 'presencia')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div id="drama-presence-matrix" style="height: 350px; width: 100%;"></div>
                        <div id="ai-res-presencia" class="mt-3" style="display:none"></div>
                    </div>
                </div>
            </div>

            <!-- Row 5: Rhythm -->
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
                    </div>
                </div>
            </div>

            <!-- Row 6: Interaction -->
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
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="chart-container shadow-sm p-4 rounded bg-dark border border-secondary border-opacity-10 h-100">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5 class="fw-bold text-uppercase mb-0" style="font-size: 0.75rem; letter-spacing: 1px; color: ${textWhite} !important;">
                                <i class="fa-solid fa-circle text-warning me-2" style="font-size: 0.5rem;"></i> Sincronía Emocional
                            </h5>
                            <button class="btn btn-xs btn-outline-warning opacity-75" style="font-size: 9px; padding: 2px 8px;" onclick="interpretarSeccionDramatica('sincronia', 'sincronia')"><i class="fa-solid fa-wand-sparkles me-1"></i>ANALIZAR CON IA</button>
                        </div>
                        <div id="heatmap-sincronia" style="height: 250px; width: 100%;"></div>
                        <div id="sync-list" class="mt-3"></div>
                        <div id="ai-res-sincronia" class="mt-3" style="display:none"></div>
                    </div>
                </div>
            </div>

            <!-- Row 7: Individual Trajectories -->
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
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Detail Panel (Fixed/Floating) -->
        <div id="drama-block-detail" class="glass-panel p-4 shadow-lg border border-warning" style="display: none; position: fixed; top: 100px; right: 20px; width: 400px; max-height: 80vh; overflow-y: auto; z-index: 1050; background: ${light ? 'rgba(255, 255, 255, 0.98)' : 'rgba(15, 15, 15, 0.95)'} !important; backdrop-filter: blur(15px);">
            <div class="d-flex justify-content-between align-items-center mb-3 border-bottom border-warning border-opacity-20 pb-2">
                <a id="drama-reader-btn" href="#" target="_blank" class="text-warning text-decoration-none fw-bold" style="font-size: 11px; letter-spacing: 0.5px;">
                    <i class="fa-solid fa-book-open me-2"></i>ABRIR EN LECTOR
                </a>
                <div class="d-flex align-items-center gap-3">
                    <h6 class="text-warning fw-bold mb-0 text-uppercase opacity-50" id="drama-block-title" style="font-size: 10px;"></h6>
                    <button class="btn btn-sm btn-link text-muted p-0" onclick="document.getElementById('drama-block-detail').style.display='none'"><i class="fa-solid fa-xmark"></i></button>
                </div>
            </div>
            <div id="drama-block-text" style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: ${textWhite}; line-height: 1.6; white-space: pre-wrap;"></div>
        </div>
    </div>
  `;

  const temp = (data.sentimiento_temporal || []);

  const safeUpdateSelect = (id, optionsHtml, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    
    if (window.choicesInstances && window.choicesInstances[id]) {
      try {
        const instance = window.choicesInstances[id];
        if (instance && instance.destroy && typeof instance.destroy === 'function') {
          instance.destroy();
        }
      } catch (err) {}
      delete window.choicesInstances[id];
    }
    
    el.innerHTML = optionsHtml;
    if (value !== undefined) el.value = value;
    
    const newEl = el.cloneNode(true);
    el.parentNode.replaceChild(newEl, el);
    
    if (typeof Choices !== 'undefined') {
       window.choicesInstances = window.choicesInstances || {};
       const c = new Choices(newEl, {
          searchEnabled: true,
          itemSelectText: '',
          shouldSort: false,
          removeItemButton: false,
          allowHTML: true
       });
       window.choicesInstances[id] = c;
       
       newEl.addEventListener('change', () => {
          if (id === 'filtro-obra') { 
             updateActosEscenas(); 
             window.filterDramaticoCharts(); 
          } else { 
             window.filterDramaticoCharts();
          }
       });
    }
  };

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
                            <div class="d-flex gap-3 align-items-center p-2 rounded animate__animated animate__fadeIn" style="width: 100%;">
                                ${fotoSrc ? `<img src="${fotoSrc}" class="rounded-circle border border-warning" style="width: 55px; height: 55px; object-fit: cover; cursor: pointer;" alt="${data.nombre_autor}" onclick="if(window.openVisorModal) window.openVisorModal('${data.nombre ? data.nombre.replace(/'/g, "\\'") : ''}', '${data.apellido ? data.apellido.replace(/'/g, "\\'") : ''}')">` : `<div class="rounded-circle border border-secondary border-opacity-25 d-flex align-items-center justify-content-center bg-dark bg-opacity-50" style="width: 55px; height: 55px; color: ${accentColor}; font-size: 18px; cursor: pointer;" onclick="if(window.openVisorModal) window.openVisorModal('${data.nombre ? data.nombre.replace(/'/g, "\\'") : ''}', '${data.apellido ? data.apellido.replace(/'/g, "\\'") : ''}')"><i class="fa-solid fa-user-pen"></i></div>`}
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
                    } else {
                        bioContainer.style.display = 'none';
                    }
                })
                .catch(() => { bioContainer.style.display = 'none'; });
            } else {
                bioContainer.style.display = 'none';
            }
        }
    }

    const actos = [...new Set(filtered.map(s => String(s.acto)))];
    actos.sort();
    
    let actosHtml = '<option value="all">Todos</option>';
    actos.forEach(a => actosHtml += `<option value="${a}">Acto ${a}</option>`);
    safeUpdateSelect('filtro-acto', actosHtml, 'all');

    const escenas = [...new Set(filtered.map(s => String(s.escena)))];
    escenas.sort();
    
    let escenasHtml = '<option value="all">Todas</option>';
    escenas.forEach(e => escenasHtml += `<option value="${e}">Escena ${e}</option>`);
    safeUpdateSelect('filtro-escena', escenasHtml, 'all');
  };

  const obras = [...new Map(temp.filter(s => s.publicacion_id && s.titulo_obra).map(s => [s.publicacion_id, s])).values()];
  let obrasHtml = '<option value="">(Todas las publicaciones)</option>';
  obras.forEach(o => obrasHtml += `<option value="${o.publicacion_id}">${o.titulo_obra}</option>`);
  
  const initialObra = (filtros.publicacion_id) ? String(filtros.publicacion_id) : '';
  safeUpdateSelect('filtro-obra', obrasHtml, initialObra);
  updateActosEscenas();
    try {
        window.renderDramaticoFull(data, 'all', 'all', initialObra);
    } catch (err) {
        console.error('[DRAMATICO] Error al pintar la vista:', err);
        mostrarError(container, 'Los datos llegaron correctamente, pero la vista teatral no pudo renderizarse.');
    }
}

window.renderDramaticoFull = function(data, filterActo = 'all', filterEscena = 'all', filterObra = 'all') {
    const light = UI_COLORS.isLight();
    const textWhite = light ? '#212121' : '#fff';
    const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
    const borderColor = light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)';
    const accentColor = UI_COLORS.accent();
    const accentAlpha = light ? 'rgba(41, 74, 96, 0.1)' : 'rgba(255, 152, 0, 0.1)';

    const ignoreKey = `ignored_${filtros.proyecto_id || 'default'}`;
    const ignoredChars = JSON.parse(localStorage.getItem(ignoreKey) || '[]');
    const deleteKey = `deleted_${filtros.proyecto_id || 'default'}`;
    const deletedChars = JSON.parse(localStorage.getItem(deleteKey) || '[]');
    const aliasKey = `aliases_${filtros.proyecto_id || 'default'}`;
    const manual_aliases = JSON.parse(localStorage.getItem(aliasKey) || '{}');
    
    const normalizeName = name => {
      if (!name) return '';
      return String(name).normalize('NFKC').trim().replace(/^[\s"«»'“”]+|[\s"«»'“”]+$/g, '').replace(/[.,;:()]+$/g, '').toLowerCase();
    };
    const aliasMap = {};
    Object.entries(manual_aliases).forEach(([k, v]) => {
      aliasMap[normalizeName(k)] = v;
    });
    
    const isObraFilterActive = filterObra !== 'all' && filterObra !== '' && filterObra !== null && filterObra !== undefined;
    const validCharsForObra = new Set();
    (data.sentimiento_temporal || []).forEach(s => {
        const matchesObra = !isObraFilterActive || String(s.publicacion_id) === String(filterObra);
        if (matchesObra) {
            (s.locuciones || []).forEach(l => {
                const rawName = l.p || '';
                const mapped = aliasMap[normalizeName(rawName)] || rawName;
                validCharsForObra.add(normalizeName(mapped));
            });
        }
    });

    // 1. Filtrar Índices de Bloques (Segmentación)
    let indicesFiltrados = [];
    const tempFiltrado = (data.sentimiento_temporal || []).filter((s, idx) => {
        const matchesObra = !isObraFilterActive || String(s.publicacion_id) === String(filterObra);
        const matchesActo = filterActo === 'all' || String(s.acto) === String(filterActo);
        const matchesEscena = filterEscena === 'all' || String(s.escena) === String(filterEscena);
        
        if (matchesObra && matchesActo && matchesEscena) {
            indicesFiltrados.push(idx);
            return true;
        }
        return false;
    });
    
    const labelsOrdenados = tempFiltrado.map(s => s.label);

    const statSegments = document.getElementById('stat-drama-segments');
    if (statSegments) statSegments.innerText = tempFiltrado.length;

    // 2. RE-AGREGACIÓN DINÁMICA (Protagonismo, Tácticas, Red, Heatmap)
    const segmentStats = {};
    const segmentCooc = new Map();
    
    indicesFiltrados.forEach(idx => {
        const block = data.sentimiento_temporal[idx];
        const presentes = new Set();
        
        (block.locuciones || []).forEach(l => {
          const rawName = l.p || '';
          const mapped = aliasMap[normalizeName(rawName)] || rawName;
          if (ignoredChars.includes(mapped) || deletedChars.includes(mapped)) return;

          const key = normalizeName(mapped);
          if (!segmentStats[key]) {
            segmentStats[key] = { palabras: 0, intervenciones: 0, tacticas: {}, displayName: mapped };
          }

          segmentStats[key].intervenciones++;
          const words = l.t ? l.t.trim().split(/\s+/).length : 0;
          segmentStats[key].palabras += words;

          const tac = l.tac || 'Informar';
          segmentStats[key].tacticas[tac] = (segmentStats[key].tacticas[tac] || 0) + 1;

          presentes.add(key);
        });
        
        const presentesList = Array.from(presentes);
        for (let i = 0; i < presentesList.length; i++) {
            for (let j = i + 1; j < presentesList.length; j++) {
                const par = [presentesList[i], presentesList[j]].sort().join('|');
                segmentCooc.set(par, (segmentCooc.get(par) || 0) + 1);
            }
        }
    });

    const showZeroKey = `drama_show_zero_${filtros.proyecto_id || 'default'}`;
    let showZero = localStorage.getItem(showZeroKey) === '1';

    const arrayReparto = (data.reparto_detalle || [])
      .filter(p => {
        const norm = normalizeName(p.nombre);
        return !ignoredChars.includes(p.nombre) && !deletedChars.includes(p.nombre) && (!isObraFilterActive || validCharsForObra.has(norm)) && (showZero || !!segmentStats[norm]);
      })
      .map(p => {
        const norm = normalizeName(p.nombre);
        const s = segmentStats[norm] || { palabras: 0, intervenciones: 0, tacticas: {}, displayName: null };
        return {
          ...p,
          palabras: s.palabras,
          intervenciones: s.intervenciones,
          palabras_por_intervencion: s.intervenciones > 0 ? (s.palabras / s.intervenciones).toFixed(1) : 0,
          perfil_tactico: s.tacticas,
          canonical_name: s.displayName || null
        };
      })
      .sort((a, b) => b.palabras - a.palabras);

    const existingNorms = new Set(arrayReparto.map(p => normalizeName(p.nombre)));
    Object.keys(segmentStats).forEach(norm => {
      if (!existingNorms.has(norm)) {
        const s = segmentStats[norm];
        const inferredName = s.displayName || (norm ? norm.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') : norm);
        arrayReparto.push({
          nombre: inferredName,
          palabras: s.palabras || 0,
          intervenciones: s.intervenciones || 0,
          palabras_por_intervencion: s.intervenciones > 0 ? (s.palabras / s.intervenciones).toFixed(1) : 0,
          perfil_tactico: s.tacticas || {},
          canonical_name: s.displayName || null,
          inferred: true
        });
      }
    });

    arrayReparto.sort((a, b) => (b.palabras || 0) - (a.palabras || 0));

    let totalPalabras = 0;
    arrayReparto.forEach(p => totalPalabras += (p.palabras || 0));

    const statChars = document.getElementById('stat-drama-chars');
    if (statChars) statChars.innerText = arrayReparto.length;

    const statWords = document.getElementById('stat-drama-words');
    if (statWords) statWords.innerHTML = `${totalPalabras.toLocaleString('es-ES')} <span class="fs-6 opacity-50 fw-normal" style="font-size: 11px;">palabras</span>`;

    const normToOriginal = {};
    (data.nodos || []).forEach(n => {
        normToOriginal[normalizeName(n.id)] = n.id;
    });
    arrayReparto.forEach(p => {
        normToOriginal[normalizeName(p.nombre)] = p.nombre;
    });

    const activeCharNames = new Set(arrayReparto.map(p => p.nombre));
    const activeNorms = new Set(arrayReparto.map(p => normalizeName(p.nombre)));

    const filteredNodes = (data.nodos || [])
        .filter(n => activeNorms.has(normalizeName(n.id)))
        .map(n => {
            const normId = normalizeName(n.id);
            return {
                ...n,
                influencia: segmentStats[normId] ? segmentStats[normId].intervenciones : 0
            };
        });

    const filteredEdges = [];
    segmentCooc.forEach((value, key) => {
        const [p1, p2] = key.split('|');
        if (activeNorms.has(p1) && activeNorms.has(p2)) {
            const origP1 = normToOriginal[p1] || p1;
            const origP2 = normToOriginal[p2] || p2;
            filteredEdges.push({ source: origP1, target: origP2, value: value });
        }
    });

    const tableContainer = document.getElementById('drama-table-body');
    if (tableContainer) {
      const controlsId = 'drama-controls-toggle';
      if (!document.getElementById(controlsId)) {
        const controlsDiv = document.createElement('div');
        controlsDiv.id = controlsId;
        controlsDiv.className = 'mb-2 d-flex align-items-center';
        controlsDiv.innerHTML = `
          <div class="form-check form-switch ms-1">
            <input class="form-check-input" type="checkbox" id="drama-show-zero" ${showZero ? 'checked' : ''}>
            <label class="form-check-label small text-muted ms-2" for="drama-show-zero">Mostrar personajes sin intervenciones</label>
          </div>
        `;
        tableContainer.parentElement.insertBefore(controlsDiv, tableContainer);
        const cb = document.getElementById('drama-show-zero');
        cb.addEventListener('change', (e) => {
          localStorage.setItem(showZeroKey, e.target.checked ? '1' : '0');
          window.renderDramaticoFull(data, filterActo, filterEscena, filterObra);
        });
      }

      tableContainer.innerHTML = arrayReparto.map(p => `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
          <td class="fw-bold py-3" style="color: var(--ds-accent);">
            ${p.nombre}
            ${p.canonical_name && normalizeName(p.nombre) !== normalizeName(p.canonical_name) ? `<div class="small text-muted mt-1" style="font-size:10px;">Canonical: ${p.canonical_name}</div>` : ''}
          </td>
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

    // --- VEGA: Tactical Streamgraph ---
    const tacticalStreamTarget = document.getElementById('drama-tactical-stream');
    const labelToOrden = {};
    labelsOrdenados.forEach((l, i) => { labelToOrden[l] = i; });
    
    const rawTactical = ((data.metricas_avanzadas || {}).flujo_tactico || [])
        .filter(t => labelToOrden[t.Bloque] !== undefined);
        
    const aggregated = {};
    rawTactical.forEach(t => {
        const key = `${t.Bloque}|||${t.Táctica}`;
        if (aggregated[key]) {
            aggregated[key].Valor += (t.Valor || 0);
        } else {
            aggregated[key] = {
                Bloque: t.Bloque,
                Táctica: t.Táctica,
                Valor: (t.Valor || 0),
                Orden: labelToOrden[t.Bloque]
            };
        }
    });
    
    const uniqueTactics = [...new Set(rawTactical.map(t => t.Táctica))];
    const tacticalData = [];
    
    labelsOrdenados.forEach((bloque, idx) => {
        uniqueTactics.forEach(tactica => {
            const key = `${bloque}|||${tactica}`;
            if (aggregated[key]) {
                tacticalData.push(aggregated[key]);
            } else {
                tacticalData.push({
                    Bloque: bloque,
                    Táctica: tactica,
                    Valor: 0,
                    Orden: idx
                });
            }
        });
    });

    if (tacticalStreamTarget && tacticalData.length > 0 && typeof vegaEmbed !== 'undefined') {
        const labelExprString = labelsOrdenados.map((lbl, idx) => `datum.value == ${idx} ? '${lbl}'`).join(' : ') + ' : \'\'';

        const streamSpec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "data": { "values": tacticalData },
            "width": "container", 
            "height": 300,
            "mark": { "type": "area", "interpolate": "monotone", "fillOpacity": 0.85 },
            "encoding": {
                "x": { 
                    "field": "Orden", 
                    "type": "quantitative", 
                    "axis": { 
                        "labelColor": textMuted, 
                        "labelFontSize": 10, 
                        "title": null, 
                        "labelAngle": -45,
                        "grid": true,
                        "gridColor": light ? "rgba(0,0,0,0.4)" : "rgba(255,255,255,0.4)",
                        "gridDash": [2, 2],
                        "values": Object.values(labelToOrden),
                        "labelExpr": labelExprString
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
                    "scale": { 
                        "domain": ["Atacar", "Persuadir", "Seducir", "Manipular", "Informar"],
                        "range": [UI_COLORS.tactics["Atacar"], UI_COLORS.tactics["Persuadir"], UI_COLORS.tactics["Seducir"], UI_COLORS.tactics["Manipular"], UI_COLORS.tactics["Informar"]]
                    }, 
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
        vegaEmbed(tacticalStreamTarget, streamSpec, { actions: false })
            .catch(err => console.error("[VEGA ERROR]", err));
    } else if (tacticalStreamTarget) {
        tacticalStreamTarget.innerHTML = '<div class="text-muted small italic opacity-50 p-5 text-center">No hay datos tácticos suficientes para generar el flujo.</div>';
    }

    // --- CHART.JS: Tactical Radar Charts ---
    const radarContainer = document.getElementById('radar-containers');
    if (radarContainer) {
        radarContainer.innerHTML = '';
        const topChars = arrayReparto.slice(0, 12);
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

            setTimeout(() => {
                const canvas = document.getElementById(charId);
                if (canvas) {
                    const ctxR = canvas.getContext('2d');
                    const tacticas = p.perfil_tactico || {};
                    const values = fixedLabels.map(label => tacticas[label] || 0);
                    
                    if (values.some(v => v > 0)) {
                        new Chart(ctxR, {
                            type: 'radar',
                            data: {
                                labels: fixedLabels,
                                datasets: [{
                                    data: values,
                                    backgroundColor: UI_COLORS.isLight() ? 'rgba(41, 74, 96, 0.2)' : 'rgba(255, 152, 0, 0.2)',
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
                                            color: (context) => {
                                                const label = fixedLabels[context.index];
                                                return UI_COLORS.tactics[label] || textMuted;
                                            },
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

    // --- CHART.JS: Protagonismo Discursivo ---
    const ctxCent = document.getElementById('drama-centrality');
    if (ctxCent) {
        if (chartsInstances['centrality']) chartsInstances['centrality'].destroy();
        
        chartsInstances['centrality'] = new Chart(ctxCent, {
            type: 'bar',
            data: {
                labels: arrayReparto.slice(0, 8).map(p => p.nombre),
                datasets: [{
                    label: 'Palabras Habladas',
                    data: arrayReparto.slice(0, 8).map(p => p.palabras),
                    backgroundColor: accentAlpha, 
                    borderColor: accentColor, 
                    borderWidth: 1.5, 
                    borderRadius: 6
                }]
            },
            options: { 
                indexAxis: 'y', 
                responsive: true, 
                maintainAspectRatio: false, 
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: borderColor, borderDash: [4, 4] }, ticks: { color: textMuted } },
                    y: { ticks: { color: textWhite }, grid: { display: false } }
                }
            }
        });
    }

    // --- VIS.JS: Red de Co-Presencia ---
    const netContainer = document.getElementById('drama-network');
    if (netContainer && typeof vis !== 'undefined') {
        const colorPalette = [
            { bg: accentColor, border: light ? '#1d3545' : '#e65100' }, 
            { bg: '#ffffff', border: '#aaaaaa' }, 
            { bg: '#2196f3', border: '#0d47a1' }, 
            { bg: '#4caf50', border: '#1b5e20' }, 
            { bg: '#9c27b0', border: '#4a148c' }, 
            { bg: '#f44336', border: '#b71c1c' }  
        ];

        const gruposPresencia = [...new Set((data.nodos || []).map(n => n.grupo))].sort();
        const getGroupColor = (groupId) => {
            const idx = gruposPresencia.indexOf(groupId);
            return colorPalette[idx % colorPalette.length];
        };

        const visData = {
            nodes: filteredNodes.map(n => {
                const colors = getGroupColor(n.grupo);
                return {
                    id: n.id,
                    label: n.name || n.id,
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
                from: e.source, 
                to: e.target,
                width: 2 + Math.log1p(e.value) * 1.5,
                color: { 
                    color: light ? 'rgba(41, 74, 96, 0.45)' : 'rgba(255, 152, 0, 0.5)', 
                    highlight: accentColor,
                    hover: accentColor 
                },
                smooth: { type: 'continuous' },
                shadow: { enabled: true, color: 'rgba(0,0,0,0.4)', size: 3 }
            }))
        };
        new vis.Network(netContainer, visData, { 
            nodes: { shape: 'dot' },
            physics: { forceAtlas2Based: { gravitationalConstant: -80, springLength: 120 }, solver: 'forceAtlas2Based', stabilization: { iterations: 100 } } 
        });
    }

    // --- VEGA: Matriz de Co-Presencia Temporal ---
    const presenceTarget = document.getElementById('drama-presence-matrix');
    if (arrayReparto && presenceTarget && typeof vegaEmbed !== 'undefined') {
        const presenceData = [];
        const matrixChars = arrayReparto.slice(0, 20);
        const matrixCharNames = matrixChars.map(p => p.nombre);

        matrixChars.forEach(p => {
            if (!p.presencia_matriz) return;
            const mapped = p.nombre;

            (p.presencia_matriz || []).forEach((val, idx) => {
                if (val > 0 && indicesFiltrados.includes(idx)) {
                    const bloq = data.sentimiento_temporal[idx];
                    presenceData.push({ "Personaje": mapped, "Bloque": (bloq && bloq.label) ? bloq.label : `S${idx+1}`, "Presente": val });
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
                    "x": { "field": "Bloque", "type": "nominal", "sort": labelsOrdenados, "axis": { "labelColor": textMuted, "labelFontSize": 9, "title": null, "grid": true, "gridColor": borderColor } },
                    "y": { "field": "Personaje", "type": "nominal", "sort": matrixCharNames, "axis": { "labelColor": textWhite, "labelFontSize": 10, "title": null, "grid": true, "gridColor": borderColor } },
                    "color": { "value": accentColor }
                },
                "background": "transparent",
                "config": { "view": { "stroke": "transparent" }, "axis": { "domain": false, "ticks": false } }
            };
            vegaEmbed(presenceTarget, spec, { actions: false });
        }
    }

    // --- CHART.JS: Ritmo Dramático ---
    const ctxR = document.getElementById('drama-rhythm-sync');
    if (ctxR && data.metricas_avanzadas) {
        if (chartsInstances['rhythm']) chartsInstances['rhythm'].destroy();
        
        const ritmoData = data.metricas_avanzadas.ritmo_bloques || [];
        const filteredRitmo = indicesFiltrados.map(idx => ritmoData[idx]);

        chartsInstances['rhythm'] = new Chart(ctxR, {
            type: 'line',
            data: {
                labels: labelsOrdenados,
                datasets: [
                    { label: 'Ritmo', data: filteredRitmo.map(r => r ? r.intervenciones : 0), borderColor: accentColor, backgroundColor: accentColor + '22', fill: true, tension: 0.4, yAxisID: 'y' },
                    { label: 'Acotaciones', data: filteredRitmo.map(r => r ? r.sent_acotaciones : 0), borderColor: UI_COLORS.isLight() ? '#1976d2' : '#2196f3', borderDash: [5, 5], fill: false, tension: 0.4, yAxisID: 'y1' }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    y: { type: 'linear', position: 'left', grid: { color: borderColor, borderDash: [4, 4] }, ticks: { color: textMuted } },
                    y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { color: UI_COLORS.isLight() ? '#1976d2' : '#2196f3' } },
                    x: { grid: { color: borderColor, borderDash: [4, 4] }, ticks: { color: textMuted, font: { size: 9 } } }
                },
                plugins: { legend: { labels: { color: textWhite } } }
            }
        });
    }

    // --- CHART.JS: Convergencia de la Tensión Dramática ---
    const ctxT = document.getElementById('drama-tension-convergence');
    if (ctxT) {
        if (chartsInstances['tension']) chartsInstances['tension'].destroy();
        
        const dataTensionValues = tempFiltrado.map(s => s.sentimiento);

        chartsInstances['tension'] = new Chart(ctxT, {
            type: 'line',
            data: {
                labels: labelsOrdenados,
                datasets: [{
                    label: 'Sentimiento General',
                    data: dataTensionValues,
                    borderColor: accentColor, backgroundColor: accentColor + '22', fill: true, tension: 0.4,
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
                        const block = tempFiltrado[idx];
                        if (block && (block.texto || block.locuciones)) {
                            const detail = document.getElementById('drama-block-detail');
                            const text = document.getElementById('drama-block-text');
                            const title = document.getElementById('drama-block-title');
                            if (detail && text) {
                                detail.style.display = 'block';
                                if (title) title.innerText = block.label || `Bloque ${idx + 1}`;
                                
                                const readerBtn = document.getElementById('drama-reader-btn');
                                if (readerBtn) {
                                    if (block.doc_id) {
                                        readerBtn.href = `/noticias/lector?id=${block.doc_id}`;
                                        readerBtn.style.display = 'inline-block';
                                    } else if (block.publicacion_id) {
                                        readerBtn.href = `/noticias/lector?id=${block.publicacion_id}`;
                                        readerBtn.style.display = 'inline-block';
                                    } else {
                                        readerBtn.style.display = 'none';
                                    }
                                }
                                
                                let html = (block.locuciones || []).map(l => `<span class="text-warning"><b>${l.p}:</b></span> ${l.t}`).join('<br><br>');
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

    // --- VEGA & HTML: Sincronía Emocional ---
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
                "background": "transparent",
                "config": { "view": { "stroke": "transparent" } }
            };
            vegaEmbed(syncHeatmap, syncSpec, { actions: false });
        }
        syncContainer.innerHTML = rawSyncs.slice(0, 10).map(s => `
            <div class="d-flex justify-content-between align-items-center mb-1 p-2 rounded border border-warning border-opacity-10" style="background: ${UI_COLORS.isLight() ? 'rgba(41, 74, 96, 0.05)' : 'rgba(255,152,0,0.05)'} !important; font-size: 11px;">
                <div class="text-truncate" style="max-width: 180px;"><span class="fw-bold">${s.p1}</span> <i class="fa-solid fa-arrows-left-right mx-1 text-warning opacity-50"></i> <span class="fw-bold">${s.p2}</span></div>
                <div class="badge bg-warning text-dark font-monospace">${Math.round(s.score * 100)}%</div>
            </div>
        `).join('');
    }

    // --- CHART.JS: Trayectoria Emocional por Personaje ---
    const ctxS = document.getElementById('drama-individual-trajectories');
    if (ctxS) {
        if (chartsInstances['trajectories']) chartsInstances['trajectories'].destroy();
        
        const palette = ['#e6a23c', '#5c94cc', '#67a67d', '#a37bb8', '#cc5c5c', '#5cb8cc'];
        const topChars = (typeof arrayReparto !== 'undefined' ? arrayReparto : []).slice(0, 10).map(r => r.nombre);
        
        const datasets = (data.reparto_detalle || [])
            .filter(p => {
                const mapped = aliasMap[normalizeName(p.nombre)] || p.nombre;
                return topChars.includes(mapped);
            })
            .slice(0, 10)
            .map((p, i) => {
                const mappedName = aliasMap[normalizeName(p.nombre)] || p.nombre;
                const fullArc = p.sentimiento_arc || [];
                const filteredArc = indicesFiltrados.map(idx => fullArc[idx] !== undefined ? fullArc[idx] : null);
                return {
                    label: mappedName, data: filteredArc, borderColor: palette[i % palette.length], 
                    backgroundColor: palette[i % palette.length] + '22',
                    tension: 0.3, fill: false, spanGaps: true, borderWidth: 2,
                    pointRadius: indicesFiltrados.length > 50 ? 0 : 3
                };
            });

        chartsInstances['trajectories'] = new Chart(ctxS, {
            type: 'line',
            data: {
                labels: labelsOrdenados,
                datasets: datasets
            },
            options: { 
                responsive: true, maintainAspectRatio: false, 
                plugins: { legend: { labels: { color: textWhite, font: { size: 10 } } } },
                scales: {
                    y: { min: -1, max: 1, grid: { color: borderColor }, ticks: { color: textMuted } },
                    x: { grid: { color: borderColor }, ticks: { color: textMuted, font: { size: 9 } } }
                },
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const idx = elements[0].index;
                        const block = tempFiltrado[idx];
                        if (block && (block.texto || block.locuciones)) {
                            const detail = document.getElementById('drama-block-detail');
                            const text = document.getElementById('drama-block-text');
                            const title = document.getElementById('drama-block-title');
                            if (detail && text) {
                                detail.style.display = 'block';
                                if (title) title.innerText = block.label || `Bloque ${idx + 1}`;
                                
                                const readerBtn = document.getElementById('drama-reader-btn');
                                if (readerBtn) {
                                    if (block.doc_id) {
                                        readerBtn.href = `/noticias/lector?id=${block.doc_id}`;
                                        readerBtn.style.display = 'inline-block';
                                    } else if (block.publicacion_id) {
                                        readerBtn.href = `/noticias/lector?id=${block.publicacion_id}`;
                                        readerBtn.style.display = 'inline-block';
                                    } else {
                                        readerBtn.style.display = 'none';
                                    }
                                }
                                
                                const datasetIdx = elements[0].datasetIndex;
                                const charName = e.chart.data.datasets[datasetIdx].label;
                                const upperChar = charName.toUpperCase();
                                
                                const relevant = (block.locuciones || []).filter(l => {
                                    const lp = (l.p || '').toUpperCase();
                                    return lp === upperChar || upperChar.includes(lp) || lp.includes(upperChar);
                                });
                                
                                let html = "";
                                if (relevant.length > 0) {
                                    html = relevant.map(l => `<span class="text-warning"><b>${l.p}:</b></span> ${l.t}`).join('<br><br>');
                                } else if (block.texto) {
                                    const lines = block.texto.split('\n');
                                    const mentions = lines.filter(line => line.toUpperCase().includes(upperChar));
                                    if (mentions.length > 0) {
                                        html = `<i class="text-muted small d-block mb-3 border-bottom border-warning border-opacity-10 pb-2">Menciones detectadas:</i>`;
                                        html += mentions.map(m => m.replace(new RegExp(`(${charName})`, 'gi'), '<span class="text-warning fw-bold">$1</span>')).join('<br><br>');
                                    } else {
                                        html = `<i class="text-muted small">No se detectaron diálogos de <b>${charName}</b> en este bloque.</i>`;
                                    }
                                } else {
                                    html = `<i class="text-muted small">No hay texto disponible para este bloque.</i>`;
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
};

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
  
  const projectKey = `aliases_${filtros.proyecto_id || 'default'}`;
  const currentAliases = JSON.parse(localStorage.getItem(projectKey) || '{}');
  
  const ignoreKey = `ignored_${filtros.proyecto_id || 'default'}`;
  const ignoredChars = JSON.parse(localStorage.getItem(ignoreKey) || '[]');
  const deleteKey = `deleted_${filtros.proyecto_id || 'default'}`;
  const deletedChars = JSON.parse(localStorage.getItem(deleteKey) || '[]');
  
  const obraEl = document.getElementById('filtro-obra');
  const filterObra = obraEl ? obraEl.value : 'all';
  const isObraFilterActive = filterObra !== 'all' && filterObra !== '' && filterObra !== null && filterObra !== undefined;
  
  const validCharsForObra = new Set();
  const normalizeName = name => {
    if (!name) return '';
    return String(name).normalize('NFKC').trim().replace(/^[\s"«»'“”]+|[\s"«»'“”]+$/g, '').replace(/[.,;:()]+$/g, '').toLowerCase();
  };
  
  (data.sentimiento_temporal || []).forEach(s => {
      const matchesObra = !isObraFilterActive || String(s.publicacion_id) === String(filterObra);
      if (matchesObra) {
          (s.locuciones || []).forEach(l => {
              const rawName = l.p || '';
              validCharsForObra.add(normalizeName(rawName));
          });
      }
  });

  let personajes = (data.nodos || []).map(n => n.id).filter(p => !deletedChars.includes(p));
  if (isObraFilterActive) {
      personajes = personajes.filter(p => validCharsForObra.has(normalizeName(p)));
  }
  personajes.sort();
  
  tableBody.innerHTML = personajes.map(p => {
    const canonical = currentAliases[p] || '';
    const isIgnored = ignoredChars.includes(p);
    return `
      <tr data-row-char="${p}" class="${isIgnored ? 'opacity-50' : ''}">
        <td class="text-info small fw-bold">${p} ${isIgnored ? '<span class="badge bg-danger ms-2" style="font-size: 8px;">OCULTO</span>' : ''}</td>
        <td class="text-center text-muted"><i class="fa-solid fa-arrow-right-long small"></i></td>
        <td>
          <input type="text" class="form-control form-control-sm bg-dark text-light border-secondary border-opacity-50 alias-input" 
                 data-original="${p}" value="${canonical}" placeholder="Nombre unificado (opcional)">
        </td>
        <td class="text-center">
            <div class="form-check form-switch d-inline-block">
                <input class="form-check-input ignore-checkbox" type="checkbox" role="switch" data-personaje="${p}" ${isIgnored ? 'checked' : ''}>
            </div>
        </td>
        <td class="text-center">
            <button type="button" class="btn btn-sm btn-outline-danger border-0 py-0" onclick="window.deleteCharacterPermanently('${p.replace(/'/g, "\\'")}')">
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
  
  const newIgnored = existingIgnored.filter(p => !currentModalCharacters.has(p));
  document.querySelectorAll('.ignore-checkbox').forEach(cb => {
    if (cb.checked) newIgnored.push(cb.dataset.personaje);
  });
  
  localStorage.setItem(projectKey, JSON.stringify(newAliases));
  localStorage.setItem(ignoreKey, JSON.stringify(newIgnored));
  
  const modalInstance = bootstrap.Modal.getInstance(document.getElementById('modalAlias'));
  if (modalInstance) modalInstance.hide();
  
  window.refrescarAnalisisDramatico();
};

window.deleteCharacterPermanently = function(personaje) {
    if (!confirm(`¿Estás seguro de que deseas eliminar a "${personaje}"?`)) return;
    const deleteKey = `deleted_${filtros.proyecto_id || 'default'}`;
    const deletedChars = JSON.parse(localStorage.getItem(deleteKey) || '[]');
    if (!deletedChars.includes(personaje)) {
        deletedChars.push(personaje);
        localStorage.setItem(deleteKey, JSON.stringify(deletedChars));
    }
    const row = document.querySelector(`tr[data-row-char="${CSS.escape(personaje)}"]`);
    if (row) row.remove();
};

window.resetAliases = function() {
  if (confirm('¿Estás seguro?')) {
    const projectKey = `aliases_${filtros.proyecto_id || 'default'}`;
    const ignoreKey = `ignored_${filtros.proyecto_id || 'default'}`;
    const deleteKey = `deleted_${filtros.proyecto_id || 'default'}`;
    localStorage.removeItem(projectKey);
    localStorage.removeItem(ignoreKey);
    localStorage.removeItem(deleteKey);
    document.querySelectorAll('.alias-input').forEach(input => input.value = '');
    document.querySelectorAll('.ignore-checkbox').forEach(cb => cb.checked = false);
  }
};

window.addEventListener('themeChanged', function() {
    const data = typeof datosActuales !== 'undefined' ? datosActuales['dramatico'] : null;
    if (!data) return;
    
    // Guardar selecciones actuales
    const obraEl = document.getElementById('filtro-obra');
    const actoEl = document.getElementById('filtro-acto');
    const escenaEl = document.getElementById('filtro-escena');
    
    const obraSel = obraEl ? obraEl.value : 'all';
    const actoSel = actoEl ? actoEl.value : 'all';
    const escenaSel = escenaEl ? escenaEl.value : 'all';
    
    // Re-generar el DOM con los colores correctos
    if (typeof loadDramatico === 'function') {
        loadDramatico(data);
    }
    
    // Restaurar selecciones
    const newObraEl = document.getElementById('filtro-obra');
    const newActoEl = document.getElementById('filtro-acto');
    const newEscenaEl = document.getElementById('filtro-escena');
    
    if (newObraEl) newObraEl.value = obraSel;
    if (newActoEl) newActoEl.value = actoSel;
    if (newEscenaEl) newEscenaEl.value = escenaSel;
    
    // Re-renderizar gráficos
    if (typeof window.filterDramaticoCharts === 'function') {
        window.filterDramaticoCharts();
    }
});

window.exportarDossier = function() {
    const dataRaw = datosActuales['dramatico'];
    if (!dataRaw) {
        Swal.fire('Error', 'No hay datos cargados para exportar.', 'error');
        return;
    }

    // 1. Obtener filtros actuales de la UI
    const obraEl = document.getElementById('filtro-obra');
    const actoEl = document.getElementById('filtro-acto');
    const escenaEl = document.getElementById('filtro-escena');
    
    const obraSel = obraEl ? obraEl.value : 'all';
    const actoSel = actoEl ? actoEl.value : 'all';
    const escenaSel = escenaEl ? escenaEl.value : 'all';
    
    const isObraFilterActive = obraSel !== 'all' && obraSel !== '';
    
    // 2. Obtener alias y personajes borrados/ignorados
    const ignoreKey = `ignored_${filtros.proyecto_id || 'default'}`;
    const ignoredChars = JSON.parse(localStorage.getItem(ignoreKey) || '[]');
    const deleteKey = `deleted_${filtros.proyecto_id || 'default'}`;
    const deletedChars = JSON.parse(localStorage.getItem(deleteKey) || '[]');
    const aliasKey = `aliases_${filtros.proyecto_id || 'default'}`;
    const manual_aliases = JSON.parse(localStorage.getItem(aliasKey) || '{}');
    
    const normalizeName = name => {
      if (!name) return '';
      return String(name).normalize('NFKC').trim().replace(/^[\s"«»'“”]+|[\s"«»'“”]+$/g, '').replace(/[.,;:()]+$/g, '').toLowerCase();
    };
    
    const aliasMap = {};
    Object.entries(manual_aliases).forEach(([k, v]) => {
      aliasMap[normalizeName(k)] = v;
    });

    // 3. Filtrar sentimiento_temporal
    const tempFiltrado = (dataRaw.sentimiento_temporal || []).filter(s => {
        const matchesObra = !isObraFilterActive || String(s.publicacion_id) === String(obraSel);
        const matchesActo = actoSel === 'all' || String(s.acto) === String(actoSel);
        const matchesEscena = escenaSel === 'all' || String(s.escena) === String(escenaSel);
        return matchesObra && matchesActo && matchesEscena;
    }).map(s => ({
        ...s,
        sentiment: s.sentimiento || 0,
        magnitude: s.subjetividad || 0
    }));

    if (tempFiltrado.length === 0) {
        Swal.fire('Atención', 'El filtro actual no contiene datos para exportar.', 'warning');
        return;
    }

    // 4. Recalcular métricas de personajes para ESTOS segmentos
    const segmentStats = {};
    tempFiltrado.forEach(block => {
        (block.locuciones || []).forEach(l => {
          const rawName = l.p || '';
          const mapped = aliasMap[normalizeName(rawName)] || rawName;
          
          // Ignorar personajes ocultos o borrados
          if (ignoredChars.includes(mapped) || deletedChars.includes(mapped)) return;

          const key = normalizeName(mapped);
          if (!segmentStats[key]) {
            segmentStats[key] = { palabras: 0, intervenciones: 0, tacticas: {}, displayName: mapped };
          }
          segmentStats[key].intervenciones++;
          const words = l.t ? l.t.trim().split(/\s+/).length : 0;
          segmentStats[key].palabras += words;
          const tac = l.tac || 'Informar';
          segmentStats[key].tacticas[tac] = (segmentStats[key].tacticas[tac] || 0) + 1;
        });
    });

    const arrayReparto = Object.keys(segmentStats).map(norm => {
        const s = segmentStats[norm];
        return {
          nombre: s.displayName,
          palabras: s.palabras,
          intervenciones: s.intervenciones,
          perfil_tactico: s.tacticas
        };
    }).sort((a, b) => b.palabras - a.palabras);

    // 5. Construir objeto final para enviar
    const obraText = obraEl && obraEl.selectedIndex >= 0 ? obraEl.options[obraEl.selectedIndex].text : 'Todas';
    const dataToExport = {
        ...dataRaw,
        sentimiento_temporal: tempFiltrado,
        reparto_detalle: arrayReparto,
        filtro_nombre: `OBRA: ${obraText} | ACTO: ${actoSel} | ESCENA: ${escenaSel}`
    };

    Swal.fire({
        title: 'Generando Dossier',
        text: 'Por favor espere mientras preparamos su informe detallado...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    fetch('/teatral/exportar_dossier', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
        },
        body: JSON.stringify({
            chart_data: dataToExport,
            filtros: filtros
        })
    })
    .then(async res => {
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            const error = new Error(errData.error || 'Error al generar el PDF');
            error.debug = errData.debug; // Adjuntar traceback si existe
            throw error;
        }
        return res.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Dossier_Teatral_${new Date().getTime()}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        Swal.close();
    })
    .catch(err => {
        console.error(err);
        let errorMsg = err.message || 'Hubo un fallo al generar el dossier.';
        
        if (err.debug) {
            Swal.fire({
                title: 'Error de Servidor (500)',
                html: `<div class="text-start">
                        <p class="text-danger fw-bold">${errorMsg}</p>
                        <hr>
                        <p class="small text-muted mb-1">Detalles técnicos del servidor:</p>
                        <pre class="bg-light p-2 border rounded" style="max-height: 250px; overflow-y: auto; text-align: left; font-size: 9px; font-family: monospace; white-space: pre-wrap;">${err.debug}</pre>
                       </div>`,
                icon: 'error',
                width: '650px'
            });
        } else {
            Swal.fire('Error', errorMsg, 'error');
        }
    });
};
