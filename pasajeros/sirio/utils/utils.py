import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pyvis.network import Network
import folium
from folium.plugins import TimestampedGeoJson, HeatMap, MarkerCluster
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import logging
from datetime import datetime
import numpy as np
from branca.colormap import LinearColormap
import matplotlib.colors as mcolors
import streamlit as st

# 👉 Importa las coordenadas oficiales desde constantes.py
from sirio.constantes import COORDENADAS_CIUDADES

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================
# FUNCIONES GEOGRÁFICAS ACTUALIZADAS
# ==========================

def generar_mapa_coropletas(df, columna_valor="conteo", titulo="Distribución Geográfica"):
    """Genera un mapa coroplético por municipio/provincia/región"""
    try:
        if df.empty:
            return None
        
        agrupaciones = ['municipio', 'provincia', 'region', 'pais']
        agrupacion_seleccionada = None
        
        for agrupacion in agrupaciones:
            if agrupacion in df.columns and df[agrupacion].notna().any():
                agrupacion_seleccionada = agrupacion
                break
        
        if not agrupacion_seleccionada:
            return None
        
        if columna_valor == "conteo":
            datos_agrupados = df.groupby(agrupacion_seleccionada).size().reset_index(name='valor')
        else:
            datos_agrupados = df.groupby(agrupacion_seleccionada)[columna_valor].mean().reset_index()
        
        datos_agrupados.columns = [agrupacion_seleccionada, 'valor']
        
        datos_agrupados['lat'] = datos_agrupados[agrupacion_seleccionada].map(
            lambda x: COORDENADAS_CIUDADES.get(x, [40.0, -3.0])[0]
        )
        datos_agrupados['lon'] = datos_agrupados[agrupacion_seleccionada].map(
            lambda x: COORDENADAS_CIUDADES.get(x, [40.0, -3.0])[1]
        )
        
        datos_agrupados = datos_agrupados.dropna(subset=['lat', 'lon'])
        
        if datos_agrupados.empty:
            return None
        
        fig = px.scatter_mapbox(
            datos_agrupados,
            lat="lat",
            lon="lon",
            size="valor",
            color="valor",
            hover_name=agrupacion_seleccionada,
            hover_data={"valor": True},
            size_max=50,
            color_continuous_scale="Viridis",
            title=f"{titulo} - Por {agrupacion_seleccionada}",
            zoom=5,
            height=600
        )
        
        fig.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 50, "l": 0, "b": 0})
        return fig
        
    except Exception as e:
        logger.error(f"Error en generar_mapa_coropletas: {e}")
        return None

def generar_heatmap(df, columna_agrupacion='municipio'):
    """Genera un mapa de calor de densidad de pasajeros"""
    try:
        if df.empty or columna_agrupacion not in df.columns:
            return None
        
        datos_agrupados = df[columna_agrupacion].value_counts().reset_index()
        datos_agrupados.columns = [columna_agrupacion, 'count']
        
        datos_agrupados['coords'] = datos_agrupados[columna_agrupacion].map(
            lambda x: COORDENADAS_CIUDADES.get(x, [40.0, -3.0])
        )
        
        datos_agrupados[['lat', 'lon']] = pd.DataFrame(
            datos_agrupados['coords'].tolist(), index=datos_agrupados.index
        )
        
        datos_agrupados = datos_agrupados.dropna(subset=['lat', 'lon'])
        
        if datos_agrupados.empty:
            return None
        
        center_lat = datos_agrupados['lat'].mean()
        center_lon = datos_agrupados['lon'].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=5)
        
        heat_data = []
        for _, row in datos_agrupados.iterrows():
            for _ in range(min(row['count'], 10)):
                heat_data.append([row['lat'], row['lon']])
        
        if heat_data:
            HeatMap(heat_data, radius=15, blur=10, gradient={
                0.4: 'blue', 0.6: 'cyan', 0.7: 'lime', 0.8: 'yellow', 1.0: 'red'
            }).add_to(m)
        
        for _, row in datos_agrupados.iterrows():
            folium.CircleMarker(
                [row['lat'], row['lon']],
                radius=min(row['count'] * 2, 20),
                popup=f"{row[columna_agrupacion]}: {row['count']} pasajeros",
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.6
            ).add_to(m)
        
        return m
        
    except Exception as e:
        logger.error(f"Error en generar_heatmap: {e}")
        return None

