# 📸 Capturas de Pantalla - hesiOX

Esta carpeta contiene las capturas de pantalla del sistema que se muestran en la página de inicio (home).

## 🎯 Capturas Necesarias

Para que la galería del home se muestre correctamente, coloca las siguientes imágenes del proyecto **S.S. Sirio**:

### 1. **red-entidades.png**
- **Vista**: Página de Análisis → Red de Entidades (D3.js)
- **Contenido**: Grafo de entidades NLP mostrando nodos (PER, LOC, ORG) conectados
- **Colores**: Nodos verdes (PER), azules (LOC), rojos (ORG) con enlaces grises
- **Dimensiones recomendadas**: 800x600px (aspect ratio 4:3)
- **Tip**: Captura con zoom que muestre claramente la red de conexiones

### 2. **mapa-geografico.png**
- **Vista**: Página de Análisis → Mapa Geográfico (Leaflet)
- **Contenido**: Mapa interactivo con marcadores rojos de ubicaciones
- **Elementos**: Mapa base, marcadores clustered, popup de ejemplo
- **Dimensiones recomendadas**: 800x600px (aspect ratio 4:3)
- **Tip**: Captura con varios marcadores visibles y un popup abierto

### 3. **nube-palabras.png**
- **Vista**: Página de Análisis → Nube de Palabras
- **Contenido**: Wordcloud generada con términos del corpus (guerra, política, sociedad, etc.)
- **Estilo**: Palabras de diferentes tamaños según frecuencia, colores variados
- **Dimensiones recomendadas**: 800x600px (aspect ratio 4:3)
- **Tip**: Captura con fondo oscuro (#1e1e1e) para consistencia visual

### 4. **timeline.png**
- **Vista**: Página de Análisis → Línea Temporal
- **Contenido**: Timeline horizontal con eventos/artículos en orden cronológico
- **Elementos**: Eje temporal, puntos de eventos, tooltips con fechas
- **Dimensiones recomendadas**: 800x600px (aspect ratio 4:3)
- **Tip**: Captura mostrando rango temporal amplio (ej: 1900-1950)

## 📐 Especificaciones Técnicas

- **Formato**: PNG (con transparencia si es posible)
- **Resolución**: Mínimo 800x600px, máximo 1920x1440px
- **Peso**: Máximo 500KB por imagen (optimizar con TinyPNG o similar)
- **Aspecto**: 4:3 (horizontal) para uniformidad en la galería
- **Fondo**: Preferiblemente con el tema oscuro del sistema (#1e1e1e)

## 🛠️ Cómo Capturar

1. **Abre el proyecto S.S. Sirio** en tu navegador
2. **Activa el tema Tech** (para consistencia visual con hesiOX)
3. **Navega a cada vista** listada arriba
4. **Usa la herramienta de captura**:
   - **Windows**: Win + Shift + S (Snipping Tool)
   - **Mac**: Cmd + Shift + 4
   - **Chrome DevTools**: F12 → Console → `document.body.style.zoom = "0.75"` (si necesitas más contenido)
5. **Recorta** al tamaño exacto 800x600 o proporcional
6. **Optimiza** el peso de la imagen:
   - Usa [TinyPNG](https://tinypng.com/)
   - O con ImageMagick: `magick convert input.png -quality 85 output.png`
7. **Renombra** según el nombre exacto listado arriba
8. **Copia** las 4 imágenes a esta carpeta

## 🔄 Fallback Automático

Si las imágenes no están disponibles, el sistema muestra **placeholders SVG** automáticos con:
- Iconos representativos de cada visualización
- Colores consistentes con el tema
- Texto descriptivo ("Red de Entidades", "Mapa Geográfico", etc.)

Los placeholders se generan inline con `onerror` en las etiquetas `<img>`.

## ✅ Verificación

Para verificar que las imágenes se muestran correctamente:

1. Copia las 4 imágenes a esta carpeta
2. Reinicia el servidor Flask: `python app.py`
3. Abre [http://localhost:5000](http://localhost:5000)
4. Desplázate hasta la sección **"Galería de Capturas del Sistema"**
5. Verifica que:
   - ✅ Las 4 imágenes cargan sin errores
   - ✅ El hover funciona (zoom + brillo)
   - ✅ Los bordes de colores se muestran (amarillo, azul, verde, rojo)
   - ✅ Las etiquetas inferiores son legibles

## 📝 Notas

- Las imágenes son **opcionales**: El sistema funciona con placeholders si no están disponibles
- **Actualización futura**: Puedes cambiar las imágenes en cualquier momento sin modificar código
- **Capturas reales recomendadas**: Muestran el potencial del sistema con datos reales del proyecto Sirio (4000+ artículos)
- **Referencia en home**: La nota inferior menciona "proyecto S.S. Sirio - Más de 4000 artículos analizados"

---

**Última actualización**: 3 de diciembre de 2025  
**hesiOX v1.4.5**
