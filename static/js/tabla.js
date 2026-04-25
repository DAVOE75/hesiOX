// ==========================================================
// 🧭 Proyecto Sirio — Gestión Completa (Lotes + Tooltips + Filtros + Columnas Visibles)
// ==========================================================

// ----------------------
// UTILIDADES HTML
// ----------------------
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function decodeHtmlEntities(text) {
  if (!text) return '';
  const txt = document.createElement('textarea');
  txt.innerHTML = text;
  return txt.value;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

// ----------------------
// 0) CONFIG COLUMNAS
// ----------------------
const COLS_STORAGE_KEY = "sirio.cols.visible.v1";

// Columnas conocidas (para reset “inteligente”)
const DEFAULT_VISIBLE_COLS = [
  "check",
  "ref",
  "titulo",
  "publicacion",
  "ciudad",
  "pais",
  "licencia",
  "temas",
  "acciones",
];

// ----------------------
// 1) UTILIDADES GENERALES
// ----------------------
function obtenerIDsSeleccionados() {
  const ids = [];
  document.querySelectorAll(".registro-checkbox:checked").forEach((checkbox) => {
    if (checkbox.dataset.id) ids.push(checkbox.dataset.id);
  });
  return ids;
}

function actualizarBotonAccionesMasivas() {
  const ids = obtenerIDsSeleccionados();
  const statusEl = document.getElementById("count-seleccionados");
  const massActionBtn = document.getElementById("btn-acciones-lote");

  if (statusEl) statusEl.textContent = ids.length;

  if (massActionBtn) {
    if (ids.length > 0) {
      massActionBtn.disabled = false;
      massActionBtn.classList.add("shadow-lg");
      massActionBtn.classList.remove("btn-secondary");
      massActionBtn.classList.add("btn-warning");
    } else {
      massActionBtn.disabled = true;
      massActionBtn.classList.remove("shadow-lg");
      massActionBtn.classList.remove("btn-warning");
      massActionBtn.classList.add("btn-secondary");
    }
  }
}

function verificarConsistenciaFila(metadatos) {
  const { titulo, publicacion, autor, fecha, contenido } = metadatos;
  return {
    titulo: titulo || "[Documento Sin Título]",
    publicacion: publicacion || "Publicación Desconocida",
    autor: autor && autor.trim() ? autor.trim() : "Anónimo",
    fecha: fecha || "Fecha Desconocida",
    licencia: metadatos.licencia || "",
    contenido: contenido || "",
  };
}

function normalizarValoresFiltro(valoresBrutos, esFecha = false) {
  if (!Array.isArray(valoresBrutos)) return [];
  let valoresLimpios = valoresBrutos
    .map((v) => {
      if (typeof v !== "string") return "";
      v = v.trim().replace(/\s+/g, " ");
      if (v.toUpperCase() === "ANÓNIMO" || v.toUpperCase() === "ANONIMO") return "Anónimo";
      // Formatear fechas AAAA-MM-DD a DD/MM/AAAA
      if (esFecha && v.length === 10 && v[4] === '-' && v[7] === '-') {
        return `${v.slice(8, 10)}/${v.slice(5, 7)}/${v.slice(0, 4)}`;
      }
      return v;
    })
    .filter((v) => v !== "");

  const valoresUnicos = [...new Set(valoresLimpios)];
  if (esFecha) return valoresUnicos;
  return valoresUnicos.sort();
}

// ======================
// FILTROS DEPENDIENTES
// ======================

// IDs de los selects de filtros dependientes
const FILTER_SELECTS = ['selectAutor', 'selectPublicacion', 'selectCiudad', 'selectPais', 'selectFecha', 'selectTemas'];

/**
 * Inicializar Choices.js para los selects de filtros y configurar eventos
 */
function initFilterChoices() {
  console.log("🔧 Inicializando Choices.js para filtros...");

  FILTER_SELECTS.forEach((id) => {
    const select = document.getElementById(id);
    if (!select) {
      console.warn(`⚠️ No se encontró el select con ID: ${id}`);
      return;
    }

    // Si ya tiene Choices.js inicializado, saltar
    if (window.choicesInstances?.[id]) {
      console.log(`ℹ️ ${id} ya tiene Choices.js`);
      return;
    }

    try {
      // Inicializar Choices.js
      const instance = new Choices(select, {
        searchEnabled: true,
        searchResultLimit: 50,
        itemSelectText: '',
        shouldSort: false,
        position: 'bottom',
        allowHTML: false,
        removeItemButton: false
      });

      // Guardar instancia
      window.choicesInstances = window.choicesInstances || {};
      window.choicesInstances[id] = instance;

      // Escuchar evento 'change' de Choices.js
      select.addEventListener('change', function (e) {
        console.log(`🔄 CHANGE en ${id}:`, select.value);
        sincronizarFiltrosConBackend(id);
      });

      console.log(`✅ Choices.js inicializado para ${id}`);
    } catch (e) {
      console.error(`❌ Error inicializando Choices.js para ${id}:`, e);
      // Fallback: usar evento change nativo
      select.addEventListener('change', function (e) {
        console.log(`🔄 CHANGE nativo en ${id}:`, select.value);
        sincronizarFiltrosConBackend(id);
      });
    }
  });

  // Incluido no usa Choices.js
  const selectIncluido = document.getElementById("selectIncluido");
  if (selectIncluido) {
    selectIncluido.addEventListener("change", () => {
      console.log("🔄 Filtro incluido cambiado:", selectIncluido.value);
      filtrarAjax(1, false);
    });
  }

  // Evento para botón Ver (filtrar fechas manual)
  const btnVer = document.getElementById("btnFiltrarFechas");
  if (btnVer) {
    btnVer.addEventListener("click", () => {
      console.log("🔄 Ejecutando filtro de fechas manual...");
      filtrarAjax(1, false);
    });
  }
}

/**
 * Actualizar un select específico (con o sin Choices.js)
 */
function actualizarSelectChoices(id, valores) {
  const el = document.getElementById(id);
  if (!el) {
    console.warn(`⚠️ No se encontró el select con ID: ${id}`);
    return;
  }

  const choicesInstance = window.choicesInstances?.[id];
  const esFecha = id === 'selectFecha';
  const valoresNorm = normalizarValoresFiltro(valores, esFecha);

  // Guardar valor actual
  const valorActual = el.value;
  console.log(`🔄 actualizarSelectChoices(${id}): valorActual="${valorActual}", choicesInstance=${!!choicesInstance}, valores=${valoresNorm.length}`);

  if (choicesInstance) {
    // Con Choices.js - destruir y recrear para forzar actualización visual
    try {
      // Limpiar todas las opciones existentes
      choicesInstance.clearChoices();

      // Crear nuevas opciones
      const opciones = [{ value: "", label: "(Todos)", selected: valorActual === "" }].concat(
        valoresNorm.map((v) => ({ value: v, label: v, selected: v === valorActual }))
      );

      // Añadir las nuevas opciones
      choicesInstance.setChoices(opciones, "value", "label", true);

      // Forzar refresco visual
      if (valorActual && valoresNorm.includes(valorActual)) {
        choicesInstance.setChoiceByValue(valorActual);
      }

      console.log(`✅ ${id} actualizado con Choices.js: ${valoresNorm.length} opciones`);
    } catch (e) {
      console.error(`❌ Error actualizando ${id} con Choices.js:`, e);
      // Fallback: actualizar select nativo
      el.innerHTML = '<option value="">(Todos)</option>';
      valoresNorm.forEach((v) => {
        const o = document.createElement("option");
        o.value = v;
        o.textContent = v;
        if (v === valorActual) o.selected = true;
        el.appendChild(o);
      });
    }
  } else {
    // Sin Choices.js - actualizar select nativo
    const previousOptions = el.options.length;
    el.innerHTML = '<option value="">(Todos)</option>';
    valoresNorm.forEach((v) => {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = v;
      if (v === valorActual) o.selected = true;
      el.appendChild(o);
    });
    console.log(`✅ ${id} actualizado sin Choices.js: ${previousOptions} → ${el.options.length} opciones`);
  }
}

/**
 * Obtener el estado actual de todos los filtros
 */
function obtenerFiltrosActuales() {
  const f = {
    autor: document.getElementById("selectAutor")?.value || "",
    publicacion: document.getElementById("selectPublicacion")?.value || "",
    ciudad: document.getElementById("selectCiudad")?.value || "",
    pais_publicacion: document.getElementById("selectPais")?.value || "",
    fecha_original: document.getElementById("selectFecha")?.value || "",
    fecha_desde: document.getElementById("inputFechaDesde")?.value || "",
    fecha_hasta: document.getElementById("inputFechaHasta")?.value || "",
    temas: document.getElementById("selectTemas")?.value || "",
    busqueda: document.querySelector('input[name="busqueda"]')?.value || "",
    incluido: document.getElementById("selectIncluido")?.value || "todos"
  };
  console.log("🔍 Filtros detectados:", f);
  return f;
}

/**
 * Cargar filtros iniciales al cargar la página
 */
async function cargarFiltrosIniciales() {
  // Sincroniza el selector de noticias por página tras recarga AJAX
  function syncNoticiasPorPaginaSelector(valor) {
    const selector = document.getElementById('noticiasPorPagina');
    if (selector && valor) {
      selector.value = valor;
    }
  }
  try {
    console.log("📥 Cargando filtros iniciales...");
    const res = await fetch("/api/valores_filtrados");
    if (res.ok) {
      const data = await res.json();
      // 3. Re-inicializar componentes de la interfaz tras la carga AJAX
      if (typeof initEditarNotas === 'function') initEditarNotas();
      if (typeof activarTooltipsAvanzados === 'function') activarTooltipsAvanzados();
      if (typeof actualizarBotonAccionesMasivas === 'function') actualizarBotonAccionesMasivas();
      initCheckboxes();

      // Sincronizar selector de noticias por página si el backend lo devuelve
      if (data.noticias_por_pagina) {
        syncNoticiasPorPaginaSelector(data.noticias_por_pagina);
      }

      // Re-aplicar visibilidad de columnas guardada en localStorage SIEMPRE tras recarga AJAX
      setTimeout(() => {
        if (typeof reapplyColumnVisibilityAfterAjax === 'function') {
          reapplyColumnVisibilityAfterAjax();
        }
      }, 50);

      console.log("✅ Tabla y filtros sincronizados");
    }
  } catch (err) {
    console.error("❌ Error en cargarFiltrosIniciales:", err);
  }
}

/**
 * Sincronizar filtros en cascada cuando uno cambia
 * @param {string} filtroModificado - ID del select que se está modificando (se excluye de la consulta)
 */
async function sincronizarFiltrosConBackend(filtroModificado = null) {
  const filtros = obtenerFiltrosActuales();
  console.log("🔄 Filtros actuales:", filtros);

  // Construir parámetros manualmente (FormData no funciona bien con Choices.js)
  const params = new URLSearchParams();
  if (filtros.autor) params.append("autor", filtros.autor);
  if (filtros.publicacion) params.append("publicacion", filtros.publicacion);
  if (filtros.ciudad) params.append("ciudad", filtros.ciudad);
  if (filtros.pais_publicacion) params.append("pais_publicacion", filtros.pais_publicacion);
  if (filtros.fecha_original) params.append("fecha_original", filtros.fecha_original);
  if (filtros.fecha_desde) params.append("fecha_desde", filtros.fecha_desde);
  if (filtros.fecha_hasta) params.append("fecha_hasta", filtros.fecha_hasta);
  if (filtros.temas) params.append("temas", filtros.temas);
  if (filtros.busqueda) params.append("busqueda", filtros.busqueda);
  if (filtros.incluido && filtros.incluido !== "todos") params.append("incluido", filtros.incluido);
  params.append("page", 1);

  // Añadir noticias por página si existe
  const noticiasPorPagina = document.getElementById('noticiasPorPagina');
  if (noticiasPorPagina) {
    params.append('noticias_por_pagina', noticiasPorPagina.value);
  }

  try {
    console.log("🚀 Filtrando con parámetros:", Object.fromEntries(params));
    const res = await fetch(`/filtrar?${params.toString()}`);

    if (res.ok) {
      const data = await res.json();
      console.log("📥 Respuesta recibida, registros en HTML:", data.html ? "✓" : "✗");

      // 1. Actualizar la tabla
      const container = document.getElementById("tabla-container");
      if (container && data.html) {
        container.innerHTML = data.html;
      }

      // 2. Actualizar los dropdowns con valores filtrados (EXCEPTO el que se modificó)
      const selectsAModificar = FILTER_SELECTS.filter(id => id !== filtroModificado);
      console.log("🔧 Actualizando selects:", selectsAModificar);

      selectsAModificar.forEach(id => {
        let valores;
        switch (id) {
          case 'selectAutor': valores = data.autores || []; break;
          case 'selectPublicacion': valores = data.publicaciones || []; break;
          case 'selectCiudad': valores = data.ciudades || []; break;
          case 'selectPais': valores = data.paises || []; break;
          case 'selectFecha': valores = data.fechas || []; break;
          case 'selectTemas': valores = data.temas || []; break;
        }
        console.log(`📝 Actualizando ${id} con ${valores?.length || 0} valores`);
        if (valores) actualizarSelectChoices(id, valores);
      });

      // 3. Re-inicializar componentes de la interfaz
      if (typeof initEditarNotas === 'function') initEditarNotas();
      if (typeof activarTooltipsAvanzados === 'function') activarTooltipsAvanzados();
      if (typeof actualizarBotonAccionesMasivas === 'function') actualizarBotonAccionesMasivas();
      initCheckboxes();

      if (typeof reapplyColumnVisibilityAfterAjax === 'function') {
        reapplyColumnVisibilityAfterAjax();
      }

      console.log("✅ Tabla y filtros sincronizados");
    } else {
      console.error("❌ Error en respuesta:", res.status);
    }
  } catch (err) {
    console.error("❌ Error sincronizando filtros:", err);
  }
}

/**
 * Resetear todos los filtros
 */
async function resetearFiltros() {
  console.log("🔄 Resetando filtros...");

  // Limpiar todos los selects
  FILTER_SELECTS.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      const choicesInstance = window.choicesInstances?.[id];
      if (choicesInstance) {
        choicesInstance.removeActiveItems();
        choicesInstance.setChoiceByValue("");
      } else {
        el.value = "";
      }
    }
  });

  // Limpiar búsqueda y fechas manuales
  const busquedaInput = document.querySelector('input[name="busqueda"]');
  if (busquedaInput) busquedaInput.value = "";

  const fDesde = document.getElementById("inputFechaDesde");
  if (fDesde) fDesde.value = "";

  const fHasta = document.getElementById("inputFechaHasta");
  if (fHasta) fHasta.value = "";

  // Limpiar incluido
  const selectIncluido = document.getElementById("selectIncluido");
  if (selectIncluido) {
    const choicesInstance = window.choicesInstances?.selectIncluido;
    if (choicesInstance) {
      choicesInstance.setChoiceByValue("todos");
    } else {
      selectIncluido.value = "todos";
    }
  }

  // Asegurar que el selector de noticias por página tenga un valor válido antes de filtrar
  const noticiasPorPagina = document.getElementById('noticiasPorPagina');
  if (noticiasPorPagina && !noticiasPorPagina.value) {
    noticiasPorPagina.value = "50";
  }

  // Recargar valores de filtros desde el backend
  await cargarFiltrosIniciales();

  // Recargar la tabla
  filtrarAjax(1, true);
}