def generar_mapa_cluster(df, columna_agrupacion='municipio'):
    """Genera un mapa con clusters de pasajeros"""
    try:
        if df.empty:
            return None
        
        coords_list = []
        for _, row in df.iterrows():
            if pd.notna(row.get(columna_agrupacion)):
                ubicacion = row[columna_agrupacion]
                if ubicacion in COORDENADAS_CIUDADES:
                    coords_list.append(COORDENADAS_CIUDADES[ubicacion])
        
        if not coords_list:
            return None
        
        center_lat = sum(coord[0] for coord in coords_list) / len(coords_list)
        center_lon = sum(coord[1] for coord in coords_list) / len(coords_list)
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=5)
        marker_cluster = MarkerCluster().add_to(m)
        
        for _, row in df.iterrows():
            if pd.notna(row.get(columna_agrupacion)):
                ubicacion = row[columna_agrupacion]
                if ubicacion in COORDENADAS_CIUDADES:
                    coords = COORDENADAS_CIUDADES[ubicacion]
                    
                    popup_info = f"""
                    <b>{row.get('nombre', '')} {row.get('apellidos', '')}</b><br>
                    Municipio: {row.get('municipio', 'N/A')}<br>
                    Edad: {row.get('edad', 'N/A')}<br>
                    Pasaje: {row.get('pasaje', 'N/A')}<br>
                    Estado: {row.get('estado', 'N/A')}
                    """
                    
                    folium.Marker(
                        coords,
                        popup=folium.Popup(popup_info, max_width=300),
                        icon=folium.Icon(color='blue', icon='user')
                    ).add_to(marker_cluster)
        
        return m
        
    except Exception as e:
        logger.error(f"Error en generar_mapa_cluster: {e}")
        return None

def generar_mapa_graduado(df, columna_valor='conteo', columna_agrupacion='municipio'):
    """Genera un mapa con círculos graduados según el valor"""
    try:
        if df.empty:
            return None
        
        if columna_valor == 'conteo':
            datos_agrupados = df.groupby(columna_agrupacion).size().reset_index(name='valor')
        elif columna_valor in df.columns:
            datos_agrupados = df.groupby(columna_agrupacion)[columna_valor].mean().reset_index()
        else:
            datos_agrupados = df.groupby(columna_agrupacion).size().reset_index(name='valor')
        
        datos_agrupados['coords'] = datos_agrupados[columna_agrupacion].map(
            lambda x: COORDENADAS_CIUDADES.get(x, [40.0, -3.0])
        )
        
        datos_agrupados[['lat', 'lon']] = pd.DataFrame(
            datos_agrupados['coords'].tolist(), index=datos_agrupados.index
        )
        datos_agrupados = datos_agrupados.dropna(subset=['lat', 'lon'])
        
        if datos_agrupados.empty:
            return None
        
        center_lat = datos_agrupados['lat'].mean()
        center_lon = datos_agrupados['lon'].mean()
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=5)
        
        max_val = datos_agrupados['valor'].max()
        min_val = datos_agrupados['valor'].min()
        
        if columna_valor == 'conteo':
            colormap = LinearColormap(
                ['green', 'yellow', 'red'],
                vmin=min_val, vmax=max_val,
                caption=f'Cantidad de pasajeros por {columna_agrupacion}'
            )
        else:
            colormap = LinearColormap(
                ['blue', 'purple', 'red'],
                vmin=min_val, vmax=max_val,
                caption=f'{columna_valor} promedio por {columna_agrupacion}'
            )
        
        for _, row in datos_agrupados.iterrows():
            ubicacion = row[columna_agrupacion]
            coords = [row['lat'], row['lon']]
            valor = row['valor']
            
            if columna_valor == 'conteo':
                radio = max(1000, min(50000, valor * 2000))
            else:
                radio = max(1000, min(50000, valor * 1000))
            
            color = colormap(valor)
            
            folium.Circle(
                coords,
                radius=radio,
                popup=f"<b>{ubicacion}</b><br>{columna_valor}: {valor:.2f if isinstance(valor, float) else valor}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.6,
                weight=2
            ).add_to(m)
        
        colormap.add_to(m)
        return m
        
    except Exception as e:
        logger.error(f"Error en generar_mapa_graduado: {e}")
        return None

