import altair as alt
import pandas as pd
import json
from typing import List, Dict

class AnalisisInnovador:
    """Clase para generar visualizaciones avanzadas con Altair"""
    
    def __init__(self):
        pass

    def _determinar_granularidad(self, publicaciones, granularidad_manual=None):
        """Helper para determinar la escala temporal basada en el span de los datos"""
        from datetime import datetime
        if granularidad_manual:
            return granularidad_manual
            
        fechas_validas = []
        for pub in publicaciones:
            f = pub.get('fecha')
            if f and isinstance(f, str):
                try:
                    if '-' in f: fechas_validas.append(datetime.strptime(f[:10], '%Y-%m-%d'))
                    elif '/' in f: fechas_validas.append(datetime.strptime(f, '%d/%m/%Y'))
                except: continue

        if not fechas_validas:
            return 'anio'
            
        span_days = (max(fechas_validas) - min(fechas_validas)).days
        if span_days <= 62: return 'dia'
        elif span_days <= 365 * 3: return 'mes'
        return 'anio'

    def _formatear_periodo(self, fecha_cruda, granularidad):
        """Helper para formatear una fecha según la granularidad detectada"""
        import re
        from datetime import datetime
        if not fecha_cruda or not isinstance(fecha_cruda, str):
            return 'Desconocido'
            
        try:
            dt = None
            if '-' in fecha_cruda: dt = datetime.strptime(fecha_cruda[:10], '%Y-%m-%d')
            elif '/' in fecha_cruda: dt = datetime.strptime(fecha_cruda, '%d/%m/%Y')
            
            if dt:
                if granularidad == 'dia': return dt.strftime('%Y-%m-%d')
                elif granularidad == 'mes': return dt.strftime('%Y-%m')
                return dt.strftime('%Y')
        except:
            pass
            
        # Fallback a búsqueda de año
        match = re.search(r'\b(1[8-9]\d{2}|20\d{2})\b', fecha_cruda)
        return match.group(1) if match else 'Desconocido'

    def generar_dispersion_lexica(self, publicaciones: List[Dict], terminos: List[str] = None, theme: str = 'dark') -> str:
        """Genera un gráfico de dispersión léxica (Lexical Dispersion Plot)"""
        # Configuración de colores según tema
        is_light = theme == 'light'
        text_color = '#294a60' if is_light else '#ccc'
        accent_color = '#0056b3' if is_light else '#ff9800'
        grid_color = 'rgba(0,0,0,0.1)' if is_light else 'rgba(255,255,255,0.1)'
        
        if not terminos:
            terminos = ["libertad", "pueblo", "nación", "derecho", "justicia"]
            
        data = []
        # Ordenar por fecha o secuencia si es posible
        for i, pub in enumerate(publicaciones):
            texto = (pub.get('contenido', '') or pub.get('titulo', '')).lower()
            palabras = texto.split()
            for j, palabra in enumerate(palabras):
                # Limpiar palabra
                palabra_limpia = ''.join(e for e in palabra if e.isalnum())
                if palabra_limpia in terminos:
                    data.append({
                        'documento_idx': i,
                        'palabra_pos': j,
                        'termino': palabra_limpia,
                        'titulo': pub.get('titulo', 'Sin título')[:30] + "..."
                    })
        
        if not data:
            return None
            
        df = pd.DataFrame(data)
        
        chart = alt.Chart(df).mark_tick(
            thickness=2,
            size=20,
            opacity=0.7
        ).encode(
            x=alt.X('documento_idx:O', title='Secuencia de Documentos'),
            y=alt.Y('termino:N', title='Término'),
            color=alt.Color('termino:N', legend=None),
            tooltip=['titulo', 'palabra_pos']
        ).properties(
            width='container',
            height=300,
            title='Dispersión Léxica en el Corpus'
        ).configure_axis(
            labelColor=text_color,
            titleColor=accent_color,
            gridColor=grid_color
        ).configure_view(
            strokeOpacity=0
        ).configure_title(
            color=accent_color
        )
        
        return chart.to_json()

    def generar_arco_sentimiento(self, resultados_sentimiento: List[Dict], theme: str = 'dark') -> str:
        """Genera un arco narrativo de sentimiento suavizado"""
        if not resultados_sentimiento:
            return None
            
        # Configuración de colores según tema
        is_light = theme == 'light'
        text_color = '#294a60' if is_light else '#ccc'
        accent_color = '#0056b3' if is_light else '#ff9800'
        grid_color = 'rgba(0,0,0,0.1)' if is_light else 'rgba(255,255,255,0.1)'
        point_color = '#0056b3' if is_light else '#ffffff'
        
        df = pd.DataFrame(resultados_sentimiento)
        df['idx'] = range(len(df))
        
        # Línea base (puntos reales)
        base = alt.Chart(df).encode(
            x=alt.X('idx:Q', title='Secuencia Narrativa'),
            y=alt.Y('sentimiento:Q', title='Sentimiento', scale=alt.Scale(domain=[-1, 1])),
            tooltip=['titulo', 'sentimiento']
        )
        
        # Puntos reales
        points = base.mark_circle(
            color=point_color,
            opacity=0.4 if is_light else 0.3,
            size=60
        )
        
        # Línea (suavizada o directa según cantidad de puntos)
        if len(df) > 3:
            # Línea suavizada (LOESS)
            line = base.transform_loess('idx', 'sentimiento').mark_line(
                color=accent_color,
                size=4,
                interpolate='monotone'
            )
            chart_content = points + line
        else:
            # Si hay pocos puntos, dibujar una linea directa
            line = base.mark_line(
                color=accent_color,
                size=3,
                opacity=0.8
            )
            chart_content = points + line
            
        chart = chart_content.properties(
            width='container',
            height=350,
            title='Arco Narrativo (Flujo Emocional)'
        ).configure_axis(
            labelColor=text_color,
            titleColor=accent_color,
            grid=True,
            gridColor=grid_color,
            gridOpacity=0.4
        ).configure_title(
            color=accent_color
        )
        
        return chart.to_json()

    def generar_heatmap_estilistico(self, resultados_estilo: List[Dict], theme: str = 'dark') -> str:
        """Genera un heatmap comparativo de métricas estilométricas"""
        if not resultados_estilo:
            return None
            
        # Configuración de colores según tema
        is_light = theme == 'light'
        text_color = '#294a60' if is_light else '#ccc'
        accent_color = '#0056b3' if is_light else '#ff9800'
        
        # Escala de colores personalizada según pedido del usuario
        if is_light:
            # Blanco 0.0 a Azul Sirio (#0056b3)
            color_scale = alt.Scale(range=['#ffffff', '#0056b3'])
        else:
            # Blanco -> Naranjas -> Rojo
            color_scale = alt.Scale(range=['#ffffff', '#ff9800', '#d32f2f'])
            
        # Preparar datos para formato largo (melted)
        data = []
        metrics = [
            'diversidad_lexica', 
            'palabras_por_oracion', 
            'longitud_promedio_palabra',
            'densidad_puntuacion',
            'ratio_hapax',
            'ratio_pronombres'
        ]
        labels = {
            'diversidad_lexica': 'Div. Léxica',
            'palabras_por_oracion': 'Pal/Orac',
            'longitud_promedio_palabra': 'Long. Pal',
            'densidad_puntuacion': 'Puntuación',
            'ratio_hapax': 'Hapax Leg.',
            'ratio_pronombres': 'Pronombres'
        }
        
        # Normalizar métricas para el heatmap (0-1)
        df_raw = pd.DataFrame(resultados_estilo)
        for m in metrics:
            if m not in df_raw.columns:
                df_raw[m] = 0
            if df_raw[m].max() != df_raw[m].min():
                df_raw[f'{m}_norm'] = (df_raw[m] - df_raw[m].min()) / (df_raw[m].max() - df_raw[m].min())
            else:
                df_raw[f'{m}_norm'] = 0.5

        for _, row in df_raw.iterrows():
            for m in metrics:
                data.append({
                    'Doc': row['titulo'][:20] + "...",
                    'Metrica': labels[m],
                    'Valor': round(float(row[m]), 3),
                    'ValorNorm': row[f'{m}_norm']
                })
        
        df = pd.DataFrame(data)
        
        chart = alt.Chart(df).mark_rect().encode(
            x=alt.X('Metrica:N', 
                    sort=list(labels.values()), 
                    title=None,
                    axis=alt.Axis(
                        labelAngle=0,
                        labelFontSize=12,
                        labelFontWeight='bold',
                        labelPadding=10,
                        orient='top'
                    )),
            y=alt.Y('Doc:O', title=None),
            color=alt.Color('ValorNorm:Q', scale=color_scale, title='Intensidad'),
            tooltip=['Doc', 'Metrica', 'Valor']
        ).properties(
            width='container',
            height=alt.Step(25),
            title='Comparativa Estilística Multidimensional (Heatmap)'
        ).configure_axis(
            labelColor=text_color,
            titleColor=accent_color,
            grid=False
        ).configure_title(
            color=accent_color
        )
        
        return chart.to_json()

    def generar_emociones_plutchik(self, publicaciones: List[Dict], granularidad: str = None) -> Dict:
        """Genera el análisis de emociones basado en la rueda de Plutchik usando un Lexicón ligero en español"""
        import re
        from collections import defaultdict
        
        # Lexicón en español (raíces/stems simples) para las 8 emociones básicas de Plutchik
        lexicon = {
            'Ira': ['ira', 'enoj', 'enfad', 'furia', 'rabi', 'odi', 'violent', 'molest', 'grita', 'indign', 'rencor', 'hostil', 'agresiv'],
            'Miedo': ['mied', 'temor', 'terror', 'peligr', 'amenaz', 'horror', 'susto', 'asust', 'pánic', 'panic', 'alarm', 'angusti', 'ansiedad'],
            'Tristeza': ['trist', 'dolor', 'pena', 'luto', 'llor', 'lágrim', 'lagrim', 'sufr', 'desastre', 'depresi', 'melancol', 'lament'],
            'Asco': ['asco', 'repugn', 'suci', 'asqueros', 'repuls', 'horribl', 'desagrad', 'nause', 'rechaz', 'despreci'],
            'Sorpresa': ['sorpres', 'asombr', 'inesperad', 'milagr', 'repent', 'choqu', 'impact', 'maravill', 'desconcert', 'imprevist'],
            'Anticipación': ['esper', 'futur', 'plan', 'pronto', 'prepar', 'ansios', 'aguard', 'expectativ', 'ilusi', 'dese', 'anhel'],
            'Confianza': ['confian', 'segur', 'fiel', 'leal', 'amig', 'verdad', 'honest', 'promes', 'alianz', 'fuert', 'sincer', 'respald', 'apoy'],
            'Alegría': ['feliz', 'alegr', 'content', 'placer', 'disfrut', 'hermos', 'éxit', 'exit', 'amor', 'reir', 'paz', 'buen', 'goz', 'satisfac', 'entusiasm']
        }
        
        # Totales globales para radar (Araña)
        totales_globales = {emo: 0 for emo in lexicon.keys()}
        
        # Para timeline temporal
        datos_temporales = defaultdict(lambda: {emo: 0 for emo in lexicon.keys()})
        
        # 1. Determinar granularidad dinámica
        granularidad = self._determinar_granularidad(publicaciones, granularidad)
        
        for pub in publicaciones:
            texto = (pub.get('contenido', '') or pub.get('titulo', '')).lower()
            fecha_cruda = pub.get('fecha')
            
            # Agrupación temporal dinámica
            fecha_agrup = self._formatear_periodo(fecha_cruda, granularidad)
                
            # Tokenización muy básica para el análisis
            palabras = re.findall(r'\b[a-záéíóúñü]+\b', texto)
            
            for palabra in palabras:
                for emocion, stems in lexicon.items():
                    # Si alguna raíz está en la palabra
                    if any(stem in palabra for stem in stems):
                        totales_globales[emocion] += 1
                        datos_temporales[fecha_agrup][emocion] += 1
                        break # Solo contar una emoción por palabra
                        
        # Formatear radar
        labels_radar = list(lexicon.keys())
        values_radar = [totales_globales[l] for l in labels_radar]
        
        # Formatear timeline
        fechas_ordenadas = sorted([f for f in datos_temporales.keys() if f != 'Desconocida'])
        if not fechas_ordenadas and 'Desconocida' in datos_temporales:
            fechas_ordenadas = ['Desconocida']
            
        timeline = {'labels': fechas_ordenadas}
        for emo in lexicon.keys():
            timeline[emo] = [datos_temporales[f][emo] for f in fechas_ordenadas]
            
        return {
            'exito': True,
            'data': {
                'radar': {
                    'labels': labels_radar,
                    'values': values_radar
                },
                'timeline': timeline,
                'granularidad': granularidad
            }
        }

    def generar_analisis_semantico(self, publicaciones: List[Dict], custom_terms: List[str] = None, granularidad: str = None) -> Dict:
        """Analiza el cambio semántico diacrónico con granularidad dinámica (Día, Mes, Año)"""
        import re
        from collections import defaultdict
        import math
        from datetime import datetime
        
        # Stopwords básicas en español
        stopwords = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'e', 'o', 'u', 'pero', 'mas', 'sino',
            'de', 'a', 'en', 'con', 'por', 'para', 'como', 'entre', 'sobre', 'sin', 'bajo', 'entre', 'hacia',
            'hasta', 'ante', 'tras', 'durante', 'que', 'quien', 'cual', 'cuya', 'donde', 'cuando', 'si', 'no',
            'es', 'son', 'fue', 'fueron', 'era', 'eran', 'ha', 'han', 'había', 'habían', 'este', 'esta', 'estos',
            'estas', 'ese', 'esa', 'esos', 'esas', 'aquel', 'aquella', 'aquellos', 'aquellas', 'mi', 'tu', 'su',
            'nuestro', 'vuestro', 'sus', 'del', 'al', 'se', 'lo', 'le', 'les', 'me', 'te', 'nos', 'os', 'muy',
            'más', 'mas', 'poco', 'mucho', 'todo', 'cada', 'algun', 'ningun', 'otro', 'otra', 'otros', 'otras'
        }
        
        # 1. Determinar granularidad automáticamente basada en el span de los datos
        granularidad = self._determinar_granularidad(publicaciones, granularidad)

        frecuencias_por_periodo = defaultdict(lambda: defaultdict(int))
        total_palabras_por_periodo = defaultdict(int)
        
        # Limpieza de términos manuales
        manual_mode = False
        if custom_terms and isinstance(custom_terms, list) and len(custom_terms) > 0:
            manual_mode = True
            custom_terms = [t.lower().strip() for t in custom_terms if t.strip()]
        
        for pub in publicaciones:
            texto = (pub.get('contenido', '') or pub.get('titulo', '')).lower()
            fecha_cruda = pub.get('fecha')
            
            # Agrupación temporal dinámica
            periodo = self._formatear_periodo(fecha_cruda, granularidad)
            
            palabras = re.findall(r'\b[a-záéíóúñü]{3,}\b', texto) 
            
            for pal in palabras:
                if pal not in stopwords:
                    frecuencias_por_periodo[periodo][pal] += 1
                    total_palabras_por_periodo[periodo] += 1
        
        # Obtener todos los periodos
        periodos_ordenados = sorted([p for p in frecuencias_por_periodo.keys() if p != 'Desconocido'])
        if not periodos_ordenados: return {'exito': False, 'error': 'No hay datos temporales suficientes'}
        
        # Selección de vocabulario a analizar
        if manual_mode:
            vocabulario = set(custom_terms)
        else:
            vocabulario = set()
            for p in periodos_ordenados:
                vocabulario.update(frecuencias_por_periodo[p].keys())
            
        stats_palabras = {}
        for pal in vocabulario:
            serie = []
            presente_en_algun_lado = False
            for p in periodos_ordenados:
                freq_rel = (frecuencias_por_periodo[p][pal] / total_palabras_por_periodo[p]) * 1000 if total_palabras_por_periodo[p] > 0 else 0
                serie.append(freq_rel)
                if freq_rel > 0: presente_en_algun_lado = True
            
            if presente_en_algun_lado:
                frecuencia_total = sum(frecuencias_por_periodo[p][pal] for p in periodos_ordenados)
                media = sum(serie) / len(serie)
                varianza = sum((x - media)**2 for x in serie) / len(serie)
                stats_palabras[pal] = {
                    'serie': serie,
                    'varianza': varianza,
                    'total': frecuencia_total
                }
        
        # Seleccionar qué mostrar en el gráfico (Top 6)
        if manual_mode:
            top_desplazadas = []
            for pal in custom_terms:
                if pal in stats_palabras:
                    top_desplazadas.append((pal, stats_palabras[pal]))
                else:
                    top_desplazadas.append((pal, {'serie': [0]*len(periodos_ordenados), 'varianza': 0}))
            top_desplazadas = top_desplazadas[:6]
        else:
            # En modo auto, filtramos por frecuencia mínima para el top
            vocab_filtrado = {k: v for k, v in stats_palabras.items() if v['total'] > 5}
            top_desplazadas = sorted(vocab_filtrado.items(), key=lambda x: x[1]['varianza'], reverse=True)[:6]
        
        # Formatear datasets
        datasets = []
        colores = ['#ff9800', '#2196f3', '#4caf50', '#9c27b0', '#f44336', '#00bcd4']
        
        for i, (pal, info) in enumerate(top_desplazadas):
            datasets.append({
                'label': pal.capitalize(),
                'data': [round(v, 4) for v in info['serie']],
                'borderColor': colores[i % len(colores)],
                'fill': False,
                'tension': 0.4
            })
            
        # Lista lateral (siempre los de mayor varianza real en el corpus filtrado)
        top_sidebar = []
        for pal, info in sorted(stats_palabras.items(), key=lambda x: x[1]['varianza'], reverse=True)[:10]:
            top_sidebar.append({
                'term': pal.capitalize(),
                'shift': f"{round(info['varianza'], 2)}"
            })
            
        return {
            'exito': True,
            'data': {
                'labels': periodos_ordenados,
                'datasets': datasets,
                'top_displaced': top_sidebar,
                'granularidad': granularidad
            }
        }
    def generar_intertextualidad_real(self, publicaciones: List[Dict]) -> Dict:
        """Detecta recirculación de textos y temas mediante solapamiento léxico (Jaccard)"""
        import re
        from collections import defaultdict
        
        # Stopwords simplificadas para el análisis de red
        stopwords = {'este', 'esta', 'estos', 'estas', 'pero', 'como', 'entre', 'sobre', 'cuando', 'donde', 'quien', 'cual'}
        
        nodes = []
        doc_sets = {}
        
        # Limitar a 100 documentos para el grafo para evitar sobrecarga en el cliente
        subset = publicaciones[:100]
        
        for i, pub in enumerate(subset):
            texto = (pub.get('contenido', '') or pub.get('titulo', '')).lower()
            # Palabras significativas (5+ letras, excluyendo ruido común)
            palabras = set(re.findall(r'\b[a-záéíóúñü]{5,}\b', texto)) - stopwords
            doc_sets[i] = palabras
            
            nodes.append({
                'id': i,
                'label': (pub.get('publicacion', '') or 'Doc')[:12],
                'title': f"<strong>{pub.get('publicacion')}</strong><br/>{pub.get('titulo')}",
                'value': min(25, 5 + len(palabras) // 10), # Tamaño basado en riqueza léxica
                'color': '#ff9800' if i % 2 == 0 else '#2196f3'
            })
            
        edges = []
        # Comparación N x N
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                set1 = doc_sets[i]
                set2 = doc_sets[j]
                
                if not set1 or not set2: continue
                
                interseccion = set1.intersection(set2)
                union = set1.union(set2)
                jaccard = len(interseccion) / len(union)
                
                # Umbral de conexión: 12% de coincidencia léxica significativa
                if jaccard > 0.12:
                    edges.append({
                        'from': i,
                        'to': j,
                        'value': round(jaccard * 15, 2), # Grosor de la línea
                        'title': f'Similitud: {round(jaccard*100, 1)}% ({len(interseccion)} palabras compartidas)'
                    })
                    
        return {
            'exito': True,
            'data': {
                'nodes': nodes,
                'edges': edges
            }
        }

    def generar_analisis_sesgos(self, publicaciones: List[Dict]) -> Dict:
        """Detecta sesgos de género, geofocalización y enfoque discursivo mediante lexicones de raíces"""
        import re
        from collections import defaultdict
        
        # Lexicones de raíces (stems) para detectar tendencias discursivas
        lexicon = {
            'Masculino': ['hombre', 'señor', 'padre', 'hijo', 'autor', 'profesor', 'diputad', 'ministr', 'caballero', 'hermano'],
            'Femenino': ['mujer', 'señora', 'madre', 'hija', 'autora', 'profesora', 'diputada', 'ministra', 'dama', 'hermana'],
            'Localismo': ['nuestr', 'nación', 'nacion', 'provinc', 'pueblo', 'local', 'ciudad', 'patria', 'región', 'vecino'],
            'Globalismo': ['extranjer', 'europa', 'mundo', 'internacional', 'exterior', 'otros', 'lejano', 'remoto', 'global'],
            'Elites': ['gobiern', 'podero', 'noble', 'rico', 'autoridad', 'capital', 'jerarqu', 'elite', 'palacio', 'mando'],
            'Popular': ['pobre', 'obrero', 'masa', 'popular', 'trabajador', 'gente', 'humilde', 'vulg', 'barrio', 'taller']
        }
        
        conteo_global = {cat: 0 for cat in lexicon.keys()}
        total_tokens = 0
        
        for pub in publicaciones:
            texto = (pub.get('contenido', '') or pub.get('titulo', '')).lower()
            for cat, stems in lexicon.items():
                for stem in stems:
                    # Búsqueda de raíces
                    matches = len(re.findall(f'\\b{stem}', texto))
                    conteo_global[cat] += matches
                    total_tokens += matches
        
        # Preparar datos para Radar y Proporciones
        if total_tokens == 0: total_tokens = 1
        
        radar_labels = list(conteo_global.keys())
        radar_values = [conteo_global[k] for k in radar_labels]
        
        # Calcular balances por dimensiones
        balances = {
            'Genero': conteo_global['Masculino'] - conteo_global['Femenino'],
            'Alcance': conteo_global['Localismo'] - conteo_global['Globalismo'],
            'Clase': conteo_global['Elites'] - conteo_global['Popular']
        }
        
        return {
            'exito': True,
            'data': {
                'labels': radar_labels,
                'values': radar_values,
                'totals': {
                    'hits': total_tokens,
                    'docs': len(publicaciones)
                },
                'balances': balances
            }
        }

    def generar_streamgraph_tactico(self, data_evolucion: List[Dict], theme: str = 'dark') -> str:
        """Genera un Streamgraph de la evolución de tácticas dramáticas"""
        if not data_evolucion:
            return None
            
        is_light = theme == 'light'
        text_color = '#294a60' if is_light else '#ccc'
        
        df = pd.DataFrame(data_evolucion)
        
        chart = alt.Chart(df).mark_area(
            interpolate='monotone',
            fillOpacity=0.8
        ).encode(
            x=alt.X('acto:N', title='Progreso de la Obra (Actos/Escenas)', axis=alt.Axis(labelAngle=0, grid=True, gridDash=[3,3])),
            y=alt.Y('valor:Q', stack='center', axis=alt.Axis(labels=False, ticks=False, title=None, grid=True, gridDash=[2,2], gridOpacity=0.5)),
            color=alt.Color('tactica:N', 
                           scale=alt.Scale(scheme='spectral'),
                           legend=alt.Legend(title="Tácticas", orient='right', labelColor=text_color, titleColor=text_color)),
            tooltip=['acto', 'tactica', 'valor']
        ).properties(
            width='container',
            height=300,
            title='Evolución del Flujo Táctico (Streamgraph)'
        ).configure_title(
            color=text_color,
            fontSize=16,
            anchor='start'
        ).configure_view(
            strokeOpacity=0
        )
        
        return chart.to_json()