// ======================
// FIN FILTROS DEPENDIENTES
// ======================

// ----------------------
// 2) COLUMNAS VISIBLES
// ----------------------
function loadVisibleCols() {
  const stored = localStorage.getItem(COLS_STORAGE_KEY);
  if (stored) {
    try {
      const arr = JSON.parse(stored);
      return new Set(arr);
    } catch (e) {
      console.warn("Error parsing stored columns:", e);
    }
  }
  return new Set(DEFAULT_VISIBLE_COLS);
}

function saveVisibleCols(visibleSet) {
  const arr = Array.from(visibleSet);
  localStorage.setItem(COLS_STORAGE_KEY, JSON.stringify(arr));
}

function applyColumnVisibility(visibleColsSet) {
  // Buscar la tabla por id directo, más robusto tras AJAX
  const table = document.getElementById("tablaRegistros");
  if (!table) return;

  // Ocultar/mostrar encabezados
  table.querySelectorAll("thead th[data-col]").forEach((th) => {
    const key = th.dataset.col;
    th.style.display = visibleColsSet.has(key) ? "" : "none";
  });

  // Ocultar/mostrar celdas
  table.querySelectorAll("tbody td[data-col]").forEach((td) => {
    const key = td.dataset.col;
    td.style.display = visibleColsSet.has(key) ? "" : "none";
  });
}