def generar_mapa_rutas(df):
    """Genera un mapa con rutas de viaje entre ciudades - ACTUALIZADO"""
    try:
        if df.empty:
            return None
        
        coords_list = list(COORDENADAS_CIUDADES.values())
        center_lat = sum(coord[0] for coord in coords_list) / len(coords_list)
        center_lon = sum(coord[1] for coord in coords_list) / len(coords_list)
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=4)
        
        colores_rutas = {
            'embarque': 'green',
            'hospedaje': 'blue',
            'destino': 'red',
            'hundimiento': 'black'
        }
        
        rutas_dibujadas = set()
        
        for _, row in df.iterrows():
            puntos_ruta = []
            tipos_ruta = []
            
            # Embarque (nueva columna)
            if pd.notna(row.get('puerto_embarque')):
                puerto = row['puerto_embarque']
                if puerto in COORDENADAS_CIUDADES:
                    puntos_ruta.append(COORDENADAS_CIUDADES[puerto])
                    tipos_ruta.append('embarque')
            
            # Hospedaje en Cartagena (nueva columna)
            if pd.notna(row.get('hospedaje_cartagena')):
                hospedaje = row['hospedaje_cartagena']
                if hospedaje in COORDENADAS_CIUDADES:
                    puntos_ruta.append(COORDENADAS_CIUDADES[hospedaje])
                    tipos_ruta.append('hospedaje')
            
            # Destino final o hundimiento
            if row.get('estado') == 'superviviente' and pd.notna(row.get('ciudad_destino_final')):
                destino = row['ciudad_destino_final']
                if destino in COORDENADAS_CIUDADES:
                    puntos_ruta.append(COORDENADAS_CIUDADES[destino])
                    tipos_ruta.append('destino')
            elif pd.notna(row.get('fecha_hundimiento')):
                puntos_ruta.append(COORDENADAS_CIUDADES.get('Nápoles', [40.0, -3.0]))  # Aproximación
                tipos_ruta.append('hundimiento')
            
            if len(puntos_ruta) >= 2:
                for i in range(len(puntos_ruta) - 1):
                    ruta_key = f"{puntos_ruta[i]}-{puntos_ruta[i + 1]}"
                    if ruta_key not in rutas_dibujadas:
                        rutas_dibujadas.add(ruta_key)
                        
                        folium.PolyLine(
                            [puntos_ruta[i], puntos_ruta[i + 1]],
                            color=colores_rutas.get(tipos_ruta[i], 'blue'),
                            weight=3,
                            opacity=0.7,
                            popup=f"Ruta: {tipos_ruta[i]} → {tipos_ruta[i + 1]}"
                        ).add_to(m)
        
        return m
        
    except Exception as e:
        logger.error(f"Error en generar_mapa_rutas: {e}")
        return None

def generar_mapa_comparativo(df_filtrado, df_completo, columna_agrupacion='municipio'):
    """Genera un mapa comparativo entre datos filtrados y completos"""
    try:
        if df_completo.empty or df_filtrado.empty:
            return None
        
        total_por_ubicacion = df_completo[columna_agrupacion].value_counts()
        filtrado_por_ubicacion = df_filtrado[columna_agrupacion].value_counts()
        
        porcentajes = {}
        for ubicacion in total_por_ubicacion.index:
            if ubicacion in COORDENADAS_CIUDADES:
                total = total_por_ubicacion[ubicacion]
                filtrado = filtrado_por_ubicacion.get(ubicacion, 0)
                porcentaje = (filtrado / total) * 100 if total > 0 else 0
                porcentajes[ubicacion] = porcentaje
        
        if not porcentajes:
            return None
        
        coords_list = [COORDENADAS_CIUDADES[ubicacion] for ubicacion in porcentajes.keys()]
        center_lat = sum(coord[0] for coord in coords_list) / len(coords_list)
        center_lon = sum(coord[1] for coord in coords_list) / len(coords_list)
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=5)
        
        colormap = LinearColormap(
            ['red', 'yellow', 'green'],
            vmin=0, vmax=100,
            caption='Porcentaje de pasajeros incluidos en filtros'
        )
        
        for ubicacion, porcentaje in porcentajes.items():
            coords = COORDENADAS_CIUDADES[ubicacion]
            color = colormap(porcentaje)
            
            folium.CircleMarker(
                coords,
                radius=min(porcentaje / 2, 15),
                popup=f"<b>{ubicacion}</b><br>Total: {total_por_ubicacion[ubicacion]}<br>Filtrados: {filtrado_por_ubicacion.get(ubicacion, 0)}<br>Porcentaje: {porcentaje:.1f}%",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2
            ).add_to(m)
        
        m.add_child(colormap)
        return m
        
    except Exception as e:
        logger.error(f"Error en generar_mapa_comparativo: {e}")
        return None

# ==========================
# FUNCIONES DE VISUALIZACIÓN MEJORADAS
# ==========================

