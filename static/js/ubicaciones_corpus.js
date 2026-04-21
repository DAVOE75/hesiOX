// Editar ubicación: muestra formulario simple en el modal
window.editarUbicacionCorpus = function(idx) {
  const ubic = window._ubicacionesCorpusData[idx];
  if (!ubic) return;
  const wrapper = document.getElementById('tabla-ubicaciones-corpus-wrapper');
  if (!wrapper) return;
  wrapper.innerHTML = `
    <form id='form-editar-ubicacion-corpus' class='mb-3'>
      <div class='mb-2'><label>Nombre</label><input type='text' class='form-control' name='nombre' value='${ubic.nombre || ''}'></div>
      <div class='mb-2'><label>Latitud</label><input type='number' step='any' class='form-control' name='lat' value='${ubic.lat || ''}'></div>
      <div class='mb-2'><label>Longitud</label><input type='number' step='any' class='form-control' name='lon' value='${ubic.lon || ''}'></div>
      <div class='mb-2'><label>Frecuencia</label><input type='number' class='form-control' name='frecuencia' value='${ubic.frecuencia || 1}'></div>
      <button type='submit' class='btn btn-primary me-2'>Guardar</button>
      <button type='button' class='btn btn-secondary' onclick='window.renderTablaUbicacionesCorpus()'>Cancelar</button>
    </form>
  `;
  document.getElementById('form-editar-ubicacion-corpus').onsubmit = function(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    // Actualiza localmente (no persiste en BD)
    window._ubicacionesCorpusData[idx] = {
      nombre: fd.get('nombre'),
      lat: parseFloat(fd.get('lat')),
      lon: parseFloat(fd.get('lon')),
      frecuencia: parseInt(fd.get('frecuencia'))
    };
    window.renderTablaUbicacionesCorpus();
  };
};
// Borrar ubicación: pide confirmación y elimina de la tabla local
window.borrarUbicacionCorpus = function(idx) {
  if (!window._ubicacionesCorpusData || !window._ubicacionesCorpusData[idx]) return;
  if (confirm('¿Seguro que quieres borrar esta ubicación?')) {
    window._ubicacionesCorpusData.splice(idx, 1);
    window.renderTablaUbicacionesCorpus();
  }
};
// JS para gestión de ubicaciones en el mapa corpus (listado, editar, crear, borrar)
// Este archivo se debe enlazar en mapa_corpus.html

// TODO: Implementar funciones similares a las de detalle_noticia.html para:
// - Listar ubicaciones (tabla)
// - Editar ubicaciones
// - Crear ubicaciones
// - Borrar ubicaciones
// - Sincronizar con la API existente

// Ejemplo de estructura básica (a completar):
window.renderTablaUbicacionesCorpus = function() {
  // Llama a la API corpus y muestra las ubicaciones en una tabla simple
  fetch('/api/cartografia_corpus')
    .then(resp => resp.json())
    .then(res => {
      const data = res.ciudades || [];
      let html = '';
      if (!Array.isArray(data) || data.length === 0) {
        html = '<div class="alert alert-warning">No hay ubicaciones encontradas.</div>';
      } else {
        html = `<table class="table table-sm table-dark table-bordered align-middle mb-0">
          <thead><tr><th>Nombre</th><th>Lat</th><th>Lon</th><th>Frecuencia</th><th>Acciones</th></tr></thead><tbody>`;
        data.forEach((ubic, idx) => {
          html += `<tr>
            <td>${ubic.nombre || ''}</td>
            <td>${ubic.lat != null ? ubic.lat.toFixed(5) : ''}</td>
            <td>${ubic.lon != null ? ubic.lon.toFixed(5) : ''}</td>
            <td>${ubic.frecuencia}</td>
            <td>
              <button class='btn btn-sm btn-warning me-1' onclick='editarUbicacionCorpus(${idx})'><i class="fa fa-edit"></i></button>
              <button class='btn btn-sm btn-danger' onclick='borrarUbicacionCorpus(${idx})'><i class="fa fa-trash"></i></button>
            </td>
          </tr>`;
        });
        html += '</tbody></table>';
        window._ubicacionesCorpusData = data;
      }
      var wrapper = document.getElementById('tabla-ubicaciones-corpus-wrapper');
      if (wrapper) wrapper.innerHTML = html;
    })
    .catch(err => {
      var wrapper = document.getElementById('tabla-ubicaciones-corpus-wrapper');
      if (wrapper) wrapper.innerHTML = '<div class="alert alert-danger">Error cargando ubicaciones.</div>';
    });
};

document.addEventListener('DOMContentLoaded', function() {
  // No crear botón flotante, solo usar el del filtro
  // Modal se sigue creando si no existe (por compatibilidad)
  if (!document.getElementById('modal-ubicaciones-corpus')) {
    const modal = document.createElement('div');
    modal.id = 'modal-ubicaciones-corpus';
    modal.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.7);z-index:2000;';
    modal.innerHTML = `
      <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:#222;padding:32px 24px 24px 24px;border-radius:12px;min-width:600px;max-width:90vw;max-height:90vh;overflow:auto;">
        <h4 class='mb-3 text-warning'><i class="fa-solid fa-table me-2"></i>Gestión de ubicaciones del corpus</h4>
        <div id="tabla-ubicaciones-corpus-wrapper"></div>
        <button class="btn btn-secondary mt-3" onclick="document.getElementById('modal-ubicaciones-corpus').style.display='none'">Cerrar</button>
      </div>
    `;
    document.body.appendChild(modal);
  }
});