function syncColumnTogglesUI(visibleColsSet) {
  document.querySelectorAll(".col-toggle[data-col]").forEach((cb) => {
    const key = cb.dataset.col;
    // check siempre visible (si existe toggle, lo bloqueamos)
    if (key === "check") {
      cb.checked = true;
      cb.disabled = true;
      return;
    }
    cb.checked = visibleColsSet.has(key);
  });
}

function initColumnToggles() {
  const panel = document.getElementById("columnas-panel");
  if (!panel) {
    console.warn("⚠️ Panel de columnas no encontrado");
    return;
  }

  let visible = loadVisibleCols();
  console.log("📊 Columnas visibles cargadas:", Array.from(visible));

  // Aplica al cargar
  applyColumnVisibility(visible);
  syncColumnTogglesUI(visible);

  // Eventos checkbox
  panel.querySelectorAll(".col-toggle[data-col]").forEach((cb) => {
    // Evitar listeners duplicados usando una flag
    if (cb.dataset.listenerAttached) return;
    cb.dataset.listenerAttached = "true";

    cb.addEventListener("change", () => {
      const key = cb.dataset.col;

      if (key === "check") {
        // se fuerza siempre visible
        cb.checked = true;
        return;
      }

      if (cb.checked) visible.add(key);
      else visible.delete(key);

      // Salvaguarda: nunca dejar sin columnas (mínimo algunas)
      if (visible.size === 0) {
        visible = new Set(DEFAULT_VISIBLE_COLS);
      }

      visible.add("check");
      saveVisibleCols(visible);
      applyColumnVisibility(visible);
    });
  });

  // Reset (activa TODAS las columnas)
  const btnReset = document.getElementById("cols-reset");
  console.log("🔍 Botón reset encontrado:", btnReset ? "SÍ" : "NO");

  if (btnReset && !btnReset.dataset.listenerAttached) {
    btnReset.dataset.listenerAttached = "true";
    console.log("✅ Listener del botón reset registrado");

    btnReset.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();

      console.log("🖱️ Click en botón Mostrar todas");

      // Marcar todos los checkboxes de columnas (excepto check que ya está marcado)
      panel.querySelectorAll(".col-toggle[data-col]").forEach((cb) => {
        const key = cb.dataset.col;
        if (key !== "check" && !cb.checked) {
          cb.checked = true;
          // Disparar evento change para que se procese
          cb.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });

      console.log("✅ Todos los checkboxes marcados");
    });
  }
}

// Llamar esto después de cualquier recarga AJAX de la tabla
function reapplyColumnVisibilityAfterAjax() {
  const visible = loadVisibleCols();
  applyColumnVisibility(visible);
  syncColumnTogglesUI(visible);
}