def procesar_presencia_listas(df, listas_columns):
    """
    Procesa la presencia en listas/documentos.
    - Considera 'X', 'x', '1' o cualquier valor no vacío como presente.
    - Retorna DataFrame con estadísticas de presencia y porcentaje.
    """
    try:
        resultados = []

        for lista_col in listas_columns:
            if lista_col in df.columns:
                # Normalizar valores para detectar presencia
                serie = df[lista_col].astype(str).str.strip().str.lower()
                presentes = serie.isin(["x", "1", "sí", "si"]).sum() + serie[~serie.isin(["nan", "", "none"])].count()

                total = len(df)
                ausentes = total - presentes
                porcentaje = (presentes / total) * 100 if total > 0 else 0

                resultados.append({
                    "Lista": lista_col,
                    "Presentes": presentes,
                    "Ausentes": ausentes,
                    "Total": total,
                    "Porcentaje Presente": round(porcentaje, 2)
                })

        return pd.DataFrame(resultados)

    except Exception as e:
        logger.error(f"Error en procesar_presencia_listas: {e}")
        return pd.DataFrame()

def generar_visualizaciones_geograficas(df, df_filtrado=None):
    """Genera múltiples visualizaciones geográficas"""
    visualizaciones = {}
    
    try:
        visualizaciones['heatmap'] = generar_heatmap(df, 'municipio')
        visualizaciones['cluster'] = generar_mapa_cluster(df, 'municipio')
        visualizaciones['graduado_conteo'] = generar_mapa_graduado(df, 'conteo', 'municipio')
        visualizaciones['rutas'] = generar_mapa_rutas(df)
        
        if df_filtrado is not None and not df_filtrado.empty:
            visualizaciones['comparativo'] = generar_mapa_comparativo(df_filtrado, df, 'municipio')
        
        visualizaciones['coropletas'] = generar_mapa_coropletas(df, 'conteo')
        
        return visualizaciones
        
    except Exception as e:
        logger.error(f"Error en generar_visualizaciones_geograficas: {e}")
        return {}

def mostrar_panel_geografico(df, df_filtrado=None):
    """Función principal para mostrar visualizaciones geográficas"""
    try:
        st.header("🗺️ Análisis Geográfico con Gradientes de Color")
        
        visualizaciones = generar_visualizaciones_geograficas(df, df_filtrado)
        
        if not visualizaciones:
            st.warning("No se pudieron generar las visualizaciones geográficas")
            return
        
        if visualizaciones.get('coropletas'):
            st.subheader("📊 Mapa de Distribución por Municipio")
            st.plotly_chart(visualizaciones['coropletas'], use_container_width=True)
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "🔥 Mapa de Calor", "👥 Clusters", "📏 Círculos Graduados", "🔄 Comparativo"
        ])
        
        with tab1:
            if visualizaciones.get('heatmap'):
                st.components.v1.html(visualizaciones['heatmap']._repr_html_(), height=500)
        
        with tab2:
            if visualizaciones.get('cluster'):
                st.components.v1.html(visualizaciones['cluster']._repr_html_(), height=500)
        
        with tab3:
            if visualizaciones.get('graduado_conteo'):
                st.components.v1.html(visualizaciones['graduado_conteo']._repr_html_(), height=500)
        
        with tab4:
            if visualizaciones.get('comparativo'):
                st.components.v1.html(visualizaciones['comparativo']._repr_html_(), height=500)
        
        if visualizaciones.get('rutas'):
            st.subheader("🛣️ Rutas de Viaje")
            st.components.v1.html(visualizaciones['rutas']._repr_html_(), height=500)
        
    except Exception as e:
        st.error(f"Error mostrando panel geográfico: {e}")

# ==========================
# FUNCIONES ORIGINALES ACTUALIZADAS
# ==========================

