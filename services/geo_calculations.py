"""
Servicio de cálculos geométricos para capas vectoriales GIS
Implementa algoritmos geodésicos para medir distancias y áreas
"""
import math


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia entre dos puntos usando la fórmula de Haversine
    Retorna distancia en kilómetros
    """
    R = 6371.0  # Radio de la Tierra en km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def calculate_linestring_length(coordinates):
    """
    Calcula la longitud total de una línea (LineString)
    coordinates: lista de [lon, lat] pares
    Retorna longitud en kilómetros
    """
    if len(coordinates) < 2:
        return 0.0
    
    total_length = 0.0
    for i in range(len(coordinates) - 1):
        lon1, lat1 = coordinates[i]
        lon2, lat2 = coordinates[i + 1]
        total_length += haversine_distance(lat1, lon1, lat2, lon2)
    
    return total_length


def calculate_polygon_area(coordinates):
    """
    Calcula el área de un polígono usando el algoritmo Shoelace
    coordinates: lista de [lon, lat] pares (primer anillo exterior)
    Retorna área aproximada en km²
    
    Nota: Esta es una aproximación planar. Para alta precisión geodésica
    se debería usar librerías como Shapely con proyecciones adecuadas.
    """
    if len(coordinates) < 3:
        return 0.0
    
    # Convertir a coordenadas proyectadas aproximadas (metros)
    # Usamos una proyección simple: 1° latitud ≈ 111 km, 1° longitud ≈ 111 km * cos(lat)
    
    # Calcular centro para la proyección
    avg_lat = sum(coord[1] for coord in coordinates) / len(coordinates)
    
    # Convertir coordenadas a metros
    coords_m = []
    for lon, lat in coordinates:
        x = lon * 111320.0 * math.cos(math.radians(avg_lat))  # metros
        y = lat * 111320.0  # metros
        coords_m.append((x, y))
    
    # Algoritmo Shoelace
    area_m2 = 0.0
    n = len(coords_m)
    for i in range(n):
        j = (i + 1) % n
        area_m2 += coords_m[i][0] * coords_m[j][1]
        area_m2 -= coords_m[j][0] * coords_m[i][1]
    
    area_m2 = abs(area_m2) / 2.0
    area_km2 = area_m2 / 1_000_000.0  # Convertir a km²
    
    return area_km2


def calculate_polygon_perimeter(coordinates):
    """
    Calcula el perímetro de un polígono
    coordinates: lista de [lon, lat] pares
    Retorna perímetro en kilómetros
    """
    if len(coordinates) < 2:
        return 0.0
    
    # Cerrar el polígono si no está cerrado
    coords = coordinates if coordinates[0] == coordinates[-1] else coordinates + [coordinates[0]]
    
    return calculate_linestring_length(coords)


def calculate_layer_metrics(features):
    """
    Calcula métricas agregadas para una colección de features
    Retorna diccionario con area_total y longitud_total
    """
    area_total = 0.0
    longitud_total = 0.0
    
    for feature in features:
        geom_type = feature.get('geometry', {}).get('type')
        coordinates = feature.get('geometry', {}).get('coordinates', [])
        
        if geom_type == 'LineString':
            longitud_total += calculate_linestring_length(coordinates)
        
        elif geom_type == 'MultiLineString':
            for line_coords in coordinates:
                longitud_total += calculate_linestring_length(line_coords)
        
        elif geom_type == 'Polygon':
            # Primer anillo es el exterior, los demás son huecos
            if coordinates:
                area_total += calculate_polygon_area(coordinates[0])
                longitud_total += calculate_polygon_perimeter(coordinates[0])
        
        elif geom_type == 'MultiPolygon':
            for polygon_coords in coordinates:
                if polygon_coords:
                    area_total += calculate_polygon_area(polygon_coords[0])
                    longitud_total += calculate_polygon_perimeter(polygon_coords[0])
    
    return {
        'area_total': round(area_total, 4) if area_total > 0 else None,
        'longitud_total': round(longitud_total, 4) if longitud_total > 0 else None
    }


def validate_geojson(geojson):
    """
    Valida que un objeto sea un GeoJSON válido
    Retorna (is_valid, error_message)
    """
    if not isinstance(geojson, dict):
        return False, "GeoJSON debe ser un objeto"
    
    if geojson.get('type') != 'FeatureCollection':
        return False, "El tipo debe ser 'FeatureCollection'"
    
    features = geojson.get('features')
    if not isinstance(features, list):
        return False, "'features' debe ser una lista"
    
    for i, feature in enumerate(features):
        if not isinstance(feature, dict):
            return False, f"Feature {i} no es un objeto"
        
        if feature.get('type') != 'Feature':
            return False, f"Feature {i} debe tener type='Feature'"
        
        geometry = feature.get('geometry')
        if not geometry or not isinstance(geometry, dict):
            return False, f"Feature {i} debe tener una geometría válida"
        
        geom_type = geometry.get('type')
        if geom_type not in ['Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString', 'MultiPolygon']:
            return False, f"Feature {i} tiene tipo de geometría inválido: {geom_type}"
        
        coordinates = geometry.get('coordinates')
        if coordinates is None:
            return False, f"Feature {i} debe tener coordenadas"
    
    return True, None


def simplify_linestring(coordinates, tolerance=0.0001):
    """
    Simplifica una línea usando el algoritmo Douglas-Peucker
    tolerance: tolerancia en grados (0.0001° ≈ 11 metros)
    Retorna coordenadas simplificadas
    """
    if len(coordinates) <= 2:
        return coordinates
    
    def perpendicular_distance(point, line_start, line_end):
        """Distancia perpendicular de un punto a una línea"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)
        
        return abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / math.sqrt(dx**2 + dy**2)
    
    # Encuentra el punto con mayor distancia
    max_dist = 0
    index = 0
    for i in range(1, len(coordinates) - 1):
        dist = perpendicular_distance(coordinates[i], coordinates[0], coordinates[-1])
        if dist > max_dist:
            max_dist = dist
            index = i
    
    # Si la max distancia es mayor que la tolerancia, recursivamente simplifica
    if max_dist > tolerance:
        # Simplifica recursivamente las dos mitades
        left = simplify_linestring(coordinates[:index + 1], tolerance)
        right = simplify_linestring(coordinates[index:], tolerance)
        
        # Combina resultados (sin duplicar el punto medio)
        return left[:-1] + right
    else:
        # Todos los puntos están cerca de la línea, solo mantén extremos
        return [coordinates[0], coordinates[-1]]