// ----------------------
// 3) ACCIONES POR LOTE
// ----------------------
function ejecutarAccionesLote() {
  const btnBorrar = document.getElementById("batch-borrar");
  if (btnBorrar) {
    const nuevoBtn = btnBorrar.cloneNode(true);
    btnBorrar.parentNode.replaceChild(nuevoBtn, btnBorrar);

    nuevoBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      const ids = obtenerIDsSeleccionados();
      if (ids.length === 0) return;

      if (!confirm(`⚠️ ¿Estás seguro de ELIMINAR ${ids.length} noticias para siempre?`)) return;

      let borrados = 0;
      for (const id of ids) {
        try {
          const res = await fetch(`/eliminar/${id}`, {
            method: "POST",
            headers: {
              'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            }
          });
          if (res.ok) {
            borrados++;
          } else {
            console.error(`Error borrando ${id}:`, await res.text());
          }
        } catch (err) {
          console.error(`Error borrando ${id}`, err);
        }
      }

      alert(`✅ Se han borrado ${borrados} noticias.`);
      filtrarAjax(1, true);
    });
  }

  const btnDuplicar = document.getElementById("batch-duplicar");
  if (btnDuplicar) {
    const nuevoBtn = btnDuplicar.cloneNode(true);
    btnDuplicar.parentNode.replaceChild(nuevoBtn, btnDuplicar);

    nuevoBtn.addEventListener("click", (e) => {
      e.preventDefault();
      const ids = obtenerIDsSeleccionados();

      if (ids.length !== 1) {
        alert("⚠️ Para duplicar, selecciona SOLO UNA noticia.");
        return;
      }

      const id = ids[0];
      const fila = document.querySelector(`tr[data-id="${id}"]`);
      if (!fila) return;

      const params = new URLSearchParams();
      if (fila.dataset.titulo) params.append("titulo", fila.dataset.titulo + " (Copia)");
      if (fila.dataset.publicacion) params.append("publicacion", fila.dataset.publicacion);
      if (fila.dataset.fecha) params.append("fecha_original", fila.dataset.fecha);
      if (fila.dataset.contenido) params.append("contenido", fila.dataset.contenido);
      if (fila.dataset.autor) params.append("apellido_autor", fila.dataset.autor);

      window.location.href = `/nueva?${params.toString()}`;
    });
  }

  const btnImprimir = document.getElementById("batch-imprimir");
  if (btnImprimir) {
    const nuevoBtn = btnImprimir.cloneNode(true);
    btnImprimir.parentNode.replaceChild(nuevoBtn, btnImprimir);

    nuevoBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      const ids = obtenerIDsSeleccionados();
      if (ids.length === 0) {
        alert("Selecciona al menos una noticia.");
        return;
      }

      const originalText = nuevoBtn.textContent;
      nuevoBtn.textContent = "⏳ Generando...";

      try {
        const response = await fetch("/imprimir_lote", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').getAttribute('content')
          },
          body: JSON.stringify({ ids: ids }),
        });

        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `Dossier_Sirio_${new Date().toISOString().slice(0, 10)}.pdf`;
          document.body.appendChild(a);
          a.click();
          a.remove();
        } else {
          alert("Error al generar el PDF.");
        }
      } catch (err) {
        console.error(err);
        alert("Error de conexión.");
      } finally {
        nuevoBtn.textContent = originalText;
      }
    });
  }

  const btnPrepararPdf = document.getElementById("batch-preparar-pdf");
  if (btnPrepararPdf) {
    const nuevoBtnPrep = btnPrepararPdf.cloneNode(true);
    btnPrepararPdf.parentNode.replaceChild(nuevoBtnPrep, btnPrepararPdf);

    nuevoBtnPrep.addEventListener("click", (e) => {
      e.preventDefault();
      const ids = obtenerIDsSeleccionados();

      if (ids.length === 0) {
        alert("Selecciona una noticia para preparar su impresión.");
        return;
      }

      if (ids.length > 1) {
        alert("La preparación detallada de PDF solo está disponible para una noticia a la vez. Para imprimir varias, usa la opción 'PDF Rápido'.");
        return;
      }

      // Redirigir a la página de preparación
      window.location.href = `/articulos/preparar_pdf/${ids[0]}`;
    });
  }

  const btnGuardarLote = document.getElementById("btn-guardar-lote");
  if (btnGuardarLote) {
    const nuevoBtn = btnGuardarLote.cloneNode(true);
    btnGuardarLote.parentNode.replaceChild(nuevoBtn, btnGuardarLote);

    nuevoBtn.addEventListener("click", async () => {
      const ids = obtenerIDsSeleccionados();
      if (ids.length === 0) {
        alert("No hay noticias seleccionadas.");
        return;
      }

      const form = document.getElementById("form-edicion-lote");
      const formData = new FormData(form);
      const updates = {};

      formData.forEach((value, key) => {
        if (value.trim() !== "") updates[key] = value.trim();
      });

      if (Object.keys(updates).length === 0) {
        alert("⚠️ No has rellenado ningún campo para actualizar.");
        return;
      }

      try {
        const res = await fetch("/actualizar_lote", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').getAttribute('content')
          },
          body: JSON.stringify({ ids: ids, updates: updates }),
        });
        const data = await res.json();

        if (data.success) {
          const modalEl = document.getElementById("batchEditModal");
          const btnClose = modalEl ? modalEl.querySelector('[data-bs-dismiss="modal"]') : null;
          if (btnClose) btnClose.click();

          alert("✅ Actualización completada.");
          form.reset();
          filtrarAjax(1, true);
        } else {
          alert("Error: " + data.message);
        }
      } catch (err) {
        console.error(err);
        alert("Error de conexión.");
      }
    });
  }

  // --- NUEVO: Exportar por lote (JSON/CSV Sirio) ---
  const btnExportJson = document.getElementById("batch-export-json");
  if (btnExportJson) {
    btnExportJson.addEventListener("click", (e) => {
      e.preventDefault();
      const ids = obtenerIDsSeleccionados();
      if (ids.length === 0) {
        alert("Selecciona al menos una noticia para exportar.");
        return;
      }
      window.location.href = `/exportar?formato=json_sirio&ids=${ids.join(",")}`;
    });
  }

  const btnExportXml = document.getElementById("batch-export-xml");
  if (btnExportXml) {
    btnExportXml.addEventListener("click", (e) => {
      e.preventDefault();
      const ids = obtenerIDsSeleccionados();
      if (ids.length === 0) {
        alert("Selecciona al menos una noticia para exportar.");
        return;
      }
      window.location.href = `/exportar?formato=xml_sirio&ids=${ids.join(",")}`;
    });
  }

  const btnExportCsv = document.getElementById("batch-export-csv");
  if (btnExportCsv) {
    btnExportCsv.addEventListener("click", (e) => {
      e.preventDefault();
      const ids = obtenerIDsSeleccionados();
      if (ids.length === 0) {
        alert("Selecciona al menos una noticia para exportar.");
        return;
      }
      window.location.href = `/exportar?formato=csv_sirio&ids=${ids.join(",")}`;
    });
  }
}