def generar_timeline(df_pasajero):
    """Genera timeline ACTUALIZADO para nuevas columnas"""
    try:
        if df_pasajero.empty:
            return pd.DataFrame()
        
        trayectorias = []
        
        for _, row in df_pasajero.iterrows():
            nombre = f"{row.get('nombre', '')} {row.get('apellidos', '')}".strip()
            
            info_parts = []
            if pd.notna(row.get('edad')): 
                info_parts.append(f"Edad: {row.get('edad')}")
            if pd.notna(row.get('sexo')): 
                info_parts.append(f"Sexo: {row.get('sexo')}")
            if pd.notna(row.get('pasaje')): 
                info_parts.append(f"Pasaje: {row.get('pasaje')}")
            if pd.notna(row.get('municipio')): 
                info_parts.append(f"Municipio: {row.get('municipio')}")
            if pd.notna(row.get('puerto_embarque')): 
                info_parts.append(f"Puerto: {row.get('puerto_embarque')}")
            
            info = " | ".join(info_parts) if info_parts else "Sin información adicional"
            
            # Nueva lógica simplificada
            if pd.notna(row.get("puerto_embarque")):
                fecha_embarque = row.get("fecha_hundimiento")
                if pd.isna(fecha_embarque):
                    fecha_embarque = pd.Timestamp('1906-08-04')
                
                if pd.notna(row.get("fecha_llegada_cartagena")):
                    trayectorias.append({
                        "nombre": nombre, 
                        "inicio": fecha_embarque, 
                        "fin": row["fecha_llegada_cartagena"],
                        "ciudad": row.get("puerto_embarque", "Embarque"), 
                        "estado": "en viaje", 
                        "info": info
                    })
                    
                    fecha_fin_hospedaje = row.get("fecha_salida_cartagena", row["fecha_llegada_cartagena"])
                    if pd.isna(fecha_fin_hospedaje):
                        fecha_fin_hospedaje = row["fecha_llegada_cartagena"] + pd.Timedelta(days=1)
                    
                    trayectorias.append({
                        "nombre": nombre, 
                        "inicio": row["fecha_llegada_cartagena"],
                        "fin": fecha_fin_hospedaje,
                        "ciudad": row.get("hospedaje_cartagena", "Cartagena"),
                        "estado": "hospedaje", 
                        "info": info
                    })
                    
                    inicio_actual = fecha_fin_hospedaje
                else:
                    inicio_actual = fecha_embarque
                
                estado_final = row.get("estado", "desconocido")
                if estado_final == "superviviente":
                    fecha_final = row.get("fecha_destino_final")
                    ciudad_final = row.get("ciudad_destino_final", "Destino final")
                    estado_etiqueta = "destino"
                else:
                    fecha_final = row.get("fecha_hundimiento")
                    ciudad_final = "Lugar hundimiento"
                    estado_etiqueta = "hundimiento"
                
                if pd.notna(fecha_final):
                    trayectorias.append({
                        "nombre": nombre, 
                        "inicio": inicio_actual, 
                        "fin": fecha_final,
                        "ciudad": ciudad_final, 
                        "estado": estado_etiqueta, 
                        "info": info
                    })
        
        if trayectorias:
            df_trayectorias = pd.DataFrame(trayectorias)
            df_trayectorias = df_trayectorias.dropna(subset=['inicio', 'fin'])
            df_trayectorias = df_trayectorias.sort_values('inicio')
            
            for col in ['inicio', 'fin']:
                if col in df_trayectorias.columns:
                    df_trayectorias[col] = df_trayectorias[col].dt.tz_localize(None)
            
            return df_trayectorias
        else:
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error en generar_timeline: {e}")
        return pd.DataFrame()

