import math
BARCELONA = (41.2463, 2.1313)
CABO_NAO = (38.7386, 0.2333)
IMPACT = (37.66250, -0.63634)
VELOCITY_KN = 14.89
distance_maneuver_nmi = VELOCITY_KN * (3.0 / 60.0)

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    d_lon = lon2 - lon1
    y = math.sin(d_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    bearing = math.atan2(y, x)
    return (math.degrees(bearing) + 360) % 360

def destination_point(lat, lon, bearing, distance_nmi):
    R = 3440.065
    lat1, lon1, brng = map(math.radians, [lat, lon, bearing])
    lat2 = math.asin(math.sin(lat1) * math.cos(distance_nmi/R) + math.cos(lat1) * math.sin(distance_nmi/R) * math.cos(brng))
    lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(distance_nmi/R) * math.cos(lat1), math.cos(distance_nmi/R) - math.sin(lat1) * math.sin(lat2))
    return math.degrees(lat2), math.degrees(lon2)

bearing_nao_impact = calculate_bearing(CABO_NAO[0], CABO_NAO[1], IMPACT[0], IMPACT[1])
bearing_back = (bearing_nao_impact + 180) % 360
maneuver_point = destination_point(IMPACT[0], IMPACT[1], bearing_back, distance_maneuver_nmi)
alt_bearing = (bearing_nao_impact - 11.25)
alt_end_point = destination_point(maneuver_point[0], maneuver_point[1], alt_bearing, distance_maneuver_nmi)

print(f"Barcelona: {BARCELONA[0]}, {BARCELONA[1]}")
print(f"Cabo Nao (Ajustado): {CABO_NAO[0]}, {CABO_NAO[1]}")
print(f"Punto Maniobra: {maneuver_point[0]}, {maneuver_point[1]}")
print(f"Impacto: {IMPACT[0]}, {IMPACT[1]}")
print(f"Ruta Alternativa Final: {alt_end_point[0]}, {alt_end_point[1]}")