// ----------------------
// 3.1) LÓGICA DE IMPORTACIÓN
// ----------------------
function initImportador() {
  const form = document.getElementById("formImportar");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("importFile");
    if (!fileInput.files.length) return;

    const btn = document.getElementById("btnDoImport");
    const progress = document.getElementById("importProgress");
    const progressBar = progress.querySelector(".progress-bar");
    const msg = document.getElementById("importMsg");

    const originalBtnHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-sync fa-spin me-1"></i> IMPORTANDO...';
    progress.classList.remove("d-none");
    progressBar.style.width = "20%";
    msg.classList.add("d-none");

    const formData = new FormData(form);

    try {
      const resp = await fetch("/importar_datos", {
        method: "POST",
        body: formData,
      });

      progressBar.style.width = "100%";
      const data = await resp.json();

      msg.classList.remove("d-none");
      if (data.success) {
        msg.className = "alert alert-success small";
        msg.innerHTML = `<strong>Éxito:</strong> ${data.message}`;
        setTimeout(() => window.location.reload(), 2000);
      } else {
        msg.className = "alert alert-danger small";
        msg.innerHTML = `<strong>Error:</strong> ${data.error || 'Ocurrió un error inesperado.'}`;
        btn.disabled = false;
        btn.innerHTML = originalBtnHtml;
      }
    } catch (err) {
      console.error(err);
      msg.classList.remove("d-none");
      msg.className = "alert alert-danger small";
      msg.textContent = "Error de conexión con el servidor.";
      btn.disabled = false;
      btn.innerHTML = originalBtnHtml;
    }
  });
}

// ----------------------
// 4) TOOLTIPS (OPCIÓN B)
// ----------------------
function activarTooltipsAvanzados() {
  document.querySelectorAll(".tooltip-preview").forEach((t) => {
    if (t._cleanup) t._cleanup();
    t.remove();
  });

  let tooltipActual = null;
  let filaFijada = null;

  const tbody = document.querySelector(".tabla-prensa tbody");
  if (!tbody) return;

  function ensureTooltipOnBody(tooltipEl) {
    if (tooltipEl.parentElement !== document.body) document.body.appendChild(tooltipEl);
  }

  function positionTooltip(tooltipEl, anchorEl) {
    const margin = 12;
    const r = anchorEl.getBoundingClientRect();
    const tw = tooltipEl.offsetWidth;
    const th = tooltipEl.offsetHeight;

    const idealLeft = r.left + r.width / 2 - tw / 2;
    const left = clamp(idealLeft, margin, window.innerWidth - tw - margin);

    const spaceBelow = window.innerHeight - r.bottom;
    const fitsBelow = spaceBelow >= th + margin;

    let top;
    if (fitsBelow) {
      tooltipEl.classList.remove("flip-up");
      top = r.bottom + margin;
    } else {
      tooltipEl.classList.add("flip-up");
      top = Math.max(margin, r.top - th - margin);
    }

    tooltipEl.style.left = `${left}px`;
    tooltipEl.style.top = `${top}px`;
  }

  function closeTooltip() {
    if (tooltipActual) {
      if (tooltipActual._cleanup) tooltipActual._cleanup();
      tooltipActual.remove();
      tooltipActual = null;
    }
    filaFijada = null;
  }

  function mostrarTooltip(fila, fijo = false) {
    const datos = {
      titulo: fila.dataset.titulo,
      publicacion: fila.dataset.publicacion,
      autor: fila.dataset.autor,
      fecha: fila.dataset.fecha,
      licencia: fila.dataset.licencia,
      contenido: fila.dataset.contenido,
      texto_original: fila.dataset.textoOriginal || ""
    };
    // Si existe el modal de cronología, rellenar la pestaña de texto original
    const modalTextoOriginal = document.getElementById("modalTextoOriginal");
    if (modalTextoOriginal) {
      if (datos.texto_original && datos.texto_original.trim().length > 0) {
        modalTextoOriginal.textContent = datos.texto_original;
      } else {
        modalTextoOriginal.innerHTML = '<em class="text-muted">Sin texto original disponible.</em>';
      }
    }

    const info = verificarConsistenciaFila(datos);

    let textoMostrar = info.contenido;
    let esLargo = false;

    if (!textoMostrar || textoMostrar.trim().length < 2) {
      textoMostrar = "<em>(Sin contenido de texto disponible)</em>";
    } else if (textoMostrar.length > 500) {
      textoMostrar = textoMostrar.substring(0, 500) + "…";
      esLargo = true;
    }

    const tooltip = document.createElement("div");
    tooltip.className = "tooltip-preview";
    if (fijo) tooltip.classList.add("fijo");

    const fullContentEsc = escapeHtml(info.contenido);
    const tituloEsc = escapeHtml(info.titulo);
    const pubEsc = escapeHtml(info.publicacion);
    const fechaEsc = escapeHtml(info.fecha);
    const licenciaEsc = escapeHtml(info.licencia);

    tooltip.innerHTML = `
      <strong>${escapeHtml(info.titulo)}</strong><br>
      <em>${escapeHtml(info.publicacion)}</em> — ${escapeHtml(info.fecha)}<br>
      ✍️ ${escapeHtml(info.autor)}
      ${info.licencia ? `<br>🔖 <span class="text-warning">${escapeHtml(info.licencia)}</span>` : ""}
      <hr>
      <div class="tooltip-scroll">${textoMostrar}</div>
      <div class="tooltip-actions">
      <button class="copiar-btn" data-text="${fullContentEsc}"><i class="fa-solid fa-copy"></i> Copiar</button>
        <a href="/noticias/detalle/${fila.dataset.id}" class="copiar-btn text-decoration-none d-inline-flex align-items-center justify-content-center"
           style="background: rgba(33, 150, 243, 0.15); color: #64b5f6; border: 1px solid rgba(33, 150, 243, 0.4); text-align: center; height: 26px;">
          <i class="fa-solid fa-expand me-1"></i> Ver completo
        </a>
        <button class="cerrar-tooltip-btn" style="background: rgba(255,69,58,0.15); color: #ff6b6b; border: 1px solid rgba(255,69,58,0.3);"><i class="fa-solid fa-xmark"></i> Cerrar</button>
      </div>
    `;

    ensureTooltipOnBody(tooltip);
    tooltipActual = tooltip;

    tooltip.style.left = "-9999px";
    tooltip.style.top = "-9999px";
    tooltip.classList.add("show");

    requestAnimationFrame(() => positionTooltip(tooltip, fila));

    const onMove = () => {
      if (!tooltipActual) return;
      positionTooltip(tooltip, fila);
    };
    window.addEventListener("scroll", onMove, true);
    window.addEventListener("resize", onMove);

    tooltip._cleanup = () => {
      window.removeEventListener("scroll", onMove, true);
      window.removeEventListener("resize", onMove);
    };
  }

  tbody.addEventListener("click", (ev) => {
    const fila = ev.target.closest("tr[data-id]");
    if (!fila) return;

    const link = ev.target.closest("a");
    const isVerNoticia = link && link.classList.contains("ver-noticia-btn");

    // Solo responder al botón "Ver noticia"
    if (isVerNoticia) {
      ev.preventDefault();
      ev.stopPropagation();
      ev.stopImmediatePropagation();

      // Toggle: si es la misma fila, cerrar; si no, mostrar
      if (filaFijada === fila) {
        closeTooltip();
        return;
      }

      closeTooltip();
      filaFijada = fila;
      mostrarTooltip(fila, true);
      return;
    }

    // Para cualquier otro elemento, no hacer nada (no abrir tooltip)
    return;
  });

  document.addEventListener(
    "click",
    (e) => {
      // No cerrar si se hace click en el botón ver-noticia o dentro del tooltip
      const isVerNoticiaBtn = e.target.closest(".ver-noticia-btn");
      const isInsideTooltip = tooltipActual && tooltipActual.contains(e.target);

      if (tooltipActual && !isInsideTooltip && !isVerNoticiaBtn) {
        closeTooltip();
      }
    },
    { capture: true }
  );
}