def generar_grafo(df_pasajero):
    """Genera grafo ACTUALIZADO para nuevas columnas"""
    try:
        if df_pasajero.empty:
            net = Network(height="400px", width="100%", bgcolor="white", font_color="black")
            net.add_node("sin_datos", label="No hay datos disponibles", color="#ffcccc")
            return net
        
        net = Network(height="500px", width="100%", bgcolor="#f0f2f6", font_color="black")
        
        net.set_options("""
        {
            "physics": {
                "enabled": true,
                "stabilization": {"iterations": 100},
                "barnesHut": {
                    "gravitationalConstant": -8000,
                    "springConstant": 0.04,
                    "damping": 0.09
                }
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 200,
                "navigationButtons": true,
                "keyboard": true
            },
            "layout": {
                "improvedLayout": true
            }
        }
        """)
        
        # NUEVAS COLUMNAS
        ciudades = set()
        columnas_ciudades = ["puerto_embarque", "ciudad_destino_final", "hospedaje_cartagena", "ciudad_destino"]
        
        for col in columnas_ciudades:
            if col in df_pasajero.columns:
                ciudades_validas = df_pasajero[col].dropna().unique()
                ciudades.update(ciudades_validas)
        
        if "estado" in df_pasajero.columns:
            estados = df_pasajero["estado"].dropna().unique()
            if any(estado != "superviviente" for estado in estados):
                ciudades.add("Lugar hundimiento")
        
        colores_ciudades = {
            "puerto_embarque": "#1f77b4",
            "hospedaje_cartagena": "#2ca02c",
            "ciudad_destino_final": "#d62728",
            "ciudad_destino": "#9467bd",
            "Lugar hundimiento": "#7f7f7f"
        }
        
        for ciudad in ciudades:
            color = "#17becf"
            tamaño = 25
            
            for col, col_color in colores_ciudades.items():
                if col == "Lugar hundimiento" and ciudad == "Lugar hundimiento":
                    color = col_color
                    tamaño = 30
                    break
                elif col in df_pasajero.columns and ciudad in df_pasajero[col].values:
                    color = col_color
                    if col == "puerto_embarque":
                        tamaño = 30
                    break
            
            net.add_node(ciudad, label=ciudad, color=color, size=tamaño,
                        font={'size': 12, 'face': 'Arial'})
        
        for _, row in df_pasajero.iterrows():
            nombre = f"{row.get('nombre', '')} {row.get('apellidos', '')}".strip()
            
            tooltip_parts = [nombre]
            if pd.notna(row.get('edad')): 
                tooltip_parts.append(f"Edad: {row.get('edad')}")
            if pd.notna(row.get('pasaje')): 
                tooltip_parts.append(f"Pasaje: {row.get('pasaje')}")
            
            tooltip = " | ".join(tooltip_parts)
            
            secuencia_ciudades = []
            
            if pd.notna(row.get("puerto_embarque")):
                secuencia_ciudades.append({
                    "ciudad": row["puerto_embarque"],
                    "tipo": "embarque"
                })
            
            if pd.notna(row.get("hospedaje_cartagena")):
                secuencia_ciudades.append({
                    "ciudad": row["hospedaje_cartagena"],
                    "tipo": "hospedaje"
                })
            
            if row.get("estado") == "superviviente" and pd.notna(row.get("ciudad_destino_final")):
                secuencia_ciudades.append({
                    "ciudad": row["ciudad_destino_final"],
                    "tipo": "destino"
                })
            else:
                secuencia_ciudades.append({
                    "ciudad": "Lugar hundimiento",
                    "tipo": "hundimiento"
                })
            
            for i in range(len(secuencia_ciudades) - 1):
                origen = secuencia_ciudades[i]["ciudad"]
                destino = secuencia_ciudades[i + 1]["ciudad"]
                
                if origen in ciudades and destino in ciudades:
                    net.add_edge(origen, destino, title=tooltip, width=2,
                                color='#888888', arrows='to')
        
        return net
        
    except Exception as e:
        logger.error(f"Error en generar_grafo: {e}")
        net = Network(height="400px", width="100%", bgcolor="white", font_color="black")
        net.add_node("error", label=f"Error: {str(e)}", color="#ffcccc")
        return net

