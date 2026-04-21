/**
 * Módulo de Análisis Novedosos en HD
 * Proyecto Sirio
 */

document.addEventListener('DOMContentLoaded', function () {
    const dhViewsContainer = document.getElementById('dh-views-container');
    const loadingState = document.getElementById('loading-state');
    const navButtons = document.querySelectorAll('.btn-sirio[data-analisis]');

    // Configuración global de Chart.js
    const isLight = () => document.body.getAttribute('data-theme') === 'light';

    Chart.defaults.color = isLight() ? '#294a60' : 'rgba(255, 255, 255, 0.7)';
    Chart.defaults.borderColor = isLight() ? 'rgba(0,0,0,0.1)' : 'rgba(255, 255, 255, 0.1)';
    Chart.defaults.font.family = "'JetBrains Mono', monospace";

    // Mapeo de funciones de carga
    const loadFunctions = {
        'keyness': loadKeyness,
        'reuse': loadTextReuse,
        'geosemantics': loadGeosemantics,
        'shift': loadSemanticShift,
        'communities': loadCommunities,
        'ngramas': loadNgrams,
        'dramatico': loadDramatico
    };

    // Event Listeners para navegación
    navButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const type = this.getAttribute('data-analisis');
            if (loadFunctions[type]) {
                setActiveButton(this);
                loadFunctions[type]();
            }
        });
    });

    function setActiveButton(activeBtn) {
        navButtons.forEach(btn => btn.classList.remove('active'));
        activeBtn.classList.add('active');
    }

    function showLoading() { 
        const loader = document.getElementById('loading-state');
        if (loader) loader.style.display = 'flex'; 
    }
    function hideLoading() { 
        const loader = document.getElementById('loading-state');
        if (loader) loader.style.display = 'none'; 
    }

    async function apiPost(endpoint, data = {}) {
        showLoading();
        try {
            const response = await fetch(`/api/analisis/${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            return result;
        } catch (error) {
            console.error(`Error en ${endpoint}:`, error);
            return { exito: false, error: 'Error de conexión' };
        } finally {
            hideLoading();
        }
    }

    function renderView(html) {
        dhViewsContainer.innerHTML = html;
        window.scrollTo(0, 0);
    }

    function renderEmptyState(title, message, suggestions = []) {
        const light = isLight();
        const bgColor = light ? 'rgba(0,0,0,0.02)' : 'rgba(255,152,0,0.02)';
        const borderColor = light ? '#d0d0d0' : 'rgba(255,152,0,0.1)';
        const textColor = light ? '#666' : 'rgba(255,255,255,0.7)';

        renderView(`
            <div class="card-panel-hd p-5 text-center" style="min-height: 500px; display: flex; flex-direction: column; justify-content: center; align-items: center; border-style: dashed; border-width: 2px; border-color: ${borderColor}; background: ${bgColor};">
                <div class="mb-4" style="font-size: 4rem; opacity: 0.2; color: var(--ds-accent-primary);">
                    <i class="fa-solid fa-magnifying-glass-chart"></i>
                </div>
                <h3 class="mb-3" style="font-weight: 700; color: ${light ? '#212121' : '#fff'} !important;">${title}</h3>
                <p class="mb-4" style="max-width: 500px; margin: 0 auto; color: ${textColor} !important;">${message}</p>
                
                ${suggestions.length ? `
                    <div class="p-4 rounded border border-secondary border-opacity-10 text-start" style="max-width: 480px; background: ${light ? 'rgba(0,0,0,0.05)' : 'rgba(0,0,0,0.25)'} !important;">
                        <div class="hd-metric-label mb-3" style="font-size: 10px; color: var(--ds-accent-primary);"><i class="fa-solid fa-lightbulb me-2"></i>Sugerencias de acción</div>
                        <ul class="mb-0 list-unstyled d-flex flex-column gap-3">
                            ${suggestions.map(s => `
                                <li class="d-flex align-items-start gap-2 small" style="color: ${textColor} !important; line-height: 1.4;">
                                    <i class="fa-solid fa-chevron-right mt-1" style="font-size: 8px; color: var(--ds-accent-primary);"></i> 
                                    <span>${s}</span>
                                </li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `);
    }


    // --- 1. Keyness ---
    async function loadKeyness() {
        const data = await apiPost('keyness', { eje: 'publicacion' });
        if (!data.exito) {
            renderView(`<div class="alert alert-danger">${data.error}</div>`);
            return;
        }

        if (!data.resultados || Object.keys(data.resultados).length === 0) {
            renderEmptyState(
                "No se encontraron palabras clave",
                "El análisis de Keyness no ha detectado palabras con una frecuencia distintiva suficiente en los grupos actuales.",
                [
                    "Ajusta los filtros (fecha, publicación, país) para cambiar el conjunto de comparación.",
                    "Asegura que el corpus seleccionado tenga suficiente diversidad de fuentes o temas.",
                    "Prueba a aumentar el 'Límite de Documentos' en el panel de filtros."
                ]
            );
            return;
        }

        const light = isLight();
        const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
        const textWhite = light ? '#212121' : '#fff';
        const cardBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.25)';
        const borderColor = light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';

        let html = `
            <div class="card-panel-hd p-4">
                <div class="section-title-hd"><i class="fa-solid fa-key"></i>Análisis de Keyness (Contrastivo)</div>
                
                <div class="p-3 mb-4 rounded border border-secondary border-opacity-10" style="background: ${cardBg} !important;">
                    <div class="d-flex justify-content-between">
                        <div style="flex: 1;">
                            <div class="hd-metric-label mb-2"><i class="fa-solid fa-info-circle text-accent me-2"></i>¿Qué es esto?</div>
                            <p class="small mb-0" style="line-height: 1.5; color: ${textMuted} !important;">Este análisis identifica qué palabras son estadísticamente más frecuentes en un conjunto de textos respecto a otros. Útil para encontrar discursos distintivos, sesgos o temas predominantes entre diferentes periódicos o regiones geográficas.</p>
                        </div>
                        <div class="ms-4 border-start border-secondary border-opacity-10 ps-4" style="min-width: 200px;">
                            <div class="mb-2">
                                <span class="hd-metric-label" style="font-size: 9px; opacity: 0.6;">TECNOLOGÍA</span>
                                <div class="small" style="font-size: 11px; color: ${textWhite} !important;">Log-Likelihood (Dunning), NLTK</div>
                            </div>
                            <div>
                                <span class="hd-metric-label" style="font-size: 9px; opacity: 0.6;">POTENCIA</span>
                                <div class="small" style="font-size: 11px; color: ${textWhite} !important;">Contraste de corpus a escala masiva</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row g-4">
        `;

        for (const [grupo, palabras] of Object.entries(data.resultados)) {
            html += `
                <div class="col-md-4">
                    <div class="p-4 bg-dark-sirio rounded h-100" style="background: ${cardBg} !important;">
                        <h5 class="border-bottom border-secondary border-opacity-25 pb-2 mb-3" style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: ${textWhite} !important;">${grupo}</h5>
                        <div class="d-flex flex-wrap gap-2">
                            ${palabras.map(p => `
                                <span class="badge-hd" 
                                      style="background: rgba(255, 152, 0, ${Math.min(0.3, p.score / 150)}); 
                                             border-color: rgba(255, 152, 0, ${Math.min(0.5, p.score / 100)});"
                                      title="Log-Likelihood: ${p.score.toFixed(2)}">
                                    ${p.palabra}
                                </span>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
        }

        html += `</div></div>`;
        renderView(html);
    }

    // --- 2. Text Reuse ---
    async function loadTextReuse() {
        const data = await apiPost('reuso-textual');
        if (!data.exito) {
            renderView(`<div class="alert alert-danger">${data.error}</div>`);
            return;
        }

        if (!data.reusos || data.reusos.length === 0) {
            renderEmptyState(
                "No se detectaron reusos textuales",
                "No se han encontrado fragmentos de texto idénticos o cuasi-idénticos entre los documentos analizados.",
                [
                    "Prueba con un rango de fechas más amplio para capturar la propagación de noticias.",
                    "Selecciona varias fuentes (periódicos) diferentes para ver si hay réplicas entre ellos.",
                    "Aumenta el 'Límite de Documentos' a 500 o 'Corporativo' para un escaneo más profundo."
                ]
            );
            return;
        }

        const light = isLight();
        const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
        const textWhite = light ? '#212121' : '#fff';
        const cardBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.25)';

        let html = `
            <div class="card-panel-hd p-4">
                <div class="section-title-hd"><i class="fa-solid fa-copy"></i>Detección de Reuso Textual</div>
                
                <div class="p-3 mb-4 rounded border border-secondary border-opacity-10" style="background: ${cardBg} !important;">
                    <div class="d-flex justify-content-between">
                        <div style="flex: 1;">
                            <div class="hd-metric-label mb-2"><i class="fa-solid fa-info-circle text-accent me-2"></i>¿Cuál es su utilidad?</div>
                            <p class="small mb-0" style="line-height: 1.5; color: ${textMuted} !important;">Detecta fragmentos de texto idénticos o muy similares que aparecen en distintos documentos. Ayuda a rastrear la propagación de noticias, la circulación de "noticias virales" del pasado, réplicas editoriales y la influencia mutua entre fuentes informativas.</p>
                        </div>
                        <div class="ms-4 border-start border-secondary border-opacity-10 ps-4" style="min-width: 200px;">
                            <div class="mb-2">
                                <span class="hd-metric-label" style="font-size: 9px; opacity: 0.6;">TECNOLOGÍA</span>
                                <div class="small" style="font-size: 11px; color: ${textWhite} !important;">Similitud N-Grams, Rabin-Karp Shingling</div>
                            </div>
                            <div>
                                <span class="hd-metric-label" style="font-size: 9px; opacity: 0.6;">POTENCIA</span>
                                <div class="small" style="font-size: 11px; color: ${textWhite} !important;">Detección de "noticias virales" históricas</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="table-responsive">
                    <table class="table-sirio-hd">
                        <thead>
                            <tr>
                                <th>Noticia Principal</th>
                                <th>Coincide con</th>
                                <th style="width: 30%;">Fragmentos</th>
                                <th class="text-end">Similitud</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.reusos.map(r => `
                                <tr>
                                    <td>
                                        <span class="hd-metric-label" style="margin-bottom: 2px;">${r.doc1.publicacion}</span>
                                        <span class="fw-bold" style="color: ${textWhite} !important;">${r.doc1.titulo}</span>
                                    </td>
                                    <td>
                                        <span class="hd-metric-label" style="margin-bottom: 2px;">${r.doc2.publicacion}</span>
                                        <span class="fw-bold" style="color: ${textWhite} !important;">${r.doc2.titulo}</span>
                                    </td>
                                    <td><small class="fst-italic" style="font-family: var(--ds-font-mono); font-size: 11px; color: ${textMuted} !important;">"${r.ejemplos.join('", "')}"</small></td>
                                    <td class="text-end">
                                        <span class="badge-hd btn-comparar-reuso" 
                                              style="color: var(--ds-accent-primary); border-color: var(--ds-accent-primary); background: rgba(255,152,0,0.05); cursor: pointer; white-space: nowrap;"
                                              data-id1="${r.doc1.id}"
                                              data-id2="${r.doc2.id}"
                                              data-fragments='${JSON.stringify(r.ejemplos)}'
                                              title="Ver comparativa lado a lado">
                                            ${r.coincidencias} N-GRAMS
                                        </span>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        renderView(html);
    }

    // --- 3. Geosemantics ---
    async function loadGeosemantics() {
        const data = await apiPost('geosemantica');
        if (!data.exito) {
            renderView(`<div class="alert alert-danger">${data.error}</div>`);
            return;
        }

        if (!data.geo_data || data.geo_data.length === 0) {
            renderEmptyState(
                "Sin datos geosemánticos",
                "No se han detectado suficientes menciones geográficas o tópicos espaciales en el corpus seleccionado.",
                [
                    "Verifica que los documentos tengan contenido textual suficiente para el reconocimiento de lugares.",
                    "Amplía los criterios de búsqueda para incluir más regiones o publicaciones.",
                    "Si estás usando 'Secuencia (Capítulos)', asegúrate de seleccionar documentos con referencias espaciales."
                ]
            );
            return;
        }

        // Theme variables
        const light = document.documentElement.getAttribute('data-theme') === 'light';
        const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
        const textWhite = light ? '#000' : '#fff';
        const cardBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.25)';
        const borderColor = light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';
        const mapBg = light ? '#f5f5f5' : '#1a1a1a';
        const mapBorder = light ? '1px solid #ddd' : '1px solid rgba(255,255,255,0.1)';

        renderView(`
            <div class="card-panel-hd p-4">
                <div class="section-title-hd"><i class="fa-solid fa-earth-americas"></i>Mapas Geosemánticos</div>
                
                <div class="p-3 mb-4 rounded border border-secondary border-opacity-10" style="background: ${cardBg} !important;">
                    <div class="d-flex justify-content-between">
                        <div style="flex: 1;">
                            <div class="hd-metric-label mb-2"><i class="fa-solid fa-info-circle text-accent me-2"></i>Cartografía del Discurso</div>
                            <p class="small mb-0" style="line-height: 1.5; color: ${textMuted} !important;">Relaciona los tópicos latentes del discurso con las ubicaciones geográficas mencionadas. Permite visualizar qué temas (política, economía, guerra, religión) predominan en cada zona del mapa, detectando patrones regionales del pensamiento social.</p>
                        </div>
                        <div class="ms-4 border-start border-secondary border-opacity-10 ps-4" style="min-width: 200px;">
                            <div class="mb-2">
                                <span class="hd-metric-label" style="font-size: 9px; opacity: 0.6;">TECNOLOGÍA</span>
                                <div class="small" style="font-size: 11px; color: ${textWhite} !important;">LDA + Leaflet.js Geocoding</div>
                            </div>
                            <div>
                                <span class="hd-metric-label" style="font-size: 9px; opacity: 0.6;">POTENCIA</span>
                                <div class="small" style="font-size: 11px; color: ${textWhite} !important;">Mapeo espacial de temas predominantes</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row g-4">
                    <div class="col-md-9">
                        <div id="geosem-map" style="height: 500px; background: ${mapBg}; border-radius: 8px; border: ${mapBorder}; overflow: hidden;"></div>
                    </div>
                    <div class="col-md-3">
                        <h5 class="hd-metric-label mb-3">Leyenda de Tópicos</h5>
                        <div class="list-group list-group-flush custom-scrollbar" style="max-height: 450px; overflow-y: auto;">
                            ${data.topicos.map(t => `
                                <div class="list-group-item bg-transparent border-secondary border-opacity-10 px-0 py-2" style="border-bottom-color: ${borderColor} !important;">
                                    <div class="d-flex align-items-center gap-2">
                                        <div style="width: 10px; height: 10px; border-radius: 50%; background: hsla(${(t.id - 1) * 72}, 100%, 50%, 0.9)"></div>
                                        <div class="hd-metric-label" style="color: var(--ds-accent-primary); margin:0;">Tópico ${t.id}</div>
                                    </div>
                                    <div style="font-size: 0.8rem; opacity: 0.7; margin-top: 4px; padding-left: 18px; color: ${textWhite} !important;">${t.palabras.slice(0, 5).map(p => p[0]).join(', ')}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `);

        // Inicializar Mapa Leaflet
        const map = L.map('geosem-map', {
            center: [40, -4],
            zoom: 5,
            zoomControl: false,
            attributionControl: false
        });

        const tileUrl = light
            ? 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
            : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
        L.tileLayer(tileUrl).addTo(map);

        L.control.zoom({ position: 'bottomright' }).addTo(map);

        // Colores por tópico
        const getTopicColor = (id) => `hsla(${(id - 1) * 72}, 100%, 50%, 0.9)`;

        // Geocodificar ciudades y añadir marcadores
        const markers = [];
        const geocodePromises = data.geo_data.map(async (g) => {
            try {
                const res = await fetch(`/api/ciudad_coords?nombre=${encodeURIComponent(g.ciudad)}`);
                if (res.ok) {
                    const coords = await res.json();

                    const popupBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(255,255,255,0.1)';
                    const popupLabelColor = light ? '#666' : 'rgba(255,255,255,0.7)';

                    const innerHTML = `
                        <div style="text-align:center; min-width: 120px;">
                            <h6 style="color:var(--ds-accent-primary); font-weight:700; text-transform:uppercase; margin-bottom:5px;">${g.ciudad}</h6>
                            <div style="background:${popupBg}; padding:5px; border-radius:4px;">
                                <div class="hd-metric-label" style="font-size:9px; margin-bottom:2px; color:${popupLabelColor};">TÓPICO DOMINANTE</div>
                                <div style="color:${textWhite}; font-weight:bold; font-size:11px;">Tópico ${g.topico_dominante}</div>
                                <div style="width:100%; height:3px; background:${getTopicColor(g.topico_dominante)}; margin-top:4px;"></div>
                            </div>
                        </div>
                    `;

                    const marker = L.circleMarker([coords.lat, coords.lon], {
                        radius: Math.sqrt(g.intensidad) * 4 + 5,
                        fillColor: getTopicColor(g.topico_dominante),
                        color: light ? '#294a60' : '#fff',
                        weight: 1,
                        opacity: 0.8,
                        fillOpacity: 0.6
                    }).bindPopup(innerHTML);

                    marker.addTo(map);
                    markers.push(marker);
                }
            } catch (e) {
                console.warn(`No se pudo geocodificar: ${g.ciudad}`);
            }
        });

        await Promise.all(geocodePromises);

        if (markers.length > 0) {
            const group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds(), { padding: [50, 50] });
        }
    }

    // --- 5. N-gramas ---
    async function loadNgrams() {
        const n = 2; // Por defecto bigramas
        const data = await apiPost('ngramas', { n });
        if (!data.exito) {
            renderView(`<div class="alert alert-danger">${data.error}</div>`);
            return;
        }

        const light = isLight();
        const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
        const textWhite = light ? '#212121' : '#fff';
        const cardBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.25)';
        const borderColor = light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';

        renderView(`
            <div class="card-panel-hd p-4">
                <div class="section-title-hd"><i class="fa-solid fa-align-left"></i>Análisis de N-gramas</div>
                
                <div class="p-3 mb-4 rounded border border-secondary border-opacity-10" style="background: ${cardBg} !important;">
                    <div class="d-flex justify-content-between">
                        <div style="flex: 1;">
                            <div class="hd-metric-label mb-2"><i class="fa-solid fa-info-circle text-accent me-2"></i>Patrones Recurrentes</div>
                            <p class="small mb-0" style="line-height: 1.5; color: ${textMuted} !important;">Identifica las secuencias de palabras más frecuentes en el corpus. Los n-gramas permiten detectar frases hechas, eslóganes políticos, nombres de entidades complejas y tópicos recurrentes capturando el contexto inmediato de las palabras.</p>
                        </div>
                        <div class="ms-4 border-start border-secondary border-opacity-10 ps-4" style="min-width: 200px;">
                            <div class="mb-2">
                                <span class="btn-group btn-group-sm mb-2">
                                    <button class="btn btn-outline-warning active btn-ngram-type" data-n="2">2-gram</button>
                                    <button class="btn btn-outline-warning btn-ngram-type" data-n="3">3-gram</button>
                                    <button class="btn btn-outline-warning btn-ngram-type" data-n="4">4-gram</button>
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-12">
                        <div style="height: 450px;">
                            <canvas id="ngram-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `);

        // Renderizar gráfico
        const ctx = document.getElementById('ngram-chart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.ngramas.slice(0, 15).map(ng => ng.texto),
                datasets: [{
                    label: 'Frecuencia',
                    data: data.ngramas.slice(0, 15).map(ng => ng.frecuencia),
                    backgroundColor: 'rgba(255, 152, 0, 0.7)',
                    borderColor: '#ff9800',
                    borderWidth: 1,
                    borderRadius: 4
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
                        grid: { color: light ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)' },
                        ticks: { color: textMuted }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: textWhite, font: { size: 11 } }
                    }
                }
            }
        });

        // Handler para cambiar N
        document.querySelectorAll('.btn-ngram-type').forEach(btn => {
            btn.addEventListener('click', async function () {
                const newN = this.getAttribute('data-n');
                document.querySelectorAll('.btn-ngram-type').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                const newData = await apiPost('ngramas', { n: newN });
                if (newData.exito) {
                    chart.data.labels = newData.ngramas.slice(0, 15).map(ng => ng.texto);
                    chart.data.datasets[0].data = newData.ngramas.slice(0, 15).map(ng => ng.frecuencia);
                    chart.update();
                }
            });
        });
    }

    // --- 4. Semantic Shift ---
    async function loadSemanticShift() {
        const light = isLight();
        const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
        const textWhite = light ? '#212121' : '#fff';
        const cardBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.25)';

        renderView(`
            <div class="card-panel-hd p-4">
                <div class="section-title-hd"><i class="fa-solid fa-clock-rotate-left"></i>Estudio de Cambio Semántico</div>
                
                <div class="p-3 mb-5 rounded border border-secondary border-opacity-10" style="background: ${cardBg} !important;">
                    <div class="d-flex justify-content-between">
                        <div style="flex: 1;">
                            <div class="hd-metric-label mb-2"><i class="fa-solid fa-info-circle text-accent me-2"></i>Evolución de Conceptos</div>
                            <p class="small mb-0" style="line-height: 1.5; color: ${textMuted} !important;">Analiza cómo cambia el "vecindario contextual" de una palabra clave (ej: Libertad, Patria, Comercio) a lo largo del tiempo. Al comparar diferentes periodos, podemos ver si un concepto ha evolucionado ideológicamente o ha cambiado de uso social predominante.</p>
                        </div>
                        <div class="ms-4 border-start border-secondary border-opacity-10 ps-4" style="min-width: 200px;">
                            <div class="mb-2">
                                <span class="hd-metric-label" style="font-size: 9px; opacity: 0.6;">TECNOLOGÍA</span>
                                <div class="small" style="font-size: 11px; color: ${textWhite} !important;">Word2Vec / Distant Supervision Embeddings</div>
                            </div>
                            <div>
                                <span class="hd-metric-label" style="font-size: 9px; opacity: 0.6;">POTENCIA</span>
                                <div class="small" style="font-size: 11px; color: ${textWhite} !important;">Evolución diacrónica de conceptos clave</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="input-group mb-5" style="max-width: 600px; margin: 0 auto;">
                    <span class="input-group-text border-secondary border-opacity-25 text-muted small" style="font-family: var(--ds-font-mono); background: ${light ? '#eee' : '#111'};">CONCEPTO</span>
                    <input type="text" id="palabra-shift" class="form-control border-secondary border-opacity-25" placeholder="Escribe palabra (ej: libertad)..." style="font-weight: 600; background: ${light ? '#fff' : '#000'}; color: ${textWhite};">
                    <button class="btn btn-sirio px-4" id="btn-run-shift" style="background: var(--ds-accent-primary); color: #000; font-weight: 700;">ANALIZAR CAMBIO</button>
                </div>
                <div id="shift-results"></div>
            </div>
        `);

        document.getElementById('btn-run-shift').addEventListener('click', async () => {
            const palabra = document.getElementById('palabra-shift').value;
            if (!palabra) return;
            const res = await apiPost('semantic-shift', { palabra });
            if (!res.exito) return;

            if (!res.periodos || res.periodos.length === 0) {
                document.getElementById('shift-results').innerHTML = `
                    <div class="alert alert-info border-secondary border-opacity-10 bg-dark bg-opacity-25 text-center p-4 mt-4">
                        <i class="fa-solid fa-circle-info me-2 text-accent"></i>
                        No se ha podido rastrear la evolución de <strong>"${palabra}"</strong>. No hay apariciones suficientes en los periodos comparados.
                    </div>
                `;
                return;
            }

            let resHtml = `<div class="row g-4">`;
            res.periodos.forEach(p => {
                const borderColor = light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';
                resHtml += `
                    <div class="col-md-6">
                        <div class="p-4 rounded text-center" style="background: ${cardBg} !important;">
                            <span class="hd-metric-label mb-3">${p.label}</span>
                            <div class="mb-4" style="font-size: 0.9rem; color: ${textMuted} !important;">Asociaciones para <strong style="color: ${textWhite} !important;">"${res.palabra}"</strong></div>
                            <div class="d-flex flex-wrap justify-content-center gap-2">
                                ${p.vecinos.map(v => `<span class="badge-hd" style="font-size: 13px; padding: 8px 15px; border-color: ${borderColor}; color: ${textWhite};">${v}</span>`).join('')}
                            </div>
                        </div>
                    </div>
                `;
            });
            resHtml += `</div>`;
            document.getElementById('shift-results').innerHTML = resHtml;
        });
    }

    // --- 5. Communities ---
    async function loadCommunities() {
        const data = await apiPost('comunidades');
        if (!data.exito) {
            renderView(`<div class="alert alert-danger">${data.error}</div>`);
            return;
        }

        if (!data.nodos || data.nodos.length === 0) {
            renderEmptyState(
                "Red de Influencia Vacía",
                "No se han encontrado suficientes interacciones entre agentes (personas, instituciones) en este conjunto de datos.",
                [
                    "Asegúrate de que el análisis de entidades esté configurado correctamente en el sistema.",
                    "Prueba con un 'Límite de Documentos' mayor para encontrar más conexiones.",
                    "Ajusta los filtros para incluir periodos de tiempo con más actividad informativa.",
                    "Verifica la configuración de 'Tipos de Entidades' para asegurar que se están extrayendo PER, ORG y LOC."
                ]
            );
            return;
        }

        const light = isLight();
        const netBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.3)';
        const netBorder = light ? '1px solid #d0d0d0' : '1px solid rgba(255,255,255,0.05)';
        const textWhite = light ? '#212121' : '#fff';
        const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
        const cardBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.25)';
        const borderColor = light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';

        renderView(`
            <div class="card-panel-hd p-4">
                <div class="section-title-hd"><i class="fa-solid fa-people-group"></i>Red de Agentes e Influencia</div>
                
                <div class="p-3 mb-4 rounded border border-secondary border-opacity-10" style="background: ${cardBg} !important;">
                    <div class="d-flex justify-content-between">
                        <div style="flex: 1;">
                            <div class="hd-metric-label mb-2"><i class="fa-solid fa-info-circle text-accent me-2"></i>Sistemas Complejos</div>
                            <p class="small mb-0" style="line-height: 1.5; color: ${textMuted} !important;">Visualiza una red de agentes (personas, instituciones) basada en su co-ocurrencia en las mismas noticias. El algoritmo identifica de forma automática "comunidades" de discurso y destaca a los 'Brokers' informativos con mayor grado de influencia en la red.</p>
                        </div>
                        <div class="ms-4 border-start border-secondary border-opacity-10 ps-4" style="min-width: 200px;">
                            <div class="mb-2">
                                <span class="hd-metric-label" style="font-size: 9px; opacity: 0.6;">TECNOLOGÍA</span>
                                <div class="small" style="font-size: 11px; color: ${textWhite} !important;">NetworkX, Louvain Partitioning, Modularity</div>
                            </div>
                            <div>
                                <span class="hd-metric-label" style="font-size: 9px; opacity: 0.6;">POTENCIA</span>
                                <div class="small" style="font-size: 11px; color: ${textWhite} !important;">Estructuras de poder y brokers informativos</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div id="communities-network" style="height: 600px; background: ${netBg}; border-radius: 8px; border: ${netBorder};"></div>
                <div class="mt-5">
                    <div class="hd-metric-label mb-4">Principales Agentes de Información (Brokers)</div>
                    <div class="row g-3">
                        ${data.nodos.slice(0, 6).map(n => `
                            <div class="col-md-2">
                                <div class="p-3 bg-dark-sirio rounded text-center" style="background: ${cardBg} !important; border-color: ${borderColor} !important;">
                                    <div class="hd-metric-value mb-1" style="color: var(--ds-accent-primary)">${n.influence || n.influencia}</div>
                                    <div class="hd-metric-label" style="font-size: 10px; color: ${textWhite} !important; opacity: 0.8;">${n.name}</div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `);

        const container = document.getElementById('communities-network');
        if (typeof vis === 'undefined') {
            container.innerHTML = `<div class="p-5 text-center text-muted"><i class="fa-solid fa-triangle-exclamation text-warning mb-2"></i><br>Librería de visualización no disponible</div>`;
            return;
        }

        const visData = {
            nodes: data.nodos.map(n => ({
                id: n.id,
                label: n.name,
                size: 8 + Math.sqrt(n.influencia || 1) * 4,
                color: {
                    background: n.influencia > 10 ? '#ff9800' : (light ? '#294a60' : '#333'),
                    border: light ? '#1e3545' : 'rgba(255,152,0,0.3)',
                    highlight: { background: '#ff9800', border: light ? '#000' : '#fff' }
                },
                font: { color: light ? '#333' : '#e0e0e0', size: 11, face: 'JetBrains Mono' }
            })),
            edges: data.enlaces.map(e => ({
                from: e.source,
                to: e.target,
                value: e.value,
                color: {
                    color: light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.05)',
                    highlight: 'rgba(255,152,0,0.5)'
                }
            }))
        };
        const options = {
            nodes: { shape: 'dot' },
            layout: { improvedLayout: false },
            physics: {
                forceAtlas2Based: { 
                    gravitationalConstant: -100, 
                    centralGravity: 0.005, 
                    springLength: 100,
                    damping: 0.8  // Añadir amortiguamiento para reducir oscilaciones
                },
                solver: 'forceAtlas2Based',
                stabilization: { 
                    iterations: 300,  // Aumentar iteraciones para mejor estabilización
                    updateInterval: 25
                },
                maxVelocity: 30,  // Limitar velocidad máxima de los nodos
                minVelocity: 0.1   // Velocidad mínima antes de considerar estabilizado
            },
            interaction: { hover: true, tooltipDelay: 200 }
        };
        const network = new vis.Network(container, visData, options);
        
        // Deshabilitar física después de la estabilización para evitar vibraciones
        network.on('stabilizationIterationsDone', function () {
            network.setOptions({ physics: false });
        });
    }

    // --- 6. Análisis Dramático ---
    async function loadDramatico() {
        const data = await apiPost('dramatico');
        if (!data.exito) {
            renderView(`<div class="alert alert-danger">${data.error}</div>`);
            return;
        }

        if (!data.nodos || data.nodos.length === 0) {
            renderEmptyState(
                "No se detectaron personajes",
                "El análisis no ha podido identificar personajes o diálogos estructurados en este conjunto de textos teatrales.",
                [
                    "Asegúrate de que los textos tengan el formato de obra teatral (PERSONAJE: Texto).",
                    "Verifica que el campo 'Reparto' esté relleno en la ficha del texto.",
                    "Aumenta el 'Límite de Documentos' para abarcar la obra completa."
                ]
            );
            return;
        }

        const light = isLight();
        const textWhite = light ? '#212121' : '#fff';
        const textMuted = light ? '#666' : 'rgba(255,255,255,0.7)';
        const cardBg = light ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.15)';
        const borderColor = light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';

        // Generar filas para la tabla de reparto
        const tableRows = (data.reparto_detalle || []).map(p => `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td class="fw-bold py-3" style="color: var(--ds-accent);">${p.nombre}</td>
                <td class="text-center font-monospace" style="color: ${textWhite};">${p.intervenciones}</td>
                <td class="text-center font-monospace" style="color: ${textWhite};">${p.palabras.toLocaleString()}</td>
                <td class="small opacity-75">
                    ${(p.top_words || []).map(w => `<span class="badge border border-secondary border-opacity-25 text-muted me-1 fw-normal">${w}</span>`).join('')}
                </td>
            </tr>
        `).join('');

        const iaInsightsHtml = data.analisis_ia ? `
            <div class="card-panel-hd p-4 mb-4" style="background: linear-gradient(135deg, rgba(255, 152, 0, 0.08) 0%, rgba(0,0,0,0) 100%); border: 1px solid rgba(255, 152, 0, 0.2) !important;">
                <div class="hd-metric-label mb-3" style="color: #ff9800 !important; letter-spacing: 1px;">
                    <i class="fa-solid fa-wand-magic-sparkles me-2"></i>INTERPRETACIÓN DISCURSIVA (IA)
                </div>
                <div class="ai-report-content" style="color: rgba(255,255,255,0.85); line-height: 1.7; font-size: 0.85rem;">
                    ${typeof marked !== 'undefined' ? marked.parse(data.analisis_ia) : data.analisis_ia.replace(/\n/g, '<br>')}
                </div>
            </div>
        ` : '';

        renderView(`
            <div class="card-panel-hd p-4">
                <div class="section-title-hd"><i class="fa-solid fa-masks-theater"></i>Laboratorio de Dramaturgia Computacional</div>
                
                ${iaInsightsHtml}

                <div class="p-3 mb-4 rounded border border-secondary border-opacity-10" style="background: ${cardBg} !important; backdrop-filter: blur(10px);">
                    <div class="d-flex justify-content-between align-items-center">
                        <div style="flex: 1;">
                            <div class="hd-metric-label mb-2"><i class="fa-solid fa-info-circle text-accent me-2"></i>Estructura y Conflicto Histórico</div>
                            <p class="small mb-0" style="line-height: 1.5; color: ${textMuted} !important;">Este análisis explota la micro-segmentación del texto para atribuir el volumen discursivo a cada actor social. La red visualiza el capital social (conexiones) y la tabla inferior desglosa la complejidad léxica por personaje.</p>
                        </div>
                    </div>
                </div>

                <div class="row g-4 mb-4">
                    <!-- Red de Personajes -->
                    <div class="col-md-7">
                        <h5 class="hd-metric-label mb-3">Mapa de Relaciones Sociales (Grafo)</h5>
                        <div id="dramatico-network" style="height: 500px; background: rgba(0,0,0,0.2); border-radius: 12px; border: 1px solid ${borderColor};"></div>
                    </div>
                    
                    <!-- Protagonismo -->
                    <div class="col-md-5">
                        <h5 class="hd-metric-label mb-3">Distribución del Protagonismo</h5>
                        <div class="p-4 rounded h-100" style="background: ${cardBg} !important; border: 1px solid ${borderColor};">
                            <div style="height: 420px;">
                                <canvas id="protagonismo-chart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tabla Detallada -->
                <div class="mt-5">
                    <h5 class="hd-metric-label mb-3">Desglose Analítico por Personaje</h5>
                    <div class="table-responsive" style="background: rgba(0,0,0,0.1); border-radius: 12px; border: 1px solid ${borderColor}; padding: 15px;">
                        <table class="table table-dark table-hover mb-0" style="--bs-table-bg: transparent; border-color: transparent;">
                            <thead>
                                <tr class="small text-muted border-bottom border-secondary border-opacity-25" style="font-size: 10px; letter-spacing: 0.5px;">
                                    <th>PERSONAJE / ACTOR</th>
                                    <th class="text-center">ESCENAS/INTERV.</th>
                                    <th class="text-center">TOT. PALABRAS</th>
                                    <th>VOCABULARIO DOMINANTE</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tableRows}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Tensión Dramática -->
                <div class="col-12 mt-5">
                    <h5 class="hd-metric-label mb-3">Cronología de la Tensión Dramática (Sentimiento)</h5>
                    <div class="card-panel-hd p-4" style="min-height: 350px; background: rgba(0,0,0,0.1) !important;">
                         <canvas id="tension-chart"></canvas>
                    </div>
                </div>
            </div>
        `);

        // 1. Grafo de Personajes
        const networkContainer = document.getElementById('dramatico-network');
        const visData = {
            nodes: data.nodos.map(n => ({
                id: n.id,
                label: n.name,
                size: 15 + Math.sqrt(n.influencia) * 4,
                color: {
                    background: '#ff9800',
                    border: 'rgba(255,255,255,0.2)',
                    highlight: { background: '#fff', border: '#ff9800' }
                },
                font: { color: '#fff', size: 11, face: 'JetBrains Mono' },
                shadow: true
            })),
            edges: data.enlaces.map(e => ({
                from: e.source,
                to: e.target,
                width: 1 + Math.log1p(e.value),
                color: { color: 'rgba(255,255,255,0.08)', highlight: '#ff9800' },
                smooth: { type: 'continuous' }
            }))
        };
        const networkOptions = {
            nodes: { shape: 'dot' },
            physics: { forceAtlas2Based: { gravitationalConstant: -80, springLength: 120 }, solver: 'forceAtlas2Based', stabilization: { iterations: 200 } }
        };
        new vis.Network(networkContainer, visData, networkOptions);

        // 2. Gráfico de Protagonismo
        const ctxP = document.getElementById('protagonismo-chart').getContext('2d');
        new Chart(ctxP, {
            type: 'bar',
            data: {
                labels: (data.reparto_detalle || []).slice(0, 8).map(p => p.nombre),
                datasets: [{
                    label: 'Palabras Habladas',
                    data: (data.reparto_detalle || []).slice(0, 8).map(p => p.palabras),
                    backgroundColor: 'rgba(255, 152, 0, 0.4)',
                    borderColor: '#ff9800',
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: textMuted }, grid: { color: borderColor } },
                    y: { ticks: { color: textWhite, font: { weight: 'bold' } }, grid: { display: false } }
                },
                plugins: { legend: { display: false } }
            }
        });

        // 3. Gráfico de Tensión Dramática
        const ctxT = document.getElementById('tension-chart').getContext('2d');
        new Chart(ctxT, {
            type: 'line',
            data: {
                labels: data.tension.map(t => t.label),
                datasets: [{
                    label: 'Tensión Emocional',
                    data: data.tension.map(t => t.sentimiento),
                    borderColor: '#ff9800',
                    backgroundColor: 'rgba(255, 152, 0, 0.05)',
                    fill: true,
                    tension: 0.5,
                    pointBackgroundColor: '#ff9800',
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: textMuted, font: { size: 9 } }, grid: { display: false } },
                    y: { 
                        min: -1, max: 1,
                        ticks: { color: textMuted },
                        grid: { color: borderColor, borderDash: [5, 5] }
                    }
                },
                plugins: {
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.9)',
                        titleColor: '#ff9800',
                        callbacks: {
                            afterLabel: function(context) {
                                return `Obra: ${data.tension[context.dataIndex].titulo_obra}`;
                            }
                        }
                    }
                }
            }
        });
    }


    // Cargar comunidades por defecto
    loadCommunities();
});