// ----------------------
// 5) EVENTOS GLOBALES
// ----------------------
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("copiar-btn") && !e.target.classList.contains("leer-btn")) {
    const raw = e.target.getAttribute("data-text") || "";
    navigator.clipboard.writeText(decodeHtmlEntities(raw));

    const original = e.target.textContent;
    e.target.textContent = "✅ Copiado";
    setTimeout(() => (e.target.textContent = original), 1300);
  }

  if (e.target.classList.contains("copiar-cita")) {
    e.preventDefault();
    e.stopPropagation();
    const url = e.target.getAttribute("data-url");
    if (url) window.open(url, "_blank");
    return;
  }

  if (e.target.classList.contains("leer-btn") || e.target.closest(".leer-btn")) {
    e.preventDefault();
    e.stopPropagation();

    const btn = e.target.classList.contains("leer-btn") ? e.target : e.target.closest(".leer-btn");

    document.querySelectorAll(".tooltip-preview").forEach((t) => {
      if (t._cleanup) t._cleanup();
      t.remove();
    });

    tooltipActual = null;
    filaFijada = null;

    const contenido = decodeHtmlEntities(btn.dataset.full || "");
    const titulo = decodeHtmlEntities(btn.dataset.titulo || "");
    const pub = decodeHtmlEntities(btn.dataset.pub || "");
    const fecha = decodeHtmlEntities(btn.dataset.fecha || "");
    const licencia = decodeHtmlEntities(btn.dataset.licencia || "");

    // Función para quitar etiquetas HTML y dejar solo texto
    const stripHtml = (html) => {
      const tmp = document.createElement("DIV");
      tmp.innerHTML = html;
      return tmp.textContent || tmp.innerText || "";
    };

    const contenidoLimpio = stripHtml(contenido);

    const modal = document.createElement("div");
    modal.className = "modal-overlay";
    modal.innerHTML = `
      <div class="modal-box">
        <button class="modal-close" style="position: absolute; top: 16px; right: 16px; border: none; background: rgba(20,20,20,0.9); color: #fff; font-size: 1.2rem; cursor: pointer; border-radius: 50%; width: 36px; height: 36px; transition: all 0.2s; z-index: 10; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(10px);" onmouseover="this.style.background='rgba(255,69,58,0.9)'; this.style.transform='scale(1.1)'" onmouseout="this.style.background='rgba(20,20,20,0.9)'; this.style.transform='scale(1)'">
          <i class="fa-solid fa-xmark"></i>
        </button>
        <h2>${escapeHtml(titulo)}</h2>
        <h4 style="color:#f5c542;">${escapeHtml(pub)} — ${escapeHtml(fecha)}</h4>
        ${licencia
        ? `<p style="font-size:0.85rem; color:#ccc;">🔖 Licencia: <strong>${escapeHtml(
          licencia
        )}</strong></p>`
        : ""
      }
        <div class="modal-scroll" style="text-align:justify;">${escapeHtml(contenidoLimpio).replace(/\n/g, "<br>")}</div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  if (e.target.classList.contains("modal-overlay") ||
    e.target.classList.contains("modal-close") ||
    e.target.closest(".modal-close")) {
    document.querySelector(".modal-overlay")?.remove();
  }

  if (e.target.classList.contains("cerrar-tooltip-btn")) {
    const tooltip = e.target.closest(".tooltip-preview");
    if (tooltip) {
      if (tooltip._cleanup) tooltip._cleanup();
      tooltip.remove();
      tooltipActual = null;
      filaFijada = null;
    }
  }
});

// ----------------------
// 6) FILTRADO / PAGINACIÓN (CORREGIDO)
// ----------------------

/**
 * Cambia la página y desplaza la vista al inicio de la tabla.
 */
function cambiarPagina(page) {
  const tableContainer = document.getElementById('tabla-container');
  if (tableContainer) {
    tableContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  filtrarAjax(page);
}

// Cambiar el número de noticias por página y recargar vía AJAX
function cambiarNoticiasPorPagina(valor) {
  filtrarAjax(1, true); // Reinicia a la primera página y fuerza AJAX instantáneo
}

// Sincronizar el valor del selector con el filtro usando delegación
document.addEventListener('change', function (e) {
  if (e.target && e.target.id === 'noticiasPorPagina') {
    const selector = e.target;
    // Actualizar el parámetro en la URL y recargar vía AJAX
    const form = document.getElementById('filtros');
    if (form) {
      // Añadir el valor al formulario antes de enviar
      let input = form.querySelector('input[name="noticias_por_pagina"]');
      if (!input) {
        input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'noticias_por_pagina';
        form.appendChild(input);
      }
      input.value = selector.value;
    }
    cambiarNoticiasPorPagina(selector.value);
  }
});

let filtrarTimeout = null;

/**
 * Lanza la petición de filtrado con un pequeño debounce para evitar peticiones excesivas.
 */
function filtrarAjax(page = 1, instant = false) {
  console.log("🎯 filtrarAjax llamado:", { page, instant });
  if (!instant) {
    clearTimeout(filtrarTimeout);
    filtrarTimeout = setTimeout(() => filtrarAjaxReal(page), 150);
  } else {
    filtrarAjaxReal(page);
  }
}

/**
 * Ejecuta la petición fetch al backend y actualiza el DOM.
 */
function filtrarAjaxReal(page = 1, noPushState = false) {
  const filtros = obtenerFiltrosActuales();
  const params = new URLSearchParams();

  // Mapeamos los filtros detectados a los parámetros de la URL
  Object.keys(filtros).forEach(key => {
    if (filtros[key]) params.set(key, filtros[key]);
  });

  params.set("page", page);

  // Añadir el valor del selector de noticias por página si existe y no es vacío
  const noticiasPorPagina = document.getElementById('noticiasPorPagina');
  if (noticiasPorPagina && noticiasPorPagina.value) {
    params.set('noticias_por_pagina', noticiasPorPagina.value);
  }

  console.log("🚀 [AJAX] Filtrando con parámetros final:", Object.fromEntries(params));

  // Actualizar la URL del navegador para que coincida con los filtros (sin recargar la página)
  // Usamos el pathname actual (que debería ser /listar) para mantener la interfaz.
  const newUrl = `${window.location.pathname}?${params.toString()}`;
  if (!noPushState && window.location.search !== `?${params.toString()}`) {
      window.history.pushState({ page, filtros: Object.fromEntries(params) }, "", newUrl);
  }

  // La ruta /filtrar ahora es gestionada por el blueprint de noticias
  fetch(`/filtrar?${params.toString()}`, {
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
      return r.json();
    })
    .then((data) => {
      console.log("✅ [AJAX] Respuesta recibida:", data.total, "resultados");
      // 1. Actualizar el cuerpo de la tabla
      const container = document.getElementById("tabla-container");
      if (container && data.html) {
        container.innerHTML = data.html;
      }

      // 2. Actualizar selectores dinámicamente (Sincronización en cascada)
      // Esto permite que si filtras por un Autor, solo aparezcan sus Publicaciones 
      const recargarSelect = (id, valores) => {
        const el = document.getElementById(id);
        if (!el) return;

        const prev = el.value;
        const choicesInstance = window.choicesInstances?.[id];
        // Usamos la utilidad de normalización de fechas del backend si es necesario [cite: 7]
        const valoresNorm = (typeof normalizarValoresFiltro === 'function')
          ? normalizarValoresFiltro(valores, id === "selectFecha")
          : valores;

        if (choicesInstance) {
          const opciones = [{ value: "", label: "Todos", selected: prev === "" }].concat(
            valoresNorm.map((v) => ({ value: v, label: v, selected: v === prev }))
          );
          choicesInstance.clearStore();
          choicesInstance.setChoices(opciones, "value", "label", true);
        } else {
          el.innerHTML = '<option value="">Todos</option>';
          valoresNorm.forEach((v) => {
            const o = document.createElement("option");
            o.value = v; o.textContent = v;
            el.appendChild(o);
          });
          el.value = valoresNorm.includes(prev) ? prev : "";
        }
      };

      // Actualizamos cada filtro con los datos únicos devueltos por el servidor 
      recargarSelect("selectAutor", data.autores || []);
      recargarSelect("selectPublicacion", data.publicaciones || []);
      recargarSelect("selectFecha", data.fechas || []);
      recargarSelect("selectCiudad", data.ciudades || []);
      recargarSelect("selectPais", data.paises || []);
      recargarSelect("selectTemas", data.temas || []);

      // 3. Re-inicializar componentes de la interfaz tras la carga AJAX
      if (typeof initEditarNotas === 'function') initEditarNotas();
      if (typeof activarTooltipsAvanzados === 'function') activarTooltipsAvanzados();
      if (typeof actualizarBotonAccionesMasivas === 'function') actualizarBotonAccionesMasivas();
      initCheckboxes();

      // 4. Actualizar enlaces de edición con el parámetro 'next' para facilitar el retorno
      actualizarEnlacesEditar();

      // Re-aplicar visibilidad de columnas guardada en localStorage 
      if (typeof reapplyColumnVisibilityAfterAjax === 'function') {
        reapplyColumnVisibilityAfterAjax();
      }

      console.log("✅ Tabla y filtros sincronizados");
    })
    .catch((err) => {
      console.error("❌ Error al filtrar:", err);
    });
}

/**
 * Inicializa los checkboxes de la tabla y el selector "Seleccionar todos".
 */
function initCheckboxes() {
  const selectAll = document.getElementById("selectAll");
  const tablaCont = document.getElementById("tabla-container");

  if (tablaCont) {
    tablaCont.onchange = (e) => {
      if (e.target.classList.contains("registro-checkbox")) {
        if (typeof actualizarBotonAccionesMasivas === 'function') {
          actualizarBotonAccionesMasivas();
        }
        if (!e.target.checked && selectAll) selectAll.checked = false;
      }
    };
  }

  if (selectAll) {
    // Clonamos para limpiar eventos previos y evitar duplicados tras AJAX
    const nuevoSelectAll = selectAll.cloneNode(true);
    selectAll.parentNode.replaceChild(nuevoSelectAll, selectAll);

    nuevoSelectAll.addEventListener("change", (e) => {
      const estadoMaestro = e.target.checked;
      const checks = document.querySelectorAll(".registro-checkbox");
      checks.forEach((c) => (c.checked = estadoMaestro));
      if (typeof actualizarBotonAccionesMasivas === 'function') {
        actualizarBotonAccionesMasivas();
      }
    });
  }
}

/**
 * IMPORTANTE: Listener automático para filtros.
 * Busca todos los selectores e inputs del panel de filtros y les asigna el evento change.
 */
document.addEventListener('DOMContentLoaded', () => {
  const filtrosPanel = document.getElementById('filtros');
  if (filtrosPanel) {
    filtrosPanel.querySelectorAll('select, input').forEach(el => {
      el.addEventListener('change', () => filtrarAjax(1));
      // Para inputs de texto, permitimos filtrar al presionar Enter
      if (el.tagName === 'INPUT' && el.type === 'text') {
        el.addEventListener('keypress', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            filtrarAjax(1);
          }
        });
      }
    });
  }
});
// ----------------------
// 7) NOTAS EDITABLES
// ----------------------
function initEditarNotas() {
  document.querySelectorAll(".nota-editable").forEach((el) => {
    const nuevoEl = el.cloneNode(true);
    el.parentNode.replaceChild(nuevoEl, el);

    nuevoEl.addEventListener("blur", async () => {
      const id = nuevoEl.dataset.id;
      const nuevaNota = nuevoEl.textContent.trim();
      if (id) {
        await fetch(`/actualizar_nota/${id}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').getAttribute('content')
          },
          body: JSON.stringify({ nota: nuevaNota }),
        });
        nuevoEl.classList.add("nota-guardada");
        setTimeout(() => nuevoEl.classList.remove("nota-guardada"), 800);
      }
    });
  });
}