def generar_mapa(df_pasajero, coords):
    """Genera mapa animado ACTUALIZADO"""
    try:
        if df_pasajero.empty:
            m = folium.Map(location=[40.0, -3.0], zoom_start=4)
            folium.Marker(
                [40.0, -3.0],
                popup="No hay datos del pasajero",
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m)
            return m
        
        features = []
        
        for _, row in df_pasajero.iterrows():
            nombre = f"{row.get('nombre', '')} {row.get('apellidos', '')}".strip()
            
            info_parts = [f"<strong>{nombre}</strong>"]
            if pd.notna(row.get('edad')): 
                info_parts.append(f"Edad: {row.get('edad')}")
            if pd.notna(row.get('pasaje')): 
                info_parts.append(f"Pasaje: {row.get('pasaje')}")
            if pd.notna(row.get('municipio')): 
                info_parts.append(f"Municipio: {row.get('municipio')}")
            if pd.notna(row.get('estado')): 
                info_parts.append(f"Estado: {row.get('estado')}")
            
            info_base = "<br>".join(info_parts)
            
            eventos = []
            
            if pd.notna(row.get("puerto_embarque")) and pd.notna(row.get("fecha_hundimiento")):
                eventos.append({
                    "ciudad": row["puerto_embarque"],
                    "fecha": row["fecha_hundimiento"] - pd.Timedelta(days=1),
                    "tipo": "Embarque",
                    "color": "green"
                })
            
            if pd.notna(row.get("hospedaje_cartagena")) and pd.notna(row.get("fecha_llegada_cartagena")):
                eventos.append({
                    "ciudad": row["hospedaje_cartagena"],
                    "fecha": row["fecha_llegada_cartagena"],
                    "tipo": "Llegada Cartagena",
                    "color": "blue"
                })
            
            if pd.notna(row.get("fecha_salida_cartagena")):
                eventos.append({
                    "ciudad": row.get("hospedaje_cartagena", "Cartagena"),
                    "fecha": row["fecha_salida_cartagena"],
                    "tipo": "Salida Cartagena",
                    "color": "purple"
                })
            
            if row.get("estado") == "superviviente" and pd.notna(row.get("ciudad_destino_final")) and pd.notna(row.get("fecha_destino_final")):
                eventos.append({
                    "ciudad": row["ciudad_destino_final"],
                    "fecha": row["fecha_destino_final"],
                    "tipo": "Destino Final",
                    "color": "red"
                })
            elif pd.notna(row.get("fecha_hundimiento")):
                eventos.append({
                    "ciudad": "Nápoles",  # Aproximación
                    "fecha": row["fecha_hundimiento"],
                    "tipo": "Hundimiento",
                    "color": "black"
                })
            
            eventos.sort(key=lambda x: x["fecha"])
            
            for evento in eventos:
                ciudad = evento["ciudad"]
                if ciudad in coords:
                    popup_info = f"{info_base}<br><strong>{evento['tipo']}</strong><br>Fecha: {evento['fecha'].strftime('%d/%m/%Y')}"
                    
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point", 
                            "coordinates": [coords[ciudad][1], coords[ciudad][0]]
                        },
                        "properties": {
                            "time": evento["fecha"].strftime("%Y-%m-%d"),
                            "popup": popup_info,
                            "icon": "circle",
                            "iconstyle": {
                                "color": evento["color"],
                                "fillColor": evento["color"],
                                "radius": 10
                            },
                            "style": {
                                "color": evento["color"],
                                "fillOpacity": 0.8,
                                "weight": 2
                            }
                        }
                    })
        
        if not features:
            m = folium.Map(location=[40.0, -3.0], zoom_start=4)
            folium.Marker(
                [40.0, -3.0],
                popup="No hay coordenadas válidas para mostrar",
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m)
            return m
        
        coords_used = [coords[ciudad] for ciudad in coords if any(f['properties']['popup'].split('<br>')[0] in ciudad for f in features)]
        if not coords_used:
            coords_used = list(coords.values())
        
        center_lat = sum(coord[0] for coord in coords_used) / len(coords_used)
        center_lon = sum(coord[1] for coord in coords_used) / len(coords_used)
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=5, tiles='OpenStreetMap')
        
        geojson = {"type": "FeatureCollection", "features": features}
        
        TimestampedGeoJson(
            geojson,
            period="P30D",
            add_last_point=True,
            auto_play=True,
            loop=False,
            max_speed=1,
            loop_button=True,
            date_options="YYYY-MM-DD",
            time_slider_drag_update=True,
            duration="P1D"
        ).add_to(m)
        
        legend_html = '''
        <div style="position: fixed; top: 10px; left: 50px; width: 220px; height: 200px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px; border-radius: 5px;">
            <p style="margin:0; font-weight:bold;">🎯 Leyenda de Eventos</p>
            <hr style="margin:5px 0;">
            <p style="margin:2px 0;"><span style="color: green">●</span> Embarque</p>
            <p style="margin:2px 0;"><span style="color: blue">●</span> Cartagena</p>
            <p style="margin:2px 0;"><span style="color: purple">●</span> Salida Cartagena</p>
            <p style="margin:2px 0;"><span style="color: red">●</span> Destino Final</p>
            <p style="margin:2px 0;"><span style="color: black">●</span> Hundimiento</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        return m
        
    except Exception as e:
        logger.error(f"Error en generar_mapa: {e}")
        m = folium.Map(location=[40.0, -3.0], zoom_start=4)
        folium.Marker(
            [40.0, -3.0],
            popup=f"Error generando mapa: {str(e)}",
            icon=folium.Icon(color="red", icon="warning-sign")
        ).add_to(m)
        return m

# ==========================
# FUNCIONES AUXILIARES (se mantienen igual)
# ==========================

def html_a_png(html_file, output_png):
    """Convierte HTML a PNG"""
    try:
        if not os.path.exists(html_file):
            logger.error(f"Archivo HTML no encontrado: {html_file}")
            return False
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1200,800")
        options.add_argument("--force-device-scale-factor=1")
        options.add_argument("--disable-gpu")
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.warning(f"Webdriver-manager falló: {e}")
            try:
                driver = webdriver.Chrome(options=options)
            except Exception as e2:
                logger.error(f"No se pudo inicializar ChromeDriver: {e2}")
                return False
        
        try:
            html_path = f"file://{os.path.abspath(html_file)}"
            driver.get(html_path)
            time.sleep(5)
            driver.set_window_size(1200, 800)
            driver.save_screenshot(output_png)
            logger.info(f"Captura guardada en: {output_png}")
            
            if os.path.exists(output_png) and os.path.getsize(output_png) > 0:
                return True
            else:
                return False
            
        except Exception as e:
            logger.error(f"Error al tomar screenshot: {e}")
            return False
            
        finally:
            try:
                driver.quit()
            except:
                pass
            
    except Exception as e:
        logger.error(f"Error en html_a_png: {e}")
        return False

def generar_resumen_estadistico(df):
    """Genera resumen estadístico"""
    try:
        resumen = {}
        resumen['total_pasajeros'] = len(df)
        resumen['columnas_disponibles'] = list(df.columns)
        
        columnas_categoricas = ['municipio', 'provincia', 'region', 'pais', 'sexo', 
                               'pasaje', 'estado', 'hospedaje_cartagena', 'puerto_embarque']
        
        for col in columnas_categoricas:
            if col in df.columns:
                resumen[f'{col}_unicos'] = df[col].nunique()
                resumen[f'{col}_distribucion'] = df[col].value_counts().head(10).to_dict()
        
        if 'edad' in df.columns:
            edad_stats = df['edad'].describe()
            resumen['edad_promedio'] = edad_stats['mean']
            resumen['edad_minima'] = edad_stats['min']
            resumen['edad_maxima'] = edad_stats['max']
            resumen['edad_mediana'] = edad_stats['50%']
        
        fechas_columns = ['fecha_hundimiento', 'fecha_destino_final', 'fecha_llegada_cartagena', 'fecha_salida_cartagena']
        
        for fecha_col in fechas_columns:
            if fecha_col in df.columns:
                fechas_validas = df[fecha_col].dropna()
                if len(fechas_validas) > 0:
                    resumen[f'{fecha_col}_primera'] = fechas_validas.min().strftime('%Y-%m-%d')
                    resumen[f'{fecha_col}_ultima'] = fechas_validas.max().strftime('%Y-%m-%d')
        
        return resumen
        
    except Exception as e:
        logger.error(f"Error en generar_resumen_estadistico: {e}")
        return {}

def validar_datos_pasajero(df_pasajero):
    """Valida datos del pasajero"""
    try:
        if df_pasajero.empty:
            return {"estado": "vacio", "errores": ["No hay datos del pasajero"]}
        
        pasajero = df_pasajero.iloc[0]
        errores = []
        advertencias = []
        
        if pd.isna(pasajero.get('nombre')) or pd.isna(pasajero.get('apellidos')):
            errores.append("Faltan nombre o apellidos")
        
        fechas = []
        if pd.notna(pasajero.get('fecha_hundimiento')):
            fechas.append(('Hundimiento', pasajero['fecha_hundimiento']))
        if pd.notna(pasajero.get('fecha_llegada_cartagena')):
            fechas.append(('Llegada Cartagena', pasajero['fecha_llegada_cartagena']))
        if pd.notna(pasajero.get('fecha_salida_cartagena')):
            fechas.append(('Salida Cartagena', pasajero['fecha_salida_cartagena']))
        if pd.notna(pasajero.get('fecha_destino_final')):
            fechas.append(('Destino Final', pasajero['fecha_destino_final']))
        
        fechas_ordenadas = sorted(fechas, key=lambda x: x[1])
        for i in range(len(fechas_ordenadas) - 1):
            if fechas_ordenadas[i][1] > fechas_ordenadas[i + 1][1]:
                advertencias.append(f"Posible incoherencia temporal: {fechas_ordenadas[i][0]} después de {fechas_ordenadas[i + 1][0]}")
        
        estado = pasajero.get('estado')
        if estado == "superviviente" and pd.notna(pasajero.get('fecha_hundimiento')):
            advertencias.append("Pasajero marcado como superviviente pero tiene fecha de hundimiento")
        elif estado != "superviviente" and pd.notna(pasajero.get('fecha_destino_final')):
            advertencias.append("Pasajero no superviviente pero tiene fecha de destino final")
        
        return {
            "estado": "ok" if not errores else "con_errores",
            "errores": errores,
            "advertencias": advertencias,
            "total_validaciones": len(errores) + len(advertencias)
        }
        
    except Exception as e:
        logger.error(f"Error en validar_datos_pasajero: {e}")
        return {"estado": "error", "errores": [f"Error en validación: {str(e)}"]}