// ----------------------
// 8) INIT DOM
// ----------------------
// ----------------------
// 8.1) BOOTSTRAP TOOLTIPS INIT
// ----------------------
function initBootstrapTooltips() {
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 DOMContentLoaded - Iniciando tabla.js");

  // Inicializaciones base
  initEditarNotas();
  activarTooltipsAvanzados();
  ejecutarAccionesLote();
  initCheckboxes();
  initBootstrapTooltips();

  // Columnas visibles
  initColumnToggles();

  // Importador
  initImportador();

  // Inicializar Choices.js para filtros y configurar eventos
  initFilterChoices();

  // Botón aplicar eliminado: no existe en todas las vistas, se evita error de null

  // Buscar texto
  const busquedaInput = document.querySelector('input[name="busqueda"]');
  if (busquedaInput) {
    // Solo filtrar al pulsar Enter (ver bloque en list.html) o al pulsar el botón Aplicar
    // No hacer nada aquí para evitar filtrado automático y reseteos inesperados
  }

  // Borrar filtros
  const btnBorrarF = document.getElementById("borrarFiltros");
  if (btnBorrarF) {
    btnBorrarF.onclick = (e) => {
      e.preventDefault();
      resetearFiltros();
    };
  }

  // Los filtros avanzados ya están manejados por las funciones globales
  // sincronizarFiltrosConBackend(), actualizarSelectChoices(), etc.
});

// ----------------------
// EXPORTACIÓN CON FILTROS
// ----------------------
/**
 * Captura todos los filtros activos de la UI y redirige a la ruta de exportación
 * @param {string} formato - El formato de exportación deseado (csv, csv_sirio, etc.)
 */
function exportarConFiltros(formato) {
  const filtros = obtenerFiltrosActuales();
  const params = new URLSearchParams();

  params.append("formato", formato);

  if (filtros.autor) params.append("autor", filtros.autor);
  if (filtros.publicacion) params.append("publicacion", filtros.publicacion);
  if (filtros.ciudad) params.append("ciudad", filtros.ciudad);
  if (filtros.pais_publicacion) params.append("pais_publicacion", filtros.pais_publicacion);
  if (filtros.fecha_original) params.append("fecha_original", filtros.fecha_original);
  if (filtros.fecha_desde) params.append("fecha_desde", filtros.fecha_desde);
  if (filtros.fecha_hasta) params.append("fecha_hasta", filtros.fecha_hasta);
  if (filtros.temas) params.append("temas", filtros.temas);
  if (filtros.busqueda) params.append("busqueda", filtros.busqueda);
  if (filtros.incluido && filtros.incluido !== "todos") params.append("incluido", filtros.incluido);

  const url = `/exportar?${params.toString()}`;
  console.log("📥 Iniciando exportación con filtros:", url);
  window.location.href = url;
}

// Hacer la función accesible globalmente
window.exportarConFiltros = exportarConFiltros;

/**
 * Alterna el estado de inclusión (activado/pausado) de una noticia vía AJAX
 */
async function toggleStatusNoticia(id, btn) {
  if (!id) return;

  // Feedback visual inmediato
  const icon = btn.tagName === 'I' ? btn : btn.querySelector('i');
  const oldClass = icon.className;
  icon.className = 'fa-solid fa-spinner fa-spin';

  try {
    const response = await fetch(`/api/noticia/${id}/toggle_incluido`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value
      }
    });

    const data = await response.json();
    if (data.success) {
      // Cambiar icono y título del botón
      const isIncluido = data.incluido;

      // Actualizar la fila en la tabla
      const tr = document.querySelector(`tr[data-id="${id}"]`);
      if (tr) {
        tr.dataset.incluido = isIncluido ? 'si' : 'no';

        // 1. Actualizar la celda "Incl." si existe
        const tdIncl = tr.querySelector('td[data-col="incl"]');
        if (tdIncl) {
          tdIncl.innerHTML = isIncluido
            ? '<i class="fa-solid fa-circle-check text-success" title="Incluido" style="font-size: 1.1rem;"></i>'
            : '<i class="fa-solid fa-circle-xmark text-danger" title="No incluido" style="font-size: 1.1rem;"></i>';
        }

        // 2. Actualizar el botón de alternar en la columna de acciones
        const btnAccion = tr.querySelector('.btn-toggle-incluir');
        if (btnAccion) {
          btnAccion.title = isIncluido ? 'Pausar (Excluir del estudio)' : 'Activar (Incluir en estudio)';
          const iconAccion = btnAccion.querySelector('i');
          if (iconAccion) {
            iconAccion.className = isIncluido ? 'fa-solid fa-pause' : 'fa-solid fa-play';
          }
        }
      }

      console.log(`✅ Noticia ${id}: ${isIncluido ? 'ACTIVADA' : 'PAUSADA'}`);

    } else {
      alert('Error al cambiar el estado de la noticia.');
      icon.className = originalClass;
    }
  } catch (err) {
    console.error('Error toggleStatus:', err);
    alert('Error de conexión.');
    icon.className = originalClass;
  }
}

window.toggleStatusNoticia = toggleStatusNoticia;

/**
 * eliminarNoticiaIndividual: Confirma y elimina una noticia específica.
 */
function eliminarNoticiaIndividual(event, titulo) {
  if (event) event.preventDefault();
  const form = event.currentTarget.closest('form');
  if (!form) return;

  hesioxConfirm({
    title: '¿Eliminar noticia?',
    text: `Se eliminará "${titulo || 'esta noticia'}" permanentemente de la biblioteca.`,
    confirmText: 'ELIMINAR'
  }).then(confirmed => {
    if (confirmed) {
      form.submit();
    }
  });
}
window.eliminarNoticiaIndividual = eliminarNoticiaIndividual;
